# Data Dictionary — TunisAssur Intelligence

All tables are in `data/cleaned/` (CSV) and mirrored in PostgreSQL. 🔑 = primary key · 🔗 = foreign key.
Currency = TND. Date window = 2022-01-01 … 2025-12-31.

---

## DimCustomer — 5,000 rows (one per customer)
| Column | Type | Notes |
|---|---|---|
| 🔑 CustomerID | text | `CUSTnnnnn` |
| FirstName / LastName | text | gender-consistent first name |
| Gender | text | `M` / `F` |
| BirthDate | date | |
| Age | int | 18–80, derived from BirthDate |
| Governorate / City | text | real Tunisian locations |
| CustomerType | text | `Particulier` / `Entreprise` |
| RegistrationDate | date | ≥ 18th birthday, within growth window |
| CustomerSegment | text | Standard/Silver/Gold/Platinum (indiv.) · PME/Grand Compte (bus.) |

## DimPolicy — 8,000 rows (one per policy term) · **hub**
| Column | Type | Notes |
|---|---|---|
| 🔑 PolicyID | text | `POLnnnnn`; renewal = new PolicyID, same customer |
| 🔗 CustomerID | text | → DimCustomer |
| 🔗 ProductID | text | → DimProduct |
| 🔗 BranchID | text | → DimBranch |
| PolicyStartDate / PolicyEndDate | date | end > start; start ≥ registration |
| CoverageType | text | product-specific tier |
| PolicyStatus | text | `Active` / `Expired` / `Cancelled` |
| PaymentFrequency | text | Annuel / Semestriel / Trimestriel / Mensuel |
| 🔗 InsuredAssetID | text | → DimVehicle (auto only, else blank) |

## DimProduct — 5 rows
| Column | Type | Notes |
|---|---|---|
| 🔑 ProductID | text | `PRD00n` |
| ProductName / ProductCategory | text | Automobile, Santé, Vie, Habitation, Professionnelle |
| CoverageDescription | text | |
| policy_share, premium_min/max, claim_frequency, severity_min/max | num | generation parameters (severities POST `SEVERITY_SCALE=0.52`) |

## DimBranch — 24 rows
| Column | Type | Notes |
|---|---|---|
| 🔑 BranchID | text | `BRnn` |
| BranchName / Governorate / City | text | one agency per governorate |
| OpeningDate | date | before the data window |

## DimVehicle — 1,989 rows (one per insured vehicle)
| Column | Type | Notes |
|---|---|---|
| 🔑 VehicleID | text | `VEHnnnnn` = auto policies' InsuredAssetID |
| 🔗 CustomerID | text | owner (degenerate; not a model relationship) |
| VehicleBrand / VehicleModel / VehicleType | text | Tunisian fleet; Berline/Citadine/SUV/Utilitaire |
| ManufacturingYear / VehicleAge / RegistrationYear | int | avg age ≈ 11.8y |

## DimDate — 1,461 rows (one per day)
| Column | Type | Notes |
|---|---|---|
| 🔑 Date | date | mark-as-date-table key |
| DateKey | int | `yyyymmdd` |
| Year, Quarter, QuarterName, YearQuarter | | |
| MonthNumber, MonthName, MonthShort, YearMonth, YearMonthSort, MonthYearLabel | | French labels + sort keys |
| WeekOfYear, DayOfMonth, DayOfWeek, DayName, IsWeekend | | |

## FactPremiums — 8,000 rows (one premium txn per policy)
| Column | Type | Notes |
|---|---|---|
| 🔑 PremiumID | text | `PRMnnnnn` |
| 🔗 PolicyID | text | → DimPolicy |
| TransactionDate | date | within policy period & window |
| PremiumAmount | num | **Written** |
| DiscountAmount | num | loyalty/segment |
| NetPremiumAmount | num | Premium − Discount |
| PaymentStatus | text | Paid / Pending / Late (→ Collected) |
| PaymentMethod | text | |

## FactClaims — 4,000 rows (one per claim)
| Column | Type | Notes |
|---|---|---|
| 🔑 ClaimID | text | `CLMnnnnn` |
| 🔗 PolicyID | text | → DimPolicy |
| ClaimDate | date | active date relationship |
| ClaimType | text | by product category |
| ClaimAmount | num | incurred (right-skewed) |
| ClaimStatus | text | Approved / Rejected / Pending |
| ApprovalDate / ClosureDate | date | role-playing (inactive); null if Pending/open |
| ClaimDescription | text | |
| 🔗 VehicleID | text | auto only; hidden degenerate in the model |

## FactPayments — 3,210 rows (one per payment)
| Column | Type | Notes |
|---|---|---|
| 🔑 PaymentID | text | `PAYnnnnn` |
| 🔗 ClaimID | text | → FactClaims (approved only); **not** an active model relationship |
| 🔗 PolicyID | text | → DimPolicy (fan-out-proof rollups) |
| PaymentDate | date | ≥ ApprovalDate |
| AmountPaid | num | Σ per claim ≤ ClaimAmount |
| PaymentMethod / PaymentStatus | text | Effectue / En cours |

## FactClaimIndicators — 4,000 rows (1:1 with FactClaims)
| Column | Type | Notes |
|---|---|---|
| 🔑🔗 ClaimID | text | → FactClaims |
| PreviousClaimsCount | int | prior claims (same customer, 12 mo) |
| DaysSincePreviousClaim | int | null if first |
| ClaimAmountDeviation | num | ClaimAmount ÷ category avg |
| RepeatedClaimIndicator | int | 1 = vehicle on >1 claim |
| RiskScore | int | 0–100 |
| RiskCategory | text | Low / Medium / High |

## Reference files (`data/reference/`)
`governorates.csv` (24, weighted), `cities.csv` (98), `products.csv` (5), `first_names.csv` (80),
`surnames.csv` (40) — curated inputs to generation.
