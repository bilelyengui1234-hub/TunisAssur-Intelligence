-- ======================================================================
-- data_validation.sql — integrity & sanity checks (run after load_data.sql)
--     psql -U postgres -d tunisassur -f sql/data_validation.sql
-- Each query should return 0 problem rows (or sensible totals). FKs are
-- already enforced by the schema; these queries prove it and add business checks.
-- ======================================================================

\echo '--- 1. Row counts ---'
SELECT 'customers' t, count(*) FROM DimCustomer
UNION ALL SELECT 'policies', count(*) FROM DimPolicy
UNION ALL SELECT 'premiums', count(*) FROM FactPremiums
UNION ALL SELECT 'claims',   count(*) FROM FactClaims
UNION ALL SELECT 'payments', count(*) FROM FactPayments;

\echo '--- 2. Orphan foreign keys (expect 0 each) ---'
SELECT count(*) AS claims_orphan_policy
FROM FactClaims c LEFT JOIN DimPolicy p USING (PolicyID) WHERE p.PolicyID IS NULL;
SELECT count(*) AS payments_orphan_claim
FROM FactPayments pay LEFT JOIN FactClaims c USING (ClaimID) WHERE c.ClaimID IS NULL;

\echo '--- 3. Payments must reference APPROVED claims (expect 0) ---'
SELECT count(*) AS payments_on_non_approved
FROM FactPayments pay JOIN FactClaims c USING (ClaimID)
WHERE c.ClaimStatus <> 'Approved';

\echo '--- 4. A claim must never be paid beyond its amount (expect 0) ---'
SELECT count(*) AS overpaid_claims FROM (
    SELECT c.ClaimID, c.ClaimAmount, SUM(pay.AmountPaid) paid
    FROM FactClaims c JOIN FactPayments pay USING (ClaimID)
    GROUP BY c.ClaimID, c.ClaimAmount
    HAVING SUM(pay.AmountPaid) > c.ClaimAmount
) q;

\echo '--- 5. Date-range check: events inside 2022-2025 (expect 0 out-of-range) ---'
SELECT
  SUM((TransactionDate < DATE '2022-01-01' OR TransactionDate > DATE '2025-12-31')::int) AS prem_out
FROM FactPremiums;

\echo '--- 6. Headline KPI sanity: loss ratio ---'
SELECT
  (SELECT SUM(PremiumAmount) FROM FactPremiums)                         AS written_premium,
  (SELECT SUM(ClaimAmount)   FROM FactClaims)                           AS incurred_all,
  (SELECT SUM(ClaimAmount)   FROM FactClaims
     WHERE ClaimStatus IN ('Approved','Pending'))                       AS incurred_appr_pending,
  (SELECT SUM(AmountPaid)    FROM FactPayments)                         AS claims_paid,
  ROUND( (SELECT SUM(ClaimAmount) FROM FactClaims)
         / (SELECT SUM(PremiumAmount) FROM FactPremiums) * 100, 1)      AS loss_ratio_pct;
