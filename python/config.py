"""
config.py — single source of truth for project-wide constants.

Every generator and validation script imports from here. Change a number once,
and the whole pipeline follows. This is deliberate: no magic numbers scattered
across scripts.
"""
from pathlib import Path

# --------------------------------------------------------------------------- #
# Reproducibility
# --------------------------------------------------------------------------- #
# A single fixed seed makes the entire synthetic dataset reproducible. Anyone
# who clones the repo and runs the generators gets byte-identical data.
SEED = 42

# --------------------------------------------------------------------------- #
# Paths (resolved relative to this file, so it works on any machine)
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"          # generated data WITH controlled quality issues
CLEANED_DIR = DATA_DIR / "cleaned"  # validated, analysis-ready data
REFERENCE_DIR = DATA_DIR / "reference"  # curated lookup pools

for _d in (RAW_DIR, CLEANED_DIR, REFERENCE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Business coverage window
# --------------------------------------------------------------------------- #
START_DATE = "2022-01-01"
END_DATE = "2025-12-31"

# --------------------------------------------------------------------------- #
# Target dataset sizes (from the project brief)
# --------------------------------------------------------------------------- #
N_CUSTOMERS = 5_000
N_POLICIES = 8_000
N_CLAIMS = 4_000
N_BRANCHES = 24          # one agency per governorate (brief says 20–30)

# Currency label (all monetary values are in Tunisian dinar)
CURRENCY = "TND"

# CSV encoding used everywhere
CSV_ENCODING = "utf-8"
