"""
app_pages/supply_demand_overview.py -- Sector-wide analysis of Michigan public universities'
graduate supply vs projected statewide occupational demand.

Strictly follows ARCHITECTURE.md:
  - Zero data/raw/ reads; loads only precomputed data/app/*.parquet marts
  - Altair visualizations exclusively with accessible data tables below every chart
  - WSU brand palette (WSU Green #0C5449, WSU Gold #F2A900, Peer Grey #737373)
  - Standardized sidebar layout (consecutive filters at top, Definitions & Sources at bottom)
  - Dynamic context caption directly below title
  - No use_container_width=True (uses width="stretch")
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from etl.common import WSU_GREEN, WSU_GOLD, PEER_GREY, PEER_GREY_LIGHT, SUB_BACCALAUREATE_FAMILIES

# --- Data Loading with Streamlit Caching ---
@st.cache_data
def load_supply_demand_data():
    summary_df = pd.read_parquet("data/app/supply_demand_summary.parquet")
    itemized_df = pd.read_parquet("data/app/supply_demand_itemized.parquet")
    return summary_df, itemized_df


summary_raw, itemized_raw = load_supply_demand_data()

# --- 1. Sidebar Layout & Filters (Consecutive at Top) ---
st.sidebar.header("Filter Settings")

# A. Award-Level Filter
AWARD_LEVEL_OPTIONS = {
    "Bachelor's and Above": "comp_annual_bach_plus",
    "Bachelor's Degrees Only": "comp_annual_bach_only",
    "All Award Levels (Certificates to Doctorates)": "comp_annual_all",
    "Graduate Degrees & Certificates Only": "comp_annual_grad_only",
    "Latest Year (2024 Total All Levels)": "comp_2024_total"
}
selected_award_label = st.sidebar.selectbox(
    "Award Level Scope",
    options=list(AWARD_LEVEL_OPTIONS.keys()),
    index=0,
    help="Select which level of academic credentials to count as graduate supply. Doctoral/master's and certificates are not interchangeable units of labor."
)
comp_col = AWARD_LEVEL_OPTIONS[selected_award_label]

# B. Demand Allocation Method Selector
METHOD_OPTIONS = {
    "Method A: Equal Split (Default / Recommended)": "openings_method_a",
    "Method B: Completions-Weighted (Alternative)": "openings_method_b"
}
selected_method_label = st.sidebar.radio(
    "Demand Allocation Method",
    options=list(METHOD_OPTIONS.keys()),
    index=0,
    help="Method A divides each SOC's openings equally across linked CIPs. Method B weights by completions (partly circular, which compresses mismatch toward 1.0)."
)
openings_col = METHOD_OPTIONS[selected_method_label]

# Allocation method explanation / caveat note
if "Method B" in selected_method_label:
    st.sidebar.info(
        "⚠️ **Methodology Note (Method B):** Allocating demand by completions introduces circularity "
        "— programs producing the most graduates receive the largest demand allocation, pulling ratios toward 1.0 "
        "and dampening genuine mismatch. 393 of 868 SOCs with 0 MI completions fall back to equal split."
    )

# C. Sub-Baccalaureate Filter Toggle
exclude_sub_bac = st.sidebar.toggle(
    "Exclude Sub-Baccalaureate Fields",
    value=True,
    help="Excludes CIP families 12 (Culinary/Personal), 46 (Construction), 47 (Mechanics), 48 (Precision Production), and 49 (Transportation), which are predominantly trained via community colleges and apprenticeships."
)

# D. In-State Retention Rate Sensitivity Slider
retention_rate = st.sidebar.slider(
    "Michigan Graduate Retention Rate (%)",
    min_value=10,
    max_value=100,
    value=100,
    step=5,
    help="Adjustable sensitivity for the share of graduates retained in Michigan's labor market. Defaults to 100% (unvalidated baseline assumption)."
)
retention_factor = retention_rate / 100.0

# Sidebar Divider & Definitions Note (at the bottom)
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    ### Definitions & Sources
    * **Statewide Demand:** Projected annual job openings from the [Michigan Bureau of Labor Market Information (MILMI)](https://www.milmi.org/) 2022–2032 Occupational Projections.
    * **Graduate Supply:** Conferred degrees from Michigan's 15 public universities reported to [NCES IPEDS](https://nces.ed.gov/ipeds/) Completions survey (First-Major, 2019–2024 annual average).
    * **Crosswalk Mapping:** NCES CIP2020-to-SOC2018 crosswalk (6,097 links across 2,143 CIPs and 868 SOCs).
    * **Supply:Demand Ratio:** Annual university completions produced per annual allocated projected opening ($\text{Graduates} / \text{Allocated Openings}$).
    * **Retention Disclaimer:** Project data does not track individual graduate out-migration. Retention rate is an interactive user assumption (WSU Pathfinder data indicates ~80%+ in-state employment for WSU specifically).
    """
)

# --- 2. Main Page Header & Dynamic Context Caption ---
st.title("Statewide Supply–Demand Match")

sub_bac_text = "Excluded (12, 46, 47, 48, 49)" if exclude_sub_bac else "Included"
st.caption(
    f"#### Scope: 15 Michigan Public Universities | Demand Horizon: 2022–2032 MILMI | "
    f"Award Levels: {selected_award_label} | Method: {selected_method_label.split(':')[0]} | "
    f"Sub-Baccalaureate: {sub_bac_text} | Retention: {retention_rate}%"
)

# --- 3. Methodological Caveats Callout ---
with st.container(border=True):
    st.markdown(
        """
        ℹ️ **Analytical Context & Screening Guardrails:**
        * **Screening Indicator, Not a Policy Verdict:** The Supply:Demand ratio measures scale alignment between university degree production and projected labor market openings. It contains no institutional cost, facility, faculty capacity, or licensure/accreditation constraint data.
        * **Supply Scope:** Community colleges, private colleges, and out-of-state talent imports are **not** present in this 15-institution supply dataset.
        * **Timeline Offset:** Labor projections cover 2022–2032 annual averages; university completions reflect 2019–2024 IPEDS reporting.
        """
    )

# --- 4. Headline Framing Number (CIP 99.9999 - No Academic Pathway) ---
TOTAL_MI_OPENINGS = 451870.0
c99_row = summary_raw[summary_raw["is_no_academic_pathway"]].iloc[0]
NO_PATHWAY_OPENINGS = float(c99_row[openings_col])
NO_PATHWAY_PCT = (NO_PATHWAY_OPENINGS / TOTAL_MI_OPENINGS) * 100.0
ACADEMIC_OPENINGS_TOTAL = TOTAL_MI_OPENINGS - NO_PATHWAY_OPENINGS

st.markdown("### 🏛️ Labor Market Framing: Academic vs. Non-Academic Pathways")

frame_col1, frame_col2, frame_col3 = st.columns([1.2, 1.2, 1.6])
with frame_col1:
    st.metric(
        label="Total Michigan Annual Openings",
        value=f"{TOTAL_MI_OPENINGS:,.0f}",
        help="Total annual job openings across all 868 SOC occupations in Michigan (2022–2032 MILMI projections)."
    )
with frame_col2:
    st.metric(
        label="No Academic Pathway (CIP 99.9999)",
        value=f"{NO_PATHWAY_OPENINGS:,.0f}",
        delta=f"{NO_PATHWAY_PCT:.1f}% of Michigan Demand",
        delta_color="off",
        help="Occupations mapped to no collegiate academic program (e.g. food prep, orderlies, cashiers, short-term substitute teachers)."
    )
with frame_col3:
    st.metric(
        label="Analyzed Collegiate Demand",
        value=f"{ACADEMIC_OPENINGS_TOTAL:,.0f}",
        delta=f"{100.0 - NO_PATHWAY_PCT:.1f}% of Total Demand",
        delta_color="normal",
        help="Occupations with formal postsecondary CIP linkages in the NCES crosswalk addressed by higher education."
    )

# --- 5. Data Filtering for Macro Distribution ---
# Exclude CIP 99.9999 from CIP-level analysis
active_df = summary_raw[~summary_raw["is_no_academic_pathway"]].copy()

# Apply Sub-Baccalaureate filter
if exclude_sub_bac:
    active_df = active_df[~active_df["is_sub_baccalaureate"]].copy()

# Apply retention factor to completions
active_df["comp_adjusted"] = active_df[comp_col] * retention_factor
active_df["active_openings"] = active_df[openings_col]
active_df["ratio"] = active_df["comp_adjusted"] / active_df["active_openings"].replace(0, np.nan)

# KPI Metrics across active scope
total_active_openings = active_df["active_openings"].sum()
total_active_graduates = active_df["comp_adjusted"].sum()
overall_active_ratio = total_active_graduates / total_active_openings if total_active_openings > 0 else 0.0

st.markdown("---")
st.markdown("### 📊 Active Scope Summary Metrics")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.metric(
        "Allocated Openings in Scope",
        f"{total_active_openings:,.0f}",
        help="Sum of allocated annual openings for all CIP families in the active selection."
    )
with kpi2:
    st.metric(
        "Annual Grads Produced",
        f"{total_active_graduates:,.0f}",
        help=f"Annual university degrees conferred (adjusted for {retention_rate}% retention)."
    )
with kpi3:
    st.metric(
        "Overall Supply : Demand Ratio",
        f"{overall_active_ratio:.2f}",
        help="Ratio of annual graduates produced per annual opening in the active selection (1.0 = balanced)."
    )
with kpi4:
    n_undersupplied = (active_df["ratio"] < 0.5).sum()
    st.metric(
        "High-Demand Deficit CIPs (<0.5 Ratio)",
        f"{n_undersupplied:,}",
        help="Number of 6-digit CIP programs producing fewer than 0.5 graduates per projected opening."
    )

# --- 6. Rollup by CIP Family (2-digit) ---
family_agg = active_df.groupby(["cip_family", "cip_family_title", "cip_family_label", "is_sub_baccalaureate"]).agg(
    n_cips=("cip", "count"),
    openings=("active_openings", "sum"),
    graduates=("comp_adjusted", "sum"),
).reset_index()

family_agg["ratio"] = family_agg["graduates"] / family_agg["openings"].replace(0, np.nan)
family_agg["ratio_display"] = family_agg["ratio"].round(2)
family_agg["openings_formatted"] = family_agg["openings"].map(lambda x: f"{x:,.1f}")
family_agg["graduates_formatted"] = family_agg["graduates"].map(lambda x: f"{x:,.1f}")

# Categorize for accessibility & distinct styling
def categorize_ratio(r):
    if pd.isna(r):
        return "No Data / Zero Demand"
    elif r < 0.5:
        return "Severe Undersupply (<0.50)"
    elif r < 0.9:
        return "Moderate Undersupply (0.50–0.89)"
    elif r <= 1.25:
        return "Balanced Supply (0.90–1.25)"
    else:
        return "High Supply / Surplus (>1.25)"

family_agg["supply_category"] = family_agg["ratio"].map(categorize_ratio)
family_agg = family_agg.sort_values("ratio", ascending=True)

# --- 7. CIP Family Macro Distribution Visualization (Altair) ---
st.markdown("---")
st.markdown("### 📈 Supply–Demand Ratio Distribution by CIP Family")
st.markdown(
    "How many graduates Michigan's 15 public universities produce per projected annual opening across academic fields. "
    "A ratio of **1.0 (dashed line)** indicates equal production to projected annual demand."
)

# Color scale with high contrast and WSU brand colors
# WSU Green for balanced, WSU Gold for high supply, Charcoal/Peer Grey for undersupply
color_scale = alt.Scale(
    domain=[
        "Severe Undersupply (<0.50)",
        "Moderate Undersupply (0.50–0.89)",
        "Balanced Supply (0.90–1.25)",
        "High Supply / Surplus (>1.25)",
        "No Data / Zero Demand"
    ],
    range=[
        "#737373",   # Peer Grey for undersupply
        "#4A8075",   # Medium WSU slate
        WSU_GREEN,   # WSU Green (#0C5449) for balanced
        WSU_GOLD,    # WSU Gold (#F2A900) for high surplus
        "#CCCCCC"    # Light Grey
    ]
)

# Base Bar Chart
bar_chart = alt.Chart(family_agg).mark_bar(height=18).encode(
    y=alt.Y(
        "cip_family_label:N",
        sort=alt.EncodingSortField(field="ratio", order="ascending"),
        title="CIP Family"
    ),
    x=alt.X(
        "ratio:Q",
        title="Supply : Demand Ratio (Graduates Conferred per Annual Opening)",
        scale=alt.Scale(domain=[0, min(float(family_agg["ratio"].max() * 1.08) if len(family_agg) > 0 and family_agg["ratio"].max() > 0 else 5.0, 10.0)])
    ),
    color=alt.Color(
        "supply_category:N",
        scale=color_scale,
        title="Supply Alignment Category"
    ),
    tooltip=[
        alt.Tooltip("cip_family_label:N", title="CIP Family"),
        alt.Tooltip("openings:Q", format=",.1f", title="Annual Allocated Openings"),
        alt.Tooltip("graduates:Q", format=",.1f", title="Annual Graduates"),
        alt.Tooltip("ratio:Q", format=".2f", title="Supply:Demand Ratio"),
        alt.Tooltip("supply_category:N", title="Alignment Category")
    ]
)

# Text labels on bars
text_labels = bar_chart.mark_text(
    align="left",
    baseline="middle",
    dx=4,
    fontSize=11,
    color="#222222"
).encode(
    text=alt.Text("ratio:Q", format=".2f")
)

# Reference line at Ratio = 1.0 (Balanced Supply)
rule_line = alt.Chart(pd.DataFrame({"x": [1.0]})).mark_rule(
    color="#111111",
    strokeDash=[5, 5],
    strokeWidth=2
).encode(
    x="x:Q"
)

rule_text = alt.Chart(pd.DataFrame({"x": [1.0], "text": ["Balanced Demand (1.0)"]})).mark_text(
    align="right",
    baseline="bottom",
    dx=-6,
    dy=-8,
    fontSize=11,
    fontWeight="bold",
    color="#111111"
).encode(
    x="x:Q",
    text="text:N"
)

chart_combined = (bar_chart + text_labels + rule_line + rule_text).properties(
    height=max(400, len(family_agg) * 26)
)

st.altair_chart(chart_combined, width="stretch")

# Accessible Data Table below Chart
with st.expander("👁️ View Accessible Data Table (CIP Family Supply–Demand Ratios)", expanded=False):
    table_display = family_agg[[
        "cip_family", "cip_family_title", "openings_formatted", "graduates_formatted", "ratio_display", "supply_category"
    ]].rename(columns={
        "cip_family": "CIP Family Code",
        "cip_family_title": "CIP Family Title",
        "openings_formatted": "Annual Openings (Allocated)",
        "graduates_formatted": "Annual Graduates",
        "ratio_display": "Supply:Demand Ratio",
        "supply_category": "Alignment Category"
    })
    st.dataframe(table_display, width="stretch", hide_index=True)
    st.download_button(
        label="Download CIP Family Table as CSV",
        data=table_display.to_csv(index=False).encode("utf-8"),
        file_name="cip_family_supply_demand_summary.csv",
        mime="text/csv"
    )

# --- 8. Absolute Magnitude Comparison (Openings vs Completions) ---
st.markdown("---")
st.markdown("### ⚖️ Absolute Scale: Annual Demand vs. Graduate Production")
st.markdown("Comparing the absolute volume of projected annual openings against annual university completions by field.")

# Reshape for grouped bar comparison
mag_df = family_agg.melt(
    id_vars=["cip_family_label", "cip_family", "ratio"],
    value_vars=["openings", "graduates"],
    var_name="Metric",
    value_name="Count"
)
mag_df["Metric_Label"] = mag_df["Metric"].map({"openings": "Projected Annual Openings", "graduates": "Annual Graduates Produced"})

mag_chart = alt.Chart(mag_df).mark_bar().encode(
    y=alt.Y("cip_family_label:N", sort=alt.EncodingSortField(field="ratio", order="ascending"), title="CIP Family"),
    x=alt.X("Count:Q", title="Annual Volume (Persons / Year)"),
    color=alt.Color(
        "Metric_Label:N",
        scale=alt.Scale(
            domain=["Projected Annual Openings", "Annual Graduates Produced"],
            range=[PEER_GREY, WSU_GREEN]
        ),
        title="Metric"
    ),
    yOffset="Metric_Label:N",
    tooltip=[
        alt.Tooltip("cip_family_label:N", title="CIP Family"),
        alt.Tooltip("Metric_Label:N", title="Metric"),
        alt.Tooltip("Count:Q", format=",.1f", title="Volume / Year")
    ]
).properties(
    height=max(450, len(family_agg) * 32)
)

st.altair_chart(mag_chart, width="stretch")

with st.expander("👁️ View Accessible Data Table (Absolute Volume Comparison)", expanded=False):
    st.dataframe(table_display[["CIP Family Code", "CIP Family Title", "Annual Openings (Allocated)", "Annual Graduates"]], width="stretch", hide_index=True)

# --- 9. Tail Analysis: High-Volume Shortage vs High-Ratio Surplus Fields ---
st.markdown("---")
st.markdown("### 🔍 Tails Analysis: Critical Shortages vs. High-Supply Programs (6-Digit CIP)")

tail_c1, tail_c2 = st.columns(2)

with tail_c1:
    st.markdown("#### 🚨 High-Volume Deficit Programs")
    st.caption(r"CIPs with $\ge 200$ annual openings and lowest supply:demand ratios.")
    shortage_cips = active_df[active_df["active_openings"] >= 200].sort_values("ratio", ascending=True).head(10)
    shortage_display = shortage_cips[["cip", "cip_title", "active_openings", "comp_adjusted", "ratio", "wage_median"]].copy()
    shortage_display["ratio"] = shortage_display["ratio"].round(2)
    shortage_display["active_openings"] = shortage_display["active_openings"].round(1)
    shortage_display["comp_adjusted"] = shortage_display["comp_adjusted"].round(1)
    shortage_display["wage_median"] = shortage_display["wage_median"].map(lambda w: f"${w:,.0f}" if pd.notna(w) else "N/A")
    shortage_display.columns = ["CIP", "Title", "Openings/Yr", "Grads/Yr", "Ratio", "Median Wage"]
    st.dataframe(shortage_display, width="stretch", hide_index=True)

with tail_c2:
    st.markdown("#### 🎓 High-Supply / Production Surplus Programs")
    st.caption(r"CIPs with $\ge 100$ annual grads and highest supply:demand ratios.")
    surplus_cips = active_df[active_df["comp_adjusted"] >= 100].sort_values("ratio", ascending=False).head(10)
    surplus_display = surplus_cips[["cip", "cip_title", "active_openings", "comp_adjusted", "ratio", "wage_median"]].copy()
    surplus_display["ratio"] = surplus_display["ratio"].round(2)
    surplus_display["active_openings"] = surplus_display["active_openings"].round(1)
    surplus_display["comp_adjusted"] = surplus_display["comp_adjusted"].round(1)
    surplus_display["wage_median"] = surplus_display["wage_median"].map(lambda w: f"${w:,.0f}" if pd.notna(w) else "N/A")
    surplus_display.columns = ["CIP", "Title", "Openings/Yr", "Grads/Yr", "Ratio", "Median Wage"]
    st.dataframe(surplus_display, width="stretch", hide_index=True)

st.info("💡 To explore the detailed occupational links and university-by-university production breakdown for any specific CIP program, use the **Supply–Demand CIP Drill-Down** page in the navigation menu.")
