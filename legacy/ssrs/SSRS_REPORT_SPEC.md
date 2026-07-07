# SSRS Paginated Report Spec — `Monthly Sales Summary.rdl`

Build this in **Power BI Report Builder** (free, the modern replacement for
Report Builder 3.0 — same `.rdl` format, works against SSRS or a Fabric
paginated report workspace) or classic SSRS Report Builder if you have
access to one. Same reasoning as the SSIS spec: `.rdl` is XML that's brittle
to hand-generate correctly, and the designer is faster and guarantees
validity.

## Dataset query

```sql
SELECT ReportMonth, Region, Category, TotalQuantity, TotalRevenue
FROM dbo.RPT_MonthlySalesSummary
WHERE ReportMonth BETWEEN @StartMonth AND @EndMonth
ORDER BY ReportMonth, Region, Category;
```

## Parameters

| Parameter | Type | Default |
|---|---|---|
| `StartMonth` | Text (`YYYY-MM`) | First month in the table |
| `EndMonth` | Text (`YYYY-MM`) | Last month in the table |

Populate the available values from a second dataset:
`SELECT DISTINCT ReportMonth FROM dbo.RPT_MonthlySalesSummary ORDER BY ReportMonth`

## Layout

1. **Header**: Report title, parameter selections, generated-on timestamp
   (`=Now()`).
2. **Tablix** grouped by `Region` → `Category`, with subtotal rows per
   region (`=SUM(TotalRevenue)`) and a grand total footer.
3. **Conditional formatting**: highlight rows where `TotalRevenue` for a
   region/category dropped >15% vs. the prior month (use a lookup or a
   second dataset joined by `DATEADD` logic) — this is the "finance packs"
   use case from the resume: a paginated report finance actually reads
   month over month, not just a flat dump.
4. Export options to test: PDF and Excel (the two formats finance teams
   actually ask for from paginated reports).

## Subscription

Configure a **data-driven or standard subscription** to email the rendered
PDF to a distribution list on the 1st business day of each month — this is
the "SSRS paginated reports/subscriptions used for finance packs" bullet
made concrete.

## What to screenshot for your portfolio

1. The report layout in the designer.
2. A rendered PDF export showing the grouped tablix with subtotals.
3. The subscription configuration screen.
