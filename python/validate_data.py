"""
validate_data.py — data integrity validator.

Phase 3 step 2. Runs a battery of checks against a data folder:
  - expected row counts            - primary-key uniqueness
  - foreign-key integrity          - date ranges within the window
  - non-negative / parseable amounts
  - claims <-> payments consistency (payments only on approved claims; paid <= claim amount)

Usage:
    python python/validate_data.py            # validates data/cleaned (asserts clean)
    python python/validate_data.py raw        # reports issues found in data/raw

cleaned/ MUST pass with zero issues (proves the ground truth is sound).
raw/ is expected to FAIL (that's the point — it proves the checks detect the injected issues).
"""
from __future__ import annotations

import sys

import pandas as pd

import config
import reference_data as ref

EXPECTED_ROWS = {
    "branches": 24, "customers": 5000, "policies": 8000,
    "premiums": 8000, "claims": 4000, "payments": 3210, "vehicles": 1989,
}
PK = {
    "branches": "BranchID", "customers": "CustomerID", "policies": "PolicyID",
    "premiums": "PremiumID", "claims": "ClaimID", "payments": "PaymentID", "vehicles": "VehicleID",
}
WIN_START = pd.Timestamp(config.START_DATE)
WIN_END = pd.Timestamp(config.END_DATE)


def _dates(s):
    return pd.to_datetime(s, errors="coerce", format="mixed", dayfirst=False)


def _nums(s):
    return pd.to_numeric(s, errors="coerce")


def validate(folder) -> list[str]:
    issues: list[str] = []
    d = {name: pd.read_csv(folder / f"{name}.csv", dtype=str, keep_default_na=False, na_values=[""])
         for name in EXPECTED_ROWS}

    # row counts & PK uniqueness
    for name, df in d.items():
        if len(df) != EXPECTED_ROWS[name]:
            issues.append(f"{name}: row count {len(df)} != expected {EXPECTED_ROWS[name]}")
        pk = PK[name]
        if not df[pk].is_unique:
            dups = len(df) - df[pk].nunique()
            issues.append(f"{name}: {dups} duplicate/blank {pk} values (PK not unique)")
        if df[pk].isna().any():
            issues.append(f"{name}: null {pk}")

    # foreign keys
    cust, pol = set(d["customers"]["CustomerID"]), set(d["policies"]["PolicyID"])
    prods = {p["ProductID"] for p in ref.PRODUCTS}
    br = set(d["branches"]["BranchID"])
    fk = [("policies", "CustomerID", cust), ("policies", "ProductID", prods),
          ("policies", "BranchID", br), ("premiums", "PolicyID", pol),
          ("claims", "PolicyID", pol), ("payments", "PolicyID", pol),
          ("payments", "ClaimID", set(d["claims"]["ClaimID"])),
          ("vehicles", "CustomerID", cust)]
    for name, col, valid in fk:
        bad = (~d[name][col].isin(valid) & d[name][col].notna()).sum()
        if bad:
            issues.append(f"{name}.{col}: {bad} values violate FK")

    # date ranges
    for name, col in [("premiums", "TransactionDate"), ("claims", "ClaimDate"),
                      ("payments", "PaymentDate")]:
        parsed = _dates(d[name][col])
        bad_fmt = parsed.isna().sum()
        if bad_fmt:
            issues.append(f"{name}.{col}: {bad_fmt} unparseable/invalid dates")
        out = ((parsed < WIN_START) | (parsed > WIN_END)).sum()
        if out:
            issues.append(f"{name}.{col}: {out} dates outside window")

    # non-negative amounts
    for name, col in [("premiums", "PremiumAmount"), ("claims", "ClaimAmount"),
                      ("payments", "AmountPaid")]:
        vals = _nums(d[name][col])
        bad = ((vals <= 0) | vals.isna()).sum()
        if bad:
            issues.append(f"{name}.{col}: {bad} non-positive/invalid amounts")

    # claims <-> payments consistency
    claims = d["claims"].copy()
    pay = d["payments"].copy()
    approved = set(claims.loc[claims["ClaimStatus"] == "Approved", "ClaimID"])
    non_appr = (~pay["ClaimID"].isin(approved)).sum()
    if non_appr:
        issues.append(f"payments: {non_appr} payments against non-approved claims")
    pay["amt"] = _nums(pay["AmountPaid"]).fillna(0)
    claims["amt"] = _nums(claims["ClaimAmount"]).fillna(0)
    paid = pay.groupby("ClaimID")["amt"].sum()
    ca = claims.groupby("ClaimID")["amt"].max()  # max() collapses duplicate ClaimIDs safely
    over = (paid > ca.reindex(paid.index).fillna(0) + 0.01).sum()
    if over:
        issues.append(f"payments: {over} claims paid beyond their claim amount")

    return issues


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "cleaned"
    folder = config.RAW_DIR if which == "raw" else config.CLEANED_DIR
    print(f"Validating data/{which} ...\n")
    issues = validate(folder)
    if not issues:
        print("PASS — 0 issues. Data is internally consistent.")
    else:
        print(f"{len(issues)} issue group(s) found:")
        for s in issues:
            print(f"  - {s}")
    if which == "cleaned":
        assert not issues, "cleaned/ must be 100% clean — ground truth is compromised!"
        print("\nAssertion OK: cleaned/ is validated ground truth.")


if __name__ == "__main__":
    main()
