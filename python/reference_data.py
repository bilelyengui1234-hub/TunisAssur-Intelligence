"""
reference_data.py — curated Tunisian reference pools (the INPUT to all generation).

These are facts about Tunisia and about TunisAssur's product catalogue. They are
curated by hand (not randomly generated) so the synthetic data is geographically
and commercially credible. Every downstream generator imports the structures below
instead of re-declaring them.

Run this file directly to (re)write the reference CSVs into data/reference/:

    python python/reference_data.py
"""
from __future__ import annotations

import pandas as pd

import config

# --------------------------------------------------------------------------- #
# 1. GOVERNORATES
#    (governorate, region, population_weight)
#    population_weight ≈ relative population share. It drives WHERE customers and
#    claims concentrate, so Grand Tunis / Sfax / Sousse dominate — not a flat map.
# --------------------------------------------------------------------------- #
GOVERNORATES: list[tuple[str, str, float]] = [
    # Grand Tunis
    ("Tunis",        "Grand Tunis",  1.10),
    ("Ariana",       "Grand Tunis",  0.63),
    ("Ben Arous",    "Grand Tunis",  0.71),
    ("Manouba",      "Grand Tunis",  0.40),
    # Nord-Est
    ("Nabeul",       "Nord-Est",     0.85),
    ("Zaghouan",     "Nord-Est",     0.19),
    ("Bizerte",      "Nord-Est",     0.62),
    # Nord-Ouest
    ("Beja",         "Nord-Ouest",   0.30),
    ("Jendouba",     "Nord-Ouest",   0.40),
    ("Le Kef",       "Nord-Ouest",   0.24),
    ("Siliana",      "Nord-Ouest",   0.22),
    # Centre-Est
    ("Sousse",       "Centre-Est",   0.90),
    ("Monastir",     "Centre-Est",   0.61),
    ("Mahdia",       "Centre-Est",   0.42),
    ("Sfax",         "Centre-Est",   1.00),
    # Centre-Ouest
    ("Kairouan",     "Centre-Ouest", 0.57),
    ("Kasserine",    "Centre-Ouest", 0.44),
    ("Sidi Bouzid",  "Centre-Ouest", 0.43),
    # Sud-Est
    ("Gabes",        "Sud-Est",      0.39),
    ("Medenine",     "Sud-Est",      0.50),
    ("Tataouine",    "Sud-Est",      0.15),
    # Sud-Ouest
    ("Gafsa",        "Sud-Ouest",    0.34),
    ("Tozeur",       "Sud-Ouest",    0.11),
    ("Kebili",       "Sud-Ouest",    0.16),
]

# --------------------------------------------------------------------------- #
# 2. CITIES / DELEGATIONS per governorate
#    Used for customer city and branch location.
# --------------------------------------------------------------------------- #
CITIES: dict[str, list[str]] = {
    "Tunis":       ["Tunis", "Le Bardo", "La Marsa", "Carthage", "El Menzah"],
    "Ariana":      ["Ariana", "Raoued", "La Soukra", "Ettadhamen"],
    "Ben Arous":   ["Ben Arous", "Rades", "Hammam Lif", "Megrine"],
    "Manouba":     ["Manouba", "Douar Hicher", "Oued Ellil", "Tebourba"],
    "Nabeul":      ["Nabeul", "Hammamet", "Kelibia", "Korba", "Menzel Temime"],
    "Zaghouan":    ["Zaghouan", "El Fahs", "Nadhour"],
    "Bizerte":     ["Bizerte", "Menzel Bourguiba", "Ras Jebel", "Mateur"],
    "Beja":        ["Beja", "Medjez el-Bab", "Testour", "Nefza"],
    "Jendouba":    ["Jendouba", "Tabarka", "Bou Salem", "Ain Draham"],
    "Le Kef":      ["Le Kef", "Dahmani", "Tajerouine", "Sakiet Sidi Youssef"],
    "Siliana":     ["Siliana", "Makthar", "Gaafour", "Bou Arada"],
    "Sousse":      ["Sousse", "Hammam Sousse", "Msaken", "Kalaa Kebira", "Enfidha"],
    "Monastir":    ["Monastir", "Moknine", "Jemmal", "Ksar Hellal", "Sahline"],
    "Mahdia":      ["Mahdia", "Ksour Essef", "Chebba", "El Jem"],
    "Sfax":        ["Sfax", "Sakiet Ezzit", "Chihia", "El Ain", "Thyna"],
    "Kairouan":    ["Kairouan", "Haffouz", "Sbikha", "Chebika"],
    "Kasserine":   ["Kasserine", "Sbeitla", "Thala", "Feriana"],
    "Sidi Bouzid": ["Sidi Bouzid", "Regueb", "Menzel Bouzaiane", "Jelma"],
    "Gabes":       ["Gabes", "Mareth", "El Hamma", "Metouia"],
    "Medenine":    ["Medenine", "Houmt Souk", "Zarzis", "Ben Gardane"],
    "Tataouine":   ["Tataouine", "Ghomrassen", "Remada", "Bir Lahmar"],
    "Gafsa":       ["Gafsa", "Metlaoui", "Redeyef", "El Guettar"],
    "Tozeur":      ["Tozeur", "Nefta", "Degache"],
    "Kebili":      ["Kebili", "Douz", "Souk Lahad"],
}

# --------------------------------------------------------------------------- #
# 3. PRODUCTS (DimProduct) + actuarial generation parameters
#    policy_share .......... fraction of all policies this product represents (sums to 1.0)
#    premium_min/max ....... annual premium range in TND
#    claim_frequency ....... avg claims per active policy-year (drives how many claims)
#    severity_min/max ...... claim amount range in TND
#    These numbers encode the business logic: Automobile is common & moderate,
#    Life is rare & severe, Health is frequent, etc.
# --------------------------------------------------------------------------- #
PRODUCTS: list[dict] = [
    {
        "ProductID": "PRD001", "ProductName": "Assurance Automobile",
        "ProductCategory": "Automobile",
        "CoverageDescription": "Responsabilite civile, dommages, vol et incendie vehicule",
        "policy_share": 0.40, "premium_min": 300, "premium_max": 1200,
        "claim_frequency": 0.35, "severity_min": 400, "severity_max": 15000,
    },
    {
        "ProductID": "PRD002", "ProductName": "Assurance Sante",
        "ProductCategory": "Sante",
        "CoverageDescription": "Frais medicaux, hospitalisation et soins",
        "policy_share": 0.22, "premium_min": 400, "premium_max": 2000,
        "claim_frequency": 0.55, "severity_min": 100, "severity_max": 8000,
    },
    {
        "ProductID": "PRD003", "ProductName": "Assurance Vie",
        "ProductCategory": "Vie",
        "CoverageDescription": "Capital deces, epargne et prevoyance",
        "policy_share": 0.12, "premium_min": 200, "premium_max": 3000,
        "claim_frequency": 0.04, "severity_min": 5000, "severity_max": 100000,
    },
    {
        "ProductID": "PRD004", "ProductName": "Assurance Habitation",
        "ProductCategory": "Habitation",
        "CoverageDescription": "Incendie, degats des eaux, vol et responsabilite habitation",
        "policy_share": 0.16, "premium_min": 150, "premium_max": 800,
        "claim_frequency": 0.18, "severity_min": 500, "severity_max": 30000,
    },
    {
        "ProductID": "PRD005", "ProductName": "Assurance Professionnelle",
        "ProductCategory": "Professionnelle",
        "CoverageDescription": "Responsabilite civile professionnelle et multirisque entreprise",
        "policy_share": 0.10, "premium_min": 500, "premium_max": 5000,
        "claim_frequency": 0.22, "severity_min": 1000, "severity_max": 50000,
    },
]

# --------------------------------------------------------------------------- #
# SEVERITY CALIBRATION
# The raw severity bands above were initially too generous: 4,000 claims produced
# a ~164% loss ratio vs written premium (an insolvent insurer). We scale all claim
# severities by a single factor to hit a realistic target loss ratio.
#   SEVERITY_SCALE = 0.52  ->  incurred ~= 85% of written premium
#                              ("margin pressure" scenario chosen for this project).
# Change this one number to re-target the loss ratio, then re-run reference_data.py
# and generate_claims.py.
# --------------------------------------------------------------------------- #
SEVERITY_SCALE = 0.52
for _p in PRODUCTS:
    _p["severity_min"] = int(round(_p["severity_min"] * SEVERITY_SCALE))
    _p["severity_max"] = int(round(_p["severity_max"] * SEVERITY_SCALE))

# --------------------------------------------------------------------------- #
# 4. NAME POOLS (gender-consistent)
#    First names are tagged by gender so Gender and FirstName always agree.
# --------------------------------------------------------------------------- #
FIRST_NAMES_MALE: list[str] = [
    "Mohamed", "Ahmed", "Ali", "Youssef", "Khaled", "Hamza", "Bilel", "Oussama",
    "Nizar", "Wael", "Anis", "Sami", "Karim", "Mehdi", "Aymen", "Hichem", "Slim",
    "Marwan", "Firas", "Rami", "Tarek", "Walid", "Zied", "Fares", "Seif", "Nabil",
    "Mohsen", "Lotfi", "Chokri", "Imed", "Ramzi", "Haythem", "Skander", "Bassem",
    "Maher", "Adel", "Sofiene", "Riadh", "Hatem", "Moez",
]
FIRST_NAMES_FEMALE: list[str] = [
    "Fatma", "Mariem", "Amira", "Ines", "Rania", "Sana", "Nour", "Yasmine",
    "Salma", "Hiba", "Asma", "Emna", "Olfa", "Dorra", "Rim", "Nesrine", "Syrine",
    "Khaoula", "Wafa", "Imen", "Sarra", "Hela", "Sabrine", "Manel", "Amel",
    "Takwa", "Ghada", "Ikram", "Chaima", "Marwa", "Sawssen", "Houda", "Faten",
    "Leila", "Sonia", "Nadia", "Donia", "Eya", "Maya", "Farah",
]
SURNAMES: list[str] = [
    "Ben Ali", "Trabelsi", "Jebali", "Gharbi", "Bouazizi", "Mejri", "Khelifi",
    "Sassi", "Hammami", "Chaabane", "Ben Salah", "Ayari", "Jlassi", "Bouzid",
    "Ben Youssef", "Nasri", "Dridi", "Ferchichi", "Zaidi", "Bennour", "Haddad",
    "Kallel", "Masmoudi", "Abidi", "Jaziri", "Guesmi", "Baccouche", "Ben Amor",
    "Khemiri", "Mabrouk", "Sellami", "Tlili", "Ben Hassine", "Rekik", "Chedly",
    "Bouchnak", "Karoui", "Ben Romdhane", "Laabidi", "Fathallah",
]


# --------------------------------------------------------------------------- #
# Helper: tidy DataFrames for the reference CSVs
# --------------------------------------------------------------------------- #
def governorates_df() -> pd.DataFrame:
    df = pd.DataFrame(GOVERNORATES, columns=["Governorate", "Region", "PopulationWeight"])
    # Normalise weights so they sum to 1 — makes them ready to use as probabilities.
    df["PopulationWeight"] = df["PopulationWeight"] / df["PopulationWeight"].sum()
    return df


def cities_df() -> pd.DataFrame:
    rows = [(gov, city) for gov, cities in CITIES.items() for city in cities]
    return pd.DataFrame(rows, columns=["Governorate", "City"])


def products_df() -> pd.DataFrame:
    return pd.DataFrame(PRODUCTS)


def first_names_df() -> pd.DataFrame:
    rows = [(n, "M") for n in FIRST_NAMES_MALE] + [(n, "F") for n in FIRST_NAMES_FEMALE]
    return pd.DataFrame(rows, columns=["FirstName", "Gender"])


def surnames_df() -> pd.DataFrame:
    return pd.DataFrame({"Surname": SURNAMES})


def write_reference_csvs() -> None:
    outputs = {
        "governorates.csv": governorates_df(),
        "cities.csv": cities_df(),
        "products.csv": products_df(),
        "first_names.csv": first_names_df(),
        "surnames.csv": surnames_df(),
    }
    for filename, df in outputs.items():
        path = config.REFERENCE_DIR / filename
        df.to_csv(path, index=False, encoding=config.CSV_ENCODING)
        print(f"  wrote {filename:20s} {len(df):4d} rows -> {path}")


def _sanity_checks() -> None:
    """Fail loudly if the curated pools are internally inconsistent."""
    share = sum(p["policy_share"] for p in PRODUCTS)
    assert abs(share - 1.0) < 1e-9, f"product policy_share must sum to 1.0, got {share}"
    assert len(GOVERNORATES) == 24, "Tunisia has 24 governorates"
    missing = set(g[0] for g in GOVERNORATES) - set(CITIES)
    assert not missing, f"governorates with no cities: {missing}"
    assert len(FIRST_NAMES_MALE) and len(FIRST_NAMES_FEMALE) and len(SURNAMES)


if __name__ == "__main__":
    print("Reference data — sanity checks...")
    _sanity_checks()
    print("OK. Writing reference CSVs:")
    write_reference_csvs()
    print("Done.")
