-- =====================================================================
-- usp_Load_RPT_MonthlySalesSummary
--
-- The stored procedure this migration replaces. Full-refresh rebuild of
-- the reporting table with basic error handling and run logging — the
-- exact "stored-procedure heavy transform" pattern the Fabric refactor
-- (fabric/notebooks/refactor_monthly_sales_summary.py) replaces with a
-- notebook + incremental Delta MERGE.
--
-- Invoked by a SQL Agent job on a nightly schedule (see
-- legacy/ssis/SSIS_PACKAGE_SPEC.md for the orchestration wrapper).
-- =====================================================================

CREATE OR ALTER PROCEDURE dbo.usp_Load_RPT_MonthlySalesSummary
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @RunID INT;
    DECLARE @StartTime DATETIME2 = SYSUTCDATETIME();

    INSERT INTO dbo.ETL_RunLog (ProcName, StartedAtUtc, Status)
    VALUES ('usp_Load_RPT_MonthlySalesSummary', @StartTime, 'Running');
    SET @RunID = SCOPE_IDENTITY();

    BEGIN TRY
        BEGIN TRANSACTION;

        TRUNCATE TABLE dbo.RPT_MonthlySalesSummary;

        INSERT INTO dbo.RPT_MonthlySalesSummary
            (ReportMonth, Region, Category, TotalQuantity, TotalRevenue, LoadedAtUtc)
        SELECT
            FORMAT(o.OrderDate, 'yyyy-MM')  AS ReportMonth,
            c.Region,
            p.Category,
            SUM(o.Quantity)                 AS TotalQuantity,
            SUM(o.Quantity * o.UnitPrice)    AS TotalRevenue,
            SYSUTCDATETIME()                AS LoadedAtUtc
        FROM dbo.Orders o
        INNER JOIN dbo.Customers c ON o.CustomerID = c.CustomerID
        INNER JOIN dbo.Products p  ON o.ProductID = p.ProductID
        GROUP BY FORMAT(o.OrderDate, 'yyyy-MM'), c.Region, p.Category;

        DECLARE @RowsAffected INT = @@ROWCOUNT;

        COMMIT TRANSACTION;

        UPDATE dbo.ETL_RunLog
        SET EndedAtUtc = SYSUTCDATETIME(), RowsAffected = @RowsAffected, Status = 'Success'
        WHERE RunID = @RunID;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;

        UPDATE dbo.ETL_RunLog
        SET EndedAtUtc = SYSUTCDATETIME(), Status = 'Failed', ErrorMessage = ERROR_MESSAGE()
        WHERE RunID = @RunID;

        THROW;  -- surface to the SQL Agent job so it alerts on failure
    END CATCH
END;
GO

-- Run it:
-- EXEC dbo.usp_Load_RPT_MonthlySalesSummary;
-- SELECT * FROM dbo.RPT_MonthlySalesSummary ORDER BY ReportMonth, Region, Category;
