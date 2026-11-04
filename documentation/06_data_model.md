# 06 — Data Model Guide (Phase 6)

Build the semantic model in Power BI Desktop: a clean **star schema**, a proper **DimDate**,
**single-direction** relationships, and **role-playing** claim dates. This is the structural
payoff of the grain work in `01_data_architecture.md`.

---

## 0. Professional refinement vs the Phase 0 sketch (read this)

Phase 0 sketched `DimCustomer → DimVehicle` and `DimVehicle → FactClaims`. Building that
literally creates **ambiguous filter paths** and Power BI would silently deactivate a
relationship:

- `DimCustomer → DimPolicy` *and* `DimCustomer → DimVehicle → DimPolicy` = two paths to policy.
- `DimVehicle → FactClaims` *and* `DimVehicle → DimPolicy → FactClaims` = two paths to claims.

**Fix (professional):** a vehicle insures a *policy*, so **DimVehicle connects only to DimPolicy**
(via `InsuredAssetID`). Everything downstream — claims, payments — inherits the vehicle through
the policy. The owner is reached via `policy → customer`, so **no `DimCustomer → DimVehicle`
relationship** is needed. Result: one unambiguous path to everything, no deactivated links.
`FactClaims[VehicleID]` becomes an informational/degenerate column (hidden).

---

## 1. Load DimDate and mark it as a date table

1. Get Data → `data/cleaned/dimdate.csv` (or from Postgres). Set types: `Date` = Date,
   `DateKey`/`Year`/sort columns = Whole Number.
2. **Model view → DimDate → Table tools → Mark as date table → `Date`.** This unlocks correct
   time-intelligence (TOTALYTD, SAMEPERIODLASTYEAR, DATEADD).
3. **Sort-by-column** (Column tools → Sort by column) so labels order chronologically:

   | Display column | Sort by |
   |---|---|
   | `MonthName` | `MonthNumber` |
   | `MonthShort` | `MonthNumber` |
   | `MonthYearLabel` | `YearMonthSort` |
   | `QuarterName` | `Quarter` |
   | `DayName` | `DayOfWeek` |

4. `File > Options > Data Load > Auto date/time` = **OFF** (no auto hierarchies).

---

## 2. Relationships — the complete matrix

Create each in Model view by dragging the field from the "one" side onto the "many" side.
**All are One→Many, single cross-filter direction (Dim → Fact), active unless noted.**

| # | From (one) · key | To (many) · key | Active | Notes |
|---|---|---|---|---|
| 1 | DimCustomer · CustomerID | DimPolicy · CustomerID | ✅ | |
| 2 | DimProduct · ProductID | DimPolicy · ProductID | ✅ | |
| 3 | DimBranch · BranchID | DimPolicy · BranchID | ✅ | |
| 4 | DimVehicle · VehicleID | DimPolicy · InsuredAssetID | ✅ | nullable on policy side (non-auto = blank) |
| 5 | DimPolicy · PolicyID | FactPremiums · PolicyID | ✅ | |
| 6 | DimPolicy · PolicyID | FactClaims · PolicyID | ✅ | |
| 7 | DimPolicy · PolicyID | FactPayments · PolicyID | ✅ | fan-out-proof rollups |
| 8 | DimDate · Date | FactPremiums · TransactionDate | ✅ | |
| 9 | DimDate · Date | FactClaims · ClaimDate | ✅ | the active claim date |
| 10 | DimDate · Date | FactClaims · ApprovalDate | ⛔ inactive | role-playing (USERELATIONSHIP) |
| 11 | DimDate · Date | FactClaims · ClosureDate | ⛔ inactive | role-playing (USERELATIONSHIP) |
| 12 | DimDate · Date | FactPayments · PaymentDate | ✅ | |

**DO NOT create `FactClaims ↔ FactPayments`.** That fact-to-fact join is the fan-out trap.
Cross-process numbers (loss ratio, paid-vs-incurred) are done with measures, each aggregating
its own fact table (Phase 7).

> When you drag a second/third DimDate link to FactClaims, Power BI makes it **inactive**
> automatically (dotted line). Leave it inactive — that's correct.

---

## 3. Role-playing dates (the inactive relationships)

A claim has three meaningful dates. `ClaimDate` drives the model by default; the others are
activated *inside specific measures* with `USERELATIONSHIP` — no duplicate date tables needed.

```DAX
-- Claims counted by when they were CLOSED (uses inactive rel #11)
Claims Closed =
CALCULATE (
    COUNTROWS ( FactClaims ),
    USERELATIONSHIP ( DimDate[Date], FactClaims[ClosureDate] )
)

-- Claims counted by APPROVAL date (uses inactive rel #10)
Claims Approved (by approval date) =
CALCULATE (
    COUNTROWS ( FactClaims ),
    USERELATIONSHIP ( DimDate[Date], FactClaims[ApprovalDate] )
)
```

Default measures (no USERELATIONSHIP) report by `ClaimDate` — i.e. when the claim occurred.

---

## 4. Model hygiene & presentation (what makes it look professional)

1. **Hide technical columns** from report view (right-click → Hide in report view):
   all key columns (`CustomerID`, `ProductID`, `BranchID`, `PolicyID`, `InsuredAssetID`,
   `ClaimID`, `PremiumID`, `PaymentID`, `VehicleID`), `DateKey`, and the sort-helper columns.
2. **Dedicated measures table:** create an empty table `_Measures` (Enter Data, one dummy column,
   delete it) and put all Phase 7 measures there, organized into **display folders**
   (Financial KPIs / Claims KPIs / Customer KPIs / Time Intelligence / Risk).
3. **Friendly names & formats:** set `$` → TND via custom format `#,0 "TND"`; set % measures to
   percentage; rename fields to business language (e.g. `NetPremiumAmount` → "Net Premium").
4. **Single direction only.** Never set a relationship to "Both" — it reintroduces ambiguity and
   wrong totals in a multi-fact model. If you think you need bidirectional, you need a measure.
5. **Star layout:** in Model view arrange dims around DimPolicy with the three facts to one side
   and DimDate above them — a readable star reads as competence in a portfolio screenshot.

---

## 5. QA checklist (before Phase 7)

- [ ] DimDate marked as date table; month/day/quarter labels sort chronologically.
- [ ] All 12 relationships exist; #10 and #11 are **inactive**; everything else active.
- [ ] No relationship is bidirectional. No `FactClaims ↔ FactPayments` link.
- [ ] No ambiguity warning; no auto-deactivated relationship you didn't intend.
- [ ] A quick matrix of `DimProduct[ProductName]` × `SUM(FactPremiums[PremiumAmount])` totals
      **13,189,230 TND** (matches SQL/Python) — proves relationships filter correctly.
- [ ] `SUM(FactClaims[ClaimAmount])` = **11,226,450**; `SUM(FactPayments[AmountPaid])` = **6,126,660**.
- [ ] Keys and helper columns hidden; `_Measures` table created.

When every box is ticked, the model is sound → Phase 7 (DAX measure library).

See `documentation/star_schema.svg` for the target diagram.
