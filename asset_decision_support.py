"""Pure decision-support helpers for the live asset-management app."""

from __future__ import annotations

import io
import json
import math
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

PLANNING_START_YEAR = 2027


def programme_assumptions(
    annual_budget_usd: int,
    *,
    planning_years: int = 5,
    cost_escalation_pct: float = 3.5,
    contingency_pct: float = 15.0,
    discount_rate_pct: float = 4.0,
    delivery_capacity_per_year: int = 14,
    grant_share_pct: float = 20.0,
    reserve_share_pct: float = 50.0,
) -> dict:
    """Return explicit, validated assumptions for an indicative capital screen."""

    if annual_budget_usd <= 0:
        raise ValueError("annual_budget_usd must be positive")
    if planning_years < 1:
        raise ValueError("planning_years must be at least one")
    if delivery_capacity_per_year < 1:
        raise ValueError("delivery_capacity_per_year must be at least one")
    for label, value in {
        "cost_escalation_pct": cost_escalation_pct,
        "contingency_pct": contingency_pct,
        "discount_rate_pct": discount_rate_pct,
        "grant_share_pct": grant_share_pct,
        "reserve_share_pct": reserve_share_pct,
    }.items():
        if value < 0:
            raise ValueError(f"{label} cannot be negative")
    if grant_share_pct + reserve_share_pct > 100:
        raise ValueError("grant and reserve shares cannot exceed 100%")

    return {
        "planning_start_year": PLANNING_START_YEAR,
        "planning_years": int(planning_years),
        "annual_budget_usd": int(annual_budget_usd),
        "cost_escalation_pct": float(cost_escalation_pct),
        "contingency_pct": float(contingency_pct),
        "discount_rate_pct": float(discount_rate_pct),
        "delivery_capacity_per_year": int(delivery_capacity_per_year),
        "grant_share_pct": float(grant_share_pct),
        "reserve_share_pct": float(reserve_share_pct),
        "debt_share_pct": float(100 - grant_share_pct - reserve_share_pct),
        "cost_basis": (
            "Synthetic treatment screens escalated to the scheduled year and "
            "uplifted by planning contingency; excludes operating costs and benefits."
        ),
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


def multi_year_programme(
    scope: pd.DataFrame,
    assumptions: dict,
    *,
    annual_budget_multiplier: float = 1.0,
    capacity_multiplier: float = 1.0,
    cost_shock_pct: float = 0.0,
) -> pd.DataFrame:
    """Sequence candidates within annual cash and delivery-capacity constraints.

    The method is intentionally inspectable: candidates retain the published
    priority order, while each year accepts the next projects that fit the
    remaining annual envelope and delivery slots. It is a planning screen, not
    mathematical optimisation or an engineering recommendation.
    """

    candidates = scope[
        scope["data_quality_status"].eq("PLANNING_READY")
        & scope["lifecycle_status"].eq("in_service")
        & scope["treatment_cost_usd"].fillna(0).gt(0)
        & scope["recommended_intervention"].ne("Monitor")
    ].copy()
    candidates = candidates.sort_values(
        ["priority_score", "annualized_risk_exposure_usd", "asset_id"],
        ascending=[False, False, True],
        kind="stable",
    ).reset_index(drop=True)

    candidates["programme_year"] = pd.Series(pd.NA, index=candidates.index, dtype="Int64")
    candidates["programme_status"] = "Deferred beyond horizon"
    candidates["screened_programme_cost_usd"] = pd.Series(
        pd.NA, index=candidates.index, dtype="Int64"
    )
    candidates["capital_present_value_usd"] = pd.Series(
        pd.NA, index=candidates.index, dtype="Int64"
    )
    candidates["decision_gate"] = "Requires validation"

    annual_budget = int(assumptions["annual_budget_usd"] * annual_budget_multiplier)
    annual_capacity = max(
        1,
        int(math.floor(assumptions["delivery_capacity_per_year"] * capacity_multiplier)),
    )
    contingency = assumptions["contingency_pct"] / 100
    escalation = assumptions["cost_escalation_pct"] / 100
    discount = assumptions["discount_rate_pct"] / 100
    shock = cost_shock_pct / 100
    start_year = assumptions["planning_start_year"]

    available = list(candidates.index)
    for year_offset in range(assumptions["planning_years"]):
        remaining_budget = annual_budget
        remaining_slots = annual_capacity
        scheduled: list[int] = []
        for index in available:
            base_cost = float(candidates.at[index, "treatment_cost_usd"])
            screened_cost = int(
                round(
                    base_cost
                    * (1 + contingency)
                    * (1 + shock)
                    * ((1 + escalation) ** year_offset)
                )
            )
            if screened_cost <= remaining_budget and remaining_slots > 0:
                programme_year = start_year + year_offset
                present_value = int(round(screened_cost / ((1 + discount) ** (year_offset + 1))))
                candidates.at[index, "programme_year"] = programme_year
                candidates.at[index, "programme_status"] = "Scheduled in screen"
                candidates.at[index, "screened_programme_cost_usd"] = screened_cost
                candidates.at[index, "capital_present_value_usd"] = present_value
                remaining_budget -= screened_cost
                remaining_slots -= 1
                scheduled.append(index)
        available = [index for index in available if index not in scheduled]

    return candidates


def programme_summary(programme: pd.DataFrame, assumptions: dict) -> dict:
    scheduled = programme[programme["programme_status"].eq("Scheduled in screen")]
    deferred = programme[programme["programme_status"].eq("Deferred beyond horizon")]
    high_risk = ["High", "Very High"]
    return {
        "planning_years": int(assumptions["planning_years"]),
        "annual_budget_usd": int(assumptions["annual_budget_usd"]),
        "total_envelope_usd": int(
            assumptions["annual_budget_usd"] * assumptions["planning_years"]
        ),
        "scheduled_assets": int(len(scheduled)),
        "scheduled_high_or_very_high": int(scheduled["risk_band"].isin(high_risk).sum()),
        "planned_capital_usd": int(scheduled["screened_programme_cost_usd"].sum()),
        "capital_present_value_usd": int(scheduled["capital_present_value_usd"].sum()),
        "deferred_candidates": int(len(deferred)),
        "deferred_treatment_cost_usd": int(deferred["treatment_cost_usd"].sum()),
        "deferred_annualized_risk_exposure_usd": int(
            deferred["annualized_risk_exposure_usd"].sum()
        ),
    }


def programme_options(scope: pd.DataFrame, assumptions: dict) -> pd.DataFrame:
    """Compare three transparent funding and delivery postures."""

    definitions = [
        (
            "Option 1",
            "Minimum response",
            "Constrain new commitments and validate only the highest priorities.",
            0.65,
            0.60,
            "Not preferred — leaves greater exposure beyond the horizon.",
        ),
        (
            "Option 2",
            "Risk-based renewal",
            "Use the selected envelope and a governed, risk-ordered delivery plan.",
            1.00,
            1.00,
            "Recommended to validation — balanced affordability and risk response.",
        ),
        (
            "Option 3",
            "Accelerated resilience",
            "Increase annual funding and delivery capacity to advance more work.",
            1.25,
            1.30,
            "Strategic alternative — requires a larger funding and capacity decision.",
        ),
    ]
    rows: list[dict] = []
    for option_id, name, posture, budget_factor, capacity_factor, recommendation in definitions:
        plan = multi_year_programme(
            scope,
            assumptions,
            annual_budget_multiplier=budget_factor,
            capacity_multiplier=capacity_factor,
        )
        result = programme_summary(
            plan,
            {
                **assumptions,
                "annual_budget_usd": int(assumptions["annual_budget_usd"] * budget_factor),
            },
        )
        rows.append(
            {
                "option_id": option_id,
                "option": name,
                "decision_posture": posture,
                "annual_envelope_usd": int(assumptions["annual_budget_usd"] * budget_factor),
                "delivery_capacity_per_year": max(
                    1,
                    int(math.floor(assumptions["delivery_capacity_per_year"] * capacity_factor)),
                ),
                "scheduled_assets": result["scheduled_assets"],
                "scheduled_high_or_very_high": result["scheduled_high_or_very_high"],
                "planned_capital_usd": result["planned_capital_usd"],
                "capital_present_value_usd": result["capital_present_value_usd"],
                "deferred_candidates": result["deferred_candidates"],
                "deferred_treatment_cost_usd": result["deferred_treatment_cost_usd"],
                "deferred_annualized_risk_exposure_usd": result[
                    "deferred_annualized_risk_exposure_usd"
                ],
                "screening_recommendation": recommendation,
            }
        )
    return pd.DataFrame(rows)


def sensitivity_analysis(scope: pd.DataFrame, assumptions: dict) -> pd.DataFrame:
    """Expose the programme's response to a small set of decision stresses."""

    grant_factor = max(0.0, 1 - assumptions["grant_share_pct"] / 100)
    cases = [
        ("Base screen", 1.0, 0.0, "Published planning assumptions"),
        ("Construction costs +15%", 1.0, 15.0, "Market escalation above contingency"),
        ("Annual envelope -10%", 0.90, 0.0, "Affordability pressure"),
        (
            "Grant not confirmed",
            grant_factor,
            0.0,
            "No bridge financing for the indicative grant share",
        ),
        ("Combined stress", 0.90, 15.0, "Cost pressure and a smaller annual envelope"),
    ]
    rows: list[dict] = []
    for name, budget_factor, shock, rationale in cases:
        plan = multi_year_programme(
            scope,
            assumptions,
            annual_budget_multiplier=budget_factor,
            cost_shock_pct=shock,
        )
        adjusted = {
            **assumptions,
            "annual_budget_usd": int(assumptions["annual_budget_usd"] * budget_factor),
        }
        result = programme_summary(plan, adjusted)
        rows.append(
            {
                "sensitivity": name,
                "decision_stress": rationale,
                "effective_annual_envelope_usd": adjusted["annual_budget_usd"],
                "cost_shock_pct": shock,
                "scheduled_assets": result["scheduled_assets"],
                "planned_capital_usd": result["planned_capital_usd"],
                "deferred_candidates": result["deferred_candidates"],
                "deferred_annualized_risk_exposure_usd": result[
                    "deferred_annualized_risk_exposure_usd"
                ],
            }
        )
    return pd.DataFrame(rows)


def funding_sources(programme: pd.DataFrame, assumptions: dict) -> pd.DataFrame:
    """Return an indicative funding mix whose shares reconcile to the plan."""

    planned = int(
        programme.loc[
            programme["programme_status"].eq("Scheduled in screen"),
            "screened_programme_cost_usd",
        ].sum()
    )
    sources = [
        (
            "Reserves / current revenue",
            assumptions["reserve_share_pct"],
            "Confirm reserve policy, competing commitments, and annual cash flow.",
        ),
        (
            "Grants / contributions",
            assumptions["grant_share_pct"],
            "Confirm programme eligibility, timing, matching share, and fallback.",
        ),
        (
            "Debt / alternative financing",
            assumptions["debt_share_pct"],
            "Confirm borrowing authority, debt servicing, and public approvals.",
        ),
    ]
    rows = []
    allocated = 0
    for index, (source, share, validation) in enumerate(sources):
        amount = planned - allocated if index == len(sources) - 1 else int(round(planned * share / 100))
        allocated += amount
        rows.append(
            {
                "funding_source": source,
                "indicative_share_pct": float(share),
                "indicative_amount_usd": int(amount),
                "validation_required": validation,
            }
        )
    return pd.DataFrame(rows)


def programme_risk_register() -> pd.DataFrame:
    """Return the material risks that must travel with the recommendation."""

    rows = [
        (1, "AM-R01", "Evidence", "Condition or treatment scope is materially wrong.", "Likely", "Major", "High", "Independent condition validation and class-specific scope sign-off before commitment.", "Engineering lead + service owner", "Open", "Condition, intervention, or estimate changes beyond the approved tolerance"),
        (2, "AM-R02", "Financial", "Construction prices exceed the planning screen.", "Likely", "Major", "High", "Retain explicit contingency, refresh estimates at each gate, and preserve an approved scope response.", "Finance + engineering lead", "Open", "Estimate-at-completion exceeds the approved control budget"),
        (3, "AM-R03", "Funding", "Grant eligibility or timing does not align with delivery.", "Possible", "Major", "High", "Confirm eligibility and matching funds; identify bridge, resequencing, and no-grant fallbacks.", "Finance lead", "Open", "Eligibility or agreement is unconfirmed at the funding gate"),
        (4, "AM-R04", "Delivery", "Internal and market capacity cannot deliver the screened volume.", "Likely", "Moderate", "High", "Validate annual resource plan, bundle compatible work, and gate procurement readiness.", "Programme sponsor", "Open", "Approved resource plan supports fewer projects than the screened year"),
        (5, "AM-R05", "Procurement", "Long-lead supply or vendor performance delays a critical project.", "Possible", "Major", "High", "Market sounding, realistic lead times, weighted evaluation, performance security, and escalation triggers.", "Procurement lead", "Open", "Market response, critical lead time, or vendor milestone misses tolerance"),
        (6, "AM-R06", "Service / safety", "Work causes an unacceptable service interruption or safety event.", "Unlikely", "Severe", "High", "Approved isolation, continuity, traffic/public-safety, emergency, and commissioning plans.", "Service owner", "Open", "Continuity or safety plan cannot meet the accepted service threshold"),
        (7, "AM-R07", "Climate / environment", "A renewed asset is under-designed for future hazard or environmental obligations.", "Possible", "Major", "High", "Complete climate-hazard and environmental screening before option selection and design freeze.", "Engineering + environment lead", "Open", "Hazard or environmental screen changes the design basis or approvals"),
        (8, "AM-R08", "Information", "Asset, inspection, cost, or GIS ownership remains unclear.", "Likely", "Moderate", "High", "Assign data owners, resolve blocked records, preserve lineage, and run publication controls.", "Asset information owner", "In treatment", "A material exception reaches scoring, GIS publication, or funding"),
        (9, "AM-R09", "Community / equity", "Access, accessibility, equity, or community impacts are omitted from the preferred option.", "Possible", "Major", "High", "Complete impact screening and targeted engagement; document trade-offs and response before approval.", "Project sponsor", "Open", "Impact review identifies an unmitigated disproportionate or access effect"),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "priority",
            "risk_id",
            "category",
            "description",
            "likelihood",
            "impact",
            "risk_level",
            "mitigation",
            "owner",
            "status",
            "trigger",
        ],
    )


def service_level_catalogue() -> pd.DataFrame:
    """Return synthetic technical and customer service planning measures.

    These are transparent scenario inputs, not adopted municipal standards.
    Keeping the target direction and numeric basis explicit lets the app show
    a real service gap without hiding unlike measures inside a composite score.
    """

    rows = [
        (
            "LOS-WAT", "Water", "Reliable drinking-water service",
            "Unplanned interruption hours per 1,000 accounts", "maximum", 4.0, 6.2, "hours / year",
            "Customers restored inside 8 hours", "minimum", 95.0, 89.0, "%",
            "Longer interruptions, public-health concern, and emergency response pressure",
            "Utilities service owner",
        ),
        (
            "LOS-STM", "Stormwater", "Safe drainage and flood resilience",
            "Critical inlets inspected before wet season", "minimum", 100.0, 82.0, "%",
            "Priority drainage complaints resolved inside target", "minimum", 90.0, 76.0, "%",
            "Localized flooding, property exposure, access disruption, and emergency work",
            "Public Works service owner",
        ),
        (
            "LOS-RDS", "Roads", "Safe and reliable movement",
            "Network lane-kilometres in fair or better condition", "minimum", 70.0, 63.0, "%",
            "Priority road defects closed inside service target", "minimum", 90.0, 78.0, "%",
            "Safety exposure, travel disruption, accessibility barriers, and higher reactive cost",
            "Transportation service owner",
        ),
        (
            "LOS-FAC", "Facilities", "Safe and available civic facilities",
            "Critical facilities passing annual life-safety inspection", "minimum", 100.0, 94.0, "%",
            "Public opening hours delivered as planned", "minimum", 98.0, 91.0, "%",
            "Facility closure, service relocation, safety exposure, and accessibility loss",
            "Facilities service owner",
        ),
        (
            "LOS-FLT", "Fleet", "Available fleet for priority services",
            "Priority fleet mechanical availability", "minimum", 95.0, 92.0, "%",
            "Service requests supplied with an available vehicle", "minimum", 95.0, 88.0, "%",
            "Delayed field response, rental pressure, overtime, and reduced service capacity",
            "Fleet service owner",
        ),
        (
            "LOS-PRK", "Parks", "Safe and accessible public recreation",
            "Scheduled safety inspections completed on time", "minimum", 100.0, 91.0, "%",
            "Priority closures resolved inside three days", "minimum", 90.0, 82.0, "%",
            "Reduced access, recreation interruption, safety concern, and public dissatisfaction",
            "Parks service owner",
        ),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "service_level_id", "asset_class", "service_outcome",
            "technical_measure", "technical_direction", "technical_target",
            "technical_actual", "technical_unit", "customer_measure",
            "customer_direction", "customer_target", "customer_actual",
            "customer_unit", "consequence_of_shortfall", "accountable_role",
        ],
    )


def service_level_position(
    scope: pd.DataFrame,
    catalogue: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Connect service performance to the asset portfolio pressure behind it."""

    catalogue = service_level_catalogue() if catalogue is None else catalogue.copy()
    portfolio = (
        scope.groupby("asset_class", observed=True)
        .agg(
            assets_in_scope=("asset_id", "count"),
            high_or_very_high_risk=(
                "risk_band", lambda values: values.isin(["High", "Very High"]).sum()
            ),
            replacement_value_usd=("replacement_cost_usd", "sum"),
            annualized_renewal_need_usd=("annualized_renewal_need_usd", "sum"),
        )
        .reset_index()
    )
    result = catalogue.merge(portfolio, on="asset_class", how="inner", validate="one_to_one")

    def gap(actual: float, target: float, direction: str) -> float:
        return max(0.0, target - actual) if direction == "minimum" else max(0.0, actual - target)

    result["technical_gap"] = result.apply(
        lambda row: gap(row["technical_actual"], row["technical_target"], row["technical_direction"]),
        axis=1,
    )
    result["customer_gap"] = result.apply(
        lambda row: gap(row["customer_actual"], row["customer_target"], row["customer_direction"]),
        axis=1,
    )
    result["service_status"] = result.apply(
        lambda row: "BELOW TARGET"
        if row["technical_gap"] > 0 or row["customer_gap"] > 0
        else "AT TARGET",
        axis=1,
    )
    return result.sort_values(
        ["service_status", "high_or_very_high_risk", "annualized_renewal_need_usd"],
        ascending=[False, False, False],
        kind="stable",
    ).reset_index(drop=True)


def lifecycle_strategy_catalogue() -> pd.DataFrame:
    """Define four options every material asset case must compare."""

    non_asset = {
        "Water": "Demand management, leak reduction, operating change, or service partnership",
        "Stormwater": "Source control, inspection/cleaning, development control, or natural asset",
        "Roads": "Demand, traffic, access, winter-service, or active-transport intervention",
        "Facilities": "Service consolidation, space sharing, lease, or operating-hours change",
        "Fleet": "Route/utilization change, shared fleet, lease, or contracted service",
        "Parks": "Service reconfiguration, partnership, stewardship, or demand management",
    }
    rows: list[tuple[str, str, str, str, str, str]] = []
    for asset_class, alternative in non_asset.items():
        rows.extend(
            [
                (
                    asset_class, "Operate and maintain",
                    "Accept and monitor current risk with targeted preventive/reactive work",
                    "Usually lowest near-term capital; may retain service and failure exposure",
                    "Maintenance history, safe operating limit, residual risk, operating cost",
                    "REQUIRES EVIDENCE",
                ),
                (
                    asset_class, "Rehabilitate",
                    "Restore performance or extend useful life without full replacement",
                    "Compare scope, extension period, repeat intervention, and whole-life cost",
                    "Condition investigation, constructability, extension life, service impact",
                    "REQUIRES EVIDENCE",
                ),
                (
                    asset_class, "Renew or replace",
                    "Reset condition and capacity where the service case justifies investment",
                    "Highest capital screen; test residual value, operating change, and resilience",
                    "Design basis, capacity need, climate/safety/accessibility screen, cost class",
                    "REQUIRES EVIDENCE",
                ),
                (
                    asset_class, "Non-infrastructure solution", alternative,
                    "Test whether service outcomes can improve without equivalent new capital",
                    "Demand evidence, policy authority, stakeholder effect, operating model",
                    "REQUIRES EVIDENCE",
                ),
            ]
        )
    return pd.DataFrame(
        rows,
        columns=[
            "asset_class", "lifecycle_strategy", "service_response",
            "cost_and_risk_question", "evidence_required", "decision_status",
        ],
    )


def programme_decision_register(
    programme: pd.DataFrame,
    assumptions: dict,
) -> pd.DataFrame:
    """Return one controlled, non-approval decision record per candidate."""

    rows: list[dict] = []
    for record in programme.to_dict(orient="records"):
        scheduled = record["programme_status"] == "Scheduled in screen"
        year = record["programme_year"]
        rows.append(
            {
                "decision_id": f"AM-DR-{record['asset_id']}-{assumptions['planning_start_year']}",
                "asset_id": record["asset_id"],
                "evidence_date": "2026-08-31",
                "decision_status": "SCREENED FOR VALIDATION"
                if scheduled
                else "DEFERRED — OWNER DECISION REQUIRED",
                "screened_year": int(year) if pd.notna(year) else None,
                "recommended_action": record["recommended_intervention"],
                "decision_basis": (
                    f"{record['risk_band']} risk; priority {float(record['priority_score']):.1f}; "
                    f"condition {int(record['condition_grade'])}/5; "
                    f"criticality {int(record['criticality_grade'])}/5"
                ),
                "accountable_role": record["service_owner"],
                "required_approvers": "Service owner + engineering + finance",
                "next_gate": "Gate 1 — evidence validation",
                "conditions": (
                    "Validate service consequence, condition, four lifecycle options, whole-life cost, "
                    "public-value impacts, funding, delivery, procurement, and residual risk."
                ),
                "expected_benefit": (
                    "Protect or restore the documented service outcome; quantify after option validation."
                ),
                "supersedes_decision_id": "",
            }
        )
    return pd.DataFrame(rows)


def decision_requirements() -> pd.DataFrame:
    """Define the minimum traceable requirements for an approvable programme."""

    return pd.DataFrame(
        [
            ("AM-REQ-01", "Evidence", "Each candidate has a unique owner, valid lifecycle, current inspection basis, condition, criticality, cost source, and authoritative GIS reference.", "No material exception enters scoring, publication, or funding; validation is signed by the data and service owners.", "Asset information owner", "Gate 1", "Partially demonstrated — synthetic controls only"),
            ("AM-REQ-02", "Service", "Criticality and urgency trace to approved service levels, consequence definitions, statutory obligations, and community needs.", "Service owner approves consequence and documents any override to the analytical priority.", "Service owner", "Gate 1", "Not evidenced by model"),
            ("AM-REQ-03", "Options", "Every material investment compares do-minimum, maintain/rehabilitate, renew/replace, and non-asset alternatives where feasible.", "Preferred treatment has documented scope, outcomes, trade-offs, and rejection rationale for viable alternatives.", "Engineering lead", "Gate 2", "Portfolio-level postures demonstrated; asset options outstanding"),
            ("AM-REQ-04", "Economics", "The preferred option includes capital, operating cost, residual value, service benefit, risk, carbon, and uncertainty over its appraisal life.", "Finance and service owners accept a transparent whole-life appraisal and sensitivity range.", "Finance lead", "Gate 2", "Capital PV only — whole-life case outstanding"),
            ("AM-REQ-05", "Public value", "Safety, accessibility, climate, environmental, equity, privacy, and statutory impacts are assessed proportionately.", "No mandatory screen is missing; impacts, mitigations, owners, and residual exceptions are approved.", "Project sponsor", "Gate 2", "Not evidenced by model"),
            ("AM-REQ-06", "Affordability", "The programme fits approved annual cash, reserve, grant, debt, and operating constraints under base and stress cases.", "Finance signs funding sources, cash flow, eligibility, fallback, and approved change thresholds.", "Finance lead", "Gate 2", "Scenario controls demonstrated; authority outstanding"),
            ("AM-REQ-07", "Delivery", "Each tranche has realistic capacity, dependencies, permits, construction windows, continuity, schedule, and procurement route.", "Integrated delivery plan passes resource, dependency, market, safety, and readiness review.", "Programme manager", "Gate 3", "Annual capacity screened; detailed plan outstanding"),
            ("AM-REQ-08", "Procurement", "Evaluation, fairness, conflicts, contract, performance, accessibility, environmental, data, GIS, warranty, and commissioning requirements are controlled.", "Procurement lead accepts the route, criteria, records, delegations, and contract controls before release.", "Procurement lead", "Gate 3", "Not evidenced by model"),
            ("AM-REQ-09", "Engagement", "Affected staff, partners, users, and community groups can influence needs, impacts, mitigations, sequencing, and communications.", "Engagement record identifies participants, feedback, response, unresolved concerns, and decision impact.", "Project sponsor", "Gates 1–4", "Stakeholder roles defined; engagement outstanding"),
            ("AM-REQ-10", "Transition", "Commissioning updates the asset/GIS record, operating procedures, maintenance plan, training, support ownership, and benefit measures.", "Service owner signs technical acceptance, operational readiness, records, training, and benefits baseline within 60 days.", "Service owner", "Gate 5", "Not evidenced by model"),
        ],
        columns=[
            "requirement_id",
            "category",
            "requirement",
            "acceptance_criteria",
            "owner",
            "decision_gate",
            "evidence_status",
        ],
    )


def benefits_register(scope: pd.DataFrame, programme: pd.DataFrame) -> pd.DataFrame:
    """Define measurable benefits without claiming outcomes that are not evidenced."""

    scheduled = programme[programme["programme_status"].eq("Scheduled in screen")]
    high_risk_scheduled = int(scheduled["risk_band"].isin(["High", "Very High"]).sum())
    material_exceptions = 9
    return pd.DataFrame(
        [
            ("B-01", "Decision quality", "Capital candidates with a traceable owner, evidence, cost, risk, and disposition", f"{len(programme)} of {len(programme)} in the synthetic screen", "100% at every approval gate", "Asset information owner", "Each gate", "Register and decision log"),
            ("B-02", "Risk response", "High / very-high assets receiving engineering validation or a documented deferral", "0 validated by this analytical model", f"All {high_risk_scheduled} scheduled high / very-high assets before commitment", "Engineering lead", "Quarterly", "Signed validation record"),
            ("B-03", "Information quality", "Material source exceptions unresolved at publication", f"{material_exceptions} deliberately blocked examples", "0 unresolved material exceptions", "Asset information owner", "Monthly", "Exception register and control results"),
            ("B-04", "Affordability", "Approved annual funding-ceiling breaches", "0 in the synthetic screen", "0 in approved plan and forecast", "Finance lead", "Monthly", "Forecast and change control"),
            ("B-05", "Delivery confidence", "Scheduled projects passing scope, funding, procurement, capacity, and dependency gates", "0 delivery-ready claims in this model", "100% before tender or internal authorization", "Programme sponsor", "Stage gate", "Gate checklist"),
            ("B-06", "Outcome assurance", "Completed projects with commissioned service, safety, accessibility, climate, and asset-record evidence", "No completed projects in this portfolio simulation", "100% within 60 days of completion", "Service owner", "At closeout", "Commissioning and benefits review"),
        ],
        columns=[
            "benefit_id",
            "objective",
            "measure",
            "baseline",
            "target",
            "owner",
            "cadence",
            "evidence",
        ],
    )


def delivery_roadmap() -> pd.DataFrame:
    """Return stage gates from mandate through benefits realization."""

    return pd.DataFrame(
        [
            ("0", "Mandate and governance", "Q4 2026", "Sponsor", "Decision owner, scope, evaluation criteria, RACI, records location", "Approve discovery mandate"),
            ("1", "Evidence validation", "Q4 2026–Q1 2027", "Engineering + service owners", "Condition, service consequence, asset/GIS ownership, data exceptions", "Accept evidence baseline"),
            ("2", "Options and business case", "Q1–Q2 2027", "Sponsor + finance", "Whole-life options, affordability, funding, climate/accessibility/equity screens, consultation plan", "Select preferred option"),
            ("3", "Design and procurement readiness", "Q2–Q4 2027", "Engineering + procurement", "Design basis, packaging, market route, evaluation, permits, continuity and safety plans", "Authorize procurement"),
            ("4", "Tranche delivery", "2027–2031", "Programme manager", "Approved scope, cost, schedule, RAID, change control, stakeholder communications", "Release each tranche"),
            ("5", "Commission and realize benefits", "At completion + annual", "Service owner", "Acceptance, asset/GIS update, training, operations handover, benefit and lessons review", "Close and sustain"),
        ],
        columns=[
            "gate",
            "phase",
            "indicative_timing",
            "accountable_role",
            "evidence_required",
            "decision",
        ],
    )


def business_case_markdown(
    summary: dict,
    programme_result: dict,
    assumptions: dict,
    options: pd.DataFrame,
) -> str:
    """Render a portable briefing note that preserves the evidence boundary."""

    recommended = options.loc[options["option_id"].eq("Option 2")].iloc[0]
    return f"""# Asset Capital Programme — Decision Brief

## Decision requested

Authorize **Option 2 — Risk-based renewal** to proceed to condition, scope,
service-impact, funding, deliverability, climate, accessibility, equity, and
procurement validation. This is a conditional planning recommendation, not
authority to spend or an engineering approval.

## Portfolio case

- {summary['assets_in_scope']} assets are in the selected planning scope.
- The scope represents {short_money(summary['replacement_value_usd'])} of synthetic replacement value and {short_money(summary['annualized_renewal_need_usd'])} of annualized renewal need.
- The recommended screen schedules {int(recommended['scheduled_assets'])} assets, including {int(recommended['scheduled_high_or_very_high'])} high / very-high risk assets, across {assumptions['planning_years']} years.
- Screened nominal capital is {short_money(recommended['planned_capital_usd'])}; capital present value is {short_money(recommended['capital_present_value_usd'])} at {assumptions['discount_rate_pct']:.1f}%.
- {int(recommended['deferred_candidates'])} candidates remain beyond the horizon with {short_money(recommended['deferred_annualized_risk_exposure_usd'])} of modelled annualized risk exposure.

## Planning assumptions

- Annual envelope: {short_money(assumptions['annual_budget_usd'])}
- Cost escalation: {assumptions['cost_escalation_pct']:.1f}% per year
- Planning contingency: {assumptions['contingency_pct']:.1f}%
- Delivery capacity: {assumptions['delivery_capacity_per_year']} projects per year
- Indicative funding mix: {assumptions['reserve_share_pct']:.1f}% reserves/current revenue, {assumptions['grant_share_pct']:.1f}% grants/contributions, {assumptions['debt_share_pct']:.1f}% debt/other

## Conditions before approval

1. Validate condition, treatment scope, service consequence, cost class, and accountable owner for every scheduled asset.
2. Complete safety, accessibility, climate, environmental, equity, and statutory screens.
3. Confirm funding eligibility, reserve and debt policy, annual cash flow, procurement route, delivery capacity, dependencies, and community engagement.
4. Resolve material source exceptions and preserve the decision, requirement, change, and approval trail.
5. Return the preferred option, sensitivities, residual risks, and benefits plan to the accountable approval body.

## Evidence boundary

All records, costs, locations, assumptions, and results are synthetic. The
screen is not an optimized or approved capital plan, a whole-life economic
appraisal, an engineering assessment, or evidence of municipal employment.
"""


def evidence_pack(
    scope: pd.DataFrame,
    programme: pd.DataFrame,
    summary: dict,
    filters: dict,
    assumptions: dict | None = None,
) -> bytes:
    """Package the scenario, business case, controls, and approval boundary."""

    assumptions = assumptions or programme_assumptions(summary["budget_usd"])
    capital_plan = multi_year_programme(scope, assumptions)
    capital_summary = programme_summary(capital_plan, assumptions)
    options = programme_options(scope, assumptions)
    sensitivities = sensitivity_analysis(scope, assumptions)
    risks = programme_risk_register()
    benefits = benefits_register(scope, capital_plan)
    roadmap = delivery_roadmap()
    sources = funding_sources(capital_plan, assumptions)
    requirements = decision_requirements()
    service_levels = service_level_catalogue()
    service_position = service_level_position(scope, service_levels)
    lifecycle_strategies = lifecycle_strategy_catalogue()
    decision_register = programme_decision_register(capital_plan, assumptions)

    manifest = {
        "title": "Synthetic asset-management decision evidence",
        "analysis_basis": "2026-08-31 committed synthetic portfolio",
        "evidence_boundary": (
            "Decision-support scenario only; not an engineering condition assessment "
            "or approved capital plan."
        ),
        "filters": filters,
        "summary": summary,
        "programme_summary": capital_summary,
        "planning_assumptions": assumptions,
        "decision_status": "CONDITIONAL — proceed to validation, not authority to spend",
        "method": (
            "Priority-ordered affordability screen using published condition x "
            "criticality risk and a lifecycle/inspection priority score. The "
            "multi-year screen adds annual cash and delivery-capacity constraints."
        ),
        "required_validation": [
            "engineering condition and treatment scope",
            "service levels and statutory obligations",
            "accessibility, climate and equity impacts",
            "project bundling, delivery capacity and procurement route",
            "funding eligibility and accountable approval",
        ],
        "service_level_status": {
            "services_in_scope": int(len(service_position)),
            "services_below_target": int(
                service_position["service_status"].eq("BELOW TARGET").sum()
            ),
            "basis": "Synthetic planning measures; not adopted municipal service standards.",
        },
    }
    briefing = business_case_markdown(summary, capital_summary, assumptions, options)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("scenario_manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("assets_in_scope.csv", scope.to_csv(index=False))
        archive.writestr("prioritized_work_programme.csv", programme.to_csv(index=False))
        archive.writestr("multi_year_capital_plan.csv", capital_plan.to_csv(index=False))
        archive.writestr("option_comparison.csv", options.to_csv(index=False))
        archive.writestr("sensitivity_analysis.csv", sensitivities.to_csv(index=False))
        archive.writestr("programme_risk_register.csv", risks.to_csv(index=False))
        archive.writestr("benefits_register.csv", benefits.to_csv(index=False))
        archive.writestr("delivery_roadmap.csv", roadmap.to_csv(index=False))
        archive.writestr("indicative_funding_sources.csv", sources.to_csv(index=False))
        archive.writestr(
            "business_case_requirements.csv", requirements.to_csv(index=False)
        )
        archive.writestr(
            "service_level_catalogue.csv", service_levels.to_csv(index=False)
        )
        archive.writestr(
            "service_level_asset_position.csv", service_position.to_csv(index=False)
        )
        archive.writestr(
            "lifecycle_strategy_catalogue.csv", lifecycle_strategies.to_csv(index=False)
        )
        archive.writestr(
            "programme_decision_register.csv", decision_register.to_csv(index=False)
        )
        archive.writestr("business_case_summary.md", briefing)
    return payload.getvalue()


def short_money(value: float | int) -> str:
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"
