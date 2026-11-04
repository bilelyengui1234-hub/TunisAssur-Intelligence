# 07 — DAX Measure Library (Phase 7)

The analytical layer. All measures live in the **`_Measures`** table, grouped into display
folders: **Financial KPIs · Claims KPIs · Customer KPIs · Time Intelligence · Risk Indicators**.

Conventions used here:
- Measures reference the model from Phase 6 (DimDate marked as date table; ClaimDate is the
  active claim→date relationship; ApprovalDate/ClosureDate inactive).
- **Golden rule:** cross-process KPIs (e.g. Loss Ratio) divide two independent scalars, each
  aggregating its *own* fact table — never a FactClaims↔FactPayments join.
- Money format: `#,0 "TND"`. Ratios: percentage.
- **Validation anchors** (full-model, no filters): Written 13,189,230 · Incurred(all) 11,226,450 ·
  Incurred(Appr+Pending) 9,540,610 · Paid 6,126,660 · Claims 4,000 (Appr 2,211 / Pend 1,214 / Rej 575) ·
  Customers 5,000 · Policies 8,000 · Avg claim 2,807 · Avg processing ≈ 70 days.

---

## A. Financial KPIs

### Total Premiums (Written)
```DAX
Total Premiums = SUM ( FactPremiums[PremiumAmount] )
```
- **What / filter context:** gross premium contracted; respects whatever slices the visual (product, branch, date via TransactionDate).
- **Example:** no filter → **13,189,230 TND**. Sliced to Automobile → that product's share.
- **Pitfall:** don't confuse with *collected* (money received) or *earned* (time-apportioned).

### Net Premiums
```DAX
Net Premiums = SUM ( FactPremiums[NetPremiumAmount] )
```
- **What:** premium after discounts (`Premium − Discount`). Example: **12,714,320 TND**.
- **Pitfall:** don't recompute as `[Total Premiums] - [Discount]` across different filters — just sum the stored column.

### Collected Premiums
```DAX
Collected Premiums =
CALCULATE ( [Net Premiums], KEEPFILTERS ( FactPremiums[PaymentStatus] = "Paid" ) )
```
- **What:** cash actually received (Paid only). Example: **9,754,505 TND**.
- **Filter context:** `KEEPFILTERS` so it intersects with any existing PaymentStatus slice instead of overriding it.
- **Pitfall:** using Collected as a stand-in for Earned — they answer different questions (cash vs. time).

### Earned Premiums  *(monthly/daily pro-rata)*
```DAX
Earned Premiums =
VAR PeriodStart = MIN ( DimDate[Date] )
VAR PeriodEnd   = MAX ( DimDate[Date] )
RETURN
CALCULATE (
    SUMX (
        FactPremiums,
        VAR polStart = RELATED ( DimPolicy[PolicyStartDate] )
        VAR polEnd   = RELATED ( DimPolicy[PolicyEndDate] )
        VAR termDays = DATEDIFF ( polStart, polEnd, DAY )
        VAR ovStart  = MAXX ( {}, 0 ) + IF ( polStart > PeriodStart, polStart, PeriodStart )
        VAR ovEnd    = IF ( polEnd < PeriodEnd, polEnd, PeriodEnd )
        VAR ovDays   = MAX ( 0, DATEDIFF ( ovStart, ovEnd, DAY ) )
        RETURN IF ( termDays > 0, FactPremiums[PremiumAmount] * DIVIDE ( ovDays, termDays ), 0 )
    ),
    REMOVEFILTERS ( DimDate )          -- see pitfall
)
```
- **What:** the slice of each premium matching coverage time *elapsed within the selected period*. A 1,200 TND annual policy running Jul→Jun contributes ~600 TND to a Jan–Jun view.
- **Filter context:** we capture `PeriodStart/End` from the DimDate selection, then **`REMOVEFILTERS(DimDate)`** so the active `TransactionDate` relationship doesn't wrongly drop policies whose premium was *transacted* outside the window. We then pro-rate by day overlap.
- **Pitfall #1 (the big one):** forgetting `REMOVEFILTERS` — the date relationship would filter FactPremiums by TransactionDate and you'd earn premium only in the month it was billed. **Pitfall #2:** dividing by 0 for zero-length terms (guarded by `termDays > 0`).

### Loss Ratio
```DAX
Loss Ratio = DIVIDE ( [Incurred Claims], [Earned Premiums] )
```
- **What:** the headline health KPI — incurred claims as a share of earned premium. Target band 60–80%; this synthetic book is calibrated to ~85% ("margin pressure").
- **Golden-rule note:** numerator sums FactClaims, denominator sums FactPremiums — **two scalars divided, zero fan-out.**
- **Also provide a quick proxy** for the exec tile:
```DAX
Loss Ratio (written) = DIVIDE ( [Total Claims Amount], [Total Premiums] )   -- = 85.1% unfiltered
```
- **Pitfall:** using *collected* premium (cash) or *paid* claims (cash) in a loss ratio — loss ratio is an **accrual** metric (earned vs incurred).

### Average Premium · Discount Total
```DAX
Average Premium = DIVIDE ( [Total Premiums], COUNTROWS ( FactPremiums ) )   -- ≈ 1,649 TND
Discount Total  = SUM ( FactPremiums[DiscountAmount] )                      -- ≈ 474,910 TND
```

---

## B. Claims KPIs

### Incurred Claims  *(the liability)*
```DAX
Incurred Claims =
CALCULATE ( SUM ( FactClaims[ClaimAmount] ),
    KEEPFILTERS ( FactClaims[ClaimStatus] IN { "Approved", "Pending" } ) )
```
- **What:** cost of claims that are (or will be) a liability — Approved + Pending reserves; **Rejected excluded**. Example: **9,540,610 TND**.
- **Pitfall:** summing *all* ClaimAmount (incl. Rejected) as "incurred" overstates losses. Keep a separate `Total Claims Amount = SUM(FactClaims[ClaimAmount])` (= 11,226,450) only for reference.

### Total Claims Paid · Outstanding Claims
```DAX
Total Claims Paid = SUM ( FactPayments[AmountPaid] )          -- 6,126,660 TND
Outstanding Claims = [Incurred Claims] - [Total Claims Paid]  -- ≈ 3,413,950 TND
```
- **What:** paid = cash disbursed (own fact table); outstanding = reserve still owed (incl. the 1,214 unpaid Pending claims).
- **Pitfall:** trying to get "outstanding per claim" by joining payments to claims — instead subtract two independent measures, or pre-aggregate in ETL.

### Claim counts & rates
```DAX
Total Claims     = COUNTROWS ( FactClaims )                                    -- 4,000
Approved Claims  = CALCULATE ( [Total Claims], FactClaims[ClaimStatus] = "Approved" )  -- 2,211
Rejected Claims  = CALCULATE ( [Total Claims], FactClaims[ClaimStatus] = "Rejected" )  -- 575
Pending Claims   = CALCULATE ( [Total Claims], FactClaims[ClaimStatus] = "Pending" )   -- 1,214
Approval Rate %  = DIVIDE ( [Approved Claims], [Total Claims] )                 -- ≈ 55%
Average Claim Amount = AVERAGE ( FactClaims[ClaimAmount] )                      -- ≈ 2,807 TND
Claim Frequency  = DIVIDE ( [Total Claims], [Total Policies] )                  -- ≈ 0.50 claims/policy
```
- **Filter context:** each count respects slicers; `Approved Claims` + `Rejected` + `Pending` = `Total Claims`.
- **Pitfall:** hard-coding status strings that differ from the cleaned domain (that's why Phase 5 canonicalized them).

### Average Processing Time (days)
```DAX
Average Processing Time =
AVERAGEX (
    FILTER ( FactClaims, NOT ISBLANK ( FactClaims[ClosureDate] ) ),
    DATEDIFF ( FactClaims[ClaimDate], FactClaims[ClosureDate], DAY )
)
```
- **What:** mean days from filing to closure, over *closed* claims only (≈ **70 days**).
- **Pitfall:** including open (null ClosureDate) claims → `DATEDIFF` with blank = wrong/zero; the `FILTER` removes them.

### Claims Closed / Approved by their own date (role-playing)
```DAX
Claims Closed =
CALCULATE ( [Total Claims], USERELATIONSHIP ( DimDate[Date], FactClaims[ClosureDate] ) )
```
- **What:** counts claims by **closure** date instead of occurrence date, activating the inactive relationship. Use for an "operations throughput" view.
- **Pitfall:** expecting the default measures to switch dates — only measures wrapped in `USERELATIONSHIP` use the alternate date.

---

## C. Customer KPIs

```DAX
Total Customers   = COUNTROWS ( DimCustomer )                                    -- 5,000
Total Policies    = COUNTROWS ( DimPolicy )                                      -- 8,000
Active Policies   = CALCULATE ( [Total Policies], DimPolicy[PolicyStatus] = "Active" )  -- 3,444
Active Customers  = CALCULATE ( DISTINCTCOUNT ( DimPolicy[CustomerID] ),
                                DimPolicy[PolicyStatus] = "Active" )
Policies per Customer        = DIVIDE ( [Total Policies], [Total Customers] )     -- ≈ 1.60
Average Premium per Customer = DIVIDE ( [Total Premiums], [Total Customers] )
```

### New Customers (acquired in the selected period)
```DAX
New Customers =
VAR s = MIN ( DimDate[Date] )
VAR e = MAX ( DimDate[Date] )
RETURN
CALCULATE (
    DISTINCTCOUNT ( DimCustomer[CustomerID] ),
    FILTER ( ALL ( DimCustomer ),
             DimCustomer[RegistrationDate] >= s && DimCustomer[RegistrationDate] <= e )
)
```
- **What:** distinct customers whose `RegistrationDate` falls in the current date selection.
- **Filter context:** DimDate has no relationship to DimCustomer, so we read the period bounds and filter RegistrationDate explicitly (`ALL` to ignore unrelated DimCustomer slicers; swap for `ALLEXCEPT` if you want to keep e.g. Governorate).
- **Pitfall:** expecting a DimDate slicer to filter customers automatically — it won't without this pattern (or an inactive DimDate→RegistrationDate relationship).

### Returning Customers · Customer Retention Rate
```DAX
Returning Customers =
COUNTROWS ( FILTER ( VALUES ( DimCustomer[CustomerID] ),
                     CALCULATE ( [Total Policies] ) > 1 ) )

Customer Retention Rate = DIVIDE ( [Active Customers], [Total Customers] )
```
- **What:** *Returning* = customers holding more than one policy (renewed/cross-sold). *Retention Rate* (pragmatic) = share of customers still holding an active policy.
- **Documented simplification:** a rigorous cohort retention (active in year *N−1* AND *N*) is possible but needs a date path to policies; this share-of-active definition is defensible and transparent — state the definition on the dashboard.
- **Pitfall:** quoting a retention % without defining the cohort — always label the denominator.

---

## D. Time Intelligence  *(needs DimDate marked as a date table)*

```DAX
Premiums PY   = CALCULATE ( [Total Premiums], SAMEPERIODLASTYEAR ( DimDate[Date] ) )
Premiums YTD  = TOTALYTD   ( [Total Premiums], DimDate[Date] )
Premiums PM   = CALCULATE ( [Total Premiums], DATEADD ( DimDate[Date], -1, MONTH ) )
Premium YoY % = DIVIDE ( [Total Premiums] - [Premiums PY], [Premiums PY] )
Premium MoM % = DIVIDE ( [Total Premiums] - [Premiums PM], [Premiums PM] )

Incurred Claims YTD = TOTALYTD ( [Incurred Claims], DimDate[Date] )
Claims PY           = CALCULATE ( [Incurred Claims], SAMEPERIODLASTYEAR ( DimDate[Date] ) )
Claims Growth %     = DIVIDE ( [Incurred Claims] - [Claims PY], [Claims PY] )
```
- **What:** standard period-over-period and cumulative KPIs. `SAMEPERIODLASTYEAR` and `TOTALYTD` rely on a **contiguous** date table (our DimDate has no gaps — verified).
- **Example:** 2025 vs 2024 premiums → strong positive `Premium YoY %` (the book grows across the window).
- **Pitfall #1:** time-intel functions silently return blank if the date table isn't *marked* as a date table or has gaps. **Pitfall #2:** putting a non-date column (e.g. `YearMonth` text) on the axis instead of a real Date — breaks the functions. Use `DimDate[Date]` / the hierarchy, with `MonthName` sorted by `MonthNumber`.

---

## E. Risk Indicators  *(activate after Phase 8)*

These reference the **risk score/category** produced in Phase 8 (stored on `FactClaimIndicators`
at claim grain, 1:1 with FactClaims, or as `RiskScore`/`RiskCategory` columns on FactClaims).

```DAX
High-Risk Claims   = CALCULATE ( [Total Claims], FactClaims[RiskCategory] = "High" )
Medium-Risk Claims = CALCULATE ( [Total Claims], FactClaims[RiskCategory] = "Medium" )
Low-Risk Claims    = CALCULATE ( [Total Claims], FactClaims[RiskCategory] = "Low" )
Average Risk Score = AVERAGE ( FactClaims[RiskScore] )
% Claims Flagged   = DIVIDE ( CALCULATE ( [Total Claims], FactClaims[RiskScore] >= 30 ), [Total Claims] )
```
- **What:** volume of claims by risk tier and the flagged share for investigation.
- **Ethics note (keep on the page):** a high score flags a claim for **human review**, it is **not** a fraud determination. Document false-positive risk and synthetic-data bias.
- **Pitfall:** treating `% Claims Flagged` as a fraud rate — it is a *screening* rate.

---

## Build order & validation

1. Create base measures first (Total Premiums, Total Claims, Total Claims Paid, Total Customers, Total Policies).
2. Layer dependent measures (Incurred, Outstanding, Loss Ratio, ratios).
3. Add time-intelligence, then risk (post Phase 8).
4. **Validate** against the anchors at the top by dropping each measure in a Card with no filters:
   `Total Premiums` = 13,189,230 · `Incurred Claims` = 9,540,610 · `Total Claims Paid` = 6,126,660 ·
   `Loss Ratio (written)` = 85.1% · `Total Customers` = 5,000. If a number is off, the model
   relationships or a filter in the measure is wrong — fix before dashboards.

> Tip: keep every measure in `_Measures` with a description typed in the Properties pane — it
> doubles as portfolio documentation and shows intent in interviews.
