# CLAUDE.md — TunisAssur Intelligence

Project memory for Claude. Read this first every session. Keep the **Current status** and
**Phase checklist** sections up to date as work progresses.

---

## What this project is

**TunisAssur Intelligence** — an end-to-end Business Intelligence *portfolio* project for a
**fictional** Tunisian insurance company. Goal: a recruiter-ready demonstration of the full
BI lifecycle (synthetic data → SQL → star-schema model → DAX → claims-risk screening →
4-page Power BI report). The user is building this to land a Junior BI / Data Analyst /
Power BI Developer role.

**Mentor mode:** act as a Senior BI Architect supervising a junior. Explain the *why* before
the *how*, challenge wrong assumptions, explain grain before creating tables, don't dump all
code at once, validate each layer before building the next.

**Ethics:** all company data is synthetic (fixed seed). Never present it as real. Risk
scoring is *preliminary screening for human review*, never an automated fraud verdict.

Full brief lives in the chat history (the "MASTER PROJECT PROMPT"); the paste ended
mid-Section 11 (Tunisian market benchmarks) — re-request the rest before Phase 10.

---

## Environment (verified 2025, user machine)

- OS: Windows 11. Shell: PowerShell primary, Bash available.
- Python **3.13.2** at `C:\Users\MSI\AppData\Local\Programs\Python\Python313`.
  - Installed: `pandas 3.0.5`, `numpy 2.4.6`. SQLite built in (`sqlite3` 3.45.3).
  - **NOT installed:** `Faker` (we use curated Tunisian reference pools instead — better realism + reproducibility).
- git **2.55** available. Repo **not yet initialized** (do it at first milestone commit).
- **PostgreSQL** runs in DOCKER (container `tunisassur-pg`, postgres:17, pwd TunisAssur2025, db tunisassur, port 5432).
  EDB direct install is 403-blocked on this machine. Docker Desktop must be started first; then `docker start tunisassur-pg`.
- Project root: `C:\Users\MSI\Desktop\TunisAssur-Intelligence`.

## Conventions

- **Fixed random seed** for ALL generators so data is reproducible. Define one seed constant, reuse everywhere.
- Two data versions: `data/raw/` (with controlled quality issues) and `data/cleaned/` (validated).
- Reference lookups in `data/reference/`. Modular Python (one generator per entity) in `python/`.
- Currency: **TND**. Date coverage: **Jan 2022 – Dec 2025**.
- Write CSVs UTF-8. Document each decision in `documentation/`.

---

## Locked architecture decisions (see `documentation/01_data_architecture.md`)

1. **Star schema**, conformed dimensions, single-direction filters only. No bidirectional relationships.
2. **DimPolicy is the hub**; PolicyID is carried on all three fact tables.
3. **Three independent fact tables** — FactPremiums, FactClaims, FactPayments — **never joined to each other**.
   Cross-process KPIs (e.g. Loss Ratio) = two separate aggregations divided (fan-out-proof).
4. **Grains:** FactPremiums = 1 premium txn; FactClaims = 1 claim; FactPayments = 1 payment
   (multiple per claim); FactClaimIndicators = 1 claim (1:1 risk enrichment).
   `ClaimAmount` only on FactClaims; `AmountPaid` only on FactPayments.
5. **Financial terms fixed:** written ≠ collected ≠ earned premium; incurred ≠ paid ≠ outstanding claims.
   **Loss Ratio = Incurred Claims ÷ Earned Premiums.** Earned = monthly pro-rata (not daily).
6. **DimDate** marked as date table; integer `DateKey` yyyymmdd; **no auto date hierarchy**.
   Role-playing claim dates (ClaimDate active; ApprovalDate/ClosureDate inactive via `USERELATIONSHIP`).
7. **Renewal = new PolicyID, same CustomerID** (so retention is measurable).
8. **Governorate meaning:** customer-governorate for claims/customer analysis; branch-governorate for branch performance.
9. 5 products: Automobile, Santé, Vie, Habitation, Professionnelle. Branches: 20–30. Customers 5,000; Policies 8,000; Premiums ~8,000; Claims 4,000; Payments > claims.

---

## Current status

**Phase 0 COMPLETE** — architecture designed, scaffolded, approved.
**Phase 1 COMPLETE** — reference pools built & verified. Files:
- `python/config.py` — SEED=42, paths, date window (2022–2025), target sizes (5k cust / 8k pol / 4k claims / 24 branches), CURRENCY=TND.
- `python/reference_data.py` — curated pools (importable constants) + CSV writer + sanity checks.
- `data/reference/`: governorates.csv (24, weighted & normalized), cities.csv (98), products.csv (5, policy_share sums to 1.0 + premium/claim params), first_names.csv (80, gender-tagged), surnames.csv (40).

**Phase 2 COMPLETE** — all 7 generators done; PRISTINE ground-truth in `data/cleaned/`
(Phase 3 will derive messy `data/raw/` from these by injecting controlled issues).
- `python/utils.py` — `get_rng(offset)` (independent seeded substreams per generator), date helpers, PK check.
- DONE `python/generate_branches.py` (offset 1) → cleaned/branches.csv (24, open pre-2022, validated).
- DONE `python/generate_customers.py` (offset 2) → cleaned/customers.csv (5,000, validated:
  weighted geography, gender-consistent names, Age 18–80, reg after 18th birthday & in window,
  Particulier 84%/Entreprise 16%, segments by type).
- DONE `python/generate_policies.py` (offset 3) → cleaned/policies.csv (8,000, validated: PK/FK,
  dates >= reg & in window, all customers >=1 policy, status in {Active,Expired,Cancelled}, auto<->vehicle).
  Renewal chains (new PolicyID, consecutive years, shared vehicle). Mix: Active 3444/Expired 4198/
  Cancelled 358; multi-policy custs 2143; auto policies 2898 (InsuredAssetID VEHnnnnn = seed for DimVehicle).
  INTENTIONAL deviation: Professionnelle ~18% (vs 10% ref share) due to Entreprise->PRD005 50% skew.
- DONE `python/generate_premiums.py` (offset 4) → cleaned/premiums.csv (8,000 = 1 per policy,
  validated: PK/FK, net=prem-disc, txn in policy period & window). Grain = 1 txn per policy term
  (NOT exploded by PaymentFrequency). Written 13.19M / Net 12.71M / Collected(Paid) 9.75M TND;
  status Paid 77%/Pending 14%/Late 9%. Written vs Collected is now derivable from PaymentStatus.
- DONE `python/generate_claims.py` (offset 5) → cleaned/claims.csv (4,000, validated: PK/FK, ClaimDate
  in policy period & window, status∈{Approved,Rejected,Pending}, Pending⇔null ApprovalDate, date ordering
  claim≤approval≤closure, auto↔vehicle). Propensity = claim_frequency×exposure; a policy may be drawn >1×.
  Status: Approved 2211/Pending 1214/Rejected 575. By product: Auto 1689/Sante 1365/Prof 538/Hab 347/Vie 61.
  228 policies with ≥3 claims (risk candidates). Avg processing (claim→closure) 70 days.
  CALIBRATION: initial severities gave ~164% loss ratio → added `SEVERITY_SCALE=0.52` in reference_data.py
  (user chose ~85% "margin pressure"). Now incurred(all) 11.23M = 85.1% of written; incurred(Appr+Pending)
  9.54M = 72.3%. products.csv severity cols are POST-scale. Re-targeting LR = change SEVERITY_SCALE & rerun
  reference_data.py + generate_claims.py.
- DONE `python/generate_payments.py` (offset 6) → cleaned/payments.csv (3,210, validated: PK, ClaimID⊆
  approved, PolicyID matches claim, date≥approval & in window, per-claim sum≤ClaimAmount, settled⇒fully paid).
  Grain = 1 payment; 1–3 per claim (avg 1.45). Carries PolicyID (fan-out-proof). Approved claims 2211;
  total paid 6.13M; fully-settled 2151/partial 60; status Effectue 3071/En cours 139.
  NOTE: Outstanding Claims KPI (DAX) = Incurred − Paid incl. the 1214 Pending claims (~3.4M), NOT the
  tiny 55K approved-partial gap. Data supports it.
- DONE `python/generate_vehicles.py` (offset 7) → cleaned/vehicles.csv (1,989 DISTINCT vehicles —
  NOT 2898: that was auto policy ROWS; renewal chains share a vehicle. Validated: PK, VehicleID set ==
  auto policies' InsuredAssetID exactly, FK CustomerID, ManufacturingYear 1998–2025, VehicleAge=2025−year).
  Tunisian fleet (VW/Peugeot/Renault lead), types Berline/Citadine/SUV/Utilitaire, avg age 11.8y.
- RNG offsets used: branches=1, customers=2, policies=3, premiums=4, claims=5, payments=6, vehicles=7. (all used)
- Deferred refinement: some Entreprise customers are very young (bias to 30+ later if desired).

**Phase 3 COMPLETE — DATA QUALITY.**
- DONE `python/inject_quality_issues.py` (offset 10) → data/raw/*.csv + documentation/03_data_quality.md.
  Injected 3,544 CONTROLLED issues (missing, dup rows, text case, mixed date formats, governorate spelling
  variants, negative/zero numerics, inconsistent categoricals). PKs left cleanable (dups allowed). Seeded.
- DONE `python/validate_data.py` — reusable validator. `python python/validate_data.py` → cleaned/ PASSES
  (0 issues, asserts); `... raw` → 13 issue groups (dup PKs, invalid amounts, categorical-case side effects).
  Checks: row counts, PK uniqueness, FK integrity, date ranges, non-neg amounts, claims↔payments consistency.
- data/raw/ = dirty source (for Power Query to clean); data/cleaned/ = validated ground truth (target).

**Phase 4 COMPLETE — SQL LAYER (PostgreSQL 17 in DOCKER).**
- EDB installer download is BLOCKED for this machine (get.enterprisedb.com → 403, geo/hotlink). winget
  PostgreSQL.PostgreSQL.17 fails at download. So we run Postgres in Docker instead (image from Docker Hub).
- Container: `tunisassur-pg` = `postgres:17`, port 5432, db `tunisassur`, user `postgres`, password
  `TunisAssur2025`. Project mounted at /project (`-v C:/Users/MSI/Desktop/TunisAssur-Intelligence:/project`).
  Start Docker Desktop first (`"C:\Program Files\Docker\Docker\Docker Desktop.exe"`), then
  `docker start tunisassur-pg` (already created). Recreate: see the docker run in session history.
- RUN SQL (from project root, Git Bash): prefix `export MSYS_NO_PATHCONV=1` (else /project path mangles), then
  `docker exec -w /project tunisassur-pg psql -U postgres -d tunisassur -f sql/<file>.sql`.
- Files: sql/schema.sql (DDL + PK/FK/CHECK + indexes), sql/load_data.sql (\copy cleaned CSVs, FK order),
  sql/data_validation.sql (integrity + KPI), sql/analytical_queries.sql (7 business queries). ALL RUN GREEN.
- Loaded counts match exactly. Validation: 0 orphans/overpaid/out-of-range. SQL KPIs == Python:
  written 13,189,230 / incurred 11,226,450 / paid 6,126,660 / LOSS RATIO 85.1%.

**Phase 5 GUIDE DELIVERED — POWER QUERY.** documentation/05_power_query_steps.md written: full
step-by-step cleaning of data/raw/ → analysis-ready, each step why/how/M-code/verify. Includes fnParseDate
(mixed date formats, day-first), governorate standardization (Trim/Proper + accent Replace, or Merge w/
reference — recommended), Gender/PolicyStatus/ClaimStatus/PaymentStatus canonicalization, remove-duplicates
on PK, invalid-numeric filtering, null→"Inconnu", query groups (_Functions/01_Reference/02_Dimensions/03_Facts).
This phase is GUI work the USER applies in Power BI Desktop — guide is the deliverable. (Alternatively they
can connect Power BI directly to the clean Postgres/cleaned CSVs and skip manual cleaning.)

**Phase 6 COMPLETE (guide + artifacts) — DATA MODEL.**
- DONE `python/generate_dimdate.py` → cleaned/dimdate.csv (1,461 days 2022–2025; DateKey int yyyymmdd;
  French month/day names + sort keys; validated no gaps). Also loaded to Postgres via sql/dim_date.sql.
- DONE documentation/06_data_model.md — full model guide: 12-relationship matrix, mark-as-date-table,
  sort-by-column, role-playing DAX (USERELATIONSHIP), hygiene (hide keys, _Measures table, display folders,
  single-direction), QA checklist with expected totals (premiums 13,189,230 / claims 11,226,450 / paid 6,126,660).
- DONE documentation/star_schema.svg — portfolio diagram of the final model.
- ⭐ PROFESSIONAL REFINEMENT vs Phase 0 sketch: DimVehicle connects ONLY to DimPolicy (via InsuredAssetID);
  NO DimCustomer→DimVehicle and NO DimVehicle→FactClaims (those create ambiguous filter paths). Claims/payments
  inherit vehicle through the policy. FactClaims[VehicleID] = hidden degenerate column. Owner via policy→customer.
- Relationships: DimDate→Fact on the DATE columns (not DateKey); ClaimDate active, Approval/Closure inactive.
  This phase is applied by the USER in Power BI Desktop (GUI); guide + DimDate + diagram are the deliverables.

**Phase 7 COMPLETE (library delivered) — DAX MEASURES.** documentation/07_dax_measures.md: full library in
5 folders (Financial/Claims/Customer/Time Intelligence/Risk), each measure with formula + explanation +
filter context + numeric example (vs anchors) + pitfalls. Key definitions LOCKED:
- Incurred Claims = Approved+Pending only (excl Rejected) = 9,540,610; Total Claims Amount (all) = 11,226,450.
- Loss Ratio = Incurred ÷ Earned Premiums (accrual); quick proxy Loss Ratio(written)=Total Claims Amount÷Written=85.1%.
- Earned Premiums = day-overlap pro-rata with REMOVEFILTERS(DimDate) (captures PeriodStart/End first) — the key gotcha.
- Outstanding = Incurred − Paid (≈3.41M, incl 1214 Pending). Retention = Active Customers ÷ Total (documented proxy).
- Time-intel uses SAMEPERIODLASTYEAR/TOTALYTD/DATEADD on DimDate[Date] (marked date table).
- Risk measures (High/Med/Low, Avg Risk Score, % Flagged) reference Phase-8 RiskScore/RiskCategory — activate after Phase 8.
User builds these in the _Measures table in Power BI. REMEMBER: cross-fact KPIs divide two scalars, never fact-to-fact join.

**Phase 8 COMPLETE — RISK SCORING.** python/generate_risk_indicators.py → cleaned/claim_indicators.csv
(4,000, 1:1 with claims, validated); loaded to Postgres via sql/risk_indicators.sql (FK→FactClaims).
Rules R1>3claims/12mo=30, R2 amount>3×cat-avg=30, R3 within30d=20, R4 repeated vehicle=20; min(100). Dist:
Low 3493 / Medium 475 / High 32; flagged(≥30) 507 (12.7%); avg score 10.4. documentation/08_risk_scoring.md
(rules + limitations/ethics: screening not fraud). Activates Phase-7 risk measures (RiskScore/RiskCategory on FactClaimIndicators).

**Phase 9 COMPLETE — DASHBOARDS.** documentation/09_dashboard_design.md (design system + 4 page specs:
Executive/Claims/Customer/Risk — layout, visuals, exact fields/measures, slicers, drill-through, tooltips,
bookmarks, conditional formatting, dynamic titles, validation anchors) + documentation/dashboard_executive_wireframe.svg.
User assembles the .pbix in Power BI Desktop; screenshots → screenshots/ → README.

**Phase 10 COMPLETE — BENCHMARKS + DOCS.** documentation/10_benchmarks.md (REAL cited Tunisian market data —
FTUSA/Atlas/UNDP: total ~3,446 MD 2023, motor ~41% by premium, penetration ~2% GDP, ~21 companies; honest
note our synthetic PREMIUM mix is Professionnelle-led vs real Motor-led). documentation/data_dictionary.md
(all tables/columns). README.md fully rewritten (portfolio front door: stack, KPIs, reproduce steps, phases,
skills, interview talking points). 

**PROJECT COMPLETE (all 11 phases).** Remaining = USER hands-on in Power BI: apply Power Query (05), build
model (06), create measures (07), build dashboards (09), screenshot → screenshots/ + powerbi/TunisAssur.pbix.
Then git init + push to GitHub for the portfolio. Docker Postgres container tunisassur-pg holds the live DB.

## Phase checklist

- [x] 0. Architecture & setup
- [x] 1. Reference data (governorates, cities, products, name pools) — branches generated in Phase 2
- [x] 2. Synthetic data generation — DONE: branches(24), customers(5000), policies(8000), premiums(8000), claims(4000), payments(3210), vehicles(1989)
- [x] 3. Data quality (inject controlled issues → raw; validation scripts) — 3,544 issues; cleaned passes, raw fails as expected
- [x] 4. SQL layer — PostgreSQL 17 in Docker (container tunisassur-pg); schema+load+validation+7 queries all green
- [x] 5. Power Query — guide delivered (documentation/05_power_query_steps.md); user applies in PBI Desktop
- [x] 6. Data model — DimDate built+loaded; 06_data_model.md guide + star_schema.svg; vehicle-routing refinement (no ambiguity)
- [x] 7. DAX library — documentation/07_dax_measures.md (5 folders, every measure documented; Incurred/LossRatio/Earned/Outstanding locked)
- [x] 8. Risk scoring — rule engine → FactClaimIndicators (Low 3493/Med 475/High 32); 08_risk_scoring.md
- [x] 9. Dashboards — 09_dashboard_design.md (4 pages) + executive wireframe (user assembles .pbix)
- [x] 10. Benchmarks & docs — 10_benchmarks.md (cited FTUSA/Atlas/UNDP) + data_dictionary.md + README rewrite

## ✅ ALL 11 PHASES COMPLETE. Code/SQL/docs done. Remaining is USER hands-on in Power BI (build .pbix from
## guides 05/06/07/09, screenshot) + git init & push to GitHub.

## Power BI MCP notes

- Server: `powerbi-modeling-mcp` (wired into `claude_desktop_config.json`). **EULA accepted.**
- To use: open the `.pbix` in Power BI Desktop, then `connection_operations` ListLocalInstances
  → Connect (connection string from the listed instance). Put measures in a dedicated
  `_Calculations` table. `table_operations GetSchema` expects references as a **list**.
