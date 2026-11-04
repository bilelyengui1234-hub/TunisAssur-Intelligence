"""
generate_risk_indicators.py — FactClaimIndicators (rule-based risk SCREENING).

Grain: one row = one claim (1:1 with FactClaims). Deterministic (no randomness).

TRANSPARENT rule-based preliminary screening (brief §9). Points:
    R1  > 3 claims in trailing 12 months (same customer) ............ 30
    R2  claim amount > 3x its category average ..................... 30
    R3  another claim by the same customer within 30 days .......... 20
    R4  repeated claims on the SAME vehicle ........................ 20
RiskScore = min(100, sum).  Category: 0-29 Low · 30-59 Medium · 60-100 High.

ETHICS: this flags claims for HUMAN REVIEW. A high score is NOT a fraud determination.
See documentation/08_risk_scoring.md for limitations.

Output: data/cleaned/claim_indicators.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
import reference_data as ref

# rule points & thresholds
PTS_FREQUENCY, PTS_AMOUNT, PTS_RAPID, PTS_VEHICLE = 30, 30, 20, 20
FREQ_WINDOW_DAYS, FREQ_THRESHOLD = 365, 3
RAPID_DAYS = 30
AMOUNT_MULTIPLE = 3.0


def generate() -> pd.DataFrame:
    claims = pd.read_csv(config.CLEANED_DIR / "claims.csv", parse_dates=["ClaimDate"])
    policies = pd.read_csv(config.CLEANED_DIR / "policies.csv")[["PolicyID", "CustomerID", "ProductID"]]
    cat = {p["ProductID"]: p["ProductCategory"] for p in ref.PRODUCTS}

    claims = claims.merge(policies, on="PolicyID", how="left")
    claims["ProductCategory"] = claims["ProductID"].map(cat)

    # --- R2 input: deviation vs category average ---
    claims["CatAvg"] = claims.groupby("ProductCategory")["ClaimAmount"].transform("mean")
    claims["ClaimAmountDeviation"] = (claims["ClaimAmount"] / claims["CatAvg"]).round(2)

    # --- R4 input: repeated claims on the same vehicle ---
    veh_size = claims.groupby("VehicleID")["ClaimID"].transform("size")
    claims["RepeatedClaimIndicator"] = (
        claims["VehicleID"].notna() & (veh_size > 1)
    ).astype(int)

    # --- R1 & R3 inputs: trailing per-customer claim history ---
    claims = claims.sort_values(["CustomerID", "ClaimDate"]).reset_index(drop=True)
    prev_cnt = np.zeros(len(claims), dtype=int)       # prior claims within 12 months
    days_since = np.full(len(claims), np.nan)         # days since previous claim (any)
    for _, g in claims.groupby("CustomerID", sort=False):
        idx = g.index.to_numpy()
        dts = g["ClaimDate"].to_numpy("datetime64[D]")
        for j in range(len(idx)):
            if j == 0:
                continue
            cur = dts[j]
            earlier = dts[:j]
            within = earlier[(earlier >= cur - np.timedelta64(FREQ_WINDOW_DAYS, "D")) & (earlier < cur)]
            prev_cnt[idx[j]] = len(within)
            days_since[idx[j]] = (cur - earlier[-1]) / np.timedelta64(1, "D")
    claims["PreviousClaimsCount"] = prev_cnt
    claims["DaysSincePreviousClaim"] = days_since

    # --- scoring ---
    r1 = np.where(claims["PreviousClaimsCount"] + 1 > FREQ_THRESHOLD, PTS_FREQUENCY, 0)
    r2 = np.where(claims["ClaimAmountDeviation"] > AMOUNT_MULTIPLE, PTS_AMOUNT, 0)
    r3 = np.where(claims["DaysSincePreviousClaim"].le(RAPID_DAYS).fillna(False), PTS_RAPID, 0)
    r4 = np.where(claims["RepeatedClaimIndicator"] == 1, PTS_VEHICLE, 0)
    score = np.minimum(100, r1 + r2 + r3 + r4)
    claims["RiskScore"] = score
    claims["RiskCategory"] = pd.cut(score, bins=[-1, 29, 59, 100],
                                    labels=["Low", "Medium", "High"]).astype(str)

    out = claims.sort_values("ClaimID")[[
        "ClaimID", "PreviousClaimsCount", "DaysSincePreviousClaim",
        "ClaimAmountDeviation", "RepeatedClaimIndicator", "RiskScore", "RiskCategory",
    ]].copy()
    # DaysSincePreviousClaim: integer or blank (NULL in CSV/Postgres)
    out["DaysSincePreviousClaim"] = [
        int(x) if pd.notna(x) else "" for x in out["DaysSincePreviousClaim"]
    ]
    return out


def validate(df: pd.DataFrame) -> None:
    claims = pd.read_csv(config.CLEANED_DIR / "claims.csv")
    assert df["ClaimID"].is_unique and df["ClaimID"].notna().all(), "ClaimID not a valid PK"
    assert len(df) == len(claims), "FactClaimIndicators must be 1:1 with FactClaims"
    assert set(df["ClaimID"]) == set(claims["ClaimID"]), "ClaimID set mismatch"
    assert df["RiskScore"].between(0, 100).all(), "RiskScore out of range"
    assert set(df["RiskCategory"]).issubset({"Low", "Medium", "High"})


def main() -> None:
    df = generate()
    validate(df)
    out = config.CLEANED_DIR / "claim_indicators.csv"
    df.to_csv(out, index=False, encoding=config.CSV_ENCODING)
    print(f"generate_risk_indicators: wrote {len(df)} indicators -> {out}\n")

    dist = df["RiskCategory"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0).astype(int)
    flagged = (df["RiskScore"] >= 30).sum()
    print("Risk category distribution:")
    print(dist.to_string())
    print(f"\nFlagged for review (score >= 30): {flagged} ({flagged/len(df):.1%})")
    print(f"Average risk score: {df['RiskScore'].mean():.1f}")
    print(f"Repeated-vehicle claims: {int(df['RepeatedClaimIndicator'].sum())}")
    print("\nTop 8 highest-risk claims:")
    print(df.sort_values("RiskScore", ascending=False).head(8).to_string(index=False))


if __name__ == "__main__":
    main()
