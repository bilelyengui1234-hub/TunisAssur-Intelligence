# 01 — Data Architecture

**Status:** Phase 0 (design, pending approval)
**Modeling pattern:** Star schema with conformed dimensions and role-playing dates.

This document defines, *before any data is generated*, the structure of the model: the
**grain** of every table, the **keys**, the **relationships** (cardinality + filter
direction), and the single most dangerous trap in this project — combining measures from
three separate fact tables (premiums, claims, payments) without multiplying values.

---

## 1. Why a star schema (and not one big table)

A single flat table mixing premiums, claims and payments would **double- and triple-count**
money the moment one policy has several premiums, several claims, and several payments per
claim. The star schema keeps each business process in its **own fact table at its own
grain**, and connects them only through **shared (conformed) dimensions**. Facts are never
joined directly to each other.

```
                          ┌───────────────┐
                          │   DimDate      │  (conformed, role-playing)
                          └───────┬───────┘
                                  │
        ┌───────────────┐         │          ┌───────────────┐
        │  DimCustomer   │        │          │  DimProduct    │
        └───────┬───────┘         │          └───────┬───────┘
                │                 │                  │
                │        ┌────────┴────────┐         │
                └────────┤    DimPolicy     ├────────┘
                ┌────────┤  (central hub)   ├────────┐
                │        └────────┬─────────┘        │
        ┌───────┴──────┐  ┌───────┴──────┐  ┌────────┴───────┐
        │ FactPremiums │  │  FactClaims   │  │  DimBranch     │
        └──────────────┘  └───────┬──────┘  └────────────────┘
                                  │ (1 claim → many payments)
                          ┌───────┴──────┐        ┌──────────────┐
                          │ FactPayments │        │  DimVehicle  │
                          └──────────────┘        └──────────────┘
                          ┌────────────────────┐
                          │ FactClaimIndicators │  (1:1 with FactClaims)
                          └────────────────────┘
```

**DimPolicy is the hub.** Every financial event (a premium, a claim) belongs to exactly one
policy, and a policy carries the customer, product and branch. This is what lets us slice
premiums *and* claims by product/branch/governorate without relating the two fact tables
to each other.

---

## 2. Grain of every table

> **Grain = what one row represents.** Fix it first; every column must be true at that grain.

### Dimensions

| Table | Grain (one row = …) | Primary key | Approx. rows |
|---|---|---|---|
| **DimDate** | one calendar day | `DateKey` (yyyymmdd) | ~1,461 (2022–2025) |
| **DimCustomer** | one customer | `CustomerID` | 5,000 |
| **DimPolicy** | one insurance policy | `PolicyID` | 8,000 |
| **DimProduct** | one insurance product | `ProductID` | 5 |
| **DimBranch** | one agency/branch | `BranchID` | 20–30 |
| **DimVehicle** | one insured vehicle | `VehicleID` | ~ auto policies |

### Facts

| Table | Grain (one row = …) | Degenerate/PK | Approx. rows |
|---|---|---|---|
| **FactPremiums** | one premium transaction for a policy | `PremiumID` | ~8,000 |
| **FactClaims** | one claim filed against a policy | `ClaimID` | 4,000 |
| **FactPayments** | one compensation payment against a claim | `PaymentID` | > 4,000 (multiple per claim) |
| **FactClaimIndicators** | one claim (risk enrichment) | `ClaimID` (1:1) | 4,000 |

**Grain rules we commit to:**
- A customer can hold **many** policies → FactPremiums/FactClaims roll up to customer *via policy*.
- A policy can have **many** claims.
- A claim can have **many** payments (partial settlements, instalments).
- `ClaimAmount` lives **only** on FactClaims (the *incurred* amount). `AmountPaid` lives
  **only** on FactPayments. They are never stored in both places.

---

## 3. Relationships (cardinality + filter direction)

All relationships are **one-to-many, single-direction** (dimension → fact), unless noted.

| From (one) | To (many) | Key | Filter direction | Active? |
|---|---|---|---|---|
| DimCustomer | DimPolicy | CustomerID | single → | ✅ |
| DimProduct | DimPolicy | ProductID | single → | ✅ |
| DimBranch | DimPolicy | BranchID | single → | ✅ |
| DimPolicy | FactPremiums | PolicyID | single → | ✅ |
| DimPolicy | FactClaims | PolicyID | single → | ✅ |
| DimPolicy | FactPayments | PolicyID | single → | ✅ |
| DimVehicle | FactClaims | VehicleID | single → | ✅ |
| DimCustomer | DimVehicle | CustomerID | single → | ✅ |
| DimDate | FactPremiums | TransactionDate | single → | ✅ |
| DimDate | FactClaims | ClaimDate | single → | ✅ (role-playing) |
| DimDate | FactClaims | ClosureDate | single → | ⛔ inactive (USERELATIONSHIP) |
| DimDate | FactPayments | PaymentDate | single → | ✅ |
| FactClaims | FactClaimIndicators | ClaimID | single → | ✅ (1:1) |

### Key decisions
- **DimDate is marked as a date table** and drives all time intelligence. It is the single
  source of dates — we never use the model's auto date/time hierarchies (they bloat the file
  and break YTD logic).
- **Role-playing dates:** FactClaims has several meaningful dates (filed, approved, closed).
  We keep **one active** relationship (`ClaimDate`) and expose the others through
  `USERELATIONSHIP` inside dedicated measures (e.g. *Claims Closed YTD*). We do **not**
  duplicate DimDate into DimClaimDate/DimCloseDate — role-playing via USERELATIONSHIP is
  cleaner for this size.
- **Single-direction filtering everywhere.** No bidirectional relationships. They cause
  ambiguous filter paths and silent wrong totals in a multi-fact model.

---

## 4. The multi-fact trap (the core of this project)

> *"Never combine financial measures from different fact tables in a way that multiplies
> values due to joins or incorrect relationships."* — project brief.

**The danger:** if you relate `FactClaims` directly to `FactPayments` (claim → payments) and
then put `ClaimAmount` and `AmountPaid` in the same visual, each claim's `ClaimAmount` is
repeated once per payment row → **incurred is inflated** by the number of payments.

**Our solution — three independent stars sharing dimensions:**

1. `FactPremiums`, `FactClaims`, `FactPayments` each connect **only to dimensions**
   (DimPolicy, DimDate, …), never to each other with an active relationship.
2. `PolicyID` is carried on **all three** fact tables, so premiums, claims and payments all
   roll up by product / branch / governorate / customer **independently and correctly**.
3. Cross-process KPIs (e.g. **Loss Ratio = Incurred Claims ÷ Earned Premiums**) are built in
   **DAX measures**, each aggregating its *own* fact table, then dividing the two scalars.
   Two independent aggregations divided — **no row multiplication**.
4. "Paid vs incurred **per claim**" (a claim-grain comparison) is handled by
   **pre-aggregating total paid per claim in the ETL/SQL layer** into a `TotalPaidToClaim`
   column on `FactClaims`, *or* by a measure using `TREATAS`/`SUMX` over claim keys — never
   by an active FactClaims↔FactPayments join. FactPayments stays at payment grain for the
   payment-level detail table on the Claims page.

```
Loss Ratio  =  DIVIDE ( [Incurred Claims] , [Earned Premiums] )
                         ▲                    ▲
                 SUM over FactClaims   SUM over FactPremiums
                 (claim grain)         (premium grain)
                 — two scalars, divided. No fan-out.
```

---

## 5. Financial definitions (fixed now, to avoid sloppy KPIs later)

The brief is explicit that these must not be conflated:

| Term | Meaning in this model | Source |
|---|---|---|
| **Written premium** | premium contracted when the policy is issued | DimPolicy / FactPremiums |
| **Collected premium** | premium actually received (PaymentStatus = Paid) | FactPremiums |
| **Earned premium** | portion of premium that corresponds to elapsed coverage time | derived (pro-rata over policy period) |
| **Incurred claims** | total ClaimAmount of claims occurring in the period | FactClaims |
| **Paid claims** | compensation actually disbursed | FactPayments |
| **Outstanding claims** | incurred − paid (reserve still owed) | FactClaims − FactPayments (measure) |

> **Rule:** Loss Ratio uses **earned** premiums and **incurred** claims — never *collected*
> premiums as a stand-in for *earned*. Earned premium needs pro-rata time logic, which we'll
> define precisely in the DAX phase.

---

## 6. Deliberate design decisions & deviations

1. **`FactClaimIndicators` kept as a separate 1:1 table** (not merged into FactClaims) so the
   risk-scoring module is self-contained and auditable. It could equally be columns on
   FactClaims; the 1:1 split is a modularity choice, documented here.
2. **`DateKey` as integer `yyyymmdd`** on facts (not a datetime) for smaller, faster joins
   and clean sort order.
3. **No bidirectional filters, no auto date hierarchy** — standard star-schema hygiene.
4. **Risk scoring is preliminary screening, not fraud detection.** A high score flags a claim
   for *human review* only. Limitations (false positives, product severity differences, small
   samples, synthetic-data bias) are documented in the risk phase.
5. **Governorate lives on DimBranch and (via customer address) on DimCustomer** — we must be
   explicit in each visual whether "claims by governorate" means *branch* governorate or
   *customer* governorate. Decision: **customer governorate** for claims/customer analysis,
   **branch governorate** for branch performance. Documented to avoid silent mismatches.

---

## 7. Open questions to resolve before generation

- **Earned premium granularity:** monthly pro-rata is enough for this project (vs. daily).
- **Vehicle ↔ claim link:** only auto claims carry a `VehicleID`; all others are null — fine,
  the relationship just won't filter non-auto claims.
- **Policy renewal modelling:** a renewal = a *new* PolicyID linked to the same CustomerID
  (so retention is measurable), rather than extending one policy row. Confirm in Phase 2.
