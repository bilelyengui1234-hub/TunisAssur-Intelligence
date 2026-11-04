-- DimDate — date dimension (load after the main schema).
--   psql -U postgres -d tunisassur -f sql/dim_date.sql   (run from project root)
DROP TABLE IF EXISTS DimDate CASCADE;
CREATE TABLE DimDate (
    "Date"         DATE PRIMARY KEY,
    DateKey        INTEGER UNIQUE NOT NULL,
    "Year"         INTEGER,
    Quarter        INTEGER,
    QuarterName    TEXT,
    YearQuarter    TEXT,
    MonthNumber    INTEGER,
    MonthName      TEXT,
    MonthShort     TEXT,
    YearMonth      TEXT,
    YearMonthSort  INTEGER,
    MonthYearLabel TEXT,
    WeekOfYear     INTEGER,
    DayOfMonth     INTEGER,
    DayOfWeek      INTEGER,
    DayName        TEXT,
    IsWeekend      INTEGER
);
\copy DimDate FROM 'data/cleaned/dimdate.csv' WITH (FORMAT csv, HEADER true)
SELECT count(*) AS dimdate_rows, min("Date") AS from_date, max("Date") AS to_date FROM DimDate;
