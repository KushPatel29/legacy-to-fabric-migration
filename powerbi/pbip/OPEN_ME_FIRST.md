# How to open this Power BI Project

Everything is pre-built in code — no clicking required. The semantic model
(TMDL) has 4 tables, 3 relationships, and 13 DAX measures; the report (PBIR)
has 3 finished pages with 25 visuals, styled with the Meridian Corporate
custom theme (`.Report/StaticResources/RegisteredResources/MeridianTheme.json`).

## Steps

1. Double-click **`FabricMigrationCommandCenter.pbip`**.
2. When the report opens, click **Refresh** to load the CSVs
   (`data/migration/` — run
   `python data_generator/generate_migration_program.py` first if it's empty).
3. If you moved/cloned this repo somewhere else: Home → Transform data →
   Edit parameters → set **DataPath** to your local
   `...\legacy-to-fabric-migration` repo root, then Refresh.

## Model notes worth knowing

- `migration_artifacts` merges the inventory and plan CSVs in Power Query
  (both loaded directly — no query references, so no privacy-firewall
  prompts).
- The `migration_artifacts[cutover_month] → dim_month` relationship is
  intentionally **inactive**: keeping it active would give `validation_runs`
  two paths to `dim_month` (ambiguous). The Cutover Burnup measure filters
  on `actual_cutover` explicitly instead.
- An artifact can only be Cutover/Retired if its final parallel run was GO —
  the pytest suite enforces this in the data, mirroring the gate the
  runnable validator applies to the single-pipeline migration.

## Report pages

| Page | What it answers |
|---|---|
| Migration Command Center | Is the program on track? (140 artifacts, % migrated, burnup, blockers) |
| Estate & Effort | What are we migrating and what does it cost? (complexity, effort variance) |
| Parallel-Run Validation | Is it safe to cut over? (GO rate, NO-GO root causes, run log) |

## Using it in Power BI Desktop

- **Refresh before you read a number.** A `.pbip` stores the model definition,
  not its data. On first open Desktop shows "Some of the tables have incomplete or
  no data"; use **Home > Refresh** so every table reloads from the CSVs. If you
  opened this project in an earlier session, Desktop may also load an old local
  cache (`.pbi/cache.abf`, not committed) and show last session's figures until
  the full refresh finishes.
- **Buttons need Ctrl+click in Desktop.** Desktop is an editor, so a plain click
  selects a button; **Ctrl+click** follows it. Previous, Next, Filters, Close and
  Clear all filters say so in their tooltips. In the Power BI service and in
  reading view a plain click works.
