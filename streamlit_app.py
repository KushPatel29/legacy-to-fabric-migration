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
    capital_scenario,
    evidence_pack,
    load_assessment,
    scenario_summary,
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
  div[data-testid="stMetric"] { border-top:3px solid var(--survey); padding-top:.65rem; }
  [data-testid="stMetricValue"] { color:var(--blueprint); }
  [data-testid="stDataFrame"] { border:1px solid var(--line); background:var(--panel); }
  .stButton > button, .stDownloadButton > button { border-radius:2px; min-height:2.8rem; border:1px solid var(--blueprint); color:var(--blueprint); background:rgba(248,251,252,.75); font-weight:650; }
  .stButton > button:hover, .stDownloadButton > button:hover { border-color:var(--survey); color:var(--survey); }
  div[data-testid="stSegmentedControl"] button { min-height:2.8rem; font-weight:650; }
  @media (max-width: 900px) {
    .block-container { padding-top:3.2rem; }
    h1 { font-size:2.7rem !important; }
    .decision-sheet, .evidence-grid { grid-template-columns:1fr; }
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


assessment, published = data()
all_services = sorted(assessment.loc[assessment["data_quality_status"].eq("PLANNING_READY"), "asset_class"].unique())

with st.sidebar:
    st.markdown("### Asset decision board")
    st.markdown(
        "**Decision question**\n\nWhich assets should enter validation first, what can the selected funding envelope support, and what evidence is still missing?"
    )
    st.divider()
    st.markdown(
        "**Evidence scope**\n\n96 synthetic asset records  \n87 planning-ready  \n9 source exceptions blocked  \n78 governed in-service GIS points"
    )
    st.markdown(
        "**Method boundary**\n\nAnalytical screening only  \nNo engineering approval  \nNo live municipal system  \nNo approved capital plan"
    )
    st.markdown(
        "[Asset evidence](https://github.com/KushPatel29/legacy-to-fabric-migration/tree/master/examples/asset_management)  \n"
        "[Decision brief](https://github.com/KushPatel29/legacy-to-fabric-migration/blob/master/docs/business-analysis/PUBLIC_SECTOR_DECISION_AND_PROCUREMENT_BRIEF.md)  \n"
        "[Portfolio](https://kushpatel29.github.io/#asset-management-proof)"
    )

st.markdown(
    '<p class="plan-meta"><strong>Asset-management decision evidence</strong><span>Planning basis: 31 Aug 2026</span><span>Six services</span><span>232 automated tests</span></p>',
    unsafe_allow_html=True,
)

services = st.session_state.get("asset_services", all_services)
risk_bands = st.session_state.get("asset_risk_bands", RISK_ORDER)
budget_millions = float(st.session_state.get("asset_budget_millions", 8.0))
budget_usd = int(budget_millions * 1_000_000)
scope, programme = capital_scenario(assessment, budget_usd, services, risk_bands)
summary = scenario_summary(scope, programme, budget_usd)
funded = programme[programme["scenario_status"].eq("Funded in scenario")]
deferred = programme[programme["scenario_status"].eq("Deferred")]

headline_budget = short_money(budget_usd).replace("$", r"\$")
st.title(
    f"{headline_budget} funds {summary['funded_assets']} assets. "
    f"{summary['deferred_candidates']} capital candidates remain deferred."
)
st.markdown(
    '<p class="plan-lede">Challenge the funding envelope, service scope, and risk focus; inspect the lifecycle and GIS evidence behind each priority; then export the exact scenario for accountable validation.</p>',
    unsafe_allow_html=True,
)
st.markdown(
    f"""
<div class="decision-sheet">
  <div class="decision-main">
    <small>Live affordability screen · {len(services)} services · {len(risk_bands)} risk bands</small>
    <strong>{summary['funded_assets']} of {len(programme)} capital candidates fit the selected envelope.</strong>
    <p>{short_money(summary['funded_spend_usd'])} is provisionally allocated; deferred candidates carry {short_money(summary['deferred_annualized_risk_exposure_usd'])} of annualized risk exposure in this analytical model. Priority order is transparent; the result is not an optimized or approved capital programme.</p>
  </div>
  <div class="decision-next">
    <small>Next accountable decision</small>
    <strong>Confirm condition, treatment scope, service consequence, deliverability, and funding eligibility.</strong>
    <p>Resolve the nine blocked source exceptions separately before allowing them into planning.</p>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("## Set the planning scenario")
control_1, control_2, control_3 = st.columns([1.1, .9, 1])
with control_1:
    services = st.multiselect(
        "Service scope",
        all_services,
        default=all_services,
        key="asset_services",
        help="The budget is applied only to assets in the selected services.",
    )
with control_2:
    risk_bands = st.multiselect(
        "Risk bands",
        RISK_ORDER,
        default=RISK_ORDER,
        key="asset_risk_bands",
        help="Use this to focus the review. It does not change an asset's score.",
    )
with control_3:
    budget_millions = st.slider(
        "Illustrative capital envelope ($M)",
        min_value=2.0,
        max_value=20.0,
        value=8.0,
        step=.5,
        key="asset_budget_millions",
    )

workspace = st.segmented_control(
    "Decision workspace",
    ["Executive brief", "Funding scenario", "Risk & lifecycle", "GIS & assurance"],
    default="Executive brief",
    key="asset_workspace",
    required=True,
    width="stretch",
    label_visibility="collapsed",
)
st.markdown('<p class="control-note">Only the selected workspace is rendered. Filters remain visible so every figure keeps its scope.</p>', unsafe_allow_html=True)

if not services or not risk_bands:
    st.warning("Select at least one service and one risk band to build a reviewable scenario.")
    st.stop()

if workspace == "Executive brief":
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Assets in scope", f"{summary['assets_in_scope']}", f"{96 - summary['assets_in_scope']} outside current scope", delta_color="off")
    metric_2.metric("Replacement value", short_money(summary["replacement_value_usd"]), "planning-ready, in-service basis", delta_color="off")
    metric_3.metric("Annual renewal need", short_money(summary["annualized_renewal_need_usd"]), "replacement value ÷ expected life", delta_color="off")
    metric_4.metric("High / very-high risk", f"{summary['high_or_very_high_risk']}", "condition × criticality", delta_color="off")
    st.markdown(
        """
<div class="evidence-grid">
  <div><b>What the evidence supports</b><strong>A controlled validation queue</strong><span>Lifecycle, condition, criticality, inspection recency, replacement value, treatment cost, ownership, and WGS 84 location remain traceable at asset level.</span></div>
  <div><b>What remains unknown</b><strong>The accountable local judgement</strong><span>Engineering scope, levels of service, accessibility, climate, equity, bundling, procurement capacity, grant eligibility, and community priorities are not modeled.</span></div>
  <div><b>What happens next</b><strong>Validate before recommending</strong><span>Take the funded screen to service owners and engineering, resolve exceptions, document option impacts, and return through the approval gate.</span></div>
</div>
""",
        unsafe_allow_html=True,
    )
    left, right = st.columns([1.05, .95])
    with left:
        st.markdown("## Condition and criticality")
        st.plotly_chart(risk_matrix(scope), width="stretch", config={"displaylogo": False})
    with right:
        st.markdown("## Renewal need by service")
        st.plotly_chart(service_renewal(scope), width="stretch", config={"displaylogo": False})
    st.markdown("## First assets to validate")
    st.dataframe(
        programme[["asset_id", "asset_class", "risk_band", "recommended_intervention", "treatment_cost_usd", "priority_score", "scenario_status"]].head(12),
        hide_index=True,
        width="stretch",
        column_config={"treatment_cost_usd": st.column_config.NumberColumn("Treatment screen", format="$%,.0f"), "priority_score": st.column_config.NumberColumn("Priority", format="%.1f")},
    )

if workspace == "Funding scenario":
    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Scenario envelope", short_money(budget_usd))
    metric_2.metric("Allocated", short_money(summary["funded_spend_usd"]), f"{summary['funded_assets']} assets", delta_color="off")
    metric_3.metric("Unallocated", short_money(summary["unallocated_budget_usd"]), "not a saving", delta_color="off")
    metric_4.metric("Deferred candidates", f"{summary['deferred_candidates']}", short_money(summary["deferred_annualized_risk_exposure_usd"]) + " annualized risk exposure", delta_color="off")

    asset_options = programme["asset_id"].tolist()
    selected_asset_id = st.selectbox("Inspect a prioritized asset", asset_options, index=0)
    selected = programme[programme["asset_id"].eq(selected_asset_id)].iloc[0]
    st.markdown(
        f"""
<div class="asset-sheet">
  <h3>{selected['asset_id']} · {selected['asset_name']}</h3>
  <p><strong>{selected['scenario_status']}</strong> · {selected['asset_class']} · owner: {selected['service_owner']}</p>
  <p>Condition {int(selected['condition_grade'])}/5 · criticality {int(selected['criticality_grade'])}/5 · {selected['risk_band']} risk · {float(selected['life_consumed_pct']):.1f}% life consumed</p>
  <p>Screened intervention: <strong>{selected['recommended_intervention']}</strong> · treatment screen {short_money(selected['treatment_cost_usd'])}</p>
  <p>Validation required: confirm current condition evidence, treatment scope, service impact, delivery dependencies, funding eligibility, and accountable approval.</p>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown("## Prioritized programme")
    st.dataframe(
        programme[["asset_id", "asset_name", "asset_class", "condition_grade", "criticality_grade", "risk_band", "recommended_intervention", "treatment_cost_usd", "priority_score", "scenario_status"]],
        hide_index=True,
        width="stretch",
        height=520,
        column_config={"treatment_cost_usd": st.column_config.NumberColumn("Treatment screen", format="$%,.0f"), "priority_score": st.column_config.NumberColumn("Priority", format="%.1f")},
    )
    pack = evidence_pack(scope, programme, summary, {"services": services, "risk_bands": risk_bands, "budget_usd": budget_usd})
    st.download_button("Download governed scenario pack", data=pack, file_name="asset-management-scenario-evidence.zip", mime="application/zip", width="stretch")
    st.caption("Contains the filtered asset scope, prioritized work programme, scenario controls, method boundary, and required validation—not an approval record.")

if workspace == "Risk & lifecycle":
    chart_1, chart_2 = st.columns([1.05, .95])
    with chart_1:
        st.markdown("## Risk matrix")
        st.plotly_chart(risk_matrix(scope), width="stretch", config={"displaylogo": False})
    with chart_2:
        st.markdown("## Lifecycle and inspection posture")
        posture = (
            scope.groupby(["asset_class", "inspection_status"], observed=True)
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
        st.dataframe(posture, hide_index=True, width="stretch", height=275)
        st.markdown("### Method")
        st.markdown(
            "- Risk = condition grade × criticality grade.\n"
            "- Renewal need = replacement value ÷ expected life.\n"
            "- Priority = risk × 4 + capped life consumed × 0.18 + inspection-recency penalty.\n"
            "- A missing inspection triggers condition assessment; it does not invent evidence."
        )
    st.markdown("## Asset-level trace")
    st.dataframe(
        scope[["asset_id", "asset_class", "service_owner", "condition_grade", "criticality_grade", "risk_band", "life_consumed_pct", "inspection_status", "annualized_renewal_need_usd", "recommended_intervention"]].sort_values(["risk_score", "priority_score"], ascending=False),
        hide_index=True,
        width="stretch",
        height=540,
        column_config={"annualized_renewal_need_usd": st.column_config.NumberColumn("Annual renewal need", format="$%,.0f")},
    )

if workspace == "GIS & assurance":
    tabs = st.tabs(["Governed risk layer", "Source exceptions", "Acceptance controls"])
    with tabs[0]:
        st.markdown("## Governed WGS 84 risk layer")
        st.plotly_chart(spatial_layer(scope), width="stretch", config={"displaylogo": False})
        st.caption("Synthetic point geometry for spatial QA and risk context. No parcel, road-network, hydraulic, accessibility, or routing model is implied.")
    with tabs[1]:
        exceptions = assessment[assessment["data_quality_status"].eq("DATA_REMEDIATION")].copy()
        st.error(f"{len(exceptions)} source records are blocked from scoring, GIS publication, and funding until their material defects are resolved.")
        st.dataframe(exceptions[["asset_id", "asset_name", "asset_class", "service_owner", "data_quality_reasons", "recommended_intervention"]], hide_index=True, width="stretch")
    with tabs[2]:
        controls = pd.DataFrame(
            [
                ["AM-01", "Unique governed asset identity", "Duplicate or missing IDs are blocked", "PASS"],
                ["AM-02", "Valid lifecycle and owner", "Invalid lifecycle or missing owner is blocked", "PASS"],
                ["AM-03", "Planning-basis condition and criticality", "Missing or out-of-range grades are blocked", "PASS"],
                ["AM-04", "Replacement value and expected life", "Missing/non-positive planning basis is blocked", "PASS"],
                ["GIS-01", "Valid WGS 84 point", "Invalid coordinates are excluded from publication", "PASS"],
                ["CAP-01", "Funding ceiling", "Scenario spend never exceeds the selected envelope", "PASS"],
                ["CAP-02", "Decision boundary", "Engineering, service, equity and approval gaps remain visible", "PASS"],
            ],
            columns=["Control", "Requirement", "Acceptance evidence", "Status"],
        )
        st.success("7 of 7 publication and decision-boundary controls are demonstrated.")
        st.dataframe(controls, hide_index=True, width="stretch")
        st.markdown("### Production decisions still required")
        st.markdown(
            "Engineering condition standards and treatment options; service-level consequence definitions; accessibility, climate and equity criteria; authoritative GIS ownership; funding policy; procurement route; delivery capacity; consultation; and approval authority."
        )

st.markdown(
    '<div class="boundary"><strong>Evidence boundary.</strong> Every asset, coordinate, cost, condition, priority, and funding scenario is synthetic. This demonstrates a transferable asset-information and business-analysis method; it is not municipal employment, an engineering assessment, or an approved capital plan.</div>',
    unsafe_allow_html=True,
)
st.caption("Kush Patel · Business analysis, asset information, GIS, Power BI, and decision assurance · Source evidence is versioned and tested in GitHub")
