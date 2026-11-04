# 03 — Data Quality Issues (Phase 3)

Controlled issues injected into `data/raw/` from pristine `data/cleaned/`. 
All are reproducible (seed). Power Query (Phase 5) cleans raw/ back to analysis-ready.

## Injected issues

| Table | Column | Issue | Count |
|---|---|---|---:|
| customers | Gender | missing values | 100 |
| customers | City | missing values | 150 |
| customers | LastName | inconsistent text case/whitespace | 250 |
| customers | Governorate | inconsistent governorate spelling | 400 |
| customers | BirthDate | mixed/non-ISO date formats | 200 |
| customers | Gender | inconsistent categorical values | 150 |
| customers | (row) | duplicate rows | 25 |
| branches | Governorate | inconsistent governorate spelling | 2 |
| branches | BranchName | inconsistent text case/whitespace | 1 |
| policies | PolicyStartDate | mixed/non-ISO date formats | 320 |
| policies | PaymentFrequency | missing values | 160 |
| policies | PolicyStatus | inconsistent categorical values | 240 |
| policies | (row) | duplicate rows | 24 |
| premiums | PremiumAmount | invalid numeric (negative/zero) | 80 |
| premiums | PaymentMethod | missing values | 240 |
| premiums | PaymentStatus | inconsistent categorical values | 320 |
| premiums | TransactionDate | mixed/non-ISO date formats | 240 |
| premiums | (row) | duplicate rows | 24 |
| claims | ClaimAmount | invalid numeric (negative/zero) | 20 |
| claims | ClaimType | missing values | 80 |
| claims | ClaimDate | mixed/non-ISO date formats | 160 |
| claims | ClaimStatus | inconsistent categorical values | 120 |
| claims | (row) | duplicate rows | 12 |
| payments | AmountPaid | invalid numeric (negative/zero) | 16 |
| payments | PaymentMethod | missing values | 64 |
| payments | PaymentDate | mixed/non-ISO date formats | 96 |
| vehicles | VehicleType | missing values | 40 |
| vehicles | ManufacturingYear | invalid numeric (negative/zero) | 10 |

## Remediation (Power Query)

| Issue | How to detect & fix |
|---|---|
| missing values | Power Query: filter/flag nulls; impute or remove; set 'Unknown' for categoricals. |
| duplicate rows | Power Query: Remove Duplicates on the primary key. |
| inconsistent text case/whitespace | Transform > Format > Trim + Clean + Proper/UPPER. |
| mixed/non-ISO date formats | Change Type with Locale, or split & reassemble to Date. |
| inconsistent governorate spelling | Merge with a governorate reference table / replace values. |
| invalid numeric (negative/zero) | Filter out or set error rows; replace with null then validate. |
| inconsistent categorical values | Replace Values / map to a canonical domain. |