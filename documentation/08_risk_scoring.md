# 08 — Claims Risk Scoring (Phase 8)

A **transparent, rule-based preliminary screening** system that flags claims for **human
review**. It is deliberately simple, explainable and auditable — the opposite of a black box.

> **This is not fraud detection.** A high score means "a human should look at this," never
> "this is fraud." See *Limitations & ethics* below.

Implementation: `python/generate_risk_indicators.py` → `data/cleaned/claim_indicators.csv`
→ Postgres `FactClaimIndicators` (1:1 with FactClaims). Deterministic (no randomness).

---

## The rules

| # | Indicator | Condition | Points |
|---|---|---|---:|
| R1 | **High frequency** | more than 3 claims by the same customer in a trailing 12 months | 30 |
| R2 | **Unusual amount** | claim amount > 3× the average for its product category | 30 |
| R3 | **Rapid succession** | another claim by the same customer within 30 days | 20 |
| R4 | **Repeated vehicle** | the same vehicle appears on more than one claim | 20 |

**RiskScore = min(100, R1 + R2 + R3 + R4).**

| Score | Category |
|---|---|
| 0–29 | **Low** |
| 30–59 | **Medium** |
| 60–100 | **High** |

## The stored indicators (`FactClaimIndicators`, 1:1 with FactClaims)

| Column | Meaning |
|---|---|
| `PreviousClaimsCount` | prior claims by the same customer within the last 12 months (feeds R1) |
| `DaysSincePreviousClaim` | days since that customer's previous claim (feeds R3); null if first claim |
| `ClaimAmountDeviation` | `ClaimAmount ÷ category average` (feeds R2); e.g. 3.50 = 3.5× the norm |
| `RepeatedClaimIndicator` | 1 if the vehicle appears on >1 claim (feeds R4) |
| `RiskScore` | 0–100 total |
| `RiskCategory` | Low / Medium / High |

## Why these rules (business logic)

- **R1 Frequency** — a customer filing many claims in a year is statistically unusual and worth a look.
- **R2 Amount** — comparing *to the product's own average* (not a global one) is fair: a 20,000 TND
  life claim is normal, a 20,000 TND health claim is not.
- **R3 Rapid succession** — several claims bunched within 30 days can indicate staged events (or
  simply a bad month — hence *review*, not *accuse*).
- **R4 Repeated vehicle** — the same car on multiple claims is a classic pattern to verify.

## Results on this dataset

| Category | Claims | Share |
|---|---:|---:|
| Low | 3,493 | 87.3% |
| Medium | 475 | 11.9% |
| High | 32 | 0.8% |

- **Flagged for review (score ≥ 30): 507 claims (12.7%).** Average score 10.4.
- Example — `CLM02496`: 3 prior claims in 12 months (R1), another within 7 days (R3), 3.5×
  category amount (R2), repeated vehicle (R4) → **score 100 (High)**. That is a genuinely
  review-worthy profile, assembled from four independently explainable signals.

## Where this can run

The same rules can live in Python (done here), **SQL** (window functions over FactClaims), or
**DAX** (measures over the model). We chose Python so the indicators are precomputed once and
served as a clean 1:1 fact table — fast in Power BI and reproducible.

## Limitations & ethics (keep this on the Risk dashboard page)

1. **Screening, not proof.** A high score is a prompt for human investigation. No customer is
   labelled fraudulent by the system.
2. **False positives are expected.** Legitimate customers *can* have a bad year (accident +
   theft + health event). The rules will flag them; a human clears them.
3. **Severity differs by product** — R2 uses category-relative deviation precisely to avoid
   penalising inherently high-value lines (Vie), but no normalisation is perfect.
4. **Small samples** — a customer with 2 claims is a weaker signal than one with 10; the flat
   point system does not weight confidence.
5. **Synthetic-data bias** — this data was generated with known rules, so the screening partly
   rediscovers its own generator. On real data, thresholds must be re-tuned against outcomes.
6. **Thresholds are policy choices**, not facts. 3 claims / 3× / 30 days are starting points to
   be validated with the claims team and adjusted to the true base rate of confirmed fraud.
