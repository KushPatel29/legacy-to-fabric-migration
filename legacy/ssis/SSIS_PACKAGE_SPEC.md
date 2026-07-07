# SSIS Package Spec — `Load_MonthlySalesSummary.dtsx`

Build this in SSDT (SQL Server Data Tools) / Visual Studio with the
Integration Services extension. It's a thin orchestration wrapper around
`usp_Load_RPT_MonthlySalesSummary` — the same shape as most production SSIS
packages that exist mainly to schedule, parameterize, and add failure
handling around a stored procedure, which is exactly why it's a good
"legacy" artifact to modernize away from.

Deliberately not hand-generated as a raw `.dtsx` XML file here: SSIS package
XML is versioned to your exact SSDT/VS release and easy to corrupt by hand;
building it in the designer takes ~15 minutes and guarantees it actually
opens. This spec is what to build.

## Control Flow

```
[Execute SQL Task: "Log Start"]
        |
[Execute SQL Task: "Run usp_Load_RPT_MonthlySalesSummary"]
        |
        |-- On Success --> [Send Mail Task: "Notify Success"] (optional)
        |-- On Failure --> [Execute SQL Task: "Log Failure"] --> [Send Mail Task: "Notify Failure"]
```

- **Log Start**: `INSERT INTO dbo.ETL_RunLog (ProcName, StartedAtUtc, Status) VALUES ('SSIS_Load_MonthlySalesSummary', SYSUTCDATETIME(), 'Running')`
- **Run usp_Load_RPT_MonthlySalesSummary**: `EXEC dbo.usp_Load_RPT_MonthlySalesSummary`
- Precedence constraint from the Execute SQL Task uses **Success/Failure**
  outcomes (right-click the arrow → Completion/Success/Failure) — this is
  the error-handling pattern referenced on the resume ("SSIS packages
  (parameterization, error handling, SQL Agent schedules)").

## Parameters

Add a package parameter `ReportCutoffDate` (DateTime, default = today) so
the same package can be re-run for a historical cutover date during
parallel-run testing without editing the SQL.

## SQL Agent Job

- **Job name**: `Nightly - Load Monthly Sales Summary`
- **Step**: Type = SQL Server Integration Services Package, points at the
  deployed `.dtsx`
- **Schedule**: Daily at 2:00 AM
- **Notifications**: Email on failure (ties to the Send Mail Task above, or
  configure at the job level under Notifications)

## What to screenshot for your portfolio

1. The Control Flow designer view with the tasks and precedence constraints
   above.
2. The SQL Agent job's Schedules tab.
3. A successful run's history (green checkmark) plus one deliberately-forced
   failure (e.g., point at a bad table name temporarily) showing the
   Failed status + error message flowing into `ETL_RunLog` — proves the
   error handling actually works, not just that the happy path runs.
