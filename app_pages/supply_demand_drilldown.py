"""
app_pages/supply_demand_drilldown.py -- Program-level & occupational drill-down
for Michigan supply vs demand matching at the 6-digit CIP level.

Strictly adheres to ARCHITECTURE.md:
  - Zero data/raw/ reads; loads only precomputed data/app/*.parquet marts
  - Altair visualizations with accessible data tables below every chart
  - WSU brand palette (WSU Green #0C5449, WSU Gold #F2A900, Peer Grey #737373)
  - Standardized sidebar layout (consecutive filters at top, Definitions & Sources at bottom)
  - Dynamic context caption directly below title
  - No use_container_width=True (uses width="stretch")
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from etl.common import (
    WSU_GREEN,
    WSU_GOLD,
    PEER_GREY,
    PEER_GREY_LIGHT,
    WSU_NAME,
    SUB_BACCALAUREATE_FAMILIES
)

# --- Data Loading with Streamlit Caching ---
@st.cache_data
def load_drilldown_data():
    summary_df = pd.read_parquet("data/app/supply_demand_summary.parquet")
    itemized_df = pd.read_parquet("data/app/supply_demand_itemized.parquet")
    completions_df = pd.read_parquet("data/app/completions_michigan.parquet")
    try:
        cip_dict_df = pd.read_parquet("data/app/cip_dictionary.parquet")
    except Exception:
        cip_dict_df = pd.DataFrame()
    return summary_df, itemized_df, completions_df, cip_dict_df


summary_raw, itemized_raw, completions_raw, cip_dict_raw = load_drilldown_data()

# Clean CIP formatting
completions_raw["cip_code"] = completions_raw["cip_code"].astype(str)

# --- 1. Sidebar Layout & Filters (Consecutive at Top) ---
st.sidebar.header("Filter Settings")

# A. CIP Family Selector
# Filter out CIP 99.9999 from the active program selection
valid_summary = summary_raw[~summary_raw["is_no_academic_pathway"]].copy()

family_list = sorted(valid_summary["cip_family_label"].dropna().unique().tolist())
# Set default to Engineering (14) or Health (51) if available
default_fam_idx = 0
for i, fam in enumerate(family_list):
    if fam.startswith("14 ") or fam.startswith("15 "):
        default_fam_idx = i
        break

selected_family_label = st.sidebar.selectbox(
    "1. Select CIP Family",
    options=family_list,
    index=default_fam_idx,
    help="Select a 2-digit CIP academic field."
)
selected_family_code = selected_family_label.split(" - ")[0]

# B. CIP Program Selector (6-digit within selected family)
cips_in_family = valid_summary[valid_summary["cip_family"] == selected_family_code].copy()
cips_in_family["label"] = cips_in_family["cip"] + " - " + cips_in_family["cip_title"]
cip_options = sorted(cips_in_family["label"].unique().tolist())

# Default to 15.1001 if available in Family 15, or first option
default_cip_idx = 0
for i, c_label in enumerate(cip_options):
    if c_label.startswith("15.1001"):
        default_cip_idx = i
        break

selected_cip_label = st.sidebar.selectbox(
    "2. Select CIP Program (6-Digit)",
    options=cip_options,
    index=default_cip_idx,
    help="Select an individual academic program to analyze."
)
selected_cip = selected_cip_label.split(" - ")[0]
selected_cip_title = " - ".join(selected_cip_label.split(" - ")[1:])

# C. Award-Level Scope Filter
AWARD_LEVEL_MAPPINGS = {
    "Bachelor's and Above": [5, 6, 7, 8, 17, 18, 19],
    "Bachelor's Degrees Only": [5],
    "All Award Levels (Certificates to Doctorates)": [1, 2, 3, 4, 5, 6, 7, 8, 17, 18, 19],
    "Graduate Degrees & Certificates Only": [6, 7, 8, 17, 18, 19]
}
selected_award_label = st.sidebar.selectbox(
    "3. Award Level Scope",
    options=list(AWARD_LEVEL_MAPPINGS.keys()),
    index=0,
    help="Filter completions to specific award levels."
)
selected_award_levels = AWARD_LEVEL_MAPPINGS[selected_award_label]

# D. Demand Allocation Method Selector
METHOD_OPTIONS = {
    "Method A: Equal Split (Default / Recommended)": "openings_method_a",
    "Method B: Completions-Weighted (Alternative)": "openings_method_b"
}
selected_method_label = st.sidebar.radio(
    "4. Demand Allocation Method",
    options=list(METHOD_OPTIONS.keys()),
    index=0,
    help="Method A divides each SOC's openings equally across linked CIPs. Method B weights by completions."
)
openings_col = METHOD_OPTIONS[selected_method_label]

# E. In-State Retention Rate Sensitivity Slider
retention_rate = st.sidebar.slider(
    "5. Michigan Graduate Retention Rate (%)",
    min_value=10,
    max_value=100,
    value=100,
    step=5,
    help="Adjustable sensitivity for the share of graduates entering the Michigan labor market. Defaults to 100% (unvalidated baseline assumption)."
)
retention_factor = retention_rate / 100.0

# Sidebar Divider & Definitions Note
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    ### Definitions & Sources
    * **Statewide Demand:** Projected annual job openings from the [Michigan Bureau of Labor Market Information (MILMI)](https://www.milmi.org/) 2022–2032 Occupational Projections.
    * **Graduate Supply:** Conferred degrees from Michigan's 15 public universities reported to [NCES IPEDS](https://nces.ed.gov/ipeds/) Completions survey (First-Major, 2019–2024 annual average).
    * **Crosswalk Mapping:** NCES CIP2020-to-SOC2018 crosswalk.
    * **Supply:Demand Ratio:** Annual university completions produced per annual allocated projected opening ($\text{Graduates} / \text{Allocated Openings}$).
    * **Retention Disclaimer:** Project data does not track individual graduate out-migration. Retention rate is an interactive user assumption (WSU Pathfinder data indicates ~80%+ in-state employment for WSU specifically).
    """
)

# --- 2. Main Page Header & Dynamic Context Caption ---
st.title("CIP & Occupational Demand Drill-Down")

st.caption(
    f"#### Program: CIP {selected_cip} — {selected_cip_title} | Demand Horizon: 2022–2032 MILMI | "
    f"Award Levels: {selected_award_label} | Method: {selected_method_label.split(':')[0]} | Retention: {retention_rate}%"
)

# Sub-baccalaureate notice if applicable
if selected_family_code in SUB_BACCALAUREATE_FAMILIES:
    st.warning(
        f"⚠️ **Sub-Baccalaureate Pipeline Notice:** CIP Family {selected_family_code} ({SUB_BACCALAUREATE_FAMILIES[selected_family_code]}) "
        "is predominantly trained through Michigan community colleges and apprenticeships. "
        "The 15-institution public university dataset does not represent this pipeline."
    )

# --- 3. Program Profile & Headline KPIs ---
cip_row = valid_summary[valid_summary["cip"] == selected_cip].iloc[0]
linked_socs = itemized_raw[itemized_raw["cip"] == selected_cip].copy()

# Calculate dynamic completions for this CIP based on award level filter
cip_comps = completions_raw[
    (completions_raw["cip_code"] == selected_cip) &
    (completions_raw["award_level"].isin(selected_award_levels))
]
n_years = completions_raw["year"].nunique()
annual_comps_unadjusted = cip_comps["total_degrees"].sum() / n_years if n_years > 0 else 0.0
annual_comps_adjusted = annual_comps_unadjusted * retention_factor

# Allocated demand under selected method
allocated_demand = linked_socs[openings_col].sum() if len(linked_socs) > 0 else 0.0
supply_demand_ratio = annual_comps_adjusted / allocated_demand if allocated_demand > 0 else np.nan

# Wages
min_wage = linked_socs["median_wage"].min()
max_wage = linked_socs["median_wage"].max()
median_wage = linked_socs["median_wage"].median()

st.markdown("### 📋 Program Summary & Labor Market Position")

kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
with kpi_c1:
    st.metric(
        label="Allocated Annual Openings",
        value=f"{allocated_demand:,.1f}",
        help=f"Projected annual openings allocated to CIP {selected_cip} under {selected_method_label.split(':')[0]}."
    )
with kpi_c2:
    st.metric(
        label="Annual Grads (15 MI Publics)",
        value=f"{annual_comps_adjusted:,.1f}",
        delta=f"{annual_comps_unadjusted:,.1f} unadjusted" if retention_rate < 100 else None,
        delta_color="off",
        help=f"Annual university degrees conferred (adjusted for {retention_rate}% retention)."
    )
with kpi_c3:
    ratio_val = f"{supply_demand_ratio:.2f}" if pd.notna(supply_demand_ratio) else "N/A"
    st.metric(
        label="Supply : Demand Ratio",
        value=ratio_val,
        help="Graduates produced per annual allocated opening (1.0 = balanced)."
    )
with kpi_c4:
    if pd.notna(median_wage):
        wage_str = f"${median_wage:,.0f}"
        wage_range_str = f"Range: ${min_wage:,.0f} – ${max_wage:,.0f}" if pd.notna(min_wage) and min_wage != max_wage else "Single SOC Match"
    else:
        wage_str = "N/A"
        wage_range_str = "Wage data suppressed"
    st.metric(
        label="Median Annual Wage (Occupations)",
        value=wage_str,
        delta=wage_range_str,
        delta_color="off",
        help="Median annualized wage across linked SOC occupations in Michigan."
    )

# CIP Definition / Description Lookup
if not cip_dict_raw.empty and "ciptitle" in cip_dict_raw.columns:
    dict_match = cip_dict_raw[cip_dict_raw["cipcode"] == selected_cip]
    if not dict_match.empty and pd.notna(dict_match["cipdefinition"].iloc[0]):
        cip_def_text = str(dict_match["cipdefinition"].iloc[0]).strip()
        with st.expander("📖 View Official NCES Program Definition", expanded=False):
            st.markdown(f"**CIP {selected_cip} Description:** {cip_def_text}")

# --- 4. Linked Occupations Breakdown ---
st.markdown("---")
st.markdown(f"### 🔗 Linked Occupations ({len(linked_socs)} SOCs Mapped)")
st.markdown(
    f"The NCES crosswalk links **CIP {selected_cip}** to **{len(linked_socs)} Standard Occupational Classification (SOC)** codes. "
    "Below is the breakdown of total statewide openings, allocated openings for this program, projected 10-year growth, and median wages."
)

if not linked_socs.empty:
    linked_socs["allocated_share"] = linked_socs[openings_col]
    linked_socs["pct_change_display"] = (linked_socs["pct_change"] * 100.0).round(1)
    linked_socs["soc_label"] = linked_socs["soc6"] + " - " + linked_socs["soc_title"]

    # Chart 1: Openings per Linked Occupation (Altair)
    soc_bar = alt.Chart(linked_socs).mark_bar(height=20).encode(
        y=alt.Y("soc_label:N", sort=alt.EncodingSortField(field="annual_openings", order="descending"), title="Occupation (SOC)"),
        x=alt.X("annual_openings:Q", title="Total Michigan Annual Openings (All Linked CIPs)"),
        color=alt.value(PEER_GREY),
        tooltip=[
            alt.Tooltip("soc_label:N", title="Occupation"),
            alt.Tooltip("annual_openings:Q", format=",.0f", title="Total MI Annual Openings"),
            alt.Tooltip("n_cips_linked:Q", title="Total Linked CIPs"),
            alt.Tooltip("allocated_share:Q", format=",.1f", title=f"Allocated to CIP {selected_cip}"),
            alt.Tooltip("pct_change_display:Q", format=".1f", title="10-Yr Growth Rate (%)"),
            alt.Tooltip("median_wage:Q", format="$,.0f", title="Median Annual Wage")
        ]
    )

    # Allocated overlay bar
    alloc_bar = alt.Chart(linked_socs).mark_bar(height=20).encode(
        y=alt.Y("soc_label:N", sort=alt.EncodingSortField(field="annual_openings", order="descending")),
        x=alt.X("allocated_share:Q", title="Allocated Openings to CIP"),
        color=alt.value(WSU_GREEN)
    )

    soc_chart_combined = (soc_bar + alloc_bar).properties(
        title="Total Michigan Openings (Grey) vs. Allocated Share to this CIP (Green)",
        height=max(220, len(linked_socs) * 36)
    )

    st.altair_chart(soc_chart_combined, width="stretch")

    # Accessible Data Table
    with st.expander("👁️ View Accessible Data Table (Linked Occupations Detail)", expanded=True):
        soc_display = linked_socs[[
            "soc6", "soc_title", "annual_openings", "n_cips_linked", "allocated_share", "pct_change_display", "median_wage", "entry_wage", "exp_wage"
        ]].copy()
        soc_display["pct_change_display"] = soc_display["pct_change_display"].map(lambda p: f"{p:+.1f}%" if pd.notna(p) else "N/A")
        soc_display["annual_openings"] = soc_display["annual_openings"].map(lambda o: f"{o:,.0f}" if pd.notna(o) else "N/A")
        soc_display["allocated_share"] = soc_display["allocated_share"].map(lambda a: f"{a:,.1f}" if pd.notna(a) else "N/A")
        soc_display["median_wage"] = soc_display["median_wage"].map(lambda w: f"${w:,.0f}" if pd.notna(w) else "Suppressed")
        soc_display["entry_wage"] = soc_display["entry_wage"].map(lambda w: f"${w:,.0f}" if pd.notna(w) else "Suppressed")
        soc_display["exp_wage"] = soc_display["exp_wage"].map(lambda w: f"${w:,.0f}" if pd.notna(w) else "Suppressed")

        soc_display.columns = [
            "SOC Code", "Occupation Title", "Total MI Openings", "Linked CIPs Count",
            f"Allocated Openings ({selected_method_label.split(':')[0]})", "10-Yr Growth (%)", "Median Wage", "Entry Wage", "Experienced Wage"
        ]
        st.dataframe(soc_display, width="stretch", hide_index=True)
else:
    st.info("No mapped occupations found for this CIP code.")

# --- 5. Institutional Production Breakdown (Who Produces These Graduates?) ---
st.markdown("---")
st.markdown("### 🏛️ University Production Breakdown (15 Michigan Publics)")
st.markdown(
    f"Annual degree completions across Michigan's 15 public universities for **CIP {selected_cip}** "
    f"(Award Level: *{selected_award_label}*, 2019–2024 annual average)."
)

inst_agg = cip_comps.groupby("institution")["total_degrees"].sum().reset_index()
inst_agg["annual_avg"] = inst_agg["total_degrees"] / n_years
inst_agg["annual_avg_adjusted"] = inst_agg["annual_avg"] * retention_factor
inst_agg = inst_agg[inst_agg["annual_avg"] > 0].sort_values("annual_avg", ascending=False)

if not inst_agg.empty:
    total_inst_grads = inst_agg["annual_avg_adjusted"].sum()
    inst_agg["market_share"] = (inst_agg["annual_avg_adjusted"] / total_inst_grads) * 100.0 if total_inst_grads > 0 else 0.0
    inst_agg["is_wsu"] = inst_agg["institution"] == WSU_NAME

    # Altair chart highlighting WSU vs Peers
    inst_chart = alt.Chart(inst_agg).mark_bar(height=22).encode(
        y=alt.Y(
            "institution:N",
            sort=alt.EncodingSortField(field="annual_avg_adjusted", order="descending"),
            title="University"
        ),
        x=alt.X("annual_avg_adjusted:Q", title=f"Annual Graduates (Adjusted for {retention_rate}% Retention)"),
        color=alt.condition(
            alt.datum.institution == WSU_NAME,
            alt.value(WSU_GREEN),
            alt.value(PEER_GREY)
        ),
        tooltip=[
            alt.Tooltip("institution:N", title="University"),
            alt.Tooltip("annual_avg:Q", format=",.1f", title="Unadjusted Annual Grads"),
            alt.Tooltip("annual_avg_adjusted:Q", format=",.1f", title="Retention-Adjusted Grads"),
            alt.Tooltip("market_share:Q", format=".1f", title="Statewide Market Share (%)")
        ]
    )

    inst_text = inst_chart.mark_text(
        align="left",
        baseline="middle",
        dx=4,
        fontSize=11,
        color="#222222"
    ).encode(
        text=alt.Text("annual_avg_adjusted:Q", format=",.1f")
    )

    inst_combined = (inst_chart + inst_text).properties(
        height=max(220, len(inst_agg) * 34)
    )

    st.altair_chart(inst_combined, width="stretch")

    # Accessible Data Table
    with st.expander("👁️ View Accessible Data Table (Institution Completions Detail)", expanded=False):
        inst_display = inst_agg[["institution", "annual_avg", "annual_avg_adjusted", "market_share"]].copy()
        inst_display["annual_avg"] = inst_display["annual_avg"].round(1)
        inst_display["annual_avg_adjusted"] = inst_display["annual_avg_adjusted"].round(1)
        inst_display["market_share"] = inst_display["market_share"].map(lambda m: f"{m:.1f}%")
        inst_display.columns = ["University", "Annual Completions (Unadjusted)", f"Annual Completions ({retention_rate}% Retention)", "Statewide Market Share (%)"]
        st.dataframe(inst_display, width="stretch", hide_index=True)
else:
    st.info(f"No completions reported for CIP {selected_cip} under the selected award level ({selected_award_label}) across the 15 Michigan public universities.")

# --- 6. Methodological Comparison (Method A vs Method B for this CIP) ---
st.markdown("---")
st.markdown("### ⚖️ Allocation Method Comparison: Equal Split vs. Completions-Weighted")

comp_meth_a = linked_socs["openings_method_a"].sum() if len(linked_socs) > 0 else 0.0
comp_meth_b = linked_socs["openings_method_b"].sum() if len(linked_socs) > 0 else 0.0
ratio_meth_a = annual_comps_adjusted / comp_meth_a if comp_meth_a > 0 else np.nan
ratio_meth_b = annual_comps_adjusted / comp_meth_b if comp_meth_b > 0 else np.nan

diff_openings = comp_meth_b - comp_meth_a

comp_col1, comp_col2, comp_col3 = st.columns([1.2, 1.2, 1.6])
with comp_col1:
    st.metric(
        "Method A: Equal Split Demand",
        f"{comp_meth_a:,.1f}",
        delta=f"Ratio: {ratio_meth_a:.2f}" if pd.notna(ratio_meth_a) else "Ratio: N/A",
        delta_color="off",
        help="Allocates openings by dividing each SOC equally across its linked CIPs (No circularity)."
    )
with comp_col2:
    st.metric(
        "Method B: Completions-Weighted Demand",
        f"{comp_meth_b:,.1f}",
        delta=f"Ratio: {ratio_meth_b:.2f}" if pd.notna(ratio_meth_b) else "Ratio: N/A",
        delta_color="off",
        help="Allocates openings in proportion to statewide completions in linked CIPs (Pulls ratios toward 1.0)."
    )
with comp_col3:
    direction = "Higher under Method B" if diff_openings > 0 else ("Lower under Method B" if diff_openings < 0 else "Identical")
    st.metric(
        "Allocation Divergence",
        f"{abs(diff_openings):,.1f} openings",
        delta=direction,
        delta_color="normal" if abs(diff_openings) < 10 else "off",
        help="Difference in allocated annual demand between the two methods."
    )

with st.expander("ℹ️ Why does demand diverge between Method A and Method B?", expanded=False):
    st.markdown(
        f"""
        * **Equal Split (Method A, {comp_meth_a:,.1f} openings):** Treats all CIP programs linked to an occupation as equally valid supply pipelines. It avoids assuming existing enrollment patterns reflect optimal market shares.
        * **Completions-Weighted (Method B, {comp_meth_b:,.1f} openings):** Shifts demand toward larger academic programs that already produce high volumes of graduates. While realistic for dominant pathways, it is partially circular because existing university supply shapes the demand allocation.
        * **Divergence:** For CIP {selected_cip}, Method B allocates **{abs(diff_openings):,.1f} {'more' if diff_openings > 0 else 'fewer'} openings** than Method A.
        """
    )
