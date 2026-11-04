-- ======================================================================
-- load_data.sql — load the CLEANED (ground-truth) CSVs into the schema.
-- Run from the PROJECT ROOT so the relative paths resolve:
--     psql -U postgres -d tunisassur -f sql/load_data.sql
-- \copy is a psql client command (reads files on THIS machine, no server
-- file permissions needed). Empty CSV fields load as NULL in CSV mode.
-- Load order respects foreign keys.
-- ======================================================================
\copy DimProduct  FROM 'data/reference/products.csv' WITH (FORMAT csv, HEADER true)
\copy DimBranch   FROM 'data/cleaned/branches.csv'   WITH (FORMAT csv, HEADER true)
\copy DimCustomer FROM 'data/cleaned/customers.csv'  WITH (FORMAT csv, HEADER true)
\copy DimVehicle  FROM 'data/cleaned/vehicles.csv'   WITH (FORMAT csv, HEADER true)
\copy DimPolicy   FROM 'data/cleaned/policies.csv'   WITH (FORMAT csv, HEADER true)
\copy FactPremiums FROM 'data/cleaned/premiums.csv'  WITH (FORMAT csv, HEADER true)
\copy FactClaims   FROM 'data/cleaned/claims.csv'    WITH (FORMAT csv, HEADER true)
\copy FactPayments FROM 'data/cleaned/payments.csv'  WITH (FORMAT csv, HEADER true)

-- quick confirmation
SELECT 'DimProduct'  t, count(*) n FROM DimProduct
UNION ALL SELECT 'DimBranch',    count(*) FROM DimBranch
UNION ALL SELECT 'DimCustomer',  count(*) FROM DimCustomer
UNION ALL SELECT 'DimVehicle',   count(*) FROM DimVehicle
UNION ALL SELECT 'DimPolicy',    count(*) FROM DimPolicy
UNION ALL SELECT 'FactPremiums', count(*) FROM FactPremiums
UNION ALL SELECT 'FactClaims',   count(*) FROM FactClaims
UNION ALL SELECT 'FactPayments', count(*) FROM FactPayments
ORDER BY t;
