"""
generate_vehicles.py — DimVehicle (one row per insured vehicle).

Grain: one row = one vehicle (a distinct InsuredAssetID carried by auto policies).

The vehicle set is NOT invented freely: it is exactly the set of InsuredAssetID values
present on PRD001 (Automobile) policies, each owned by that policy's customer. This keeps
DimVehicle in perfect referential agreement with the auto policies and claims.

Attributes reflect the real Tunisian car park (popular brands, fleet skewed older).

Output: data/cleaned/vehicles.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
import utils

RNG_OFFSET = 7
WINDOW_END_YEAR = int(config.END_DATE[:4])     # 2025 — reference year for age

# Brand -> list of (model, type); brands weighted by rough Tunisian popularity.
CATALOG = {
    "Volkswagen": [("Golf", "Berline"), ("Polo", "Citadine"), ("Passat", "Berline"),
                   ("Tiguan", "SUV"), ("Caddy", "Utilitaire")],
    "Peugeot":    [("208", "Citadine"), ("301", "Berline"), ("308", "Berline"),
                   ("2008", "SUV"), ("3008", "SUV"), ("Partner", "Utilitaire")],
    "Renault":    [("Clio", "Citadine"), ("Symbol", "Berline"), ("Megane", "Berline"),
                   ("Captur", "SUV"), ("Kangoo", "Utilitaire")],
    "Citroen":    [("C3", "Citadine"), ("C-Elysee", "Berline"), ("C4", "Berline"),
                   ("Berlingo", "Utilitaire")],
    "Fiat":       [("Tipo", "Berline"), ("500", "Citadine"), ("Panda", "Citadine"),
                   ("Doblo", "Utilitaire")],
    "Kia":        [("Picanto", "Citadine"), ("Rio", "Citadine"), ("Cerato", "Berline"),
                   ("Sportage", "SUV")],
    "Hyundai":    [("i10", "Citadine"), ("i20", "Citadine"), ("Accent", "Berline"),
                   ("Tucson", "SUV"), ("Creta", "SUV")],
    "Toyota":     [("Yaris", "Citadine"), ("Corolla", "Berline"), ("RAV4", "SUV"),
                   ("Hilux", "Utilitaire")],
    "Ford":       [("Fiesta", "Citadine"), ("Focus", "Berline"), ("Ranger", "Utilitaire")],
    "Seat":       [("Ibiza", "Citadine"), ("Leon", "Berline"), ("Arona", "SUV")],
    "Dacia":      [("Sandero", "Citadine"), ("Logan", "Berline"), ("Duster", "SUV"),
                   ("Dokker", "Utilitaire")],
    "Isuzu":      [("D-Max", "Utilitaire"), ("MU-X", "SUV")],
    "Suzuki":     [("Swift", "Citadine"), ("Vitara", "SUV")],
    "Chevrolet":  [("Spark", "Citadine"), ("Aveo", "Berline")],
}
BRAND_WEIGHTS = {
    "Volkswagen": 0.14, "Peugeot": 0.13, "Renault": 0.12, "Citroen": 0.08, "Fiat": 0.07,
    "Kia": 0.08, "Hyundai": 0.08, "Toyota": 0.06, "Ford": 0.05, "Seat": 0.05,
    "Dacia": 0.06, "Isuzu": 0.04, "Suzuki": 0.02, "Chevrolet": 0.02,
}


def generate() -> pd.DataFrame:
    rng = utils.get_rng(RNG_OFFSET)

    policies = pd.read_csv(config.CLEANED_DIR / "policies.csv")
    auto = policies[policies["ProductID"] == "PRD001"][["InsuredAssetID", "CustomerID"]]
    # one owner per vehicle (renewals of the same auto line share the InsuredAssetID)
    auto = auto.drop_duplicates("InsuredAssetID").dropna(subset=["InsuredAssetID"])
    auto = auto.sort_values("InsuredAssetID").reset_index(drop=True)
    n = len(auto)

    brands = list(BRAND_WEIGHTS)
    bw = np.array([BRAND_WEIGHTS[b] for b in brands], dtype=float)
    bw /= bw.sum()
    brand_idx = rng.choice(len(brands), size=n, p=bw)

    chosen_brand, chosen_model, chosen_type = [], [], []
    for bi in brand_idx:
        brand = brands[bi]
        model, vtype = CATALOG[brand][int(rng.integers(0, len(CATALOG[brand])))]
        chosen_brand.append(brand)
        chosen_model.append(model)
        chosen_type.append(vtype)

    # Age skewed older (mode ~8y), 0..27y -> ManufacturingYear 1998..2025
    age = np.round(rng.triangular(0, 8, 27, size=n)).astype(int)
    manuf_year = WINDOW_END_YEAR - age
    manuf_year = np.clip(manuf_year, 1998, WINDOW_END_YEAR)
    veh_age = WINDOW_END_YEAR - manuf_year
    reg_year = np.minimum(manuf_year + rng.integers(0, 2, size=n), WINDOW_END_YEAR)

    df = pd.DataFrame({
        "VehicleID": auto["InsuredAssetID"].to_numpy(),
        "CustomerID": auto["CustomerID"].to_numpy(),
        "VehicleBrand": chosen_brand,
        "VehicleModel": chosen_model,
        "VehicleType": chosen_type,
        "ManufacturingYear": manuf_year,
        "VehicleAge": veh_age,
        "RegistrationYear": reg_year,
    })
    return df


def validate(df: pd.DataFrame) -> None:
    policies = pd.read_csv(config.CLEANED_DIR / "policies.csv")
    customers = pd.read_csv(config.CLEANED_DIR / "customers.csv")
    auto_assets = set(policies.loc[policies["ProductID"] == "PRD001", "InsuredAssetID"].dropna())

    assert utils.pk_is_unique(df, "VehicleID"), "VehicleID not a valid PK"
    # vehicle set must EXACTLY match the auto policies' assets
    assert set(df["VehicleID"]) == auto_assets, "DimVehicle does not match auto policy assets"
    assert df["CustomerID"].isin(set(customers["CustomerID"])).all(), "orphan CustomerID"
    assert df[["VehicleBrand", "VehicleModel", "VehicleType"]].notna().all().all()
    assert df["ManufacturingYear"].between(1998, WINDOW_END_YEAR).all()
    assert (df["VehicleAge"] == WINDOW_END_YEAR - df["ManufacturingYear"]).all()
    assert (df["RegistrationYear"] >= df["ManufacturingYear"]).all()
    assert (df["RegistrationYear"] <= WINDOW_END_YEAR).all()


def main() -> None:
    df = generate()
    validate(df)
    out = config.CLEANED_DIR / "vehicles.csv"
    df.to_csv(out, index=False, encoding=config.CSV_ENCODING)
    print(f"generate_vehicles: wrote {len(df)} vehicles -> {out}\n")
    print("Top brands:")
    print((df["VehicleBrand"].value_counts(normalize=True) * 100).round(1).head(8).to_string())
    print("\nVehicleType:", df["VehicleType"].value_counts().to_dict())
    print(f"VehicleAge: min={df.VehicleAge.min()} mean={df.VehicleAge.mean():.1f} max={df.VehicleAge.max()}")
    print("\nSample:")
    print(df.head(6).to_string(index=False))


if __name__ == "__main__":
    main()
