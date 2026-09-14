"""Live asset-management decision board built on committed synthetic evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from asset_decision_support import (
    RISK_COLOURS,
    RISK_ORDER,
    benefits_register,
    capital_scenario,
    decision_requirements,
    delivery_roadmap,
    evidence_pack,
    funding_sources,
    load_assessment,
    multi_year_programme,
    programme_assumptions,
    programme_options,
    programme_risk_register,
    programme_summary,
    scenario_summary,
    sensitivity_analysis,
    short_money,
)


ROOT = Path(__file__).resolve().parent
SUMMARY_PATH = (
    ROOT
    / "examples"
    / "asset_management"
    / "output"
    / "asset_management_summary.json"
)

st.set_page_config(
    page_title="Asset Management Decision Board | Kush Patel",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
<style>
  :root {
    --blueprint: #102A43;
    --survey: #177E75;
    --sheet: #EAF0F2;
    --ink: #14212B;
    --muted: #50616C;
    --line: #AFC0C8;
    --funding: #D9922E;
    --exception: #B84A3A;
    --panel: #F8FBFC;
  }
  .stApp {
    background-color: var(--sheet);
    background-image:
      linear-gradient(rgba(16,42,67,.035) 1px, transparent 1px),
      linear-gradient(90deg, rgba(16,42,67,.035) 1px, transparent 1px);
    background-size: 32px 32px;
    color: var(--ink);
  }
  .block-container { max-width: 1440px; padding-top: 2.1rem; }
  [data-testid="stSidebar"] { background: var(--blueprint); border-right: 0; }
  [data-testid="stSidebar"] * { color: #EAF0F2 !important; }
  [data-testid="stSidebar"] a { color: #65D3C9 !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(234,240,242,.2); }
  h1, h2, h3 { color: var(--blueprint) !important; letter-spacing: -.025em; }
  h1 { max-width: 28ch; font-size: clamp(2.2rem,3.4vw,4.3rem) !important; line-height: 1.05 !important; }
  p, li, label, [data-testid="stCaptionContainer"] { color: var(--ink); }
  a { color: #075E57 !important; }
  :focus-visible { outline: 3px solid var(--funding) !important; outline-offset: 3px !important; }
  .plan-meta { display:flex; flex-wrap:wrap; gap:.6rem 1rem; margin:.15rem 0 1rem; color:var(--muted); font-size:.8rem; }
  .plan-meta strong { color:var(--survey); }
  .plan-meta span { border-left:1px solid var(--line); padding-left:1rem; }
  .plan-lede { max-width:76ch; color:var(--muted); font-size:1.05rem; line-height:1.7; margin:1rem 0 1.25rem; }
  .decision-sheet { display:grid; grid-template-columns:minmax(0,1.45fr) minmax(270px,.75fr); border:2px solid var(--blueprint); background:rgba(248,251,252,.92); margin:1.1rem 0 1.35rem; }
  .decision-sheet > div { padding:1.15rem 1.3rem; }
  .decision-sheet .decision-main { border-right:1px solid var(--line); }
  .decision-sheet small { display:block; color:var(--muted); margin-bottom:.4rem; }
  .decision-sheet strong { display:block; color:var(--blueprint); font-size:clamp(1.35rem,2.2vw,2.15rem); line-height:1.18; }
  .decision-sheet p { margin:.65rem 0 0; color:var(--muted); line-height:1.55; }
  .decision-sheet .decision-next strong { color:var(--survey); font-size:1.08rem; }
  .control-strip { border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:.85rem 0 .25rem; margin-bottom:1rem; }
  .control-note { color:var(--muted); font-size:.82rem; margin:.2rem 0 1rem; }
  .evidence-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); border:1px solid var(--line); margin:1rem 0 1.25rem; background:rgba(248,251,252,.8); }
  .evidence-grid > div { padding:1rem 1.1rem; border-right:1px solid var(--line); }
  .evidence-grid > div:last-child { border-right:0; }
  .evidence-grid b { display:block; color:var(--funding); margin-bottom:.35rem; }
  .evidence-grid strong { display:block; color:var(--blueprint); margin-bottom:.35rem; }
  .evidence-grid span { color:var(--muted); font-size:.87rem; line-height:1.5; }
  .boundary { border-left:4px solid var(--exception); background:rgba(184,74,58,.07); padding:.85rem 1rem; margin:1rem 0; color:var(--muted); }
  .boundary strong { color:var(--exception); }
  .asset-sheet { border:1px solid var(--line); background:rgba(248,251,252,.88); padding:1.1rem 1.2rem; margin:.6rem 0 1rem; }
  .asset-sheet h3 { margin:.1rem 0 .5rem; }
  .asset-sheet p { margin:.35rem 0; color:var(--muted); }
  .asset-sheet strong { color:var(--blueprint); }
  .gate-sheet { display:grid; grid-template-columns:minmax(0,.7fr) minmax(0,1.3fr); border:2px solid var(--survey); background:rgba(23,126,117,.06); margin:.8rem 0 1.15rem; }
  .gate-sheet > div { padding:1rem 1.15rem; }
  .gate-sheet > div:first-child { background:var(--survey); }
  .gate-sheet > div:first-child small, .gate-sheet > div:first-child strong { color:#F8FBFC; }
  .gate-sheet small { display:block; color:var(--muted); margin-bottom:.35rem; }
  .gate-sheet strong { display:block; color:var(--blueprint); font-size:1.12rem; line-height:1.35; }
  .gate-sheet p { color:var(--muted); margin:.4rem 0 0; }
  .assumption-note { border-left:3px solid var(--funding); padding:.55rem .8rem; color:var(--muted); background:rgba(217,146,46,.07); margin:.35rem 0 1rem; }
  div[data-testid="stMetric"] { border-top:3px solid var(--survey); padding-top:.65rem; }
  [data-testid="stMetricValue"] { color:var(--blueprint); }
  [data-testid="stDataFrame"] { border:1px solid var(--line); background:var(--panel); }
  .stButton > button, .stDownloadButton > button { border-radius:2px; min-height:2.8rem; border:1px solid var(--blueprint); color:var(--blueprint); background:rgba(248,251,252,.75); font-weight:650; }
  .stButton > button:hover, .stDownloadButton > button:hover { border-color:var(--survey); color:var(--survey); }
  div[data-testid="stSegmentedControl"] button { min-height:2.8rem; font-weight:650; }
  @media (max-width: 900px) {
    .block-container { padding-top:3.2rem; }
    h1 { font-size:2.7rem !important; }
    .decision-sheet, .evidence-grid, .gate-sheet { grid-template-columns:1fr; }
    .decision-sheet .decision-main { border-right:0; border-bottom:1px solid var(--line); }
    .evidence-grid > div { border-right:0; border-bottom:1px solid var(--line); }
    .evidence-grid > div:last-child { border-bottom:0; }
  }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def data() -> tuple[pd.DataFrame, dict]:
    return load_assessment(), json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def risk_matrix(scope: pd.DataFrame) -> go.Figure:
    grouped = (
        scope.groupby(["criticality_grade", "condition_grade"], observed=True)
        .agg(asset_count=("asset_id", "count"), replacement_value=("replacement_cost_usd", "sum"))
        .reset_index()
    )
    grouped["risk_score"] = grouped["criticality_grade"] * grouped["condition_grade"]
    grouped["risk_band"] = grouped["risk_score"].map(
        lambda score: "Very High" if score >= 16 else "High" if score >= 10 else "Moderate" if score >= 5 else "Low"
    )
    figure = go.Figure()
    for band in RISK_ORDER:
        part = grouped[grouped["risk_band"].eq(band)]
        figure.add_trace(
            go.Scatter(
                x=part["criticality_grade"],
                y=part["condition_grade"],
                mode="markers+text",
                name=band,
                text=part["asset_count"].astype(int),
                textposition="middle center",
                marker={
                    "size": 18 + part["asset_count"] * 3.2,
                    "color": RISK_COLOURS[band],
                    "line": {"color": "#EAF0F2", "width": 1},
                    "opacity": .92,
                },
                customdata=part[["replacement_value"]],
                hovertemplate=(
                    "Criticality %{x:.0f}<br>Condition %{y:.0f}<br>"
                    "%{text} assets<br>Replacement value $%{customdata[0]:,.0f}<extra></extra>"
                ),
            )
        )
    figure.update_layout(
        height=410,
        margin={"l": 10, "r": 10, "t": 25, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F8FBFC",
        legend={"orientation": "h", "y": 1.12, "x": 0},
        xaxis={"title": "Criticality →", "dtick": 1, "range": [0.5, 5.5], "gridcolor": "#D2DDE2"},
        yaxis={"title": "Condition → worse", "dtick": 1, "range": [0.5, 5.5], "gridcolor": "#D2DDE2"},
        font={"family": "Aptos, Segoe UI, sans-serif", "color": "#14212B"},
    )
    return figure


def service_renewal(scope: pd.DataFrame) -> go.Figure:
    totals = (
        scope.groupby("asset_class", observed=True)["annualized_renewal_need_usd"]
        .sum()
        .sort_values()
    )
    figure = go.Figure(
        go.Bar(
            x=totals.values,
            y=totals.index,
            orientation="h",
            marker_color="#177E75",
            text=[short_money(value) for value in totals.values],
            textposition="outside",
            hovertemplate="%{y}<br>$%{x:,.0f} per year<extra></extra>",
        )
    )
    figure.update_layout(
        height=410,
        margin={"l": 10, "r": 65, "t": 25, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F8FBFC",
        xaxis={"title": "Annualized renewal need", "gridcolor": "#D2DDE2"},
        yaxis={"title": ""},
        font={"family": "Aptos, Segoe UI, sans-serif", "color": "#14212B"},
    )
    return figure


def spatial_layer(scope: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    for band in RISK_ORDER:
        part = scope[scope["risk_band"].eq(band)]
        figure.add_trace(
            go.Scatter(
                x=part["longitude"],
                y=part["latitude"],
                mode="markers",
                name=band,
                text=part["asset_id"],
                customdata=part[["asset_class", "condition_grade", "criticality_grade", "recommended_intervention"]],
                marker={
                    "size": 7 + part["criticality_grade"] * 2.6,
                    "color": RISK_COLOURS[band],
                    "line": {"color": "#F8FBFC", "width": 1},
                    "opacity": .9,
                },
                hovertemplate=(
                    "<b>%{text}</b><br>%{customdata[0]}<br>Condition %{customdata[1]:.0f} · "
                    "criticality %{customdata[2]:.0f}<br>%{customdata[3]}<extra></extra>"
                ),
            )
        )
    figure.update_layout(
        height=540,
        margin={"l": 10, "r": 10, "t": 25, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#102A43",
        legend={"orientation": "h", "y": 1.08, "x": 0},
        xaxis={"title": "Longitude · WGS 84", "gridcolor": "rgba(234,240,242,.16)", "color": "#D7E3E8"},
        yaxis={"title": "Latitude · WGS 84", "gridcolor": "rgba(234,240,242,.16)", "color": "#D7E3E8", "scaleanchor": "x", "scaleratio": 1},
        font={"family": "Aptos, Segoe UI, sans-serif", "color": "#14212B"},
    )
    return figure


def annual_plan_chart(programme: pd.DataFrame, assumptions: dict) -> go.Figure:
    years = list(
        range(
            assumptions["planning_start_year"],
            assumptions["planning_start_year"] + assumptions["planning_years"],
        )
    )
    scheduled = programme[programme["programme_status"].eq("Scheduled in screen")]
    annual = (
        scheduled.groupby("programme_year", observed=True)
        .agg(
            planned_capital_usd=("screened_programme_cost_usd", "sum"),
            scheduled_assets=("asset_id", "count"),
        )
        .reindex(years, fill_value=0)
    )
    figure = go.Figure(
        go.Bar(
            x=[str(year) for year in years],
            y=annual["planned_capital_usd"],
            customdata=annual[["scheduled_assets"]],
            marker_color="#177E75",
            text=[short_money(value) for value in annual["planned_capital_usd"]],
            textposition="outside",
            hovertemplate=(
                "%{x}<br>$%{y:,.0f} screened capital<br>"
                "%{customdata[0]:.0f} assets<extra></extra>"
            ),
        )
    )
    figure.add_hline(
        y=assumptions["annual_budget_usd"],
        line_color="#D9922E",
        line_dash="dash",
        annotation_text="Annual envelope",
        annotation_position="top left",
    )
    figure.update_layout(
        height=390,
        margin={"l": 10, "r": 30, "t": 35, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#F8FBFC",
        xaxis={"title": "Programme year", "type": "category"},
        yaxis={"title": "Screened capital", "gridcolor": "#D2DDE2"},
        showlegend=False,
        font={"family": "Aptos, Segoe UI, sans-serif", "color": "#14212B"},
    )
    return figure


assessment, published = data()
all_services = sorted(
    assessment.loc[
        assessment["data_quality_status"].eq("PLANNING_READY"), "asset_class"
    ].unique()
)

with st.sidebar:
    st.markdown("### Asset decision board")
    st.markdown(
        "**Decision question**\n\nWhich capital posture should proceed to validation, "
        "what can be delivered and afforded, and what must be proven before approval?"
    )
    st.divider()
    st.markdown(
        "**Evidence scope**\n\n96 synthetic asset records  \n87 planning-ready  \n"
        "9 source exceptions blocked  \n78 governed in-service GIS points"
    )
    st.markdown(
        "**Method boundary**\n\nAnalytical screening only  \nNo engineering approval  \n"
        "No live municipal system  \nNo authority to spend"
    )
    st.markdown(
        "[Asset evidence](https://github.com/KushPatel29/legacy-to-fabric-migration/tree/master/examples/asset_management)  \n"
        "[Capital business case](https://github.com/KushPatel29/legacy-to-fabric-migration/blob/master/docs/business-analysis/ASSET_CAPITAL_PROGRAM_BUSINESS_CASE.md)  \n"
        "[Portfolio](https://kushpatel29.github.io/#asset-management-proof)"
    )

st.markdown(
    '<p class="plan-meta"><strong>Asset capital-programme evidence</strong>'
    '<span>Planning basis: 31 Aug 2026</span><span>Six services</span>'
    '<span>Versioned + CI tested</span></p>',
    unsafe_allow_html=True,
)
st.title("Build a five-year asset programme decision that survives challenge.")
st.markdown(
    '<p class="plan-lede">Move from condition and GIS evidence to options, '
    "affordability, sensitivities, delivery gates, owned risks, measurable benefits, "
    "and an exportable approval pack. Every result keeps its assumption and evidence "
    'boundary visible.</p>',
    unsafe_allow_html=True,
)

st.markdown("## Set the decision basis")
control_1, control_2, control_3 = st.columns([1.1, .9, 1])
with control_1:
    services = st.multiselect(
        "Service scope",
        all_services,
        default=all_services,
        key="asset_services",
        help="The programme includes only planning-ready, in-service assets in these services.",
    )
with control_2:
    risk_bands = st.multiselect(
        "Risk bands",
        RISK_ORDER,
        default=RISK_ORDER,
        key="asset_risk_bands",
        help="This focuses the review; it never changes an asset's published score.",
    )
with control_3:
    budget_millions = st.slider(
        "Illustrative annual envelope ($M)",
        min_value=2.0,
        max_value=20.0,
        value=8.0,
        step=.5,
        key="asset_budget_millions",
    )

with st.expander("Planning, delivery, and funding assumptions"):
    assumption_1, assumption_2, assumption_3 = st.columns(3)
    with assumption_1:
        planning_years = st.select_slider(
            "Planning horizon (years)",
            options=[3, 5, 7, 10],
            value=5,
            key="asset_planning_years",
        )
        delivery_capacity = st.slider(
            "Delivery capacity (projects / year)",
            min_value=4,
            max_value=24,
            value=14,
            key="asset_delivery_capacity",
        )
    with assumption_2:
        escalation_pct = st.slider(
            "Annual cost escalation (%)",
            min_value=0.0,
            max_value=10.0,
            value=3.5,
            step=.5,
            key="asset_escalation_pct",
        )
        contingency_pct = st.slider(
            "Planning contingency (%)",
            min_value=0.0,
            max_value=30.0,
            value=15.0,
            step=1.0,
            key="asset_contingency_pct",
        )
        discount_rate_pct = st.slider(
            "Capital discount rate (%)",
            min_value=0.0,
            max_value=10.0,
            value=4.0,
            step=.5,
            key="asset_discount_rate_pct",
        )
    with assumption_3:
        grant_share_pct = st.slider(
            "Indicative grant share (%)",
            min_value=0,
            max_value=50,
            value=20,
            key="asset_grant_share_pct",
        )
        reserve_share_pct = st.slider(
            "Indicative reserve / revenue share (%)",
            min_value=0,
            max_value=100 - grant_share_pct,
            value=min(50, 100 - grant_share_pct),
            key="asset_reserve_share_pct",
        )
        st.markdown(
            f'<div class="assumption-note">Debt / other is the balancing '
            f"{100 - grant_share_pct - reserve_share_pct}%. Funding sources are "
            "indicative until policy, eligibility, timing, and authority are confirmed.</div>",
            unsafe_allow_html=True,
        )

if not services or not risk_bands:
    st.warning("Select at least one service and one risk band to build a reviewable case.")
    st.stop()

budget_usd = int(budget_millions * 1_000_000)
assumptions = programme_assumptions(
    budget_usd,
    planning_years=planning_years,
    cost_escalation_pct=escalation_pct,
    contingency_pct=contingency_pct,
    discount_rate_pct=discount_rate_pct,
    delivery_capacity_per_year=delivery_capacity,
    grant_share_pct=grant_share_pct,
    reserve_share_pct=reserve_share_pct,
)
scope, programme = capital_scenario(assessment, budget_usd, services, risk_bands)
summary = scenario_summary(scope, programme, budget_usd)
capital_plan = multi_year_programme(scope, assumptions)
capital_summary = programme_summary(capital_plan, assumptions)
options = programme_options(scope, assumptions)
sensitivities = sensitivity_analysis(scope, assumptions)
risks = programme_risk_register()
benefits = benefits_register(scope, capital_plan)
roadmap = delivery_roadmap()
sources = funding_sources(capital_plan, assumptions)
requirements = decision_requirements()

st.markdown(
    f"""
<div class="decision-sheet">
  <div class="decision-main">
    <small>Option 2 screen · {len(services)} services · {planning_years}-year horizon</small>
    <strong>{capital_summary['scheduled_assets']} of {len(capital_plan)} candidates are scheduled inside a {short_money(budget_usd)} annual envelope.</strong>
    <p>{short_money(capital_summary['planned_capital_usd'])} of escalated, contingent capital is screened across the horizon. {capital_summary['deferred_candidates']} candidates remain beyond it with {short_money(capital_summary['deferred_annualized_risk_exposure_usd'])} of modelled annualized risk exposure.</p>
  </div>
  <div class="decision-next">
    <small>Decision status</small>
    <strong>CONDITIONAL — proceed to validation, not authority to spend.</strong>
    <p>Every scheduled asset still needs accountable condition, scope, service, cost, funding, delivery, climate, accessibility, equity, safety, and procurement evidence.</p>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

workspace = st.segmented_control(
    "Decision workspace",
    [
        "Decision brief",
        "Business case",
        "Funding plan",
        "Risk & lifecycle",
        "GIS & assurance",
    ],
    default="Decision brief",
    key="asset_workspace",
    required=True,
    width="stretch",
    label_visibility="collapsed",
)
st.markdown(
    '<p class="control-note">Only the selected workspace is rendered. The decision '
    "basis remains visible so each output keeps its scope and assumptions.</p>",
    unsafe_allow_html=True,
)

if workspace == "Decision brief":
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric(
        "Assets in scope",
        f"{summary['assets_in_scope']}",
        f"{96 - summary['assets_in_scope']} outside current scope",
        delta_color="off",
    )
    metric_2.metric(
        "Replacement value",
        short_money(summary["replacement_value_usd"]),
        "planning-ready, in-service basis",
        delta_color="off",
    )
    metric_3.metric(
        "Annual renewal need",
        short_money(summary["annualized_renewal_need_usd"]),
        "replacement value ÷ expected life",
        delta_color="off",
    )
    metric_4.metric(
        "High / very-high risk",
        f"{summary['high_or_very_high_risk']}",
        "condition × criticality",
        delta_color="off",
    )
    st.markdown(
        """
<div class="evidence-grid">
  <div><b>Case for change</b><strong>Renewal pressure must become a governed decision</strong><span>Condition, criticality, inspection recency, replacement value, treatment screen, ownership, and WGS 84 location remain traceable at asset level.</span></div>
  <div><b>Recommended posture</b><strong>Take risk-based renewal to validation</strong><span>Option 2 balances the selected annual envelope and delivery capacity. It is a screening recommendation—not approval.</span></div>
  <div><b>Approval conditions</b><strong>Prove the local case before commitment</strong><span>Validate service levels, engineering scope, whole-life options, climate, safety, accessibility, equity, funding, procurement, consultation, and deliverability.</span></div>
</div>
""",
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.05, .95])
    with left:
        st.markdown("## Condition and criticality")
        st.plotly_chart(
            risk_matrix(scope), width="stretch", config={"displaylogo": False}
        )
    with right:
        st.markdown("## Renewal need by service")
        st.plotly_chart(
            service_renewal(scope), width="stretch", config={"displaylogo": False}
        )
    st.markdown("## First assets to validate")
    st.dataframe(
        capital_plan[
            [
                "asset_id",
                "asset_class",
                "risk_band",
                "recommended_intervention",
                "treatment_cost_usd",
                "priority_score",
                "programme_year",
                "programme_status",
            ]
        ].head(12),
        hide_index=True,
        width="stretch",
        column_config={
            "treatment_cost_usd": st.column_config.NumberColumn(
                "Treatment screen", format="$%,.0f"
            ),
            "priority_score": st.column_config.NumberColumn("Priority", format="%.1f"),
            "programme_year": st.column_config.NumberColumn("Screened year", format="%d"),
        },
    )

if workspace == "Business case":
    st.markdown(
        """
<div class="gate-sheet">
  <div><small>Recommended decision</small><strong>OPTION 2 · RISK-BASED RENEWAL</strong></div>
  <div><small>Approval wording</small><strong>Authorize structured validation and option development within the selected planning basis.</strong><p>Do not authorize construction or procurement until the stated evidence gates are passed and residual risks are accepted.</p></div>
</div>
""",
        unsafe_allow_html=True,
    )
    case_tabs = st.tabs(
        ["Options & affordability", "Sensitivity", "Risk & benefits", "Delivery gates"]
    )
    with case_tabs[0]:
        st.markdown("## Three decision postures")
        st.dataframe(
            options[
                [
                    "option",
                    "annual_envelope_usd",
                    "delivery_capacity_per_year",
                    "scheduled_assets",
                    "scheduled_high_or_very_high",
                    "capital_present_value_usd",
                    "deferred_candidates",
                    "deferred_annualized_risk_exposure_usd",
                ]
            ],
            hide_index=True,
            width="stretch",
            column_config={
                "option": "Option",
                "annual_envelope_usd": st.column_config.NumberColumn(
                    "Annual envelope", format="$%,.0f"
                ),
                "delivery_capacity_per_year": st.column_config.NumberColumn(
                    "Capacity / year", format="%d"
                ),
                "scheduled_assets": st.column_config.NumberColumn(
                    "Scheduled", format="%d"
                ),
                "scheduled_high_or_very_high": st.column_config.NumberColumn(
                    "High / very-high", format="%d"
                ),
                "capital_present_value_usd": st.column_config.NumberColumn(
                    "Capital PV", format="$%,.0f"
                ),
                "deferred_candidates": st.column_config.NumberColumn(
                    "Beyond horizon", format="%d"
                ),
                "deferred_annualized_risk_exposure_usd": st.column_config.NumberColumn(
                    "Deferred annualized risk", format="$%,.0f"
                ),
            },
        )
        st.caption(
            "Minimum response constrains new commitments; risk-based renewal uses "
            "the selected basis; accelerated resilience increases both funding and "
            "delivery capacity."
        )
        st.caption(
            "Capital PV discounts screened project costs only. This is not a "
            "whole-life economic NPV because operating costs, service benefits, "
            "residual values, and monetized risk reduction have not been evidenced."
        )
        st.markdown("## Indicative funding case for Option 2")
        st.dataframe(
            sources,
            hide_index=True,
            width="stretch",
            column_config={
                "funding_source": "Funding source",
                "indicative_share_pct": st.column_config.NumberColumn(
                    "Share", format="%.1f%%"
                ),
                "indicative_amount_usd": st.column_config.NumberColumn(
                    "Indicative amount", format="$%,.0f"
                ),
                "validation_required": "Validation required",
            },
        )
    with case_tabs[1]:
        st.markdown("## What could change the recommendation?")
        st.dataframe(
            sensitivities,
            hide_index=True,
            width="stretch",
            column_config={
                "sensitivity": "Sensitivity",
                "decision_stress": "Decision stress",
                "effective_annual_envelope_usd": st.column_config.NumberColumn(
                    "Effective annual envelope", format="$%,.0f"
                ),
                "cost_shock_pct": st.column_config.NumberColumn(
                    "Cost shock", format="%.1f%%"
                ),
                "scheduled_assets": st.column_config.NumberColumn(
                    "Scheduled", format="%d"
                ),
                "planned_capital_usd": st.column_config.NumberColumn(
                    "Planned capital", format="$%,.0f"
                ),
                "deferred_candidates": st.column_config.NumberColumn(
                    "Beyond horizon", format="%d"
                ),
                "deferred_annualized_risk_exposure_usd": st.column_config.NumberColumn(
                    "Deferred annualized risk", format="$%,.0f"
                ),
            },
        )
        worst = sensitivities.sort_values(
            "deferred_annualized_risk_exposure_usd", ascending=False
        ).iloc[0]
        st.warning(
            f"Most material tested stress: {worst['sensitivity']} leaves "
            f"{int(worst['deferred_candidates'])} candidates beyond the horizon "
            f"with {short_money(worst['deferred_annualized_risk_exposure_usd'])} "
            "of modelled annualized risk exposure. Reconfirm the option if this "
            "threshold is unacceptable."
        )
    with case_tabs[2]:
        st.markdown("## Programme risk register")
        st.dataframe(
            risks,
            hide_index=True,
            width="stretch",
            height=390,
            column_config={
                "priority": "Priority",
                "risk_id": "Risk ID",
                "category": "Category",
                "description": "Risk event",
                "likelihood": "Likelihood",
                "impact": "Impact",
                "risk_level": "Level",
                "mitigation": "Treatment",
                "owner": "Owner",
                "status": "Status",
                "trigger": "Escalation trigger",
            },
        )
        st.caption(
            "All nine material risks remain open or in treatment. Owners are "
            "accountable roles, not invented individuals."
        )
        st.markdown("## Benefits and assurance register")
        st.dataframe(
            benefits,
            hide_index=True,
            width="stretch",
            height=340,
            column_config={
                "benefit_id": "Benefit ID",
                "objective": "Objective",
                "measure": "Measure",
                "baseline": "Baseline",
                "target": "Target",
                "owner": "Owner",
                "cadence": "Cadence",
                "evidence": "Evidence",
            },
        )
    with case_tabs[3]:
        st.markdown("## Decision and delivery roadmap")
        st.dataframe(
            roadmap,
            hide_index=True,
            width="stretch",
            height=390,
            column_config={
                "gate": "Gate",
                "phase": "Phase",
                "indicative_timing": "Indicative timing",
                "accountable_role": "Accountable role",
                "evidence_required": "Evidence required",
                "decision": "Decision",
            },
        )
        st.markdown("## Traceable business-case requirements")
        st.dataframe(
            requirements,
            hide_index=True,
            width="stretch",
            height=390,
            column_config={
                "requirement_id": "Requirement ID",
                "category": "Category",
                "requirement": "Requirement",
                "acceptance_criteria": "Acceptance criteria",
                "owner": "Owner",
                "decision_gate": "Decision gate",
                "evidence_status": "Evidence status",
            },
        )
        st.markdown("### Minimum evidence before authority to spend")
        st.markdown(
            "1. Signed engineering condition and treatment-scope validation.\n"
            "2. Service-level, safety, accessibility, climate, environmental, equity, and statutory impact assessment.\n"
            "3. Cost class, whole-life alternatives, funding eligibility, cash flow, and affordability sign-off.\n"
            "4. Procurement route, market capacity, project bundling, dependencies, permits, and delivery-resource plan.\n"
            "5. Stakeholder and community engagement record, residual-risk acceptance, and accountable approval."
        )

    pack = evidence_pack(
        scope,
        programme,
        summary,
        {"services": services, "risk_bands": risk_bands, "budget_usd": budget_usd},
        assumptions,
    )
    st.download_button(
        "Download investment-committee evidence pack",
        data=pack,
        file_name="asset-capital-programme-business-case.zip",
        mime="application/zip",
        width="stretch",
    )
    st.caption(
        "Includes the exact scope, assumptions, multi-year plan, three options, "
        "sensitivities, funding mix, risk and benefits registers, delivery roadmap, "
        "and portable decision brief—not an approval record."
    )

if workspace == "Funding plan":
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Annual envelope", short_money(budget_usd))
    metric_2.metric(
        f"{planning_years}-year capital",
        short_money(capital_summary["planned_capital_usd"]),
        "escalated + contingent",
        delta_color="off",
    )
    metric_3.metric(
        "Scheduled assets",
        f"{capital_summary['scheduled_assets']}",
        f"{capital_summary['scheduled_high_or_very_high']} high / very-high",
        delta_color="off",
    )
    metric_4.metric(
        "Beyond horizon",
        f"{capital_summary['deferred_candidates']}",
        short_money(capital_summary["deferred_annualized_risk_exposure_usd"])
        + " annualized risk",
        delta_color="off",
    )
    st.markdown("## Annual affordability and throughput")
    st.plotly_chart(
        annual_plan_chart(capital_plan, assumptions),
        width="stretch",
        config={"displaylogo": False},
    )

    if capital_plan.empty:
        st.info("No capital candidates remain in the selected service and risk scope.")
    else:
        asset_options = capital_plan["asset_id"].tolist()
        selected_asset_id = st.selectbox(
            "Inspect a prioritized asset", asset_options, index=0
        )
        selected = capital_plan[capital_plan["asset_id"].eq(selected_asset_id)].iloc[0]
        programme_year = (
            str(int(selected["programme_year"]))
            if pd.notna(selected["programme_year"])
            else "Beyond horizon"
        )
        screened_cost = (
            short_money(selected["screened_programme_cost_usd"])
            if pd.notna(selected["screened_programme_cost_usd"])
            else "Not scheduled"
        )
        st.markdown(
            f"""
<div class="asset-sheet">
  <h3>{selected['asset_id']} · {selected['asset_name']}</h3>
  <p><strong>{selected['programme_status']}</strong> · screened year: {programme_year} · {selected['asset_class']} · owner: {selected['service_owner']}</p>
  <p>Condition {int(selected['condition_grade'])}/5 · criticality {int(selected['criticality_grade'])}/5 · {selected['risk_band']} risk · {float(selected['life_consumed_pct']):.1f}% life consumed</p>
  <p>Screened intervention: <strong>{selected['recommended_intervention']}</strong> · source treatment screen {short_money(selected['treatment_cost_usd'])} · scheduled cost {screened_cost}</p>
  <p>Validation required: condition, alternatives, service impact, whole-life cost, dependencies, climate/accessibility/equity/safety screens, funding, procurement, delivery, and approval.</p>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown("## Multi-year prioritized programme")
        st.dataframe(
            capital_plan[
                [
                    "asset_id",
                    "asset_name",
                    "asset_class",
                    "risk_band",
                    "recommended_intervention",
                    "priority_score",
                    "programme_year",
                    "screened_programme_cost_usd",
                    "programme_status",
                    "decision_gate",
                ]
            ],
            hide_index=True,
            width="stretch",
            height=520,
            column_config={
                "priority_score": st.column_config.NumberColumn(
                    "Priority", format="%.1f"
                ),
                "programme_year": st.column_config.NumberColumn(
                    "Screened year", format="%d"
                ),
                "screened_programme_cost_usd": st.column_config.NumberColumn(
                    "Escalated + contingent cost", format="$%,.0f"
                ),
            },
        )

if workspace == "Risk & lifecycle":
    chart_1, chart_2 = st.columns([1.05, .95])
    with chart_1:
        st.markdown("## Asset risk matrix")
        st.plotly_chart(
            risk_matrix(scope), width="stretch", config={"displaylogo": False}
        )
    with chart_2:
        st.markdown("## Lifecycle and inspection posture")
        posture = (
            scope.groupby(["asset_class", "inspection_status"], observed=True)
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        st.dataframe(posture, hide_index=True, width="stretch", height=275)
        st.markdown("### Published method")
        st.markdown(
            "- Risk = condition grade × criticality grade.\n"
            "- Renewal need = replacement value ÷ expected life.\n"
            "- Priority = risk × 4 + capped life consumed × 0.18 + inspection-recency penalty.\n"
            "- A missing inspection triggers condition assessment; it does not invent evidence."
        )
    st.markdown("## Asset-level trace")
    st.dataframe(
        scope.sort_values(
            ["risk_score", "priority_score"], ascending=False
        )[
            [
                "asset_id",
                "asset_class",
                "service_owner",
                "condition_grade",
                "criticality_grade",
                "risk_band",
                "life_consumed_pct",
                "inspection_status",
                "annualized_renewal_need_usd",
                "recommended_intervention",
            ]
        ],
        hide_index=True,
        width="stretch",
        height=540,
        column_config={
            "annualized_renewal_need_usd": st.column_config.NumberColumn(
                "Annual renewal need", format="$%,.0f"
            )
        },
    )

if workspace == "GIS & assurance":
    tabs = st.tabs(["Governed risk layer", "Source exceptions", "Acceptance controls"])
    with tabs[0]:
        st.markdown("## Governed WGS 84 risk layer")
        st.plotly_chart(
            spatial_layer(scope), width="stretch", config={"displaylogo": False}
        )
        st.caption(
            "Synthetic point geometry for spatial QA and risk context. No parcel, "
            "road-network, hydraulic, accessibility, climate-hazard, or routing "
            "model is implied."
        )
    with tabs[1]:
        exceptions = assessment[
            assessment["data_quality_status"].eq("DATA_REMEDIATION")
        ].copy()
        st.error(
            f"{len(exceptions)} source records are blocked from scoring, GIS "
            "publication, and funding until their material defects are resolved."
        )
        st.dataframe(
            exceptions[
                [
                    "asset_id",
                    "asset_name",
                    "asset_class",
                    "service_owner",
                    "data_quality_reasons",
                    "recommended_intervention",
                ]
            ],
            hide_index=True,
            width="stretch",
        )
    with tabs[2]:
        controls = pd.DataFrame(
            [
                ["AM-01", "Unique governed asset identity", "Duplicate or missing IDs are blocked", "PASS"],
                ["AM-02", "Valid lifecycle and owner", "Invalid lifecycle or missing owner is blocked", "PASS"],
                ["AM-03", "Planning-basis condition and criticality", "Missing or out-of-range grades are blocked", "PASS"],
                ["AM-04", "Replacement value and expected life", "Missing/non-positive planning basis is blocked", "PASS"],
                ["GIS-01", "Valid WGS 84 point", "Invalid coordinates are excluded from publication", "PASS"],
                ["CAP-01", "Annual funding ceiling", "Screened annual spend never exceeds the selected envelope", "PASS"],
                ["CAP-02", "Delivery capacity", "Annual scheduled count never exceeds the selected capacity", "PASS"],
                ["CAP-03", "Decision boundary", "Engineering, service, impact, funding, delivery, and approval gaps remain visible", "PASS"],
            ],
            columns=["Control", "Requirement", "Acceptance evidence", "Status"],
        )
        st.success("8 of 8 publication and decision-boundary controls are demonstrated.")
        st.dataframe(controls, hide_index=True, width="stretch")
        st.markdown("### Production decisions still required")
        st.markdown(
            "Engineering condition standards and treatment alternatives; service-level "
            "consequence definitions; safety, accessibility, climate, environment, and "
            "equity criteria; authoritative GIS ownership; whole-life economics; funding "
            "policy; procurement route; delivery capacity; consultation; and approval authority."
        )

st.markdown(
    '<div class="boundary"><strong>Evidence boundary.</strong> Every asset, coordinate, '
    "cost, condition, priority, option, benefit target, and funding scenario is "
    "synthetic. This demonstrates a transferable asset-information and business-analysis "
    "method; it is not municipal employment, an engineering assessment, a whole-life "
    'economic appraisal, or an approved capital plan.</div>',
    unsafe_allow_html=True,
)
st.caption(
    "Kush Patel · Business analysis, asset information, GIS, Power BI, capital "
    "planning, and decision assurance · Source evidence is versioned and tested in GitHub"
)
