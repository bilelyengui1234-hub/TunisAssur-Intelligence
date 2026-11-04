-- ======================================================================
-- TunisAssur Intelligence — PostgreSQL schema (star schema)
-- Dimensions and facts mirror the Power BI model. PK/FK enforce integrity.
-- Load order (see load_data.sql): product, branch, customer, vehicle,
-- policy, premiums, claims, payments.
-- ======================================================================
DROP TABLE IF EXISTS FactPayments CASCADE;
DROP TABLE IF EXISTS FactClaims   CASCADE;
DROP TABLE IF EXISTS FactPremiums CASCADE;
DROP TABLE IF EXISTS DimPolicy    CASCADE;
DROP TABLE IF EXISTS DimVehicle   CASCADE;
DROP TABLE IF EXISTS DimCustomer  CASCADE;
DROP TABLE IF EXISTS DimBranch    CASCADE;
DROP TABLE IF EXISTS DimProduct   CASCADE;

-- ---------------------------- Dimensions -----------------------------
CREATE TABLE DimProduct (
    ProductID           VARCHAR(10) PRIMARY KEY,
    ProductName         TEXT NOT NULL,
    ProductCategory     TEXT NOT NULL,
    CoverageDescription TEXT,
    policy_share        NUMERIC(5,4),
    premium_min         INTEGER,
    premium_max         INTEGER,
    claim_frequency     NUMERIC(5,4),
    severity_min        INTEGER,
    severity_max        INTEGER
);

CREATE TABLE DimBranch (
    BranchID    VARCHAR(10) PRIMARY KEY,
    BranchName  TEXT NOT NULL,
    Governorate TEXT NOT NULL,
    City        TEXT,
    OpeningDate DATE
);

CREATE TABLE DimCustomer (
    CustomerID       VARCHAR(12) PRIMARY KEY,
    FirstName        TEXT,
    LastName         TEXT,
    Gender           VARCHAR(2),
    BirthDate        DATE,
    Age              INTEGER,
    Governorate      TEXT,
    City             TEXT,
    CustomerType     TEXT,
    RegistrationDate DATE,
    CustomerSegment  TEXT
);

CREATE TABLE DimVehicle (
    VehicleID         VARCHAR(12) PRIMARY KEY,
    CustomerID        VARCHAR(12) REFERENCES DimCustomer(CustomerID),
    VehicleBrand      TEXT,
    VehicleModel      TEXT,
    VehicleType       TEXT,
    ManufacturingYear INTEGER,
    VehicleAge        INTEGER,
    RegistrationYear  INTEGER
);

CREATE TABLE DimPolicy (
    PolicyID         VARCHAR(12) PRIMARY KEY,
    CustomerID       VARCHAR(12) NOT NULL REFERENCES DimCustomer(CustomerID),
    ProductID        VARCHAR(10) NOT NULL REFERENCES DimProduct(ProductID),
    BranchID         VARCHAR(10) NOT NULL REFERENCES DimBranch(BranchID),
    PolicyStartDate  DATE NOT NULL,
    PolicyEndDate    DATE NOT NULL,
    CoverageType     TEXT,
    PolicyStatus     TEXT,
    PaymentFrequency TEXT,
    InsuredAssetID   VARCHAR(12) REFERENCES DimVehicle(VehicleID),
    CHECK (PolicyEndDate > PolicyStartDate)
);

-- ------------------------------ Facts --------------------------------
CREATE TABLE FactPremiums (
    PremiumID        VARCHAR(12) PRIMARY KEY,
    PolicyID         VARCHAR(12) NOT NULL REFERENCES DimPolicy(PolicyID),
    TransactionDate  DATE NOT NULL,
    PremiumAmount    NUMERIC(12,2) NOT NULL CHECK (PremiumAmount > 0),
    DiscountAmount   NUMERIC(12,2) NOT NULL CHECK (DiscountAmount >= 0),
    NetPremiumAmount NUMERIC(12,2) NOT NULL,
    PaymentStatus    TEXT,
    PaymentMethod    TEXT
);

CREATE TABLE FactClaims (
    ClaimID          VARCHAR(12) PRIMARY KEY,
    PolicyID         VARCHAR(12) NOT NULL REFERENCES DimPolicy(PolicyID),
    ClaimDate        DATE NOT NULL,
    ClaimType        TEXT,
    ClaimAmount      NUMERIC(12,2) NOT NULL CHECK (ClaimAmount > 0),
    ClaimStatus      TEXT,
    ApprovalDate     DATE,
    ClosureDate      DATE,
    ClaimDescription TEXT,
    VehicleID        VARCHAR(12) REFERENCES DimVehicle(VehicleID)
);

CREATE TABLE FactPayments (
    PaymentID     VARCHAR(12) PRIMARY KEY,
    ClaimID       VARCHAR(12) NOT NULL REFERENCES FactClaims(ClaimID),
    PolicyID      VARCHAR(12) NOT NULL REFERENCES DimPolicy(PolicyID),
    PaymentDate   DATE NOT NULL,
    AmountPaid    NUMERIC(12,2) NOT NULL CHECK (AmountPaid > 0),
    PaymentMethod TEXT,
    PaymentStatus TEXT
);

-- Helpful indexes for the analytical queries (FK columns)
CREATE INDEX idx_policy_customer ON DimPolicy(CustomerID);
CREATE INDEX idx_policy_product  ON DimPolicy(ProductID);
CREATE INDEX idx_policy_branch   ON DimPolicy(BranchID);
CREATE INDEX idx_prem_policy     ON FactPremiums(PolicyID);
CREATE INDEX idx_claim_policy    ON FactClaims(PolicyID);
CREATE INDEX idx_pay_claim       ON FactPayments(ClaimID);
