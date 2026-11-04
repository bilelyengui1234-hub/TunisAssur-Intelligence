# 05 — Power Query Cleaning Guide (Phase 5)

Goal: import the **dirty** `data/raw/*.csv` into Power BI Desktop and clean them back to
analysis-ready tables (matching `data/cleaned/` ground truth). Each step says **why / how /
M code / how to verify**. Do not advance to the data model until every table is clean.

> Reference: the issues to reverse are listed in `documentation/03_data_quality.md`
> (3,544 injected issues: missing values, duplicates, text case, mixed date formats,
> governorate spelling, invalid numerics, inconsistent categoricals).

---

## 0. Import & organise

**How:** `Home > Get Data > Text/CSV`, pick each file in `data/raw/`
(branches, customers, policies, premiums, claims, payments, vehicles). In the preview set
**Delimiter = Comma** and **First row as headers**. Click **Transform Data** (not Load) to open
Power Query Editor.

**Organise (right pane > New Group):**
- `_Functions` — helper functions (below)
- `01_Reference` — governorates, products (from `data/reference/`)
- `02_Dimensions` — DimBranch, DimCustomer, DimVehicle, DimPolicy
- `03_Facts` — FactPremiums, FactClaims, FactPayments

> Tip: turn OFF `File > Options > Data Load > Auto date/time` (we use our own DimDate later).

---

## 1. `_Functions`: a robust date parser

**Why:** raw dates come in mixed formats (`2024-10-13`, `13/10/2024`, `2024/10/13`,
`13-10-2024`). A single "Change Type" can't handle all of them. One function does.

**How:** `Home > New Source > Blank Query`, rename to **fnParseDate**, open **Advanced Editor**,
paste:

```powerquery
// fnParseDate: parse mixed date text to a date. Day-first for non-ISO (our data uses DD/MM/YYYY).
(txt as nullable text) as nullable date =>
let
    t = if txt = null then null else Text.Trim(txt),
    out =
        if t = null or t = "" then null
        else
            let
                norm  = Text.Replace(t, "/", "-"),
                parts = Text.Split(norm, "-"),
                a = Number.FromText(parts{0}),
                b = Number.FromText(parts{1}),
                c = Number.FromText(parts{2})
            in
                if Text.Length(parts{0}) = 4
                then #date(a, b, c)        // YYYY-MM-DD  or YYYY/MM/DD
                else #date(c, b, a)        // DD-MM-YYYY  or DD/MM/YYYY (day first)
in
    out
```

**Verify:** create a Blank Query `= fnParseDate("13/10/2024")` → should return a **date**
`13/10/2024`; `= fnParseDate("2024-10-13")` → same date.

---

## 2. Reusable cleaning patterns

Use these throughout (UI path, then the M it generates):

| Task | UI | M |
|---|---|---|
| Trim + clean text | select cols > Transform > Format > Trim, then Clean | `Table.TransformColumns(Source, {{"Col", each Text.Clean(Text.Trim(_)), type text}})` |
| Proper/UPPER case | Transform > Format > Capitalize Each Word | `Table.TransformColumns(…, {{"Col", Text.Proper, type text}})` |
| Remove duplicates on a key | select key column > Home > Remove Rows > Remove Duplicates | `Table.Distinct(Source, {"KeyCol"})` |
| Replace a value | Transform > Replace Values | `Table.ReplaceValue(…, "old","new", Replacer.ReplaceText, {"Col"})` |
| Null → default | Transform > Replace Values (value = null) | `Table.ReplaceValue(…, null, "Inconnu", Replacer.ReplaceValue, {"Col"})` |
| Filter invalid numbers | filter dropdown | `Table.SelectRows(Source, each [Amount] <> null and [Amount] > 0)` |

---

## 3. DimBranch

1. **Set types:** BranchID/Name/Governorate/City = Text; OpeningDate via fnParseDate.
   `= Table.TransformColumns(Source, {{"OpeningDate", fnParseDate, type date}})`
2. **Trim + Clean** BranchName and Governorate.
3. **Standardise governorate** (see §4 mapping) — e.g. `beja `→`Beja`.
4. **Verify:** 24 rows; `Governorate` distinct count = 24; no nulls in BranchID.

## 4. DimCustomer (the governorate showcase)

**Why:** `Governorate` has case/space/accent variants (`BÉJA`, `beja `, `Béja`) — 400 of them.
Leaving them splits one region into several on every chart.

1. **Remove duplicates** on `CustomerID` (25 dup rows): `Table.Distinct(Source, {"CustomerID"})`.
2. **Trim + Clean** FirstName, LastName, City, Governorate.
3. **Standardise Governorate** — two options:
   - *Simple:* Trim → `Text.Proper` → Replace Values for accents:
     `Béja→Beja`, `Gabès→Gabes`, `Médenine→Medenine`, `Kef→Le Kef`.
   - *Best practice (recommended):* **Merge** against the governorate reference list so only
     valid names survive and typos are caught:
     ```powerquery
     // after cleaning case, validate against reference
     Merged = Table.NestedJoin(Cleaned, {"Governorate"}, Governorates, {"Governorate"}, "ref", JoinKind.LeftOuter)
     // rows where ref is empty = unmatched spelling to fix
     ```
4. **Standardise Gender** → canonical `M`/`F` (variants `Male/H/m`, `Female/Femme/f`):
   ```powerquery
   Table.TransformColumns(Source, {{"Gender", each
       let g = Text.Upper(Text.Trim(_ ?? "")) in
       if List.Contains({"M","MALE","H"}, g) then "M"
       else if List.Contains({"F","FEMALE","FEMME"}, g) then "F"
       else null, type text}})
   ```
5. **Missing values:** Gender nulls → leave null or `"Inconnu"`; City nulls → `"Inconnu"`.
6. **Dates:** BirthDate, RegistrationDate via fnParseDate. Set Age = whole number.
7. **Verify:** 5000 rows; `Governorate` distinct = 24; `Gender` ∈ {M,F,(null)}; BirthDate is a Date type.

## 5. DimVehicle

1. Remove duplicates on `VehicleID`.
2. **ManufacturingYear**: replace invalid (negative/zero from injection) → null, then filter or
   set to null. `Table.SelectRows(_, each [ManufacturingYear] <> null and Number.From([ManufacturingYear]) > 1950)`.
3. Null `VehicleType` → `"Inconnu"`.
4. Types: years = whole number; recompute `VehicleAge = 2025 - ManufacturingYear` if needed.
5. **Verify:** no VehicleType nulls; ManufacturingYear between 1998–2025.

## 6. DimPolicy

1. **Remove duplicates** on `PolicyID` (24 dup rows).
2. **PolicyStatus** → canonical {Active, Expired, Cancelled}:
   Trim → `Text.Proper`, then Replace `Canceled`→`Cancelled`.
3. **PaymentFrequency** nulls → `"Inconnu"` (or most-common value).
4. **Dates:** PolicyStartDate, PolicyEndDate via fnParseDate.
5. **Verify:** 8000 rows; PolicyStatus has exactly 3 values; `PolicyEndDate > PolicyStartDate`
   (add a temp check column `= [PolicyEndDate] > [PolicyStartDate]`, filter FALSE → expect none).

## 7. FactPremiums

1. **Remove duplicates** on `PremiumID` (24 dup rows).
2. Types: PremiumAmount/DiscountAmount/NetPremiumAmount = Decimal; TransactionDate via fnParseDate.
3. **Invalid amounts:** filter out `PremiumAmount <= 0` or null (80 injected). Document that in
   production you'd quarantine, not silently drop.
4. **PaymentStatus** → {Paid, Pending, Late}: Trim → `Text.Proper`.
5. **PaymentMethod** nulls → `"Inconnu"`.
6. **Verify:** PremiumAmount all > 0; NetPremium = Premium − Discount (temp check column).

## 8. FactClaims

1. **Remove duplicates** on `ClaimID` (12 dup rows).
2. Types: ClaimAmount = Decimal; ClaimDate/ApprovalDate/ClosureDate via fnParseDate (nulls stay null).
3. **Invalid ClaimAmount:** filter `<= 0` / null (20 injected).
4. **ClaimType** nulls → `"Inconnu"`.
5. **ClaimStatus** → {Approved, Rejected, Pending}: Trim → Text.Proper, Replace
   `Refused→Rejected`, `En attente→Pending`.
6. **Verify:** ClaimStatus has exactly 3 values; `ApprovalDate >= ClaimDate` where not null.

## 9. FactPayments

1. Types: AmountPaid = Decimal; PaymentDate via fnParseDate.
2. **Invalid AmountPaid:** filter `<= 0` / null (16 injected).
3. **PaymentMethod** nulls → `"Inconnu"`. PaymentStatus Trim → Text.Proper.
4. **Verify:** AmountPaid all > 0; every `ClaimID` still exists in FactClaims (referential check).

---

## 10. Final verification (before building the model)

Run these mental/visual checks (they mirror `python/validate_data.py`):

- **Row counts** ≈ ground truth (after dropping invalid rows): customers 5000, policies 8000,
  premiums ~7920 (8000 − dropped invalids), claims ~3980, payments ~3200, vehicles 1989.
- **Keys unique & non-null** in every table (no duplicates remain).
- **Governorate** distinct = 24 everywhere it appears.
- **Dates** are real Date types (not text), inside 2022–2025 for transactions/claims/payments.
- **Amounts** strictly > 0.
- **Categoricals** each collapsed to their canonical domain.

> Cross-check: you can compare against `data/cleaned/` (the known-good truth) — your cleaned
> queries should match it except for the invalid rows you deliberately dropped.

When all pass → **Close & Apply**, then Phase 6 (relationships, DimDate, role-playing dates).

---

## Appendix: loading the reference tables

In `01_Reference`, import `data/reference/governorates.csv` and `products.csv`. Keep
`governorates` as the lookup for the Merge in §4. `products.csv` can seed **DimProduct**
(or connect DimProduct from Postgres — either source works).
