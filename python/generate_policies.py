"""
generate_policies.py — DimPolicy (8,000 policies). THE HUB of the star schema.

Grain: one row = one insurance policy (a single contract term).

Logic (see chat notes / documentation/01_data_architecture.md):
  - 1 base policy per customer + 3,000 extras distributed by segment propensity -> exactly 8,000.
  - Renewals = NEW PolicyID, same customer+product (yearly chains, capped at 4 = window years).
    Customers with more policies get a second product line (cross-sell).
  - PolicyStartDate >= max(window_start, RegistrationDate). Chains anchored to end near 2025.
  - PolicyStatus derived: renewed->Expired, last & ongoing->Active, last & ended->Expired,
    plus ~5% Cancelled early.
  - Branch = customer's governorate agency. CoverageType/PaymentFrequency vary by product.
  - Auto policies carry InsuredAssetID (seed for DimVehicle).

Output: data/cleaned/policies.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
import reference_data as ref
import utils

RNG_OFFSET = 3
AUTO_PID = "PRD001"
RENEW_CAP = 4           # max length of a yearly renewal chain (window is 4 years)
CANCEL_RATE = 0.05
TERM_DAYS = 365

SEGMENT_PROPENSITY = {
    "Standard": 1.0, "Silver": 1.5, "Gold": 2.5, "Platinum": 4.0,
    "PME": 2.0, "Grand Compte": 3.0,
}
PAYMENT_FREQ = (["Annuel", "Semestriel", "Trimestriel", "Mensuel"], [0.45, 0.20, 0.20, 0.15])
COVERAGE_BY_CATEGORY = {
    "Automobile":      (["Tiers", "Tiers Plus", "Tous Risques"], [0.35, 0.25, 0.40]),
    "Sante":           (["Base", "Etendue", "Premium"],          [0.45, 0.35, 0.20]),
    "Vie":             (["Temporaire", "Mixte", "Epargne"],      [0.40, 0.35, 0.25]),
    "Habitation":      (["Base", "Multirisque", "Premium"],      [0.45, 0.40, 0.15]),
    "Professionnelle": (["RC Pro", "Multirisque Pro", "Premium"],[0.40, 0.40, 0.20]),
}


def _make_lines(rng: np.random.Generator, m: int) -> list[int]:
    """Split m policies into product lines, each <= RENEW_CAP (a renewal chain length)."""
    if m <= 1:
        return [1]
    lines, remaining = [], m
    while remaining > 0 and len(lines) < 5:        # at most 5 lines (5 products)
        take = min(RENEW_CAP, remaining)
        if remaining > 1 and rng.random() < 0.35:  # sometimes start a new product line early
            take = int(rng.integers(1, min(RENEW_CAP, remaining) + 1))
        lines.append(take)
        remaining -= take
    if remaining > 0:                               # safety: fold leftovers into existing lines
        lines[-1] += remaining
    return lines


def _pick_product(rng: np.random.Generator, candidates: list[dict]) -> dict:
    w = np.array([p["policy_share"] for p in candidates], dtype=float)
    w /= w.sum()
    return candidates[int(rng.choice(len(candidates), p=w))]


def generate() -> pd.DataFrame:
    rng = utils.get_rng(RNG_OFFSET)
    win_start = pd.Timestamp(config.START_DATE)
    win_end = pd.Timestamp(config.END_DATE)

    customers = pd.read_csv(config.CLEANED_DIR / "customers.csv",
                            parse_dates=["RegistrationDate"])
    branches = pd.read_csv(config.CLEANED_DIR / "branches.csv")
    gov_to_branch = dict(zip(branches["Governorate"], branches["BranchID"]))

    products = ref.PRODUCTS
    prod_by_id = {p["ProductID"]: p for p in products}

    # --- policies per customer: 1 base + weighted extras = exactly N_POLICIES ---
    n = len(customers)
    extras = config.N_POLICIES - n
    prop = customers["CustomerSegment"].map(SEGMENT_PROPENSITY).to_numpy(dtype=float, copy=True)
    prop /= prop.sum()
    extra_idx = rng.choice(n, size=extras, p=prop)
    m_per_customer = np.ones(n, dtype=int) + np.bincount(extra_idx, minlength=n)

    rows = []
    pid_counter = 0
    veh_counter = 0

    cust = customers.to_dict("records")
    for i, c in enumerate(cust):
        m = int(m_per_customer[i])
        reg = pd.Timestamp(c["RegistrationDate"])
        earliest = max(win_start, reg)
        branch = gov_to_branch[c["Governorate"]]

        # primary product (Entreprise skews to Professionnelle)
        if c["CustomerType"] == "Entreprise" and rng.random() < 0.50:
            primary = prod_by_id["PRD005"]
        else:
            primary = _pick_product(rng, products)

        lines = _make_lines(rng, m)
        used_ids = {primary["ProductID"]}
        for li, length in enumerate(lines):
            if li == 0:
                product = primary
            else:
                remaining_products = [p for p in products if p["ProductID"] not in used_ids] or products
                product = _pick_product(rng, remaining_products)
                used_ids.add(product["ProductID"])

            cat = product["ProductCategory"]
            cov_vals, cov_p = COVERAGE_BY_CATEGORY[cat]
            coverage = str(rng.choice(cov_vals, p=cov_p))
            freq = str(rng.choice(PAYMENT_FREQ[0], p=PAYMENT_FREQ[1]))

            # one vehicle per auto line (shared across its renewals)
            asset_id = None
            if product["ProductID"] == AUTO_PID:
                veh_counter += 1
                asset_id = f"VEH{str(veh_counter).zfill(5)}"

            # can we fit a yearly renewal chain of this length inside the window?
            latest_start0 = win_end - pd.Timedelta(days=(length - 1) * TERM_DAYS)
            chain_ok = (length <= RENEW_CAP) and (latest_start0 >= earliest)

            if chain_ok:
                span = (latest_start0 - earliest).days
                start0 = earliest + pd.Timedelta(days=int(rng.integers(0, span + 1)))
                starts = [start0 + pd.Timedelta(days=k * TERM_DAYS) for k in range(length)]
                is_chain = True
            else:
                span = max((win_end - earliest).days, 0)
                starts = [earliest + pd.Timedelta(days=int(rng.integers(0, span + 1)))
                          for _ in range(length)]
                is_chain = False

            for k, start in enumerate(starts):
                pid_counter += 1
                policy_id = f"POL{str(pid_counter).zfill(5)}"
                is_last = (k == length - 1)

                if rng.random() < CANCEL_RATE:
                    end = start + pd.Timedelta(days=int(rng.integers(30, 335)))
                    status = "Cancelled"
                else:
                    end = start + pd.Timedelta(days=TERM_DAYS)
                    if is_chain and not is_last:
                        status = "Expired"          # superseded by its renewal
                    else:
                        status = "Active" if end > win_end else "Expired"

                rows.append({
                    "PolicyID": policy_id,
                    "CustomerID": c["CustomerID"],
                    "ProductID": product["ProductID"],
                    "BranchID": branch,
                    "PolicyStartDate": start.normalize(),
                    "PolicyEndDate": end.normalize(),
                    "CoverageType": coverage,
                    "PolicyStatus": status,
                    "PaymentFrequency": freq,
                    "InsuredAssetID": asset_id,
                })

    df = pd.DataFrame(rows)
    return df


def validate(df: pd.DataFrame) -> None:
    win_start = pd.Timestamp(config.START_DATE)
    win_end = pd.Timestamp(config.END_DATE)
    customers = pd.read_csv(config.CLEANED_DIR / "customers.csv", parse_dates=["RegistrationDate"])
    branches = pd.read_csv(config.CLEANED_DIR / "branches.csv")

    assert utils.pk_is_unique(df, "PolicyID"), "PolicyID not a valid PK"
    assert len(df) == config.N_POLICIES, f"expected {config.N_POLICIES}, got {len(df)}"
    # FK integrity
    assert df["CustomerID"].isin(set(customers["CustomerID"])).all(), "orphan CustomerID"
    assert df["ProductID"].isin({p["ProductID"] for p in ref.PRODUCTS}).all(), "bad ProductID"
    assert df["BranchID"].isin(set(branches["BranchID"])).all(), "bad BranchID"
    # coverage: all customers own >= 1 policy
    assert df["CustomerID"].nunique() == len(customers), "some customers have no policy"
    # date integrity
    assert (df["PolicyStartDate"] >= win_start).all(), "policy starts before window"
    assert (df["PolicyStartDate"] <= win_end).all(), "policy starts after window"
    assert (df["PolicyEndDate"] > df["PolicyStartDate"]).all(), "end not after start"
    reg = customers.set_index("CustomerID")["RegistrationDate"]
    assert (df["PolicyStartDate"].values >= reg.loc[df["CustomerID"]].values).all(), \
        "policy starts before customer registration"
    # status domain
    assert set(df["PolicyStatus"]).issubset({"Active", "Expired", "Cancelled"})
    # auto <-> vehicle link
    auto = df["ProductID"] == "PRD001"
    assert df.loc[auto, "InsuredAssetID"].notna().all(), "auto policy without vehicle"
    assert df.loc[~auto, "InsuredAssetID"].isna().all(), "non-auto policy with a vehicle"


def main() -> None:
    df = generate()
    validate(df)
    out = config.CLEANED_DIR / "policies.csv"
    df.to_csv(out, index=False, encoding=config.CSV_ENCODING)
    print(f"generate_policies: wrote {len(df)} policies -> {out}\n")

    prod_names = {p["ProductID"]: p["ProductName"] for p in ref.PRODUCTS}
    print("By product:")
    print((df["ProductID"].map(prod_names).value_counts(normalize=True) * 100).round(1).to_string())
    print("\nBy status:", df["PolicyStatus"].value_counts().to_dict())
    ppc = df.groupby("CustomerID").size()
    print(f"\nPolicies/customer: min={ppc.min()} mean={ppc.mean():.2f} max={ppc.max()} "
          f"| multi-policy customers={(ppc > 1).sum()}")
    print(f"Auto policies (with vehicle): {(df['ProductID'] == 'PRD001').sum()}")
    print("\nSample:")
    print(df.head(6).to_string(index=False))


if __name__ == "__main__":
    main()
