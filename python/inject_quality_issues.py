"""
inject_quality_issues.py — derive MESSY data/raw/ from pristine data/cleaned/.

Phase 3 step 1. We take the validated ground-truth tables and inject a CONTROLLED,
reproducible set of real-world data-quality problems, writing the dirty versions to
data/raw/. Power Query (Phase 5) will clean raw/ back toward the known-good cleaned/.

Issues injected (all seeded, all tracked and reported):
  - missing values            - duplicate rows
  - inconsistent text case    - mixed/invalid date formats
  - governorate spelling vars  - invalid numerics (negative / zero)
  - inconsistent categoricals

Rule: PKs are NOT corrupted in a way that breaks the model (duplicates are allowed as a
cleanable issue). Output: data/raw/*.csv  +  documentation/03_data_quality.md
"""
from __future__ import annotations

import pandas as pd

import config
import utils

RNG_OFFSET = 10
ISSUE_LOG: list[dict] = []


def _log(table, column, issue, count):
    ISSUE_LOG.append({"table": table, "column": column, "issue": issue, "count": int(count)})


def _idx(rng, n, frac):
    k = max(1, int(round(n * frac)))
    return rng.choice(n, size=k, replace=False)


def set_missing(rng, df, table, col, frac):
    i = _idx(rng, len(df), frac)
    df.loc[df.index[i], col] = None
    _log(table, col, "missing values", len(i))


def messy_case(rng, df, table, col, frac):
    i = _idx(rng, len(df), frac)
    for j in i:
        v = df.iat[j, df.columns.get_loc(col)]
        if isinstance(v, str) and v:
            df.iat[j, df.columns.get_loc(col)] = rng.choice(
                [v.upper(), v.lower(), f"  {v}", f"{v}  "])
    _log(table, col, "inconsistent text case/whitespace", len(i))


def messy_dates(rng, df, table, col, frac):
    i = _idx(rng, len(df), frac)
    loc = df.columns.get_loc(col)
    cnt = 0
    for j in i:
        v = df.iat[j, loc]
        if isinstance(v, str) and v.count("-") == 2 and len(v) == 10:
            y, m, d = v.split("-")
            df.iat[j, loc] = rng.choice([f"{d}/{m}/{y}", f"{y}/{m}/{d}", f"{d}-{m}-{y}"])
            cnt += 1
    _log(table, col, "mixed/non-ISO date formats", cnt)


def messy_governorate(rng, df, table, col, frac):
    accent = {"Beja": "Béja", "Gabes": "Gabès", "Medenine": "Médenine", "Le Kef": "Kef"}
    i = _idx(rng, len(df), frac)
    loc = df.columns.get_loc(col)
    for j in i:
        v = df.iat[j, loc]
        if isinstance(v, str) and v:
            opts = [v.upper(), v.lower(), f"{v} ", accent.get(v, v)]
            df.iat[j, loc] = rng.choice(opts)
    _log(table, col, "inconsistent governorate spelling", len(i))


def messy_categorical(rng, df, table, col, mapping, frac):
    i = _idx(rng, len(df), frac)
    loc = df.columns.get_loc(col)
    for j in i:
        v = df.iat[j, loc]
        if isinstance(v, str) and v in mapping:
            df.iat[j, loc] = rng.choice(mapping[v])
    _log(table, col, "inconsistent categorical values", len(i))


def invalid_numeric(rng, df, table, col, frac):
    i = _idx(rng, len(df), frac)
    loc = df.columns.get_loc(col)
    for j in i:
        v = df.iat[j, loc]
        try:
            num = float(v)
            df.iat[j, loc] = str(int(-abs(num))) if rng.random() < 0.5 else "0"
        except (TypeError, ValueError):
            pass
    _log(table, col, "invalid numeric (negative/zero)", len(i))


def dup_rows(rng, df, table, frac):
    i = _idx(rng, len(df), frac)
    dups = df.iloc[i].copy()
    out = pd.concat([df, dups], ignore_index=True)
    _log(table, "(row)", "duplicate rows", len(i))
    return out


def load(name):
    return pd.read_csv(config.CLEANED_DIR / name, dtype=str, keep_default_na=False, na_values=[""])


def save(df, name):
    df.to_csv(config.RAW_DIR / name, index=False, encoding=config.CSV_ENCODING)


def main():
    rng = utils.get_rng(RNG_OFFSET)

    # customers
    c = load("customers.csv")
    set_missing(rng, c, "customers", "Gender", 0.02)
    set_missing(rng, c, "customers", "City", 0.03)
    messy_case(rng, c, "customers", "LastName", 0.05)
    messy_governorate(rng, c, "customers", "Governorate", 0.08)
    messy_dates(rng, c, "customers", "BirthDate", 0.04)
    messy_categorical(rng, c, "customers", "Gender", {"M": ["Male", "H", "m"], "F": ["Female", "Femme", "f"]}, 0.03)
    c = dup_rows(rng, c, "customers", 0.005)
    save(c, "customers.csv")

    # branches
    b = load("branches.csv")
    messy_governorate(rng, b, "branches", "Governorate", 0.10)
    messy_case(rng, b, "branches", "BranchName", 0.05)
    save(b, "branches.csv")

    # policies
    p = load("policies.csv")
    messy_dates(rng, p, "policies", "PolicyStartDate", 0.04)
    set_missing(rng, p, "policies", "PaymentFrequency", 0.02)
    messy_categorical(rng, p, "policies", "PolicyStatus",
                      {"Active": ["active", "ACTIVE"], "Expired": ["expired", "EXPIRED"],
                       "Cancelled": ["cancelled", "Canceled"]}, 0.03)
    p = dup_rows(rng, p, "policies", 0.003)
    save(p, "policies.csv")

    # premiums
    pr = load("premiums.csv")
    invalid_numeric(rng, pr, "premiums", "PremiumAmount", 0.01)
    set_missing(rng, pr, "premiums", "PaymentMethod", 0.03)
    messy_categorical(rng, pr, "premiums", "PaymentStatus",
                      {"Paid": ["paid", "PAID", "Paid "], "Pending": ["pending", "PENDING"],
                       "Late": ["late", "LATE"]}, 0.04)
    messy_dates(rng, pr, "premiums", "TransactionDate", 0.03)
    pr = dup_rows(rng, pr, "premiums", 0.003)
    save(pr, "premiums.csv")

    # claims
    cl = load("claims.csv")
    invalid_numeric(rng, cl, "claims", "ClaimAmount", 0.005)
    set_missing(rng, cl, "claims", "ClaimType", 0.02)
    messy_dates(rng, cl, "claims", "ClaimDate", 0.04)
    messy_categorical(rng, cl, "claims", "ClaimStatus",
                      {"Approved": ["approved", "APPROVED"], "Rejected": ["rejected", "Refused"],
                       "Pending": ["pending", "En attente"]}, 0.03)
    cl = dup_rows(rng, cl, "claims", 0.003)
    save(cl, "claims.csv")

    # payments
    pay = load("payments.csv")
    invalid_numeric(rng, pay, "payments", "AmountPaid", 0.005)
    set_missing(rng, pay, "payments", "PaymentMethod", 0.02)
    messy_dates(rng, pay, "payments", "PaymentDate", 0.03)
    save(pay, "payments.csv")

    # vehicles
    v = load("vehicles.csv")
    set_missing(rng, v, "vehicles", "VehicleType", 0.02)
    invalid_numeric(rng, v, "vehicles", "ManufacturingYear", 0.005)
    save(v, "vehicles.csv")

    report = pd.DataFrame(ISSUE_LOG)
    total = report["count"].sum()
    print(f"Injected {total:,} issues across {report['table'].nunique()} tables -> {config.RAW_DIR}\n")
    print(report.to_string(index=False))

    # Markdown documentation of issues + remediation
    _write_doc(report)


def _write_doc(report: pd.DataFrame):
    remediation = {
        "missing values": "Power Query: filter/flag nulls; impute or remove; set 'Unknown' for categoricals.",
        "duplicate rows": "Power Query: Remove Duplicates on the primary key.",
        "inconsistent text case/whitespace": "Transform > Format > Trim + Clean + Proper/UPPER.",
        "mixed/non-ISO date formats": "Change Type with Locale, or split & reassemble to Date.",
        "inconsistent governorate spelling": "Merge with a governorate reference table / replace values.",
        "invalid numeric (negative/zero)": "Filter out or set error rows; replace with null then validate.",
        "inconsistent categorical values": "Replace Values / map to a canonical domain.",
    }
    lines = ["# 03 — Data Quality Issues (Phase 3)\n",
             "Controlled issues injected into `data/raw/` from pristine `data/cleaned/`. ",
             "All are reproducible (seed). Power Query (Phase 5) cleans raw/ back to analysis-ready.\n",
             "## Injected issues\n",
             "| Table | Column | Issue | Count |",
             "|---|---|---|---:|"]
    for _, r in report.iterrows():
        lines.append(f"| {r['table']} | {r['column']} | {r['issue']} | {r['count']} |")
    lines += ["\n## Remediation (Power Query)\n", "| Issue | How to detect & fix |", "|---|---|"]
    for k, v in remediation.items():
        lines.append(f"| {k} | {v} |")
    (config.PROJECT_ROOT / "documentation" / "03_data_quality.md").write_text(
        "\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
