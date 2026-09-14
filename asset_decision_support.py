"""Pure decision-support helpers for the live asset-management app."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
ASSESSMENT_PATH = (
    ROOT
    / "examples"
    / "asset_management"
    / "output"
    / "asset_portfolio_assessment.csv"
)

NUMERIC_COLUMNS = (
    "expected_life_years",
    "replacement_cost_usd",
    "condition_grade",
    "criticality_grade",
    "maintenance_backlog_usd",
    "longitude",
    "latitude",
    "age_years",
    "life_consumed_pct",
    "days_since_inspection",
    "risk_score",
    "annualized_risk_exposure_usd",
    "annualized_renewal_need_usd",
    "treatment_cost_usd",
    "priority_score",
)

RISK_ORDER = ["Low", "Moderate", "High", "Very High"]
RISK_COLOURS = {
    "Low": "#177E75",
    "Moderate": "#D2A43A",
    "High": "#D9792B",
    "Very High": "#B84A3A",
}


def load_assessment(path: Path = ASSESSMENT_PATH) -> pd.DataFrame:
    """Load the committed assessment with stable analytical types."""

    frame = pd.read_csv(path, dtype={"asset_id": "string"}, keep_default_na=False)
    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["risk_band"] = pd.Categorical(
        frame["risk_band"], categories=RISK_ORDER + ["Not scored"], ordered=True
    )
    return frame


def capital_scenario(
    assessment: pd.DataFrame,
    budget_usd: int,
    services: list[str] | None = None,
    risk_bands: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return the scoped asset portfolio and a transparent funded programme."""

    scope = assessment[
        assessment["data_quality_status"].eq("PLANNING_READY")
        & assessment["lifecycle_status"].eq("in_service")
    ].copy()
    if services:
        scope = scope[scope["asset_class"].isin(services)].copy()
    if risk_bands:
        scope = scope[scope["risk_band"].isin(risk_bands)].copy()

    programme = scope[
        scope["treatment_cost_usd"].fillna(0).gt(0)
        & scope["recommended_intervention"].ne("Monitor")
    ].copy()
    programme = programme.sort_values(
        ["priority_score", "annualized_risk_exposure_usd", "asset_id"],
        ascending=[False, False, True],
        kind="stable",
    )

    remaining = int(budget_usd)
    statuses: list[str] = []
    for cost in programme["treatment_cost_usd"].fillna(0):
        if int(cost) <= remaining:
            statuses.append("Funded in scenario")
            remaining -= int(cost)
        else:
            statuses.append("Deferred")
    programme["scenario_status"] = statuses
    programme["running_programme_cost_usd"] = programme[
        "treatment_cost_usd"
    ].where(programme["scenario_status"].eq("Funded in scenario"), 0).cumsum()
    return scope, programme


def scenario_summary(scope: pd.DataFrame, programme: pd.DataFrame, budget_usd: int) -> dict:
    funded = programme[programme["scenario_status"].eq("Funded in scenario")]
    deferred = programme[programme["scenario_status"].eq("Deferred")]
    funded_spend = int(funded["treatment_cost_usd"].sum())
    return {
        "assets_in_scope": int(len(scope)),
        "replacement_value_usd": int(scope["replacement_cost_usd"].sum()),
        "annualized_renewal_need_usd": int(
            scope["annualized_renewal_need_usd"].sum()
        ),
        "high_or_very_high_risk": int(
            scope["risk_band"].isin(["High", "Very High"]).sum()
        ),
        "budget_usd": int(budget_usd),
        "funded_assets": int(len(funded)),
        "funded_spend_usd": funded_spend,
        "unallocated_budget_usd": int(budget_usd) - funded_spend,
        "deferred_candidates": int(len(deferred)),
        "deferred_annualized_risk_exposure_usd": int(
            deferred["annualized_risk_exposure_usd"].sum()
        ),
    }


def evidence_pack(
    scope: pd.DataFrame,
    programme: pd.DataFrame,
    summary: dict,
    filters: dict,
) -> bytes:
    """Package the exact scenario inputs, outputs, assumptions, and controls."""

    manifest = {
        "title": "Synthetic asset-management decision evidence",
        "analysis_basis": "2026-08-31 committed synthetic portfolio",
        "evidence_boundary": (
            "Decision-support scenario only; not an engineering condition assessment "
            "or approved capital plan."
        ),
        "filters": filters,
        "summary": summary,
        "method": (
            "Priority-ordered affordability screen using published condition x "
            "criticality risk and a lifecycle/inspection priority score."
        ),
        "required_validation": [
            "engineering condition and treatment scope",
            "service levels and statutory obligations",
            "accessibility, climate and equity impacts",
            "project bundling, delivery capacity and procurement route",
            "funding eligibility and accountable approval",
        ],
    }
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("scenario_manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("assets_in_scope.csv", scope.to_csv(index=False))
        archive.writestr("prioritized_work_programme.csv", programme.to_csv(index=False))
    return payload.getvalue()


def short_money(value: float | int) -> str:
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"
