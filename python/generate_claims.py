"""
generate_claims.py — FactClaims (4,000 claims).

Grain: one row = one claim filed against a policy.

Logic (see chat notes / documentation/01_data_architecture.md):
  - Claim slots are drawn with replacement across policies, weighted by
    product claim_frequency x policy exposure (term overlap with the window).
    => Sante claims a lot, Vie rarely; a policy can be drawn >1 time (repeated claims).
  - ClaimDate falls inside the policy's covered period (within the window).
  - ClaimAmount is right-skewed within the product's severity_min/max (many small, few huge).
  - Role-playing dates: ApprovalDate = ClaimDate + 3..90d; ClosureDate after that.
    A decision that would land past the window stays Pending (null approval). Recent claims skew Pending.
  - Status in {Approved, Rejected, Pending}. Only Approved claims flow to payments next.
  - Auto claims carry the policy's VehicleID (InsuredAssetID).

Output: data/cleaned/claims.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
import reference_data as ref
import utils

RNG_OFFSET = 5
AMOUNT_SKEW = 3.0          # u**3 pushes most claims toward the low end
RECENT_DAYS = 90           # claims in the last 90 days of the window skew Pending

CLAIM_TYPES = {
    "Automobile":      ["Collision", "Vol", "Bris de glace", "Incendie", "Dommages tiers"],
    "Sante":           ["Hospitalisation", "Consultation", "Pharmacie", "Chirurgie", "Analyses"],
    "Vie":             ["Deces", "Invalidite", "Rachat"],
    "Habitation":      ["Degat des eaux", "Incendie", "Vol", "Bris", "Catastrophe naturelle"],
    "Professionnelle": ["RC professionnelle", "Dommages materiels", "Perte exploitation", "Litige"],
}


def generate() -> pd.DataFrame:
    rng = utils.get_rng(RNG_OFFSET)
    win_start = pd.Timestamp(config.START_DATE)
    win_end = pd.Timestamp(config.END_DATE)

    policies = pd.read_csv(config.CLEANED_DIR / "policies.csv",
                           parse_dates=["PolicyStartDate", "PolicyEndDate"])
    prod = {p["ProductID"]: p for p in ref.PRODUCTS}

    # Exposure (years) = overlap of the policy term with the data window.
    cov_lo = policies["PolicyStartDate"].clip(lower=win_start)
    cov_hi = policies["PolicyEndDate"].clip(upper=win_end)
    exposure = ((cov_hi - cov_lo).dt.days.clip(lower=0) / 365.0).clip(lower=0.05).to_numpy()
    freq = policies["ProductID"].map(lambda i: prod[i]["claim_frequency"]).to_numpy(float, copy=True)
    weight = freq * exposure
    weight = weight / weight.sum()

    # Draw exactly N_CLAIMS claim slots (a policy may be chosen multiple times).
    idx = rng.choice(len(policies), size=config.N_CLAIMS, p=weight)

    pid = policies["PolicyID"].to_numpy()
    prodid = policies["ProductID"].to_numpy()
    asset = policies["InsuredAssetID"].to_numpy()
    starts = policies["PolicyStartDate"].to_numpy("datetime64[D]")
    ends = policies["PolicyEndDate"].to_numpy("datetime64[D]")
    wstart = np.datetime64(win_start, "D")
    wend = np.datetime64(win_end, "D")

    rows = []
    for n, i in enumerate(idx):
        category = prod[prodid[i]]["ProductCategory"]
        # ClaimDate inside covered period within the window
        lo = max(starts[i], wstart)
        hi = min(ends[i], wend)
        span = int((hi - lo) / np.timedelta64(1, "D"))
        claim_date = pd.Timestamp(lo + np.timedelta64(int(rng.integers(0, span + 1)), "D"))

        ctype = str(rng.choice(CLAIM_TYPES[category]))

        # Right-skewed amount within the product's severity band
        smin = prod[prodid[i]]["severity_min"]
        smax = prod[prodid[i]]["severity_max"]
        amount = smin + (smax - smin) * (rng.random() ** AMOUNT_SKEW)
        amount = int(round(amount / 10.0) * 10)

        # Status: recent claims skew Pending
        recent = (win_end - claim_date).days < RECENT_DAYS
        if recent:
            status = str(rng.choice(["Approved", "Rejected", "Pending"], p=[0.25, 0.10, 0.65]))
        else:
            status = str(rng.choice(["Approved", "Rejected", "Pending"], p=[0.62, 0.15, 0.23]))

        approval_date = pd.NaT
        closure_date = pd.NaT
        if status in ("Approved", "Rejected"):
            delay = int(rng.integers(3, 91))
            ad = claim_date + pd.Timedelta(days=delay)
            if ad > win_end:
                status = "Pending"            # decision would fall outside the window
            else:
                approval_date = ad
                if status == "Rejected":
                    closure_date = ad          # closed at rejection
                else:  # Approved
                    cd = ad + pd.Timedelta(days=int(rng.integers(1, 61)))
                    closure_date = cd if cd <= win_end else pd.NaT  # else still being settled

        rows.append({
            "ClaimID": f"CLM{str(n + 1).zfill(5)}",
            "PolicyID": pid[i],
            "ClaimDate": claim_date.normalize(),
            "ClaimType": ctype,
            "ClaimAmount": amount,
            "ClaimStatus": status,
            "ApprovalDate": approval_date,
            "ClosureDate": closure_date,
            "ClaimDescription": f"{ctype} ({category})",
            "VehicleID": asset[i] if prodid[i] == "PRD001" else None,
        })

    df = pd.DataFrame(rows)
    for c in ("ClaimDate", "ApprovalDate", "ClosureDate"):
        df[c] = pd.to_datetime(df[c])
    return df


def validate(df: pd.DataFrame) -> None:
    win_start = pd.Timestamp(config.START_DATE)
    win_end = pd.Timestamp(config.END_DATE)
    policies = pd.read_csv(config.CLEANED_DIR / "policies.csv",
                           parse_dates=["PolicyStartDate", "PolicyEndDate"])
    pol = policies.set_index("PolicyID")

    assert utils.pk_is_unique(df, "ClaimID"), "ClaimID not a valid PK"
    assert len(df) == config.N_CLAIMS, f"expected {config.N_CLAIMS}, got {len(df)}"
    assert df["PolicyID"].isin(set(policies["PolicyID"])).all(), "orphan PolicyID"
    assert (df["ClaimAmount"] > 0).all(), "non-positive claim amount"
    assert df["ClaimDate"].between(win_start, win_end).all(), "claim date outside window"
    # claim inside the policy period
    s = pol.loc[df["PolicyID"], "PolicyStartDate"].to_numpy()
    e = pol.loc[df["PolicyID"], "PolicyEndDate"].to_numpy()
    cd = df["ClaimDate"].to_numpy()
    assert (cd >= s).all() and (cd <= e).all(), "claim date outside policy period"
    assert set(df["ClaimStatus"]).issubset({"Approved", "Rejected", "Pending"})
    # status <-> approval invariant
    pend = df["ClaimStatus"] == "Pending"
    assert df.loc[pend, "ApprovalDate"].isna().all(), "Pending claim has an ApprovalDate"
    assert df.loc[~pend, "ApprovalDate"].notna().all(), "decided claim missing ApprovalDate"
    # date ordering
    dec = df.dropna(subset=["ApprovalDate"])
    assert (dec["ApprovalDate"] >= dec["ClaimDate"]).all(), "approval before claim"
    clo = df.dropna(subset=["ClosureDate"])
    assert (clo["ClosureDate"] >= clo["ApprovalDate"]).all(), "closure before approval"
    # auto <-> vehicle link
    auto = df["PolicyID"].map(pol["ProductID"]) == "PRD001"
    assert df.loc[auto, "VehicleID"].notna().all(), "auto claim without vehicle"
    assert df.loc[~auto, "VehicleID"].isna().all(), "non-auto claim with a vehicle"


def main() -> None:
    df = generate()
    validate(df)
    out = config.CLEANED_DIR / "claims.csv"
    df.to_csv(out, index=False, encoding=config.CSV_ENCODING)
    print(f"generate_claims: wrote {len(df)} claims -> {out}\n")

    policies = pd.read_csv(config.CLEANED_DIR / "policies.csv")
    prod_names = {p["ProductID"]: p["ProductName"] for p in ref.PRODUCTS}
    by_prod = df["PolicyID"].map(policies.set_index("PolicyID")["ProductID"]).map(prod_names)
    print("Claims by product:")
    print(by_prod.value_counts().to_string())
    print("\nStatus:", df["ClaimStatus"].value_counts().to_dict())
    print(f"Total incurred (ClaimAmount): {df['ClaimAmount'].sum():,.0f} {config.CURRENCY}")
    print(f"Avg claim: {df['ClaimAmount'].mean():,.0f} | max: {df['ClaimAmount'].max():,.0f} {config.CURRENCY}")
    claims_per_policy = df.groupby("PolicyID").size()
    print(f"Policies with >=3 claims (risk candidates): {(claims_per_policy >= 3).sum()}")
    proc = (df["ClosureDate"] - df["ClaimDate"]).dt.days.dropna()
    print(f"Avg processing time (claim->closure): {proc.mean():.0f} days")
    print("\nSample:")
    print(df.head(6).to_string(index=False))


if __name__ == "__main__":
    main()
