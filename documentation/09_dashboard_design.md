# 09 — Power BI Dashboard Design (Phase 9)

Four report pages — **Executive · Claims · Customer · Risk** — built on the Phase 6 model and
Phase 7 measures. This spec gives, per page: layout, visuals, exact fields/measures, slicers,
interactions, and the professional touches (drill-through, tooltips, bookmarks, conditional
formatting, dynamic titles). Wireframe: `documentation/dashboard_executive_wireframe.svg`.

---

## Design system (apply to all pages)

| Token | Value | Use |
|---|---|---|
| Navy | `#0B2545` | headers, KPI text, primary bars |
| Teal | `#2A9D8F` | positive / premium series |
| Muted orange | `#E76F51` | claims series, warnings |
| Red | `#D00000` | **risk only** — High tier, alerts |
| Slate | `#264653` | secondary text, date series |
| Light gray | `#F8F9FA` | page background |
| White | `#FFFFFF` | card backgrounds |

- **Font:** Segoe UI. Titles 14–16 bold, KPI values 28–32 bold, body 10–11.
- **Grid:** 12-column feel; 16px gutters; KPI cards in a top row of equal width.
- **Money:** `#,0 "TND"`; large values `#,0,"K"`/`,,"M"`. Ratios as %.
- **Consistency:** same slicer panel (left, 220px) on every page; same card style (white, soft
  shadow, 8px radius); one accent color per metric family (premium=teal, claims=orange).
- **Restraint:** no 3-D, no pie beyond 1 small share chart, no chart-junk. White space is a feature.

---

## PAGE 1 — Executive Overview
*Audience: management. Must communicate performance in ~30 seconds.*

**KPI row (6 cards):** `Total Premiums` · `Incurred Claims` · `Total Claims Paid` ·
`Active Policies` · `Loss Ratio` · `Customer Retention Rate`.
- Loss Ratio card: conditional color — teal < 75%, orange 75–90%, red > 90%.

**Body:**
| Zone | Visual | Fields / Measures |
|---|---|---|
| Left wide | **Line chart** premium vs claims over time | Axis `DimDate[MonthYearLabel]`; lines `[Total Premiums]`, `[Incurred Claims]` |
| Right | **Bar** premiums by product | Axis `DimProduct[ProductName]`; value `[Total Premiums]` |
| Mid-left | **Map / bar** performance by branch | `DimBranch[Governorate]`; `[Total Premiums]` |
| Mid-right | **KPI with YoY** | `[Total Premiums]`, `[Premium YoY %]` as callout |
| Bottom | **Clustered column** YoY compare | Axis `DimDate[Year]`; `[Total Premiums]`, `[Incurred Claims]` |

**Slicers:** Year, Product, Governorate. **Interactions:** cross-filter on; clicking a product
filters the trend + branch visuals. **Dynamic title:** `= "Executive Overview — " & SELECTEDVALUE(DimDate[Year], "All Years")`.

---

## PAGE 2 — Claims Analysis

**KPI row (5):** `Total Claims` · `Approved Claims` · `Rejected Claims` · `Pending Claims` ·
`Average Claim Amount`.

| Zone | Visual | Fields / Measures |
|---|---|---|
| Left | **Donut** claim status mix | Legend `FactClaims[ClaimStatus]`; value `[Total Claims]` |
| Center | **Bar** claims by product | `DimProduct[ProductName]`; `[Total Claims]`, tooltip `[Incurred Claims]` |
| Right | **Map/bar** claims by governorate | `DimCustomer[Governorate]`; `[Total Claims]` |
| Mid | **Line** claims by month | `DimDate[MonthYearLabel]`; `[Incurred Claims]` |
| Mid | **Card + gauge** processing time | `[Average Processing Time]` (target line 60d) |
| Bottom | **Table** claim detail (drill-through target) | ClaimID, ClaimDate, Product, ClaimType, ClaimAmount, ClaimStatus, `[Average Processing Time]` |

**Slicers:** ClaimStatus, Product, Year. **Drill-through:** from any product/governorate visual →
this page filtered to that selection (set page as drill-through on `ProductName`).
**Conditional formatting:** ClaimStatus data bars; Rejected rows tinted. **Tooltip page:** a mini
tooltip showing status split + avg amount for the hovered product.

---

## PAGE 3 — Customer Intelligence

**KPI row (4):** `Total Customers` · `Active Customers` · `New Customers` · `Customer Retention Rate`.

| Zone | Visual | Fields / Measures |
|---|---|---|
| Left | **Bar** customers by segment | `DimCustomer[CustomerSegment]`; `[Total Customers]` |
| Center | **Stacked bar** customers by governorate × type | `Governorate` × `CustomerType`; `[Total Customers]` |
| Right | **Column** premium per customer by segment | `CustomerSegment`; `[Average Premium per Customer]` |
| Mid | **Histogram** age distribution | `DimCustomer[Age]` (bins); count |
| Mid | **Donut** gender split | `DimCustomer[Gender]` |
| Bottom | **Line** new customers over time | `DimDate[MonthYearLabel]`; `[New Customers]` |

**Slicers:** Segment, CustomerType, Governorate, Gender. **Interactions:** segment ↔ geography
cross-filter. **Dynamic title** reflects selected segment.

---

## PAGE 4 — Risk & Fraud Indicators
*Header banner (navy): "Preliminary screening for human review — not a fraud determination."*

**KPI row (5):** `High-Risk Claims` · `Medium-Risk Claims` · `Low-Risk Claims` ·
`Average Risk Score` · `% Claims Flagged`.

| Zone | Visual | Fields / Measures |
|---|---|---|
| Left | **Column** claims by risk category | `FactClaimIndicators[RiskCategory]`; `[Total Claims]` — color Low teal / Med orange / High red |
| Center | **Histogram** risk score distribution | `RiskScore` (bins of 10); count |
| Right | **Bar** which rule fires most | measures per rule (or `RepeatedClaimIndicator` sum, etc.) |
| Mid | **Scatter** amount vs deviation | X `ClaimAmountDeviation`, Y `ClaimAmount`, color `RiskCategory` |
| Bottom | **Flagged-claims table** (score ≥ 30) | ClaimID, Customer, Product, ClaimAmount, PreviousClaimsCount, DaysSincePreviousClaim, ClaimAmountDeviation, RepeatedClaimIndicator, RiskScore, RiskCategory |

**Slicers:** RiskCategory, Product, Governorate. **Conditional formatting:** RiskScore color scale
(green→red); High rows red left-border. **Table filter:** visual-level filter `RiskScore ≥ 30`.
**Drill-through:** from a flagged claim → the Claims detail page for full context.

---

## Cross-page professional features

- **Navigation:** a left nav with 4 buttons (bookmarks + page navigation action); current page highlighted.
- **Bookmarks:** "Reset filters" button (bookmark capturing cleared slicers); optional "Focus mode" for each hero chart.
- **Tooltips:** report-page tooltips for product and governorate (mini KPI + trend).
- **Dynamic titles:** every page title reacts to slicer selection via a title measure.
- **Conditional formatting:** Loss Ratio and RiskScore use the traffic-light thresholds above.
- **Sync slicers:** Year syncs across Executive/Claims/Customer so context carries between pages.
- **Accessibility:** avoid red/green-only encodings for non-risk metrics; label values directly.
- **Performance:** base every visual on measures (not implicit column aggregations); hide unused columns.

## Validation before "done"

- Executive `Total Premiums` card = **13,189,230 TND** with no slicers (ties to SQL/Python).
- `Incurred Claims` = **9,540,610**; `Loss Ratio (written)` ≈ **85.1%**.
- Risk page: High = **32**, Flagged % = **12.7%**.
- Every slicer cross-filters without errors; drill-through lands on the right filtered context.

> Screenshots of each finished page go in `screenshots/` and are embedded in the README (Phase 10).
