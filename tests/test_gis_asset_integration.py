"""Contract tests for the synthetic GIS-to-asset migration gate."""

import csv
import json
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "gis_asset_integration"
sys.path.insert(0, str(EXAMPLE))

import reconcile_gis_assets as gis  # noqa: E402


def built():
    assets, collection = gis.load_sources()
    rows, approved, summary = gis.reconcile(assets, collection)
    return assets, collection, rows, approved, summary


def test_sources_are_small_explicit_and_synthetic():
    assets, collection, _, _, _ = built()
    assert len(assets) == 8
    assert len(collection["features"]) == 9
    assert all(asset["asset_id"].startswith("A-") for asset in assets)


def test_duplicate_business_key_is_blocked():
    _, _, rows, _, _ = built()
    row = next(item for item in rows if item["asset_id"] == "A-1005")
    assert row["feature_count"] == 2
    assert row["reasons"] == "duplicate_gis_link"


def test_missing_geometry_is_routed_to_an_owner():
    _, _, rows, _, _ = built()
    row = next(item for item in rows if item["asset_id"] == "A-1006")
    assert row["verdict"] == "BLOCKED"
    assert row["service_owner"] == "Fleet"
    assert row["reasons"] == "missing_gis_feature"


def test_orphan_invalid_geometry_and_status_drift_are_visible():
    _, _, rows, _, summary = built()
    reasons = {item["asset_id"]: item["reasons"] for item in rows}
    assert reasons["A-9999"] == "orphan_gis_feature"
    assert reasons["A-1007"] == "invalid_geometry"
    assert reasons["A-1004"] == "status_mismatch"
    assert set(summary["exceptions"].values()) == {1}


def test_only_clean_unique_matches_reach_the_approved_layer():
    _, _, _, approved, summary = built()
    ids = {item["properties"]["asset_id"] for item in approved["features"]}
    assert ids == {"A-1001", "A-1002", "A-1003", "A-1008"}
    assert summary["approved_features"] == 4
    assert all(gis.valid_wgs84_point(feature) for feature in approved["features"])


def test_published_outputs_are_parseable_and_auditable():
    with (EXAMPLE / "output" / "gis_asset_reconciliation.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    approved = json.loads((EXAMPLE / "output" / "approved_asset_layer.geojson").read_text(encoding="utf-8"))
    summary = json.loads((EXAMPLE / "output" / "gis_asset_summary.json").read_text(encoding="utf-8"))
    assert len(rows) == 9
    assert len(approved["features"]) == summary["approved_features"] == 4
    assert all(item["verdict"] in {"APPROVED", "BLOCKED"} for item in rows)


def test_summary_reconciles_source_approved_and_exception_counts():
    assets, collection, rows, approved, summary = built()
    assert summary["register_assets"] == len(assets)
    assert summary["gis_features"] == len(collection["features"])
    assert summary["approved_features"] == len(approved["features"])
    assert summary["blocked_records"] == sum(row["verdict"] == "BLOCKED" for row in rows)


def test_readme_visual_is_a_1600_by_900_png():
    image = ROOT / "docs" / "business-analysis" / "gis-asset-reconciliation.png"
    payload = image.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", payload[16:24]) == (1600, 900)
