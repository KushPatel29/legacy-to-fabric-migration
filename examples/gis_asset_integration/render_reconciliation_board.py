"""Render the GIS asset reconciliation acceptance board from published outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUTPUT = ROOT / "docs" / "business-analysis" / "gis-asset-reconciliation.png"

BG = "#071014"
PANEL = "#0d1b20"
GRID = "#29454b"
INK = "#e8f1ef"
MUTED = "#8ea7a8"
CYAN = "#46e5d5"
AMBER = "#e4b35a"
RED = "#f06d67"


def main() -> None:
    source = json.loads((HERE / "gis_features.geojson").read_text(encoding="utf-8"))
    summary = json.loads((HERE / "output" / "gis_asset_summary.json").read_text(encoding="utf-8"))
    with (HERE / "output" / "gis_asset_reconciliation.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    verdict = {row["asset_id"]: row for row in rows}

    plt.rcParams.update({"font.family": "DejaVu Sans"})
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor=BG)
    map_ax = fig.add_axes((0.055, 0.13, 0.64, 0.70), facecolor=PANEL)
    side_ax = fig.add_axes((0.735, 0.13, 0.225, 0.70), facecolor=PANEL)

    fig.text(0.055, 0.93, "A map is only as trustworthy as its asset keys",
             color=INK, fontsize=28, fontweight="bold", va="top")
    fig.text(0.055, 0.865,
             "Synthetic asset register + WGS 84 feature layer · governed migration acceptance gate",
             color=MUTED, fontsize=14, va="top")

    display_features = []
    for feature in source["features"]:
        lon, lat = feature["geometry"]["coordinates"]
        if -180 <= lon <= 180 and -90 <= lat <= 90:
            display_features.append(feature)

    for feature in display_features:
        asset_id = feature["properties"]["asset_id"]
        row = verdict[asset_id]
        if row["record_type"] == "orphan_gis_feature":
            color, marker, label = RED, "X", "Orphan GIS feature"
        elif row["verdict"] == "APPROVED":
            color, marker, label = CYAN, "o", "Approved asset"
        else:
            color, marker, label = AMBER, "s", "Blocked exception"
        map_ax.scatter(feature["geometry"]["coordinates"][0], feature["geometry"]["coordinates"][1],
                       s=130, c=color, marker=marker, edgecolors=BG, linewidths=1.4,
                       zorder=3, label=label)
        map_ax.annotate(asset_id, xy=feature["geometry"]["coordinates"], xytext=(7, 7),
                        textcoords="offset points", color=INK, fontsize=9, fontweight="bold")

    map_ax.set_xlim(-115.13, -114.89)
    map_ax.set_ylim(49.425, 49.59)
    map_ax.set_xlabel("Longitude · OGC:CRS84", color=MUTED, labelpad=10)
    map_ax.set_ylabel("Latitude", color=MUTED, labelpad=10)
    map_ax.tick_params(colors=MUTED, labelsize=9)
    map_ax.grid(color=GRID, linewidth=0.8, alpha=0.7)
    for spine in map_ax.spines.values():
        spine.set_color(GRID)

    handles, labels = map_ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    legend = map_ax.legend(unique.values(), unique.keys(), loc="lower left", ncol=3,
                           facecolor=BG, edgecolor=GRID, framealpha=0.92, fontsize=9)
    for text in legend.get_texts():
        text.set_color(INK)

    side_ax.set_xlim(0, 1)
    side_ax.set_ylim(0, 1)
    side_ax.set_xticks([])
    side_ax.set_yticks([])
    for spine in side_ax.spines.values():
        spine.set_color(GRID)

    side_ax.text(0.09, 0.91, "ACCEPTANCE RESULT", color=CYAN, fontsize=11, fontweight="bold")
    side_ax.text(0.09, 0.80, str(summary["approved_features"]), color=INK,
                 fontsize=30, fontweight="bold")
    side_ax.text(0.09, 0.745, "approved features", color=MUTED, fontsize=10)
    side_ax.text(0.56, 0.80, str(summary["blocked_records"]), color=AMBER,
                 fontsize=30, fontweight="bold")
    side_ax.text(0.56, 0.745, "exception records", color=MUTED, fontsize=10)
    side_ax.plot((0.09, 0.91), (0.68, 0.68), color=GRID, linewidth=1)
    side_ax.text(0.09, 0.62, "EXCEPTION LEDGER", color=CYAN, fontsize=11, fontweight="bold")

    labels = [
        ("Missing feature", "missing_asset_features"),
        ("Orphan feature", "orphan_features"),
        ("Duplicate key", "duplicate_asset_links"),
        ("Invalid geometry", "invalid_geometry_features"),
        ("Status mismatch", "status_mismatches"),
    ]
    for index, (label, key) in enumerate(labels):
        y = 0.55 - index * 0.085
        side_ax.text(0.09, y, label, color=INK, fontsize=10, va="center")
        side_ax.text(0.88, y, str(summary["exceptions"][key]), color=AMBER,
                     fontsize=13, fontweight="bold", ha="right", va="center")

    side_ax.text(0.09, 0.075,
                 "Publish rule\n1 key · valid point · aligned status",
                 color=MUTED, fontsize=10, linespacing=1.5)
    fig.text(0.055, 0.055,
             "All records and coordinates are synthetic · invalid and duplicate examples are deliberate test cases",
             color=MUTED, fontsize=10)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, facecolor=BG, dpi=100)
    plt.close(fig)
    print(f"Rendered {OUTPUT}")


if __name__ == "__main__":
    main()
