"""
generate_payments.py — FactPayments (one row = one compensation payment).

Grain: one row = one payment disbursed against an APPROVED claim.
A claim may be settled in several payments (instalments), so payments > approved claims.

Settlement logic (ties to the claim's own lifecycle):
  - Claim with a ClosureDate  -> FULLY paid: sum(AmountPaid) == ClaimAmount.
  - Approved but not closed    -> PARTIALLY paid: sum(AmountPaid) < ClaimAmount
                                  (remainder = Outstanding Claims downstream).
  - PaymentDate >= ApprovalDate, within the window (and <= ClosureDate when settled).
  - Each payment carries PolicyID (fan-out-proof rollups; we NEVER active-join to FactClaims).

Output: data/cleaned/payments.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
import utils

RNG_OFFSET = 6
N_PAYMENTS_DIST = ([1, 2, 3], [0.65, 0.25, 0.10])
PARTIAL_FRACTION = (0.30, 0.85)      # of ClaimAmount when a claim is still being settled
METHODS = (["Virement", "Cheque", "Carte"], [0.70, 0.20, 0.10])
RECENT_PROCESSING_DAYS = 30          # payments in the last 30 days -> 'En cours'


def _round10(x: float) -> int:
    return int(round(x / 10.0) * 10)


def _split_amount(rng: np.random.Generator, total: int, n: int) -> list[int]:
    """Split `total` into n positive parts (multiples of 10), summing exactly to total."""
    if n == 1:
        return [total]
    w = rng.random(n)
    w = w / w.sum()
    parts = [_round10(total * wi) for wi in w[:-1]]
    parts.append(total - sum(parts))      # last absorbs the remainder (keeps exact sum)
    # guard against non-positive parts
    for i in range(len(parts)):
        if parts[i] <= 0:
            j = int(np.argmax(parts))
            parts[j] -= 10
            parts[i] = 10
    return parts


def generate() -> pd.DataFrame:
    rng = utils.get_rng(RNG_OFFSET)
    win_end = pd.Timestamp(config.END_DATE)

    claims = pd.read_csv(config.CLEANED_DIR / "claims.csv",
                         parse_dates=["ClaimDate", "ApprovalDate", "ClosureDate"])
    approved = claims[claims["ClaimStatus"] == "Approved"].reset_index(drop=True)

    rows = []
    pay_counter = 0
    for c in approved.to_dict("records"):
        approval = pd.Timestamp(c["ApprovalDate"])
        closure = c["ClosureDate"]
        settled = pd.notna(closure)
        claim_amount = int(c["ClaimAmount"])

        if settled:
            total = claim_amount
            bound = pd.Timestamp(closure)
        else:
            frac = rng.uniform(*PARTIAL_FRACTION)
            total = max(_round10(claim_amount * frac), 10)
            bound = win_end

        n = int(rng.choice(N_PAYMENTS_DIST[0], p=N_PAYMENTS_DIST[1]))
        amounts = _split_amount(rng, total, n)

        span = max((bound - approval).days, 0)
        offsets = sorted(int(rng.integers(0, span + 1)) for _ in range(n))

        for k in range(n):
            pay_counter += 1
            pdate = (approval + pd.Timedelta(days=offsets[k])).normalize()
            status = "En cours" if (win_end - pdate).days < RECENT_PROCESSING_DAYS else "Effectue"
            rows.append({
                "PaymentID": f"PAY{str(pay_counter).zfill(5)}",
                "ClaimID": c["ClaimID"],
                "PolicyID": c["PolicyID"],
                "PaymentDate": pdate,
                "AmountPaid": int(amounts[k]),
                "PaymentMethod": str(rng.choice(METHODS[0], p=METHODS[1])),
                "PaymentStatus": status,
            })

    df = pd.DataFrame(rows)
    df["PaymentDate"] = pd.to_datetime(df["PaymentDate"])
    return df


def validate(df: pd.DataFrame) -> None:
    win_start = pd.Timestamp(config.START_DATE)
    win_end = pd.Timestamp(config.END_DATE)
    claims = pd.read_csv(config.CLEANED_DIR / "claims.csv",
                         parse_dates=["ApprovalDate", "ClosureDate"])
    approved = claims[claims["ClaimStatus"] == "Approved"].set_index("ClaimID")

    assert utils.pk_is_unique(df, "PaymentID"), "PaymentID not a valid PK"
    # payments only against approved claims
    assert df["ClaimID"].isin(set(approved.index)).all(), "payment on a non-approved claim"
    # PolicyID consistent with the claim's policy
    assert (df["PolicyID"].to_numpy() ==
            approved.loc[df["ClaimID"], "PolicyID"].to_numpy()).all(), "payment PolicyID mismatch"
    assert (df["AmountPaid"] > 0).all(), "non-positive payment"

    # per-claim sum <= ClaimAmount; settled claims fully paid
    paid = df.groupby("ClaimID")["AmountPaid"].sum()
    ca = approved["ClaimAmount"]
    assert (paid <= ca.loc[paid.index] + 1e-6).all(), "overpayment beyond claim amount"
    settled_ids = approved.index[approved["ClosureDate"].notna()]
    settled_paid = paid.reindex(settled_ids).dropna()
    assert (settled_paid == ca.loc[settled_paid.index]).all(), "settled claim not fully paid"

    # dates: within window and on/after approval (and <= closure when settled)
    ap = approved.loc[df["ClaimID"], "ApprovalDate"].to_numpy()
    assert (df["PaymentDate"].to_numpy() >= ap).all(), "payment before approval"
    assert df["PaymentDate"].between(win_start, win_end).all(), "payment outside window"
    assert set(df["PaymentStatus"]).issubset({"Effectue", "En cours"})


def main() -> None:
    df = generate()
    validate(df)
    out = config.CLEANED_DIR / "payments.csv"
    df.to_csv(out, index=False, encoding=config.CSV_ENCODING)
    print(f"generate_payments: wrote {len(df)} payments -> {out}\n")

    claims = pd.read_csv(config.CLEANED_DIR / "claims.csv")
    approved = claims[claims["ClaimStatus"] == "Approved"]
    incurred_appr = approved["ClaimAmount"].sum()
    total_paid = df["AmountPaid"].sum()
    paid_per_claim = df.groupby("ClaimID").size()
    fully = (claims.set_index("ClaimID")["ClosureDate"].notna()
             .reindex(approved["ClaimID"]).sum())

    print(f"Approved claims            : {len(approved):,}")
    print(f"Payments                   : {len(df):,} "
          f"(avg {paid_per_claim.mean():.2f} per claim, max {paid_per_claim.max()})")
    print(f"Incurred (approved claims) : {incurred_appr:,.0f} {config.CURRENCY}")
    print(f"Total claims paid          : {total_paid:,.0f} {config.CURRENCY}")
    print(f"Outstanding (approved)     : {incurred_appr - total_paid:,.0f} {config.CURRENCY}")
    print(f"Fully-settled claims       : {int(fully):,} | partially settled: {len(approved) - int(fully):,}")
    print("PaymentStatus:", df["PaymentStatus"].value_counts().to_dict())
    print("\nSample:")
    print(df.head(6).to_string(index=False))


if __name__ == "__main__":
    main()
