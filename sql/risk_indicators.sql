-- FactClaimIndicators — rule-based risk screening, 1:1 with FactClaims.
--   psql -U postgres -d tunisassur -f sql/risk_indicators.sql   (from project root)
DROP TABLE IF EXISTS FactClaimIndicators CASCADE;
CREATE TABLE FactClaimIndicators (
    ClaimID                VARCHAR(12) PRIMARY KEY REFERENCES FactClaims(ClaimID),
    PreviousClaimsCount    INTEGER,
    DaysSincePreviousClaim INTEGER,
    ClaimAmountDeviation   NUMERIC(8,2),
    RepeatedClaimIndicator INTEGER,
    RiskScore              INTEGER CHECK (RiskScore BETWEEN 0 AND 100),
    RiskCategory           TEXT CHECK (RiskCategory IN ('Low','Medium','High'))
);
\copy FactClaimIndicators FROM 'data/cleaned/claim_indicators.csv' WITH (FORMAT csv, HEADER true)

-- distribution check
SELECT RiskCategory, COUNT(*) AS claims,
       ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (), 1) AS pct
FROM FactClaimIndicators
GROUP BY RiskCategory
ORDER BY MIN(RiskScore);
