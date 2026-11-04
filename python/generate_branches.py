"""
generate_branches.py — DimBranch (one agency per governorate).

Grain: one row = one TunisAssur agency.
All branches open BEFORE the data window (2005–2021) so every policy can be
attributed to an already-existing branch.

Output: data/cleaned/branches.csv
"""
from __future__ import annotations

import pandas as pd

import config
import reference_data as ref
import utils

RNG_OFFSET = 1  # independent substream for branches


def generate() -> pd.DataFrame:
    rng = utils.get_rng(RNG_OFFSET)

    govs = [g[0] for g in ref.GOVERNORATES]
    # Capital city of each governorate = first city in its list.
    capitals = {gov: ref.CITIES[gov][0] for gov in govs}

    branch_ids = [f"BR{str(i + 1).zfill(2)}" for i in range(len(govs))]
    names = [f"Agence {capitals[g]}" for g in govs]
    cities = [capitals[g] for g in govs]

    # Opening dates spread across 2005-01-01 .. 2021-12-31 (all pre-window).
    opening = utils.random_dates(rng, "2005-01-01", "2021-12-31", len(govs))

    df = pd.DataFrame({
        "BranchID": branch_ids,
        "BranchName": names,
        "Governorate": govs,
        "City": cities,
        "OpeningDate": pd.to_datetime(opening).normalize(),
    })
    return df


def validate(df: pd.DataFrame) -> None:
    assert utils.pk_is_unique(df, "BranchID"), "BranchID not a valid PK"
    assert len(df) == config.N_BRANCHES, f"expected {config.N_BRANCHES} branches, got {len(df)}"
    assert (df["OpeningDate"] <= pd.Timestamp(config.START_DATE)).all(), \
        "some branches open after the data window starts"
    assert set(df["Governorate"]).issubset({g[0] for g in ref.GOVERNORATES})


def main() -> None:
    df = generate()
    validate(df)
    out = config.CLEANED_DIR / "branches.csv"
    df.to_csv(out, index=False, encoding=config.CSV_ENCODING)
    print(f"generate_branches: wrote {len(df)} branches -> {out}")
    print(df.head().to_string(index=False))


if __name__ == "__main__":
    main()
