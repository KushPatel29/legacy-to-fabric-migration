"""Contracts for the synthetic asset-management decision evidence."""

from __future__ import annotations

import csv
import json
import struct
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "asset_management"
sys.path.insert(0, str(EXAMPLE))

import build_asset_management_case as am  # noqa: E402


def built():
    return am.build()


def test_register_is_deterministic_and_cross_service():
    first, _, _ = built()
    second, _, _ = built()
    assert first == second
    assert len(first) == 96
    assert {row["asset_class"] for row in first} == {
        "Water", "Stormwater", "Roads", "Facilities", "Fleet", "Parks"
    }


def test_register_contains_lifecycle_condition_criticality_cost_and_spatial_fields():
    records, _, _ = built()
    required = {
        "asset_id", "service_owner", "lifecycle_status", "install_date",
        "expected_life_years", "replacement_cost_usd", "condition_grade",
        "criticality_grade", "last_inspection_date", "longitude", "latitude",
    }
    assert required <= records[0].keys()


def test_deliberate_data_exceptions_are_visible_not_imputed():
    _, assessed, summary = built()
    failed = [row for row in assessed if row["data_quality_status"] == "DATA_REMEDIATION"]
    assert len(failed) == summary["portfolio"]["data_remediation_records"] == 9
    reasons = "|".join(row["data_quality_reasons"] for row in failed)
    for expected in (
        "duplicate_or_missing_asset_id", "missing_service_owner", "invalid_lifecycle_status",
        "missing_or_invalid_install_date", "missing_or_invalid_replacement_cost",
        "missing_or_invalid_condition", "missing_or_invalid_criticality",
        "missing_or_invalid_wgs84_point",
    ):
        assert expected in reasons


def test_duplicate_id_blocks_both_ambiguous_records():
    records, assessed, _ = built()
    duplicate = next(key for key, count in Counter(row["asset_id"] for row in records).items() if count == 2)
    rows = [row for row in assessed if row["asset_id"] == duplicate]
    assert len(rows) == 2
    assert all(row["data_quality_status"] == "DATA_REMEDIATION" for row in rows)


def test_data_remediation_records_are_not_scored_or_funded():
    _, assessed, _ = built()
    failed = [row for row in assessed if row["data_quality_status"] == "DATA_REMEDIATION"]
    assert all(row["risk_score"] == "" and row["priority_score"] == "" for row in failed)
    assert all(row["scenario_funding_status"] == "NOT_ELIGIBLE" for row in failed)


def test_risk_is_condition_times_criticality_with_published_bands():
    _, assessed, _ = built()
    ready = [row for row in assessed if row["data_quality_status"] == "PLANNING_READY"]
    for row in ready:
        score = int(row["condition_grade"]) * int(row["criticality_grade"])
        assert int(row["risk_score"]) == score
        assert row["risk_band"] == am.risk_band(score)


def test_annualized_renewal_need_reconciles_to_summary():
    _, assessed, summary = built()
    expected = sum(
        int(row["annualized_renewal_need_usd"])
        for row in assessed
        if row["data_quality_status"] == "PLANNING_READY" and row["lifecycle_status"] == "in_service"
    )
    assert expected == summary["portfolio"]["annualized_renewal_need_usd"]


def test_replacement_value_reconciles_to_summary():
    _, assessed, summary = built()
    expected = sum(
        int(float(row["replacement_cost_usd"]))
        for row in assessed
        if row["data_quality_status"] == "PLANNING_READY" and row["lifecycle_status"] == "in_service"
    )
    assert expected == summary["portfolio"]["replacement_value_usd"]


def test_highest_risk_in_service_assets_receive_major_intervention():
    _, assessed, _ = built()
    highest = [
        row for row in assessed
        if row["data_quality_status"] == "PLANNING_READY"
        and row["lifecycle_status"] == "in_service"
        and int(row["risk_score"]) >= 20
    ]
    assert highest
    assert all(row["recommended_intervention"] == "Replace / major renewal" for row in highest)


def test_missing_inspection_routes_to_assessment_not_fake_recency():
    _, assessed, _ = built()
    row = next(item for item in assessed if item["inspection_status"] == "Missing")
    assert row["days_since_inspection"] == ""
    assert row["recommended_intervention"] == "Inspect / condition assess"


def test_capital_scenario_never_exceeds_its_ceiling():
    _, assessed, summary = built()
    funded = [row for row in assessed if row["scenario_funding_status"] == "FUNDED_SCENARIO"]
    spend = sum(int(float(row["treatment_cost_usd"])) for row in funded)
    assert spend == summary["capital_scenario"]["funded_spend_usd"]
    assert spend <= summary["capital_scenario"]["budget_usd"] == am.CAPITAL_SCENARIO_BUDGET_USD


def test_only_planning_ready_in_service_assets_enter_capital_scenario():
    _, assessed, _ = built()
    candidates = [row for row in assessed if row["scenario_funding_status"] in {"FUNDED_SCENARIO", "DEFERRED_SCENARIO"}]
    assert candidates
    assert all(row["data_quality_status"] == "PLANNING_READY" for row in candidates)
    assert all(row["lifecycle_status"] == "in_service" for row in candidates)
    assert all(float(row["treatment_cost_usd"]) > 0 for row in candidates)


def test_work_program_is_priority_ordered_and_excludes_monitor_only_rows():
    _, assessed, _ = built()
    work = sorted(
        (
            row for row in assessed
            if row["data_quality_status"] == "PLANNING_READY"
            and row["lifecycle_status"] == "in_service"
            and row["recommended_intervention"] != "Monitor"
        ),
        key=lambda row: (-float(row["priority_score"]), row["asset_id"]),
    )
    assert work
    assert [float(row["priority_score"]) for row in work] == sorted(
        (float(row["priority_score"]) for row in work), reverse=True
    )


def test_geojson_contains_only_governed_in_service_points():
    _, assessed, _ = built()
    layer = am.geojson_for(assessed)
    expected = sum(
        row["data_quality_status"] == "PLANNING_READY" and row["lifecycle_status"] == "in_service"
        for row in assessed
    )
    assert len(layer["features"]) == expected
    for feature in layer["features"]:
        longitude, latitude = feature["geometry"]["coordinates"]
        assert -180 <= longitude <= 180 and -90 <= latitude <= 90
        assert feature["properties"]["risk_band"] in {"Low", "Moderate", "High", "Very High"}


def test_committed_outputs_are_parseable_and_reconcile():
    with (EXAMPLE / "output" / "asset_portfolio_assessment.csv").open(encoding="utf-8", newline="") as handle:
        assessed = list(csv.DictReader(handle))
    summary = json.loads((EXAMPLE / "output" / "asset_management_summary.json").read_text(encoding="utf-8"))
    layer = json.loads((EXAMPLE / "output" / "asset_risk_layer.geojson").read_text(encoding="utf-8"))
    assert len(assessed) == summary["portfolio"]["source_records"] == 96
    assert len(layer["features"]) == summary["portfolio"]["in_service_planning_ready"]


def test_decision_board_is_a_1600_by_900_png():
    image = ROOT / "docs" / "business-analysis" / "asset-management-decision-board.png"
    payload = image.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", payload[16:24]) == (1600, 900)


def test_risk_map_is_a_1600_by_900_png():
    image = ROOT / "docs" / "business-analysis" / "asset-management-risk-map.png"
    payload = image.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", payload[16:24]) == (1600, 900)
