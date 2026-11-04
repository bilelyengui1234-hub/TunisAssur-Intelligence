-- ======================================================================
-- analytical_queries.sql — the 7 business questions from the brief.
--     psql -U postgres -d tunisassur -f sql/analytical_queries.sql
-- Demonstrates JOIN, GROUP BY, HAVING, ORDER BY, CASE, aggregates,
-- date analysis, subqueries/CTEs. Each query states its business meaning.
-- NOTE: premiums, claims and payments are aggregated SEPARATELY and never
-- joined fact-to-fact (same rule as the Power BI model — avoids fan-out).
-- ======================================================================

\echo '=== Q1. Total premium revenue by product (written vs collected) ==='
-- Business: which products drive revenue, and how much is actually collected?
SELECT pr.ProductName,
       COUNT(*)                                            AS premiums,
       SUM(f.PremiumAmount)                                AS written_premium,
       SUM(f.NetPremiumAmount)                             AS net_premium,
       SUM(CASE WHEN f.PaymentStatus = 'Paid'
                THEN f.NetPremiumAmount ELSE 0 END)        AS collected_premium
FROM FactPremiums f
JOIN DimPolicy  p  ON p.PolicyID  = f.PolicyID
JOIN DimProduct pr ON pr.ProductID = p.ProductID
GROUP BY pr.ProductName
ORDER BY written_premium DESC;

\echo '=== Q2. Claims by governorate (customer governorate) ==='
-- Business: where do claims concentrate geographically?
SELECT cu.Governorate,
       COUNT(*)            AS claim_count,
       SUM(c.ClaimAmount)  AS total_incurred
FROM FactClaims c
JOIN DimPolicy   p  ON p.PolicyID   = c.PolicyID
JOIN DimCustomer cu ON cu.CustomerID = p.CustomerID
GROUP BY cu.Governorate
ORDER BY claim_count DESC;

\echo '=== Q3. Average claim amount by insurance type ==='
-- Business: severity profile per product line.
SELECT pr.ProductName,
       COUNT(*)                   AS claim_count,
       ROUND(AVG(c.ClaimAmount),0) AS avg_claim,
       MAX(c.ClaimAmount)         AS max_claim
FROM FactClaims c
JOIN DimPolicy  p  ON p.PolicyID  = c.PolicyID
JOIN DimProduct pr ON pr.ProductID = p.ProductID
GROUP BY pr.ProductName
ORDER BY avg_claim DESC;

\echo '=== Q4. Customers with more than 3 claims (frequency risk candidates) ==='
-- Business: who files unusually many claims? (HAVING on a grouped count)
SELECT cu.CustomerID,
       cu.FirstName || ' ' || cu.LastName AS customer,
       cu.Governorate,
       COUNT(*)           AS claim_count,
       SUM(c.ClaimAmount) AS total_incurred
FROM FactClaims c
JOIN DimPolicy   p  ON p.PolicyID   = c.PolicyID
JOIN DimCustomer cu ON cu.CustomerID = p.CustomerID
GROUP BY cu.CustomerID, customer, cu.Governorate
HAVING COUNT(*) > 3
ORDER BY claim_count DESC, total_incurred DESC;

\echo '=== Q5. Active policies expiring within 30 days (renewal pipeline) ==='
-- Business: retention action list. Reference "today" = end of data window.
WITH ref AS (SELECT DATE '2025-12-31' AS today)
SELECT p.PolicyID, pr.ProductName, cu.FirstName || ' ' || cu.LastName AS customer,
       p.PolicyEndDate,
       (p.PolicyEndDate - (SELECT today FROM ref)) AS days_to_expiry
FROM DimPolicy p
JOIN DimProduct  pr ON pr.ProductID  = p.ProductID
JOIN DimCustomer cu ON cu.CustomerID = p.CustomerID
WHERE p.PolicyStatus = 'Active'
  AND p.PolicyEndDate BETWEEN (SELECT today FROM ref)
                          AND (SELECT today FROM ref) + INTERVAL '30 days'
ORDER BY p.PolicyEndDate;

\echo '=== Q6. Monthly premium evolution ==='
-- Business: revenue trend over time (date_trunc for month grain).
SELECT to_char(date_trunc('month', TransactionDate), 'YYYY-MM') AS year_month,
       COUNT(*)             AS premiums,
       SUM(PremiumAmount)   AS written_premium
FROM FactPremiums
GROUP BY date_trunc('month', TransactionDate)
ORDER BY year_month;

\echo '=== Q7. Total compensation paid by branch ==='
-- Business: claims payout burden per agency. Payments carry PolicyID ->
-- roll up via policy's branch WITHOUT touching FactClaims (no fan-out).
SELECT b.BranchName, b.Governorate,
       COUNT(DISTINCT pay.ClaimID) AS claims_paid,
       SUM(pay.AmountPaid)         AS total_compensation
FROM FactPayments pay
JOIN DimPolicy p ON p.PolicyID = pay.PolicyID
JOIN DimBranch b ON b.BranchID = p.BranchID
GROUP BY b.BranchName, b.Governorate
ORDER BY total_compensation DESC;
