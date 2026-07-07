# Cutover Runbook — Monthly Sales Summary: SSIS/T-SQL → Fabric

## Scope

Retire `usp_Load_RPT_MonthlySalesSummary` (SQL Agent job `Nightly - Load
Monthly Sales Summary`) in favor of the Fabric notebook
`fabric/notebooks/refactor_monthly_sales_summary.py`, without disrupting the
downstream SSRS paginated report or any consumer of `RPT_MonthlySalesSummary`.

## Pre-cutover checklist

- [ ] Fabric Lakehouse populated with `customers`, `products`, `orders` tables
      (same source data as the legacy SQL Server tables)
- [ ] Fabric notebook runs end-to-end without error
- [ ] Parallel-run validation (`validation/parallel_run_validation.py`)
      returns **GO** for at least 3 consecutive nightly runs, not just one —
      a single clean run can hide an edge case (e.g. a month-end boundary
      bug) that only shows up on specific dates
- [ ] SSRS report repointed to a view over the Fabric output (or the Fabric
      output synced back to SQL Server) and manually spot-checked against
      the legacy version for the same parameters
- [ ] Stakeholder sign-off from whoever consumes the finance pack

## Cutover steps

1. Run both pipelines in parallel for the agreed validation window (this
   project used 3 nights; scale to your own risk tolerance — first
   cutover of a finance-facing report warrants more, not fewer).
2. On each run, execute `parallel_run_validation.py` and log the verdict.
   Any **NO-GO** resets the validation window — don't cherry-pick a
   passing run after a failing one.
3. Once the validation window is clean, disable the SQL Agent job
   (`Nightly - Load Monthly Sales Summary`) — disable, don't delete, so
   there's an instant rollback path.
4. Point the SSRS/Power BI Report Builder dataset at the new source.
5. Monitor the first live Fabric-only run closely; keep the legacy SQL
   Server environment intact and query-able for at least one full
   reporting cycle (one month, for a monthly report) before decommissioning.
6. After the retention window with no issues, decommission: drop the SQL
   Agent job, archive `usp_Load_RPT_MonthlySalesSummary`, document the
   final state.

## Rollback plan

If the Fabric pipeline produces a bad number in production: re-enable the
SQL Agent job, repoint the SSRS dataset back to `dbo.RPT_MonthlySalesSummary`,
and investigate the Fabric notebook offline — never debug a broken pipeline
that a live finance report depends on.

## What actually went wrong during this build (keep this section honest)

During validation, the row-level checksum check initially reported a
**false FAIL** even though row counts and dollar control totals matched
exactly — `total_quantity` came back as `int64` from one implementation and
`float64` from the other (2326 vs 2326.0), which is enough to change a raw
string checksum despite being the same value. Fixed by normalizing dtypes
before hashing in `validation/parallel_run_validation.py`. This is exactly
the kind of validation-tooling bug a real cutover runbook should call out —
a checksum mismatch always needs to be triaged, not treated as an automatic
NO-GO, since it can be the check that's wrong instead of the data.
