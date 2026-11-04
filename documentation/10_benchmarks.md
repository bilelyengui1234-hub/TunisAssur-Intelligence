# 10 — Tunisian Insurance Market Benchmarks (Phase 11 of the brief)

External context for the project. **These are real, published market statistics — they are NOT
our synthetic data.** TunisAssur is fictional; this page lets a reader sanity-check whether the
*shape* of our synthetic model is plausible against the real Tunisian market, and gives honest
notes where it diverges.

> ⚠️ Sources sometimes disagree (different vintages/revisions). Figures are shown with `≈` and
> cited. Always verify against the primary FTUSA report before quoting in a real setting.

---

## Real market snapshot (FTUSA / Atlas Magazine / UNDP)

| Indicator | Real market | Year |
|---|---|---|
| Total premiums (whole market) | ≈ **3,445.9 MD** (million dinars) | 2023 |
| Total premiums | ≈ 3,819.6 MD (+10.85%) | 2024 |
| **Motor (automobile) share** | ≈ **40.8–41%** of premiums (~1,406–1,413 MD) | 2023 |
| Motor share | ≈ 39.64% | 2024 |
| **Life** share | ≈ 17.5% (UNDP) to ~28% (Atlas) — *sources disagree* | 2023 |
| **Health** share | ≈ 15% | 2023–24 |
| Avg motor premium / inhabitant | ≈ 117 TND | 2023 |
| Insurance penetration | ≈ 1.8%–2.34% of GDP | 2023 |
| Insurance density | ≈ 97 USD / ≈ 313 TND per capita | 2024 |
| Active insurance companies | ≈ 21 | 2023 |

Key real-world takeaways: **motor dominates the Tunisian market** (~40% of premium), penetration
is **low** (~2% of GDP — room to grow), and the market is **growing ~10%/year**.

---

## Synthetic project vs. the market (honest comparison)

| Dimension | TunisAssur (synthetic) | Real market | Verdict |
|---|---|---|---|
| Motor share **by policy count** | 36.2% | — | plausible |
| Motor share **by premium** | ~22% (Automobile) | ~41% | **diverges** (see note) |
| Top line **by premium** | Professionnelle (~40%) | Motor | **diverges** |
| Health share (policies) | 22% | ~15% (premium) | different basis, broadly plausible |
| Loss ratio | 85% (by design) | varies; motor often stressed | plausibly "margin pressure" |
| Growth over window | rising each year | ~10%/yr | directionally correct |
| Governorate concentration | Tunis/Sfax/Sousse lead | matches population | realistic |

**Honest divergence note:** our synthetic *premium* mix is led by **Professionnelle**, because we
gave businesses high premiums and skewed them to that product. The **real** market is led by
**Motor premium**. This is a known calibration choice, not an accident. To make the premium mix
mirror the market, you would (a) raise Automobile's `premium_min/max` and/or policy share, and
(b) reduce the Entreprise→Professionnelle skew in `generate_policies.py` — then re-run Phase 2.
Documenting this trade-off openly is itself good analyst practice.

---

## How to present benchmarks in the report

- Add a **reference line** (e.g. market motor share ~41%, market loss ratio target) on the
  relevant Executive/Claims visuals, clearly labelled **"Tunisian market (FTUSA 2023)"**.
- Never blend market totals into company measures — show them as annotations or a separate
  "Market context" card, so synthetic ≠ real is unambiguous.
- State penetration (~2% of GDP) as the growth narrative: an under-insured market.

---

## Sources

- FTUSA — *Le Marché Tunisien des Assurances 2023* — https://www.ftusanet.org/wp-content/uploads/2024/10/Rapport-FTUSA-2023.pdf
- FTUSA — 2024 report — https://www.ftusanet.org/wp-content/uploads/2025/12/Rapport-FTUSA-02122025.pdf
- Atlas Magazine — *The Tunisian insurance market* — https://www.atlas-mag.net/en/articles/tunisian-insurance-market-1
- UNDP — *Regional Diagnostic: Insurance and Risk Financing in Arab States* — https://www.undp.org/sites/g/files/zskgke326/files/2026-02/regional-diagnostic_arab-states.pdf
- African Manager — *Tunisia penetration 2.34% of GDP* — https://en.africanmanager.com/tunisia-ranks-fifth-in-africa-for-insurance-penetration-at-2-34-of-gdp/

> Figures retrieved 2026; always reconcile with the latest primary FTUSA report.
