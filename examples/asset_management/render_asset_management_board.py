"""Render the committed 1600x900 asset-management evidence board."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
TARGET = ROOT.parents[1] / "docs" / "business-analysis" / "asset-management-decision-board.png"
MAP_TARGET = ROOT.parents[1] / "docs" / "business-analysis" / "asset-management-risk-map.png"


def money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return f"${value / 1_000:.0f}K"


def card(ax, x, y, w, h, label, value, note=""):
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.018",
                         transform=ax.transAxes, linewidth=1, edgecolor="#29404a", facecolor="#101b22")
    ax.add_patch(box)
    ax.text(x + .018, y + h - .035, label, transform=ax.transAxes, color="#78909c",
            fontsize=8.5, fontweight="bold", va="top")
    ax.text(x + .018, y + h * .48, value, transform=ax.transAxes, color="#eaf4f5",
            fontsize=20, fontweight="bold", va="center")
    if note:
        ax.text(x + .018, y + .022, note, transform=ax.transAxes, color="#9fb1b8",
                fontsize=7.5, va="bottom")


def main() -> None:
    summary = json.loads((OUTPUT / "asset_management_summary.json").read_text(encoding="utf-8"))
    with (OUTPUT / "asset_portfolio_assessment.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    with (OUTPUT / "prioritized_work_program.csv").open(encoding="utf-8", newline="") as handle:
        work = list(csv.DictReader(handle))

    ready = [r for r in rows if r["data_quality_status"] == "PLANNING_READY" and r["lifecycle_status"] == "in_service"]
    portfolio = summary["portfolio"]
    scenario = summary["capital_scenario"]

    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.titleweight": "bold"})
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor="#081015")
    canvas = fig.add_axes([0, 0, 1, 1])
    canvas.set_axis_off()

    fig.text(.04, .952, "ASSET MANAGEMENT DECISION BOARD", color="#35ded6", fontsize=11, fontweight="bold")
    fig.text(.04, .905, "From asset register to risk, renewal need and a controlled work-program scenario",
             color="#f4fbfb", fontsize=21, fontweight="bold")
    fig.text(.04, .872, "Synthetic portfolio · 31 Aug 2026 basis · condition 1 good → 5 very poor · risk = condition × criticality",
             color="#91a6ad", fontsize=9.5)

    card(canvas, .04, .715, .17, .12, "PORTFOLIO", f"{portfolio['source_records']} assets",
         f"{portfolio['planning_ready_records']} planning-ready · {portfolio['data_remediation_records']} data exceptions")
    card(canvas, .225, .715, .17, .12, "REPLACEMENT VALUE", money(portfolio["replacement_value_usd"]),
         "in-service, planning-ready basis")
    card(canvas, .41, .715, .17, .12, "ANNUAL RENEWAL NEED", money(portfolio["annualized_renewal_need_usd"]),
         "replacement value ÷ expected life")
    very_high = portfolio["risk_band_counts"]["Very High"]
    high = portfolio["risk_band_counts"]["High"]
    card(canvas, .595, .715, .17, .12, "HIGH / VERY HIGH RISK", f"{high + very_high} assets",
         f"{very_high} very high · {high} high")
    card(canvas, .78, .715, .17, .12, "$8M CAPITAL SCENARIO", f"{scenario['funded_assets']} funded",
         f"{money(scenario['funded_spend_usd'])} modelled · priority-ordered, not approved")

    # Risk matrix
    ax_risk = fig.add_axes([.055, .33, .36, .31], facecolor="#101b22")
    colours = {"Low": "#2a9d8f", "Moderate": "#e9c46a", "High": "#f4a261", "Very High": "#e76f51"}
    size_counts = Counter((int(r["criticality_grade"]), int(r["condition_grade"])) for r in ready)
    for (criticality, condition), count in size_counts.items():
        band = "Very High" if condition * criticality >= 16 else "High" if condition * criticality >= 10 else "Moderate" if condition * criticality >= 5 else "Low"
        ax_risk.scatter(criticality, condition, s=90 + count * 44, color=colours[band],
                        edgecolors="#eaf4f5", linewidths=.7, alpha=.92)
        ax_risk.text(criticality, condition, str(count), ha="center", va="center", color="#081015",
                     fontsize=8, fontweight="bold")
    ax_risk.set_xlim(.5, 5.5); ax_risk.set_ylim(.5, 5.5)
    ax_risk.set_xticks(range(1, 6)); ax_risk.set_yticks(range(1, 6))
    ax_risk.set_xlabel("CRITICALITY  →", color="#91a6ad", fontsize=8, fontweight="bold")
    ax_risk.set_ylabel("CONDITION  →  (WORSE)", color="#91a6ad", fontsize=8, fontweight="bold")
    ax_risk.set_title("RISK MATRIX · bubble = asset count", loc="left", color="#f4fbfb", fontsize=10, pad=12)
    ax_risk.tick_params(colors="#9fb1b8", labelsize=8)
    ax_risk.grid(color="#29404a", alpha=.45, linewidth=.6)
    for spine in ax_risk.spines.values(): spine.set_color("#29404a")

    # Renewal need by service
    ax_need = fig.add_axes([.455, .33, .25, .31], facecolor="#101b22")
    service = summary["service_class_totals"]
    names = sorted(service, key=lambda name: service[name]["annualized_renewal_need_usd"])
    values = [service[name]["annualized_renewal_need_usd"] / 1_000_000 for name in names]
    ax_need.barh(names, values, color="#35ded6", alpha=.82)
    for i, value in enumerate(values):
        ax_need.text(value + max(values) * .025, i, f"${value:.2f}M", va="center", color="#dce8ea", fontsize=8)
    ax_need.set_title("ANNUALIZED RENEWAL NEED", loc="left", color="#f4fbfb", fontsize=10, pad=12)
    ax_need.set_xlabel("$M per year · planning basis", color="#91a6ad", fontsize=8)
    ax_need.tick_params(colors="#9fb1b8", labelsize=8)
    ax_need.grid(axis="x", color="#29404a", alpha=.4, linewidth=.6)
    for spine in ax_need.spines.values(): spine.set_color("#29404a")

    # Work program table
    ax_table = fig.add_axes([.745, .30, .205, .34])
    ax_table.set_axis_off()
    ax_table.text(0, 1.045, "TOP CONTROLLED ACTIONS", color="#f4fbfb", fontsize=10, fontweight="bold", transform=ax_table.transAxes)
    ax_table.text(0, 1.005, "ranked by transparent priority score", color="#91a6ad", fontsize=7.5, transform=ax_table.transAxes)
    y = .93
    for rank, row in enumerate(work[:7], start=1):
        ax_table.text(0, y, f"{rank:02d}", color="#35ded6", fontsize=8, fontweight="bold", transform=ax_table.transAxes)
        ax_table.text(.11, y, row["asset_id"], color="#edf6f7", fontsize=8, fontweight="bold", transform=ax_table.transAxes)
        ax_table.text(.48, y, row["risk_band"].upper(), color=colours[row["risk_band"]], fontsize=7.2,
                      fontweight="bold", transform=ax_table.transAxes)
        action = row["recommended_intervention"].replace(" / ", " · ")
        ax_table.text(.11, y - .055, action[:30], color="#a9bcc2", fontsize=7.2, transform=ax_table.transAxes)
        ax_table.text(.98, y - .055, money(float(row["treatment_cost_usd"] or 0)), color="#a9bcc2",
                      fontsize=7.2, ha="right", transform=ax_table.transAxes)
        ax_table.plot([0, 1], [y - .085, y - .085], color="#29404a", linewidth=.7, transform=ax_table.transAxes)
        y -= .125

    # Bottom controls band
    box = FancyBboxPatch((.04, .075), .91, .145, boxstyle="round,pad=0.012,rounding_size=0.018",
                         transform=canvas.transAxes, linewidth=1, edgecolor="#29404a", facecolor="#0d171d")
    canvas.add_patch(box)
    fig.text(.06, .18, "DECISION CONTROLS", color="#35ded6", fontsize=9, fontweight="bold")
    controls = [
        ("DATA CONFIDENCE", f"{portfolio['data_remediation_records']} records blocked from planning until source defects are resolved"),
        ("GIS GOVERNANCE", "Only planning-ready, in-service WGS 84 points publish to the risk layer"),
        ("FUNDING BOUNDARY", f"{scenario['deferred_candidates']} candidates deferred; budget scenario is not an approved capital plan"),
        ("TRACEABILITY", "Condition, criticality, life, inspection, intervention, cost, priority and funding status remain row-level"),
    ]
    x_positions = [.06, .285, .51, .735]
    for (label, note), x in zip(controls, x_positions):
        fig.text(x, .145, label, color="#dce8ea", fontsize=7.8, fontweight="bold")
        wrapped = note.replace(" until ", "\nuntil ").replace(" publish ", "\npublish ").replace("; budget ", ";\nbudget ").replace(", intervention", ",\nintervention")
        fig.text(x, .105, wrapped, color="#91a6ad", fontsize=7.2, linespacing=1.35)

    fig.text(.04, .035, "PORTFOLIO EVIDENCE · ALL RECORDS, COORDINATES, COSTS, CONDITIONS AND SCENARIOS ARE SYNTHETIC",
             color="#6f858d", fontsize=7.8, fontweight="bold")
    fig.savefig(TARGET, dpi=100, facecolor=fig.get_facecolor(), bbox_inches=None)
    plt.close(fig)
    print(TARGET)

    # A second artifact proves the assessed rows remain useful as governed
    # spatial data instead of ending as a chart-only aggregate.
    fig = plt.figure(figsize=(16, 9), dpi=100, facecolor="#081015")
    ax = fig.add_axes([.055, .11, .70, .76], facecolor="#0d171d")
    for band in ("Low", "Moderate", "High", "Very High"):
        subset = [row for row in ready if row["risk_band"] == band]
        ax.scatter(
            [float(row["longitude"]) for row in subset],
            [float(row["latitude"]) for row in subset],
            s=[45 + int(row["criticality_grade"]) * 23 for row in subset],
            c=colours[band], label=f"{band} · {len(subset)}", alpha=.88,
            edgecolors="#eaf4f5", linewidths=.55,
        )
    labelled = sorted(ready, key=lambda row: (-int(row["risk_score"]), -float(row["priority_score"]), row["asset_id"]))[:8]
    for row in labelled:
        ax.annotate(row["asset_id"], (float(row["longitude"]), float(row["latitude"])),
                    xytext=(5, 6), textcoords="offset points", color="#edf6f7", fontsize=7,
                    bbox=dict(boxstyle="round,pad=.2", facecolor="#081015", edgecolor="#29404a", alpha=.9))
    ax.set_title("GOVERNED ASSET RISK LAYER", loc="left", color="#f4fbfb", fontsize=20, pad=18, fontweight="bold")
    ax.text(0, 1.015, "Planning-ready, in-service WGS 84 points only · bubble size = criticality",
            transform=ax.transAxes, color="#91a6ad", fontsize=9)
    ax.set_xlabel("LONGITUDE · OGC:CRS84", color="#91a6ad", fontsize=8, fontweight="bold")
    ax.set_ylabel("LATITUDE", color="#91a6ad", fontsize=8, fontweight="bold")
    ax.tick_params(colors="#9fb1b8", labelsize=8)
    ax.grid(color="#29404a", alpha=.42, linewidth=.65)
    for spine in ax.spines.values(): spine.set_color("#29404a")
    legend = ax.legend(loc="lower left", ncol=4, frameon=True, facecolor="#101b22",
                       edgecolor="#29404a", fontsize=8)
    for item in legend.get_texts(): item.set_color("#dce8ea")

    side = fig.add_axes([.79, .11, .165, .76])
    side.set_axis_off()
    side.text(0, 1, "PUBLISHING CONTROLS", transform=side.transAxes, color="#35ded6",
              fontsize=9, fontweight="bold", va="top")
    controls = [
        ("96", "source records"),
        ("87", "planning-ready"),
        ("9", "data exceptions blocked"),
        (str(len(ready)), "in-service points published"),
        (str(portfolio["risk_band_counts"]["Very High"]), "very-high risk assets"),
    ]
    y = .90
    for value, label in controls:
        side.text(0, y, value, transform=side.transAxes, color="#f4fbfb", fontsize=24,
                  fontweight="bold", va="top")
        side.text(0, y - .055, label, transform=side.transAxes, color="#91a6ad", fontsize=8,
                  va="top")
        side.plot([0, 1], [y - .105, y - .105], transform=side.transAxes, color="#29404a", linewidth=.8)
        y -= .145
    side.text(0, .12, "EXCLUDED BEFORE PUBLISH", transform=side.transAxes, color="#e9c46a",
              fontsize=8, fontweight="bold")
    side.text(0, .075, "duplicate/missing ID · owner · lifecycle · install date · cost · condition · criticality · invalid coordinate",
              transform=side.transAxes, color="#9fb1b8", fontsize=7.5, linespacing=1.4, wrap=True)
    fig.text(.055, .045, "SYNTHETIC COORDINATES · STRAIGHT VISUAL SCREENING ONLY · NOT A SURVEY, NETWORK ROUTE OR PRODUCTION GIS LAYER",
             color="#6f858d", fontsize=7.8, fontweight="bold")
    fig.savefig(MAP_TARGET, dpi=100, facecolor=fig.get_facecolor(), bbox_inches=None)
    plt.close(fig)
    print(MAP_TARGET)


if __name__ == "__main__":
    main()
