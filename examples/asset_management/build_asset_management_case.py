"""Build a deterministic, synthetic municipal asset-management evidence pack.

The model is deliberately transparent. It combines lifecycle, condition,
criticality, inspection recency, replacement value, and data confidence into a
reviewable risk and work-program scenario. It is decision support, not an
optimiser and not a production asset-management system.
"""

from __future__ import annotations

import csv
import json
import math
import random
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
REGISTER = ROOT / "asset_register.csv"
AS_OF_DATE = date(2026, 8, 31)
SEED = 20260914
CAPITAL_SCENARIO_BUDGET_USD = 8_000_000

CLASS_SPECS = (
    ("WAT", "Water", 24, 650_000, 75, "Utilities"),
    ("STM", "Stormwater", 16, 275_000, 60, "Public Works"),
    ("RDS", "Roads", 20, 1_850_000, 35, "Transportation"),
    ("FAC", "Facilities", 12, 4_600_000, 50, "Facilities"),
    ("FLT", "Fleet", 12, 180_000, 12, "Fleet"),
    ("PRK", "Parks", 12, 220_000, 25, "Parks"),
)

PROBABILITY_OF_FAILURE = {1: 0.01, 2: 0.03, 3: 0.08, 4: 0.18, 5: 0.35}
CONSEQUENCE_MULTIPLIER = {1: 0.80, 2: 1.00, 3: 1.25, 4: 1.60, 5: 2.00}
RISK_COLOURS = {
    "Low": "#2a9d8f",
    "Moderate": "#e9c46a",
    "High": "#f4a261",
    "Very High": "#e76f51",
}

SOURCE_FIELDS = (
    "asset_id", "asset_name", "asset_class", "service_owner", "lifecycle_status",
    "install_date", "expected_life_years", "replacement_cost_usd", "condition_grade",
    "criticality_grade", "last_inspection_date", "maintenance_backlog_usd",
    "longitude", "latitude", "cost_centre",
)

ASSESSMENT_FIELDS = SOURCE_FIELDS + (
    "data_quality_status", "data_quality_reasons", "age_years", "life_consumed_pct",
    "days_since_inspection", "inspection_status", "risk_score", "risk_band",
    "annualized_risk_exposure_usd", "annualized_renewal_need_usd",
    "recommended_intervention", "treatment_cost_usd", "priority_score",
    "scenario_funding_status",
)


def iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def number(value: str) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def risk_band(score: int) -> str:
    if score >= 16:
        return "Very High"
    if score >= 10:
        return "High"
    if score >= 5:
        return "Moderate"
    return "Low"


def generate_register() -> list[dict[str, str]]:
    """Generate the same 96-record, cross-service portfolio every run."""

    rng = random.Random(SEED)
    records: list[dict[str, str]] = []
    sequence = 0

    for prefix, asset_class, count, base_cost, expected_life, owner in CLASS_SPECS:
        for class_index in range(1, count + 1):
            sequence += 1
            lifecycle = "in_service"
            if sequence % 23 == 0:
                lifecycle = "retired"
            elif sequence % 19 == 0:
                lifecycle = "planned"

            if lifecycle == "planned":
                install_year = 2027
                condition = 1
            else:
                install_year = rng.randint(1968, 2023)
                age = AS_OF_DATE.year - install_year
                consumed = age / expected_life
                condition = max(1, min(5, round(1 + consumed * 4 + rng.uniform(-0.75, 0.75))))
                if lifecycle == "retired":
                    condition = max(condition, 4)

            criticality = rng.choices([1, 2, 3, 4, 5], weights=[8, 18, 34, 26, 14], k=1)[0]
            replacement = round(base_cost * rng.uniform(0.62, 1.55) / 1_000) * 1_000
            inspection_days = rng.randint(35, 1_350)
            backlog = round(replacement * rng.uniform(0.002, 0.075) / 100) * 100

            grid_x = (sequence - 1) % 12
            grid_y = (sequence - 1) // 12
            longitude = -115.115 + grid_x * 0.015 + rng.uniform(-0.0025, 0.0025)
            latitude = 49.445 + grid_y * 0.014 + rng.uniform(-0.0025, 0.0025)

            records.append({
                "asset_id": f"{prefix}-{class_index:03d}",
                "asset_name": f"{asset_class} Asset {class_index:02d}",
                "asset_class": asset_class,
                "service_owner": owner,
                "lifecycle_status": lifecycle,
                "install_date": f"{install_year}-07-01",
                "expected_life_years": str(expected_life),
                "replacement_cost_usd": str(int(replacement)),
                "condition_grade": str(condition),
                "criticality_grade": str(criticality),
                "last_inspection_date": (AS_OF_DATE - timedelta(days=inspection_days)).isoformat(),
                "maintenance_backlog_usd": str(int(backlog)),
                "longitude": f"{longitude:.6f}",
                "latitude": f"{latitude:.6f}",
                "cost_centre": f"{prefix}-{100 + class_index // 6}",
            })

    # Deliberate source defects: the control layer must show its failure paths.
    records[5]["install_date"] = ""
    records[11]["last_inspection_date"] = ""  # incomplete inspection evidence, not a hard block
    records[17]["replacement_cost_usd"] = ""
    records[31]["condition_grade"] = ""
    records[44]["criticality_grade"] = "6"
    records[59]["latitude"] = "95.000000"
    records[73]["asset_id"] = records[72]["asset_id"]
    records[82]["lifecycle_status"] = "unknown"
    records[90]["service_owner"] = ""

    return records


def quality_reasons(record: dict[str, str], id_counts: Counter[str]) -> list[str]:
    reasons: list[str] = []
    if not record["asset_id"] or id_counts[record["asset_id"]] != 1:
        reasons.append("duplicate_or_missing_asset_id")
    if not record["service_owner"]:
        reasons.append("missing_service_owner")
    if record["lifecycle_status"] not in {"in_service", "planned", "retired"}:
        reasons.append("invalid_lifecycle_status")
    if iso_date(record["install_date"]) is None:
        reasons.append("missing_or_invalid_install_date")

    life = number(record["expected_life_years"])
    if life is None or life <= 0:
        reasons.append("missing_or_invalid_expected_life")
    replacement = number(record["replacement_cost_usd"])
    if replacement is None or replacement <= 0:
        reasons.append("missing_or_invalid_replacement_cost")
    condition = number(record["condition_grade"])
    if condition is None or condition not in {1, 2, 3, 4, 5}:
        reasons.append("missing_or_invalid_condition")
    criticality = number(record["criticality_grade"])
    if criticality is None or criticality not in {1, 2, 3, 4, 5}:
        reasons.append("missing_or_invalid_criticality")

    longitude = number(record["longitude"])
    latitude = number(record["latitude"])
    if longitude is None or latitude is None or not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        reasons.append("missing_or_invalid_wgs84_point")
    return reasons


def intervention(
    lifecycle: str,
    condition: int,
    risk_score_value: int,
    inspection_status: str,
) -> str:
    if lifecycle == "planned":
        return "Commission / validate data"
    if lifecycle == "retired":
        return "Retire / dispose"
    # A condition value without inspection evidence is not strong enough to
    # support a capital intervention. Refresh the evidence before spending.
    if inspection_status == "Missing":
        return "Inspect / condition assess"
    if condition >= 5 or risk_score_value >= 20:
        return "Replace / major renewal"
    if condition >= 4 or risk_score_value >= 15:
        return "Rehabilitate"
    if inspection_status != "Current":
        return "Inspect / condition assess"
    if condition >= 3:
        return "Planned maintenance"
    return "Monitor"


def treatment_cost(action: str, replacement_cost: float) -> float:
    factor = {
        "Replace / major renewal": 0.75,
        "Rehabilitate": 0.35,
        "Planned maintenance": 0.03,
    }.get(action, 0.0)
    return round(replacement_cost * factor / 1_000) * 1_000


def assess(records: list[dict[str, str]]) -> list[dict[str, str]]:
    id_counts = Counter(record["asset_id"] for record in records)
    assessed: list[dict[str, str]] = []

    for source in records:
        row = dict(source)
        reasons = quality_reasons(source, id_counts)
        if reasons:
            row.update({
                "data_quality_status": "DATA_REMEDIATION",
                "data_quality_reasons": "|".join(reasons),
                "age_years": "", "life_consumed_pct": "", "days_since_inspection": "",
                "inspection_status": "Not assessed", "risk_score": "", "risk_band": "Not scored",
                "annualized_risk_exposure_usd": "", "annualized_renewal_need_usd": "",
                "recommended_intervention": "Resolve source-data exception",
                "treatment_cost_usd": "", "priority_score": "", "scenario_funding_status": "NOT_ELIGIBLE",
            })
            assessed.append(row)
            continue

        installed = iso_date(source["install_date"])
        inspected = iso_date(source["last_inspection_date"])
        expected_life = int(float(source["expected_life_years"]))
        replacement = float(source["replacement_cost_usd"])
        condition = int(float(source["condition_grade"]))
        criticality = int(float(source["criticality_grade"]))
        age_years = max(0, AS_OF_DATE.year - installed.year)
        life_consumed = age_years / expected_life * 100

        days_since_inspection = (AS_OF_DATE - inspected).days if inspected else None
        if days_since_inspection is None:
            inspection_status = "Missing"
        elif days_since_inspection > 730:
            inspection_status = "Overdue"
        else:
            inspection_status = "Current"

        score = condition * criticality
        band = risk_band(score)
        exposure = replacement * PROBABILITY_OF_FAILURE[condition] * CONSEQUENCE_MULTIPLIER[criticality]
        renewal_need = replacement / expected_life if source["lifecycle_status"] == "in_service" else 0.0
        action = intervention(source["lifecycle_status"], condition, score, inspection_status)
        cost = treatment_cost(action, replacement)
        inspection_penalty = 8 if inspection_status == "Missing" else 5 if inspection_status == "Overdue" else 0
        priority = score * 4 + min(life_consumed, 150) * 0.18 + inspection_penalty

        row.update({
            "data_quality_status": "PLANNING_READY",
            "data_quality_reasons": "",
            "age_years": str(age_years),
            "life_consumed_pct": f"{life_consumed:.1f}",
            "days_since_inspection": "" if days_since_inspection is None else str(days_since_inspection),
            "inspection_status": inspection_status,
            "risk_score": str(score),
            "risk_band": band,
            "annualized_risk_exposure_usd": str(int(round(exposure))),
            "annualized_renewal_need_usd": str(int(round(renewal_need))),
            "recommended_intervention": action,
            "treatment_cost_usd": str(int(cost)),
            "priority_score": f"{priority:.1f}",
            "scenario_funding_status": "NOT_CAPITAL_SCENARIO",
        })
        assessed.append(row)

    candidates = sorted(
        (
            row for row in assessed
            if row["data_quality_status"] == "PLANNING_READY"
            and row["lifecycle_status"] == "in_service"
            and float(row["treatment_cost_usd"] or 0) > 0
        ),
        key=lambda row: (-float(row["priority_score"]), -float(row["annualized_risk_exposure_usd"]), row["asset_id"]),
    )
    remaining = CAPITAL_SCENARIO_BUDGET_USD
    for row in candidates:
        cost = float(row["treatment_cost_usd"])
        if cost <= remaining:
            row["scenario_funding_status"] = "FUNDED_SCENARIO"
            remaining -= cost
        else:
            row["scenario_funding_status"] = "DEFERRED_SCENARIO"
    return assessed


def summary_for(records: list[dict[str, str]], assessed: list[dict[str, str]]) -> dict:
    ready = [row for row in assessed if row["data_quality_status"] == "PLANNING_READY"]
    in_service = [row for row in ready if row["lifecycle_status"] == "in_service"]
    funded = [row for row in in_service if row["scenario_funding_status"] == "FUNDED_SCENARIO"]
    deferred = [row for row in in_service if row["scenario_funding_status"] == "DEFERRED_SCENARIO"]
    risk_counts = Counter(row["risk_band"] for row in in_service)
    class_replacement = Counter()
    class_renewal_need = Counter()
    for row in in_service:
        class_replacement[row["asset_class"]] += float(row["replacement_cost_usd"])
        class_renewal_need[row["asset_class"]] += float(row["annualized_renewal_need_usd"])

    replacement_value = sum(float(row["replacement_cost_usd"]) for row in in_service)
    annual_need = sum(float(row["annualized_renewal_need_usd"]) for row in in_service)
    funded_spend = sum(float(row["treatment_cost_usd"]) for row in funded)
    return {
        "analysis_basis": "synthetic_asset_lifecycle_condition_criticality_and_data_confidence_scenario",
        "as_of_date": AS_OF_DATE.isoformat(),
        "seed": SEED,
        "evidence_boundary": "All assets, coordinates, costs, conditions, risks, and scenarios are synthetic.",
        "portfolio": {
            "source_records": len(records),
            "unique_asset_ids": len({row["asset_id"] for row in records}),
            "planning_ready_records": len(ready),
            "data_remediation_records": len(assessed) - len(ready),
            "in_service_planning_ready": len(in_service),
            "replacement_value_usd": int(round(replacement_value)),
            "annualized_renewal_need_usd": int(round(annual_need)),
            "poor_or_very_poor_condition": sum(int(row["condition_grade"]) >= 4 for row in in_service),
            "overdue_or_missing_inspections": sum(row["inspection_status"] != "Current" for row in in_service),
            "risk_band_counts": {band: risk_counts[band] for band in ("Low", "Moderate", "High", "Very High")},
        },
        "capital_scenario": {
            "budget_usd": CAPITAL_SCENARIO_BUDGET_USD,
            "funded_assets": len(funded),
            "funded_spend_usd": int(round(funded_spend)),
            "unallocated_budget_usd": int(round(CAPITAL_SCENARIO_BUDGET_USD - funded_spend)),
            "deferred_candidates": len(deferred),
            "deferred_annualized_risk_exposure_usd": int(round(sum(float(row["annualized_risk_exposure_usd"]) for row in deferred))),
            "method_note": "Transparent priority-ordered affordability scenario; not portfolio optimisation or an approved capital plan.",
        },
        "service_class_totals": {
            key: {
                "replacement_value_usd": int(round(class_replacement[key])),
                "annualized_renewal_need_usd": int(round(class_renewal_need[key])),
            }
            for key in sorted(class_replacement)
        },
        "methods": {
            "condition_scale": "1 good to 5 very poor",
            "criticality_scale": "1 low to 5 very high",
            "risk_score": "condition_grade x criticality_grade (1 to 25)",
            "risk_bands": "Low 1-4; Moderate 5-9; High 10-15; Very High 16-25",
            "annualized_renewal_need": "replacement_cost / expected_life for in-service, planning-ready assets",
            "annualized_risk_exposure": "replacement_cost x condition probability x criticality consequence multiplier",
            "priority_score": "risk x 4 + capped life-consumed x 0.18 + inspection-recency penalty",
        },
    }


def geojson_for(assessed: list[dict[str, str]]) -> dict:
    features = []
    for row in assessed:
        if row["data_quality_status"] != "PLANNING_READY" or row["lifecycle_status"] != "in_service":
            continue
        properties = {
            "asset_id": row["asset_id"],
            "asset_name": row["asset_name"],
            "asset_class": row["asset_class"],
            "service_owner": row["service_owner"],
            "condition_grade": int(row["condition_grade"]),
            "criticality_grade": int(row["criticality_grade"]),
            "risk_score": int(row["risk_score"]),
            "risk_band": row["risk_band"],
            "replacement_cost_usd": int(float(row["replacement_cost_usd"])),
            "recommended_intervention": row["recommended_intervention"],
            "scenario_funding_status": row["scenario_funding_status"],
            "marker-color": RISK_COLOURS[row["risk_band"]],
        }
        features.append({
            "type": "Feature",
            "id": row["asset_id"],
            "properties": properties,
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["longitude"]), float(row["latitude"])],
            },
        })
    return {
        "type": "FeatureCollection",
        "name": "synthetic_asset_management_risk_layer",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }


def write_csv(path: Path, rows: list[dict[str, str]], fields: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def publish(records: list[dict[str, str]], assessed: list[dict[str, str]], summary: dict) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    write_csv(REGISTER, records, SOURCE_FIELDS)
    write_csv(OUTPUT / "asset_portfolio_assessment.csv", assessed, ASSESSMENT_FIELDS)

    work = sorted(
        (
            row for row in assessed
            if row["data_quality_status"] == "PLANNING_READY"
            and row["lifecycle_status"] == "in_service"
            and row["recommended_intervention"] != "Monitor"
        ),
        key=lambda row: (-float(row["priority_score"]), row["asset_id"]),
    )
    write_csv(OUTPUT / "prioritized_work_program.csv", work, ASSESSMENT_FIELDS)
    (OUTPUT / "asset_management_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT / "asset_risk_layer.geojson").write_text(
        json.dumps(geojson_for(assessed), indent=2) + "\n", encoding="utf-8"
    )


def build() -> tuple[list[dict[str, str]], list[dict[str, str]], dict]:
    records = generate_register()
    assessed = assess(records)
    summary = summary_for(records, assessed)
    return records, assessed, summary


def main() -> None:
    records, assessed, summary = build()
    publish(records, assessed, summary)
    portfolio = summary["portfolio"]
    scenario = summary["capital_scenario"]
    print(
        f"Asset portfolio: {portfolio['source_records']} source records; "
        f"{portfolio['planning_ready_records']} planning-ready; "
        f"{portfolio['data_remediation_records']} routed for data remediation."
    )
    print(
        f"Capital scenario: ${scenario['funded_spend_usd']:,.0f} across "
        f"{scenario['funded_assets']} assets within an ${scenario['budget_usd']:,.0f} ceiling."
    )


if __name__ == "__main__":
    main()
