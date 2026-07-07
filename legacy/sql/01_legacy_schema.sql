-- =====================================================================
-- Legacy schema — SQL Server (run in SQL Server Developer Edition, free,
-- or a Fabric Warehouse if you want to skip installing SQL Server locally)
-- Represents the "before" state: an OLTP-ish sales schema plus a
-- stored-procedure-maintained reporting table, the pattern called out on
-- the resume as "SQL Server BI estate ... stored-procedure heavy
-- transforms".
-- =====================================================================

CREATE TABLE dbo.Customers (
    CustomerID   INT PRIMARY KEY,
    CustomerName VARCHAR(100) NOT NULL,
    Region       VARCHAR(50) NOT NULL
);

CREATE TABLE dbo.Products (
    ProductID   INT PRIMARY KEY,
    ProductName VARCHAR(100) NOT NULL,
    Category    VARCHAR(50) NOT NULL,
    UnitPrice   DECIMAL(10,2) NOT NULL
);

CREATE TABLE dbo.Orders (
    OrderID    INT PRIMARY KEY,
    OrderDate  DATE NOT NULL,
    CustomerID INT NOT NULL REFERENCES dbo.Customers(CustomerID),
    ProductID  INT NOT NULL REFERENCES dbo.Products(ProductID),
    Quantity   INT NOT NULL,
    UnitPrice  DECIMAL(10,2) NOT NULL
);

-- The reporting table an SSRS paginated report queries directly.
-- Rebuilt nightly by usp_Load_RPT_MonthlySalesSummary via a SQL Agent job.
CREATE TABLE dbo.RPT_MonthlySalesSummary (
    ReportMonth   CHAR(7) NOT NULL,        -- 'YYYY-MM'
    Region        VARCHAR(50) NOT NULL,
    Category      VARCHAR(50) NOT NULL,
    TotalQuantity INT NOT NULL,
    TotalRevenue  DECIMAL(14,2) NOT NULL,
    LoadedAtUtc   DATETIME2 NOT NULL,
    PRIMARY KEY (ReportMonth, Region, Category)
);

-- ETL run log — what a "SQL Agent scheduling + error handling" resume
-- bullet looks like as an actual artifact.
CREATE TABLE dbo.ETL_RunLog (
    RunID        INT IDENTITY PRIMARY KEY,
    ProcName     VARCHAR(100) NOT NULL,
    StartedAtUtc DATETIME2 NOT NULL,
    EndedAtUtc   DATETIME2 NULL,
    RowsAffected INT NULL,
    Status       VARCHAR(20) NOT NULL DEFAULT 'Running',  -- Running / Success / Failed
    ErrorMessage VARCHAR(MAX) NULL
);

-- Bulk-load the generated CSVs (adjust path to wherever you copied them):
--   BULK INSERT dbo.Customers FROM 'C:\...\data\customers.csv' WITH (FORMAT='CSV', FIRSTROW=2);
--   BULK INSERT dbo.Products  FROM 'C:\...\data\products.csv'  WITH (FORMAT='CSV', FIRSTROW=2);
--   BULK INSERT dbo.Orders    FROM 'C:\...\data\orders.csv'    WITH (FORMAT='CSV', FIRSTROW=2);
