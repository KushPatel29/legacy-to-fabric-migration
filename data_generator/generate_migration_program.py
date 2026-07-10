"""
Synthetic enterprise migration-program dataset.

Models the estate a real SQL Server -> Fabric modernization program tracks:

  1. migration_inventory.csv    - the discovered legacy estate (what exists)
  2. migration_plan.csv         - wave assignment, target platform, status,
                                  effort planned vs actual (what's the plan)
  3. parallel_run_results.csv   - per-artifact validation runs with the same
                                  three checks the runnable validator in
                                  validation/ implements (is it safe to cut over)

Fixed seed so CI and the Power BI screenshots are reproducible.

Usage:
    python generate_migration_program.py
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "migration"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- estate mix
SOURCE_TYPES = [
    ("SSIS Package", 45),
    ("SSRS Report", 38),
    ("Stored Procedure ETL", 30),
    ("SQL Agent Job", 17),
    ("Access/Excel Feed", 10),
]
DOMAINS = ["Finance", "Sales", "Supply Chain", "Operations", "HR", "Marketing"]
DOMAIN_WEIGHTS = [0.28, 0.22, 0.20, 0.14, 0.09, 0.07]
COMPLEXITY = ["Low", "Medium", "High"]
CRITICALITY = ["Tier 1", "Tier 2", "Tier 3"]

TARGET_BY_SOURCE = {
    "SSIS Package": ["Fabric Pipeline", "Dataflow Gen2", "Fabric Notebook"],
    "SSRS Report": ["Power BI Report", "Power BI Paginated Report"],
    "Stored Procedure ETL": ["Fabric Notebook", "Dataflow Gen2"],
    "SQL Agent Job": ["Fabric Pipeline"],
    "Access/Excel Feed": ["Dataflow Gen2", "Fabric Notebook"],
}

# Waves are quarters; earlier waves take low-complexity, low-tier work first
# (strangler-fig sequencing), later waves take the Tier 1 / High items.
WAVES = {
    "Wave 1": ("2025-Q3", date(2025, 9, 15)),
    "Wave 2": ("2025-Q4", date(2025, 12, 15)),
    "Wave 3": ("2026-Q1", date(2026, 3, 15)),
    "Wave 4": ("2026-Q2", date(2026, 6, 15)),
    "Wave 5": ("2026-Q3", date(2026, 9, 15)),
    "Wave 6": ("2026-Q4", date(2026, 12, 15)),
}
TODAY = date(2026, 7, 10)  # program "as-of" date, matches repo narrative

NAME_STEMS = {
    "SSIS Package": ["Load", "Extract", "Sync", "Stage", "Merge"],
    "SSRS Report": ["Rpt", "Pack", "Statement", "Scorecard", "Summary"],
    "Stored Procedure ETL": ["usp_Load", "usp_Build", "usp_Refresh", "usp_Rebuild"],
    "SQL Agent Job": ["Nightly", "Hourly", "MonthEnd", "Weekly"],
    "Access/Excel Feed": ["Upload", "Manual", "Bridge", "Adhoc"],
}
SUBJECTS = [
    "MonthlySalesSummary", "ARAging", "InventorySnapshot", "GLPosting",
    "CustomerMaster", "ProductMaster", "OTIFDaily", "PayrollExtract",
    "VendorSpend", "PriceList", "DemandForecast", "ShipmentManifest",
    "MarginBridge", "CommissionCalc", "BudgetVsActual", "HeadcountRoster",
    "PromoLift", "FreightCost", "ExpiryRisk", "CampaignSpend",
]


def pick_domain():
    return random.choices(DOMAINS, weights=DOMAIN_WEIGHTS, k=1)[0]


def complexity_for(loc):
    if loc < 400:
        return "Low"
    if loc < 1200:
        return "Medium"
    return "High"


def wave_for(complexity, criticality):
    """Strangler-fig sequencing: simple + non-critical first."""
    score = COMPLEXITY.index(complexity) + (2 - CRITICALITY.index(criticality))
    # score 0 (Low/Tier3) .. 4 (High/Tier1)
    base = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5}[score]
    return f"Wave {min(6, base + random.choice([0, 0, 1]))}"


def main():
    inventory, plan, runs = [], [], []
    artifact_id = 0
    run_id = 0

    for source_type, count in SOURCE_TYPES:
        for _ in range(count):
            artifact_id += 1
            subject = random.choice(SUBJECTS)
            stem = random.choice(NAME_STEMS[source_type])
            name = f"{stem}_{subject}_{artifact_id:03d}"
            loc = int(random.lognormvariate(6.2, 0.9)) + 60
            complexity = complexity_for(loc)
            criticality = random.choices(CRITICALITY, weights=[0.25, 0.45, 0.30])[0]
            deps = max(0, int(random.gauss(3 if complexity == "Low" else 7, 3)))
            domain = pick_domain()

            inventory.append({
                "artifact_id": artifact_id,
                "artifact_name": name,
                "source_type": source_type,
                "domain": domain,
                "complexity": complexity,
                "criticality": criticality,
                "lines_of_code": loc,
                "dependency_count": deps,
            })

            wave = wave_for(complexity, criticality)
            quarter, cutover_target = WAVES[wave]
            target = random.choice(TARGET_BY_SOURCE[source_type])
            effort_planned = round({"Low": 3, "Medium": 8, "High": 18}[complexity]
                                   * random.uniform(0.7, 1.4), 1)

            # Status derived from where the wave sits relative to TODAY.
            if cutover_target < TODAY - timedelta(days=45):
                status = random.choices(
                    ["Retired", "Cutover", "Blocked"], weights=[0.78, 0.16, 0.06])[0]
            elif cutover_target < TODAY + timedelta(days=45):
                status = random.choices(
                    ["Cutover", "Parallel Run", "In Progress", "Blocked"],
                    weights=[0.30, 0.38, 0.24, 0.08])[0]
            elif cutover_target < TODAY + timedelta(days=170):
                status = random.choices(
                    ["In Progress", "Parallel Run", "Not Started"],
                    weights=[0.45, 0.15, 0.40])[0]
            else:
                status = random.choices(
                    ["Not Started", "In Progress"], weights=[0.85, 0.15])[0]

            done = status in ("Cutover", "Retired")
            effort_actual = (round(effort_planned * random.uniform(0.75, 1.6), 1)
                             if done else "")
            actual_cutover = ""
            if done:
                jitter = random.randint(-40, 55)
                d = cutover_target + timedelta(days=jitter)
                actual_cutover = min(d, TODAY - timedelta(days=3)).isoformat()
            blocker = ""
            if status == "Blocked":
                blocker = random.choice([
                    "Source schema drift", "Upstream owner sign-off pending",
                    "Gateway credentials", "Unsupported 3rd-party component",
                    "Data contract dispute"])

            plan.append({
                "artifact_id": artifact_id,
                "wave": wave,
                "wave_quarter": quarter,
                "target_platform": target,
                "status": status,
                "planned_cutover": cutover_target.isoformat(),
                "actual_cutover": actual_cutover,
                "effort_planned_days": effort_planned,
                "effort_actual_days": effort_actual,
                "blocker_reason": blocker,
            })

            # Parallel-run validation history for anything at/past Parallel Run.
            if status in ("Parallel Run", "Cutover", "Retired"):
                n_runs = random.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
                for attempt in range(1, n_runs + 1):
                    run_id += 1
                    final = attempt == n_runs
                    # Final run of a cutover/retired artifact must be GO;
                    # earlier attempts fail with a realistic reason.
                    if final and done:
                        go = True
                    elif final and status == "Parallel Run":
                        go = random.random() < 0.55
                    else:
                        go = False
                    reason = ""
                    rc = ct = ck = True
                    if not go:
                        reason = random.choice([
                            "Row count drift", "Control total variance",
                            "Checksum mismatch", "Schema drift",
                            "Late-arriving data window"])
                        rc = reason != "Row count drift"
                        ct = reason != "Control total variance"
                        ck = reason not in ("Checksum mismatch", "Schema drift",
                                            "Late-arriving data window")
                    run_month = (cutover_target - timedelta(
                        days=random.randint(10, 80) + (n_runs - attempt) * 25))
                    runs.append({
                        "run_id": run_id,
                        "artifact_id": artifact_id,
                        "run_date": run_month.isoformat(),
                        "attempt": attempt,
                        "row_count_match": rc,
                        "control_totals_match": ct,
                        "checksum_match": ck,
                        "verdict": "GO" if go else "NO-GO",
                        "mismatch_reason": reason,
                    })

    for fname, rows in [("migration_inventory.csv", inventory),
                        ("migration_plan.csv", plan),
                        ("parallel_run_results.csv", runs)]:
        with open(OUT_DIR / fname, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {len(rows):4d} rows -> {fname}")


if __name__ == "__main__":
    main()
