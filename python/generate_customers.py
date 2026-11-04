"""
generate_customers.py — DimCustomer (5,000 customers).

Grain: one row = one customer (an individual, or the manager representing a business).

Generation logic (see chat notes / documentation):
  - Governorate drawn by PopulationWeight  -> realistic geographic concentration.
  - Gender ~50/50; FirstName drawn from the MATCHING gender pool (no mismatches).
  - Age ~ clipped Normal(42, 13) in [18, 80]; BirthDate derived from Age.
  - RegistrationDate in [max(2019-01-01, 18th birthday), END_DATE]  -> temporally valid.
  - CustomerType: Particulier 85% / Entreprise 15%.
  - CustomerSegment: value tier by type.

Output: data/cleaned/customers.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
import reference_data as ref
import utils

RNG_OFFSET = 2  # independent substream for customers

SEGMENTS = {
    "Particulier": (["Standard", "Silver", "Gold", "Platinum"], [0.60, 0.25, 0.12, 0.03]),
    "Entreprise":  (["PME", "Grand Compte"],                     [0.75, 0.25]),
}


def generate() -> pd.DataFrame:
    rng = utils.get_rng(RNG_OFFSET)
    n = config.N_CUSTOMERS
    end = pd.Timestamp(config.END_DATE)

    # --- Identity keys ---
    customer_ids = [f"CUST{str(i + 1).zfill(5)}" for i in range(n)]

    # --- Gender then gender-consistent first name ---
    gender = rng.choice(["M", "F"], size=n, p=[0.50, 0.50])
    male_names = np.array(ref.FIRST_NAMES_MALE, dtype=object)
    female_names = np.array(ref.FIRST_NAMES_FEMALE, dtype=object)
    first_name = np.where(
        gender == "M",
        male_names[rng.integers(0, len(male_names), size=n)],
        female_names[rng.integers(0, len(female_names), size=n)],
    )
    last_name = np.array(ref.SURNAMES, dtype=object)[rng.integers(0, len(ref.SURNAMES), size=n)]

    # --- Geography by population weight ---
    govs = [g[0] for g in ref.GOVERNORATES]
    weights = np.array([g[2] for g in ref.GOVERNORATES], dtype=float)
    governorate = utils.weighted_choice(rng, govs, weights, n)
    # City: uniform within the drawn governorate.
    city = np.array([rng.choice(ref.CITIES[g]) for g in governorate], dtype=object)

    # --- Age -> BirthDate ---
    age = np.clip(np.round(rng.normal(42, 13, size=n)), 18, 80).astype(int)
    # BirthDate = end_of_window - age years - random day offset within the year.
    birth = end - pd.to_timedelta(age * 365.25 + rng.integers(0, 365, size=n), unit="D")
    birth = pd.to_datetime(birth).normalize()
    # Recompute Age from BirthDate so the two columns are always consistent.
    age_consistent = ((end - birth).days / 365.25).astype(int)

    # --- Customer type & segment ---
    cust_type = rng.choice(["Particulier", "Entreprise"], size=n, p=[0.85, 0.15])
    segment = np.empty(n, dtype=object)
    for t, (tiers, probs) in SEGMENTS.items():
        mask = cust_type == t
        segment[mask] = rng.choice(tiers, size=mask.sum(), p=probs)

    # --- RegistrationDate: after 18th birthday AND within growth window ---
    eighteenth = birth + pd.DateOffset(years=18)
    window_start = pd.Timestamp("2019-01-01")
    reg_start = pd.Series(np.maximum(eighteenth.values, np.datetime64(window_start)))
    reg_date = utils.random_dates_between(rng, reg_start, pd.Series([end] * n))

    df = pd.DataFrame({
        "CustomerID": customer_ids,
        "FirstName": first_name,
        "LastName": last_name,
        "Gender": gender,
        "BirthDate": birth,
        "Age": age_consistent,
        "Governorate": governorate,
        "City": city,
        "CustomerType": cust_type,
        "RegistrationDate": pd.to_datetime(reg_date).dt.normalize(),
        "CustomerSegment": segment,
    })
    return df


def validate(df: pd.DataFrame) -> None:
    end = pd.Timestamp(config.END_DATE)
    assert utils.pk_is_unique(df, "CustomerID"), "CustomerID not a valid PK"
    assert len(df) == config.N_CUSTOMERS, f"expected {config.N_CUSTOMERS}, got {len(df)}"
    assert df.notna().all().all(), "unexpected nulls in pristine customer data"
    assert df["Age"].between(18, 80).all(), "age outside [18, 80]"
    assert df["Gender"].isin(["M", "F"]).all()
    assert set(df["Governorate"]).issubset({g[0] for g in ref.GOVERNORATES})
    # Temporal integrity: registered as an adult, within the window.
    assert (df["RegistrationDate"] <= end).all(), "registration after window end"
    age_at_reg = (df["RegistrationDate"] - df["BirthDate"]).dt.days / 365.25
    assert (age_at_reg >= 18 - 1e-6).all(), "some customers registered before turning 18"


def main() -> None:
    df = generate()
    validate(df)
    out = config.CLEANED_DIR / "customers.csv"
    df.to_csv(out, index=False, encoding=config.CSV_ENCODING)
    print(f"generate_customers: wrote {len(df)} customers -> {out}\n")
    print("By region:")
    reg_map = {g[0]: g[1] for g in ref.GOVERNORATES}
    print(df["Governorate"].map(reg_map).value_counts().to_string())
    print("\nCustomerType:", df["CustomerType"].value_counts().to_dict())
    print("CustomerSegment:", df["CustomerSegment"].value_counts().to_dict())
    print("Gender:", df["Gender"].value_counts().to_dict())
    print(f"Age: min={df.Age.min()} mean={df.Age.mean():.1f} max={df.Age.max()}")
    print("\nSample:")
    print(df.head(6).to_string(index=False))


if __name__ == "__main__":
    main()
