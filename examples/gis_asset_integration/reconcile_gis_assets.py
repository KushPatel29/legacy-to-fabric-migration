"""Reconcile a governed asset register with a WGS 84 GIS point layer.

The example is intentionally synthetic. It demonstrates a migration acceptance
gate: only features with one valid geometry, one governed asset key, and an
aligned lifecycle status are published to the approved layer.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SOURCE_DIR / "output"


def load_sources(source_dir: Path = SOURCE_DIR) -> tuple[list[dict], dict]:
    with (source_dir / "asset_register.csv").open(encoding="utf-8", newline="") as handle:
        assets = list(csv.DictReader(handle))
    features = json.loads((source_dir / "gis_features.geojson").read_text(encoding="utf-8"))
    return assets, features


def valid_wgs84_point(feature: dict) -> bool:
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    return (
        geometry.get("type") == "Point"
        and len(coordinates) == 2
        and all(isinstance(value, (int, float)) for value in coordinates)
        and -180 <= coordinates[0] <= 180
        and -90 <= coordinates[1] <= 90
    )


def reconcile(assets: list[dict], collection: dict) -> tuple[list[dict], dict, dict]:
    features = collection["features"]
    asset_by_id = {asset["asset_id"]: asset for asset in assets}
    features_by_asset: dict[str, list[dict]] = defaultdict(list)
    for feature in features:
        features_by_asset[feature.get("properties", {}).get("asset_id", "")].append(feature)

    rows: list[dict] = []
    approved_features: list[dict] = []
    exception_counts: Counter = Counter()

    for asset in assets:
        asset_id = asset["asset_id"]
        linked = features_by_asset.get(asset_id, [])
        reasons: list[str] = []
        gis_status = ""

        if not linked:
            reasons.append("missing_gis_feature")
            exception_counts["missing_asset_features"] += 1
        elif len(linked) > 1:
            reasons.append("duplicate_gis_link")
            exception_counts["duplicate_asset_links"] += 1
        else:
            feature = linked[0]
            gis_status = feature["properties"].get("gis_status", "")
            if not valid_wgs84_point(feature):
                reasons.append("invalid_geometry")
                exception_counts["invalid_geometry_features"] += 1
            if gis_status != asset["status"]:
                reasons.append("status_mismatch")
                exception_counts["status_mismatches"] += 1

        verdict = "APPROVED" if not reasons else "BLOCKED"
        rows.append({
            "record_type": "asset",
            "asset_id": asset_id,
            "asset_name": asset["asset_name"],
            "asset_class": asset["asset_class"],
            "service_owner": asset["service_owner"],
            "register_status": asset["status"],
            "gis_status": gis_status,
            "feature_count": len(linked),
            "verdict": verdict,
            "reasons": "|".join(reasons),
        })

        if verdict == "APPROVED":
            source = linked[0]
            properties = dict(source["properties"])
            properties.update({
                "asset_name": asset["asset_name"],
                "asset_class": asset["asset_class"],
                "service_owner": asset["service_owner"],
                "cost_centre": asset["cost_centre"],
                "validation_status": "approved",
            })
            approved_features.append({
                "type": "Feature",
                "id": source.get("id"),
                "properties": properties,
                "geometry": source["geometry"],
            })

    for asset_id, linked in sorted(features_by_asset.items()):
        if asset_id in asset_by_id:
            continue
        exception_counts["orphan_features"] += len(linked)
        rows.append({
            "record_type": "orphan_gis_feature",
            "asset_id": asset_id,
            "asset_name": "",
            "asset_class": "",
            "service_owner": "Data Steward",
            "register_status": "",
            "gis_status": linked[0].get("properties", {}).get("gis_status", ""),
            "feature_count": len(linked),
            "verdict": "BLOCKED",
            "reasons": "orphan_gis_feature",
        })

    approved = {
        "type": "FeatureCollection",
        "name": "approved_synthetic_municipal_assets",
        "crs": collection.get("crs"),
        "features": approved_features,
    }
    summary = {
        "analysis_basis": "asset_key_geometry_and_status_acceptance_gate",
        "coordinate_system": "OGC:CRS84 (WGS 84 longitude/latitude)",
        "register_assets": len(assets),
        "gis_features": len(features),
        "approved_features": len(approved_features),
        "blocked_records": sum(row["verdict"] == "BLOCKED" for row in rows),
        "exceptions": {
            key: exception_counts[key]
            for key in (
                "missing_asset_features",
                "orphan_features",
                "duplicate_asset_links",
                "invalid_geometry_features",
                "status_mismatches",
            )
        },
        "data_note": "All records and coordinates are synthetic and are not City of Fernie data.",
    }
    return rows, approved, summary


def publish(rows: list[dict], approved: dict, summary: dict, output_dir: Path = OUTPUT_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "record_type", "asset_id", "asset_name", "asset_class", "service_owner",
        "register_status", "gis_status", "feature_count", "verdict", "reasons",
    ]
    with (output_dir / "gis_asset_reconciliation.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "approved_asset_layer.geojson").write_text(
        json.dumps(approved, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "gis_asset_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    assets, collection = load_sources()
    rows, approved, summary = reconcile(assets, collection)
    publish(rows, approved, summary)
    print(
        f"GIS acceptance gate: {summary['approved_features']} approved; "
        f"{summary['blocked_records']} exception records routed for review."
    )


if __name__ == "__main__":
    main()
