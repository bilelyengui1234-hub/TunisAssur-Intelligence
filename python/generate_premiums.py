"""
generate_premiums.py — FactPremiums (one premium transaction per policy term).

Grain: one row = one premium transaction for a policy.
(We deliberately do NOT explode by PaymentFrequency — that would inflate premium totals.
 PaymentFrequency on the policy describes HOW it's collected, not how many fact rows exist.)

Supports the Written vs Collected distinction:
  - Written premium   = PremiumAmount (contracted).
  - Net premium       = PremiumAmount - DiscountAmount.
  - Collected premium = NetPremiumAmount where PaymentStatus == 'Paid' (derived downstream).

Output: data/cleaned/premiums.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
import reference_data as ref
import utils

RNG_OFFSET = 4

# Coverage-tier price multipliers (labels come from generate_policies.py).
COVERAGE_MULTIPLIER = {
    "Tiers": 1.0, "Tiers Plus": 1.3, "Tous Risques": 1.7,
    "Base": 1.0, "Etendue": 1.3, "Premium": 1.7,
    "Temporaire": 1.0, "Mixte": 1.4, "Epargne": 1.8,
    "Multirisque": 1.3,
    "RC Pro": 1.0, "Multirisque Pro": 1.4,
}
# Probability a customer of a given segment receives ANY discount.
SEGMENT_DISCOUNT_PROB = {
    "Standard": 0.30, "Silver": 0.40, "Gold": 0.60, "Platinum": 0.80,
    "PME": 0.40, "Grand Compte": 0.60,
}
PAYMENT_METHODS = (["Virement", "Carte", "Especes", "Cheque", "Prelevement"],
                   [0.30, 0.25, 0.15, 0.15, 0.15])


def _round5(x: np.ndarray) -> np.ndarray:
    return (np.round(x / 5.0) * 5).astype(int)


def generate() -> pd.DataFrame:
    rng = utils.get_rng(RNG_OFFSET)
    win_end = pd.Timestamp(config.END_DATE)

    policies = pd.read_csv(config.CLEANED_DIR / "policies.csv",
                           parse_dates=["PolicyStartDate", "PolicyEndDate"])
    customers = pd.read_csv(config.CLEANED_DIR / "customers.csv",
                            usecols=["CustomerID", "CustomerSegment"])
    policies = policies.merge(customers, on="CustomerID", how="left")

    n = len(policies)
    prod = {p["ProductID"]: p for p in ref.PRODUCTS}
    pmin = policies["ProductID"].map(lambda i: prod[i]["premium_min"]).to_numpy(float, copy=True)
    pmax = policies["ProductID"].map(lambda i: prod[i]["premium_max"]).to_numpy(float, copy=True)

    # Base premium within the product range, scaled by coverage tier.
    base = pmin + rng.random(n) * (pmax - pmin)
    factor = policies["CoverageType"].map(COVERAGE_MULTIPLIER).to_numpy(float, copy=True)
    premium = _round5(base * factor)

    # Discount tied to loyalty/segment.
    disc_prob = policies["CustomerSegment"].map(SEGMENT_DISCOUNT_PROB).to_numpy(float, copy=True)
    has_disc = rng.random(n) < disc_prob
    disc_pct = rng.choice([0.05, 0.10, 0.15], size=n, p=[0.5, 0.3, 0.2])
    discount = _round5(premium * disc_pct * has_disc)
    discount = np.minimum(discount, premium)              # never exceed premium
    net = premium - discount

    # TransactionDate at inception (start + 0..7 days), clamped to policy period & window.
    starts = policies["PolicyStartDate"]
    txn = starts + pd.to_timedelta(rng.integers(0, 8, size=n), unit="D")
    cap = policies["PolicyEndDate"].clip(upper=win_end)
    txn = pd.Series(np.minimum(txn.to_numpy("datetime64[ns]"),
                               cap.to_numpy("datetime64[ns]")))

    # PaymentStatus: Cancelled policies skew toward unpaid.
    cancelled = (policies["PolicyStatus"] == "Cancelled").to_numpy()
    status = np.empty(n, dtype=object)
    status[~cancelled] = rng.choice(["Paid", "Pending", "Late"],
                                    size=(~cancelled).sum(), p=[0.80, 0.12, 0.08])
    status[cancelled] = rng.choice(["Paid", "Pending", "Late"],
                                   size=cancelled.sum(), p=[0.40, 0.40, 0.20])

    method = rng.choice(PAYMENT_METHODS[0], size=n, p=PAYMENT_METHODS[1])

    df = pd.DataFrame({
        "PremiumID": [f"PRM{str(i + 1).zfill(5)}" for i in range(n)],
        "PolicyID": policies["PolicyID"].to_numpy(),
        "TransactionDate": pd.to_datetime(txn).dt.normalize(),
        "PremiumAmount": premium,
        "DiscountAmount": discount,
        "NetPremiumAmount": net,
        "PaymentStatus": status,
        "PaymentMethod": method,
    })
    return df


def validate(df: pd.DataFrame) -> None:
    win_start = pd.Timestamp(config.START_DATE)
    win_end = pd.Timestamp(config.END_DATE)
    policies = pd.read_csv(config.CLEANED_DIR / "policies.csv",
                           parse_dates=["PolicyStartDate", "PolicyEndDate"])
    pol = policies.set_index("PolicyID")

    assert utils.pk_is_unique(df, "PremiumID"), "PremiumID not a valid PK"
    assert len(df) == len(policies), "expected one premium per policy"
    assert df["PolicyID"].isin(set(policies["PolicyID"])).all(), "orphan PolicyID"
    assert (df["PremiumAmount"] > 0).all(), "non-positive premium"
    assert (df["DiscountAmount"] >= 0).all() and (df["DiscountAmount"] <= df["PremiumAmount"]).all()
    assert (df["NetPremiumAmount"] == df["PremiumAmount"] - df["DiscountAmount"]).all()
    assert df["TransactionDate"].between(win_start, win_end).all(), "txn date outside window"
    # txn within the policy's own period
    s = pol.loc[df["PolicyID"], "PolicyStartDate"].to_numpy()
    e = pol.loc[df["PolicyID"], "PolicyEndDate"].to_numpy()
    t = df["TransactionDate"].to_numpy()
    assert (t >= s).all() and (t <= e).all(), "txn date outside policy period"
    assert set(df["PaymentStatus"]).issubset({"Paid", "Pending", "Late"})


def main() -> None:
    df = generate()
    validate(df)
    out = config.CLEANED_DIR / "premiums.csv"
    df.to_csv(out, index=False, encoding=config.CSV_ENCODING)
    print(f"generate_premiums: wrote {len(df)} premiums -> {out}\n")

    written = df["PremiumAmount"].sum()
    net = df["NetPremiumAmount"].sum()
    collected = df.loc[df["PaymentStatus"] == "Paid", "NetPremiumAmount"].sum()
    print(f"Written premium   : {written:,.0f} {config.CURRENCY}")
    print(f"Net premium       : {net:,.0f} {config.CURRENCY} (discounts {written - net:,.0f})")
    print(f"Collected (Paid)  : {collected:,.0f} {config.CURRENCY}")
    print(f"Avg premium       : {df['PremiumAmount'].mean():,.0f} {config.CURRENCY}")
    print("\nPaymentStatus:", df["PaymentStatus"].value_counts().to_dict())
    print("PaymentMethod:", df["PaymentMethod"].value_counts().to_dict())
    print("\nSample:")
    print(df.head(6).to_string(index=False))


if __name__ == "__main__":
    main()
