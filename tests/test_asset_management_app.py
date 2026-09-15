"""Contracts for the live asset-management decision board."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from streamlit.testing.v1 import AppTest

from asset_decision_support import (
    benefits_register,
    capital_scenario,
    decision_requirements,
    delivery_roadmap,
    evidence_pack,
    funding_sources,
    lifecycle_strategy_catalogue,
    load_assessment,
    multi_year_programme,
    programme_decision_register,
    programme_assumptions,
    programme_options,
    programme_risk_register,
    programme_summary,
    scenario_summary,
    sensitivity_analysis,
    service_level_catalogue,
    service_level_position,
)


ROOT = Path(__file__).resolve().parent.parent


def test_dynamic_capital_scenario_reconciles_to_published_baseline():
    assessment = load_assessment()
    scope, programme = capital_scenario(assessment, 8_000_000)
    summary = scenario_summary(scope, programme, 8_000_000)

    assert summary["assets_in_scope"] == 78
    assert summary["replacement_value_usd"] == 110_586_000
    assert summary["annualized_renewal_need_usd"] == 2_546_670
    assert summary["high_or_very_high_risk"] == 44
    assert summary["funded_assets"] == 13
    assert summary["funded_spend_usd"] == 7_999_000
    assert summary["deferred_candidates"] == 42


def test_filtered_scenarios_never_exceed_the_budget_or_fund_blocked_records():
    assessment = load_assessment()
    scope, programme = capital_scenario(
        assessment,
        3_500_000,
        services=["Water", "Roads"],
        risk_bands=["High", "Very High"],
    )
    funded = programme[programme["scenario_status"].eq("Funded in scenario")]

    assert funded["treatment_cost_usd"].sum() <= 3_500_000
    assert set(scope["asset_class"]) <= {"Water", "Roads"}
    assert set(scope["risk_band"].astype(str)) <= {"High", "Very High"}
    assert scope["data_quality_status"].eq("PLANNING_READY").all()
    assert scope["lifecycle_status"].eq("in_service").all()


def test_evidence_pack_preserves_scope_programme_controls_and_boundary():
    assessment = load_assessment()
    scope, programme = capital_scenario(assessment, 8_000_000)
    summary = scenario_summary(scope, programme, 8_000_000)
    payload = evidence_pack(
        scope,
        programme,
        summary,
        {"services": ["all"], "risk_bands": ["all"], "budget_usd": 8_000_000},
    )

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert set(archive.namelist()) == {
            "scenario_manifest.json",
            "assets_in_scope.csv",
            "prioritized_work_programme.csv",
            "multi_year_capital_plan.csv",
            "option_comparison.csv",
            "sensitivity_analysis.csv",
            "programme_risk_register.csv",
            "benefits_register.csv",
            "delivery_roadmap.csv",
            "indicative_funding_sources.csv",
            "business_case_requirements.csv",
            "service_level_catalogue.csv",
            "service_level_asset_position.csv",
            "lifecycle_strategy_catalogue.csv",
            "programme_decision_register.csv",
            "business_case_summary.md",
        }
        manifest = json.loads(archive.read("scenario_manifest.json"))
        briefing = archive.read("business_case_summary.md").decode("utf-8")
    assert manifest["summary"]["funded_spend_usd"] == 7_999_000
    assert "not an engineering condition assessment" in manifest["evidence_boundary"]
    assert len(manifest["required_validation"]) == 5
    assert manifest["decision_status"].startswith("CONDITIONAL")
    assert manifest["service_level_status"] == {
        "services_in_scope": 6,
        "services_below_target": 6,
        "basis": "Synthetic planning measures; not adopted municipal service standards.",
    }
    assert "not authority to spend" in " ".join(briefing.split())


def test_programme_assumptions_reconcile_the_indicative_funding_mix():
    assumptions = programme_assumptions(
        8_000_000, grant_share_pct=20, reserve_share_pct=50
    )

    assert assumptions["planning_years"] == 5
    assert assumptions["debt_share_pct"] == 30
    assert (
        assumptions["grant_share_pct"]
        + assumptions["reserve_share_pct"]
        + assumptions["debt_share_pct"]
        == 100
    )


def test_multi_year_programme_respects_each_year_budget_and_delivery_capacity():
    assessment = load_assessment()
    scope, _ = capital_scenario(assessment, 8_000_000)
    assumptions = programme_assumptions(8_000_000)
    plan = multi_year_programme(scope, assumptions)
    scheduled = plan[plan["programme_status"].eq("Scheduled in screen")]

    annual = scheduled.groupby("programme_year").agg(
        spend=("screened_programme_cost_usd", "sum"),
        projects=("asset_id", "count"),
    )
    assert annual["spend"].le(8_000_000).all()
    assert annual["projects"].le(14).all()
    assert scheduled["decision_gate"].eq("Requires validation").all()
    assert plan["asset_id"].is_unique
    assert programme_summary(plan, assumptions) == {
        "planning_years": 5,
        "annual_budget_usd": 8_000_000,
        "total_envelope_usd": 40_000_000,
        "scheduled_assets": 50,
        "scheduled_high_or_very_high": 38,
        "planned_capital_usd": 39_723_156,
        "capital_present_value_usd": 35_372_580,
        "deferred_candidates": 5,
        "deferred_treatment_cost_usd": 5_663_000,
        "deferred_annualized_risk_exposure_usd": 3_006_601,
    }


def test_business_case_options_are_distinct_and_recommend_the_balanced_posture():
    assessment = load_assessment()
    scope, _ = capital_scenario(assessment, 8_000_000)
    options = programme_options(scope, programme_assumptions(8_000_000))

    assert options["option_id"].tolist() == ["Option 1", "Option 2", "Option 3"]
    assert options["annual_envelope_usd"].is_monotonic_increasing
    assert options["scheduled_assets"].is_monotonic_increasing
    assert options.loc[options["option_id"].eq("Option 2"), "screening_recommendation"].iloc[0].startswith(
        "Recommended to validation"
    )


def test_sensitivity_analysis_exposes_cost_funding_and_combined_stresses():
    assessment = load_assessment()
    scope, _ = capital_scenario(assessment, 8_000_000)
    sensitivity = sensitivity_analysis(scope, programme_assumptions(8_000_000))

    assert sensitivity["sensitivity"].tolist() == [
        "Base screen",
        "Construction costs +15%",
        "Annual envelope -10%",
        "Grant not confirmed",
        "Combined stress",
    ]
    base = sensitivity.iloc[0]
    stressed = sensitivity[sensitivity["sensitivity"].ne("Base screen")]
    assert stressed["scheduled_assets"].le(base["scheduled_assets"]).all()
    assert stressed["deferred_candidates"].ge(base["deferred_candidates"]).all()


def test_risks_benefits_and_roadmap_have_named_owners_controls_and_gates():
    assessment = load_assessment()
    scope, _ = capital_scenario(assessment, 8_000_000)
    assumptions = programme_assumptions(8_000_000)
    plan = multi_year_programme(scope, assumptions)
    risks = programme_risk_register()
    benefits = benefits_register(scope, plan)
    roadmap = delivery_roadmap()
    requirements = decision_requirements()

    assert len(risks) == 9
    assert risks[["description", "likelihood", "impact", "risk_level", "mitigation", "owner", "status", "trigger"]].notna().all().all()
    assert risks["risk_id"].is_unique
    assert benefits["benefit_id"].is_unique
    assert benefits[["baseline", "target", "owner", "cadence", "evidence"]].notna().all().all()
    assert roadmap["gate"].tolist() == ["0", "1", "2", "3", "4", "5"]
    assert roadmap["accountable_role"].notna().all()
    assert len(requirements) == 10
    assert requirements["requirement_id"].is_unique
    assert requirements[["acceptance_criteria", "owner", "decision_gate", "evidence_status"]].notna().all().all()


def test_indicative_funding_sources_reconcile_to_screened_capital():
    assessment = load_assessment()
    scope, _ = capital_scenario(assessment, 8_000_000)
    assumptions = programme_assumptions(8_000_000)
    plan = multi_year_programme(scope, assumptions)
    sources = funding_sources(plan, assumptions)

    scheduled = plan[plan["programme_status"].eq("Scheduled in screen")]
    assert sources["indicative_share_pct"].sum() == 100
    assert sources["indicative_amount_usd"].sum() == scheduled[
        "screened_programme_cost_usd"
    ].sum()
    assert sources["validation_required"].str.len().gt(20).all()


def test_service_levels_connect_outcomes_targets_and_asset_pressure():
    assessment = load_assessment()
    scope, _ = capital_scenario(assessment, 8_000_000)
    catalogue = service_level_catalogue()
    position = service_level_position(scope, catalogue)

    assert len(catalogue) == len(position) == 6
    assert set(catalogue["technical_direction"]) == {"minimum", "maximum"}
    assert position["service_level_id"].is_unique
    assert position["service_status"].eq("BELOW TARGET").all()
    assert position["technical_gap"].gt(0).all()
    assert position["customer_gap"].gt(0).all()
    assert position["high_or_very_high_risk"].sum() == 44
    assert position["annualized_renewal_need_usd"].sum() == 2_546_670


def test_lifecycle_options_and_decision_records_preserve_approval_boundary():
    assessment = load_assessment()
    scope, _ = capital_scenario(assessment, 8_000_000)
    assumptions = programme_assumptions(8_000_000, planning_years=10)
    plan = multi_year_programme(scope, assumptions)
    strategies = lifecycle_strategy_catalogue()
    decisions = programme_decision_register(plan, assumptions)

    assert len(strategies) == 24
    assert strategies.groupby("asset_class")["lifecycle_strategy"].nunique().eq(4).all()
    assert "Non-infrastructure solution" in set(strategies["lifecycle_strategy"])
    assert decisions["decision_id"].is_unique
    assert len(decisions) == len(plan) == 55
    assert decisions["decision_status"].eq("SCREENED FOR VALIDATION").all()
    assert decisions["required_approvers"].eq(
        "Service owner + engineering + finance"
    ).all()
    assert decisions["conditions"].str.contains("four lifecycle options").all()


def test_streamlit_app_runs_and_exposes_all_decision_workspaces():
    app = AppTest.from_file(ROOT / "streamlit_app.py", default_timeout=30).run()

    assert not app.exception
    assert app.title[0].value == (
        "Build a ten-year asset programme decision that survives challenge."
    )
    assert app.multiselect[0].value == [
        "Facilities",
        "Fleet",
        "Parks",
        "Roads",
        "Stormwater",
        "Water",
    ]
    workspace = app.get("button_group")[0]
    assert workspace.options == [
        "Decision brief",
        "Business case",
        "Service levels",
        "Funding plan",
        "Risk & lifecycle",
        "GIS & assurance",
    ]
    assert workspace.value == "Decision brief"
    metrics = {metric.label: metric.value for metric in app.metric}
    assert metrics["Assets in scope"] == "78"
    assert metrics["High / very-high risk"] == "44"

    workspace.set_value("Service levels").run(timeout=30)
    service_metrics = {metric.label: metric.value for metric in app.metric}
    assert service_metrics["Services assessed"] == "6"
    assert service_metrics["Below target"] == "6"
    assert app.selectbox[0].value == "Roads"

    workspace.set_value("Business case").run(timeout=30)
    assert [tab.label for tab in app.tabs] == [
        "Options & affordability",
        "Sensitivity",
        "Risk & benefits",
        "Delivery gates",
    ]
    assert [button.label for button in app.get("download_button")] == [
        "Download investment-committee evidence pack"
    ]

    app.get("button_group")[0].set_value("Funding plan").run(timeout=30)
    funding_metrics = {metric.label: metric.value for metric in app.metric}
    assert funding_metrics["Annual envelope"] == "$8.00M"
    assert funding_metrics["Scheduled assets"] == "55"
    assert app.selectbox[0].value == "RDS-001"

    app.get("button_group")[0].set_value("Risk & lifecycle").run(timeout=30)
    assert not app.exception
    assert any("Asset risk matrix" in item.value for item in app.markdown)

    app.get("button_group")[0].set_value("GIS & assurance").run(timeout=30)
    assert [tab.label for tab in app.tabs] == [
        "Governed risk layer",
        "Source exceptions",
        "Acceptance controls",
    ]
    assert any("8 of 8" in item.value for item in app.success)
