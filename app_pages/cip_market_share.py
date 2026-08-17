import streamlit as st
import pandas as pd
import altair as alt
import os
import numpy as np
import duckdb

from etl.common import COLLEGE_NAMES, PEER_GREY, WSU_GREEN, WSU_NAME, split_college_codes

# Cache the data load
@st.cache_data(ttl=3600)
def load_completions_data():
    try:
        file_path = 'data/app/completions_benchmark.parquet'
        if not os.path.exists(file_path):
            return pd.DataFrame()
        # wsu_college is load-bearing: the "WSU School/College" sidebar filter builds its
        # options from this column, and silently offers only "All Colleges" without it.
        query = """
            SELECT year, institution, cip_code, award_level, total_degrees,
                   is_mi_public, is_urban_peer, is_public_r1, wsu_college
            FROM 'data/app/completions_benchmark.parquet'
        """
        return duckdb.query(query).df()
    except Exception as e:
        st.error(f"Failed to load completions data from local files: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_cip_dictionary():
    try:
        file_path = 'data/app/cip_dictionary.parquet'
        if not os.path.exists(file_path):
            return pd.DataFrame()
        query = """
            SELECT 
                REPLACE(REPLACE(CAST(cipfamily AS VARCHAR), '="', ''), '"', '') AS cip_family,
                REPLACE(REPLACE(CAST(cipcode AS VARCHAR), '="', ''), '"', '') AS cip_code,
                ciptitle
            FROM 'data/app/cip_dictionary.parquet'
        """
        return duckdb.query(query).df()
    except Exception as e:
        st.error(f"Failed to load CIP dictionary from local files: {e}")
        return pd.DataFrame()


# --- SPRINT 2: Michigan occupational demand loaders ---
@st.cache_data(ttl=3600)
def load_demand_summary():
    try:
        file_path = 'data/app/cip_demand_summary.parquet'
        if not os.path.exists(file_path):
            return pd.DataFrame()
        return duckdb.query(f"SELECT * FROM '{file_path}'").df()
    except Exception as e:
        st.error(f"Failed to load demand summary from local files: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_demand_itemized():
    try:
        file_path = 'data/app/cip_demand_itemized.parquet'
        if not os.path.exists(file_path):
            return pd.DataFrame()
        return duckdb.query(f"SELECT * FROM '{file_path}'").df()
    except Exception as e:
        st.error(f"Failed to load itemized demand from local files: {e}")
        return pd.DataFrame()



with st.spinner("Loading local data..."):
    df_all = load_completions_data()
    cip_dict = load_cip_dictionary()
    demand_summary = load_demand_summary()
    demand_itemized = load_demand_itemized()

# The loaders above return an empty frame on failure, so stop here with an explanation
# rather than letting the column access below raise a bare KeyError at the user.
if df_all.empty:
    st.error(
        "Completions data could not be loaded from `data/app/completions_benchmark.parquet`. "
        "Run `python etl/compile_app_data.py` from the project root to rebuild it."
    )
    st.stop()

if cip_dict.empty:
    st.error(
        "CIP dictionary could not be loaded from `data/app/cip_dictionary.parquet`. "
        "Run `python etl/compile_app_data.py` from the project root to rebuild it."
    )
    st.stop()

# Data cleaning
df_all['cip_code'] = df_all['cip_code'].astype(str)
df_all['total_degrees'] = pd.to_numeric(df_all['total_degrees'], errors='coerce').fillna(0)

# Sidebar filters
st.sidebar.header("Filters")

selected_cohort = st.sidebar.selectbox(
    "Select Cohort Group",
    options=["Michigan Publics (MASU)", "Urban Peer Publics", "Public R1 Universities"]
)

if selected_cohort == "Michigan Publics (MASU)":
    df = df_all[df_all['is_mi_public'] == 1].copy()
elif selected_cohort == "Urban Peer Publics":
    df = df_all[df_all['is_urban_peer'] == 1].copy()
else:
    df = df_all[df_all['is_public_r1'] == 1].copy()

st.title("CIP Market Share & CAGR Analysis")
st.caption(f"#### Scope: {selected_cohort} | Years: 2019 to 2024 | Metrics: Degrees Conferred, Market Share, CAGR")

all_schools = sorted(df['institution'].unique().tolist())
selected_schools = st.sidebar.multiselect(
    "Select Universities",
    options=all_schools,
    default=all_schools
)

AWARD_LEVELS = {
    3: "Associate's degree",
    5: "Bachelor's degree",
    7: "Master's degree",
    9: "Doctor's degree"
}
award_level_filter = st.sidebar.multiselect(
    "Award Level(s)",
    options=list(AWARD_LEVELS.keys()),
    format_func=lambda x: AWARD_LEVELS.get(x, f"Level {x}"),
    default=[5]
)

if award_level_filter:
    df_filtered = df[df['award_level'].isin(award_level_filter)]
else:
    df_filtered = df

if selected_schools:
    df_filtered = df_filtered[df_filtered['institution'].isin(selected_schools)]

# WSU School/College selector
colleges_in_data = set()
if 'wsu_college' in df_all.columns:
    for cell in df_all['wsu_college'].dropna().unique():
        colleges_in_data.update(split_college_codes(cell))

sorted_colleges = sorted(list(colleges_in_data))
college_options = ['All Colleges'] + sorted_colleges

selected_college_code = st.sidebar.selectbox(
    "WSU School/College",
    options=college_options,
    format_func=lambda x: COLLEGE_NAMES.get(x, x) if x != 'All Colleges' else 'All Colleges (No Filter)'
)

if selected_college_code != 'All Colleges':
    # Find all CIP codes that map to this WSU college
    wsu_rows = df_all[(df_all['institution'] == WSU_NAME) & (df_all['wsu_college'].notna())]
    target_cips_for_college = wsu_rows[wsu_rows['wsu_college'].apply(
        lambda val: selected_college_code in split_college_codes(val)
    )]['cip_code'].unique()
    
    # Filter df_filtered to only include these CIP codes
    df_filtered = df_filtered[df_filtered['cip_code'].isin(target_cips_for_college)]

st.sidebar.subheader("CIP Code Selection")
st.sidebar.markdown("Select 2-digit CIP Families, then optionally filter to specific 6-digit codes. If no 6-digit codes are selected, the entire family will be aggregated.")

# Build CIP lookup dictionaries
families = cip_dict[cip_dict['cip_code'].str.len() == 2].copy()
families['label'] = families['cip_code'] + " - " + families['ciptitle']
family_map = dict(zip(families['cip_family'], families['label']))

cip_labels = cip_dict[cip_dict['cip_code'].str.len() == 7].copy()
cip_labels['label'] = cip_labels['cip_code'] + " - " + cip_labels['ciptitle']
cip_map = dict(zip(cip_labels['cip_code'], cip_labels['label']))

# Available families in the data
available_families = sorted(df_filtered['cip_code'].str[:2].unique())

selected_family_codes = st.sidebar.multiselect(
    "1. Select CIP Family (2-digit)",
    options=available_families,
    format_func=lambda x: family_map.get(x, x)
)

# Available specific CIPs based on family selection
if selected_family_codes:
    valid_cips = df_filtered[df_filtered['cip_code'].str[:2].isin(selected_family_codes)]['cip_code'].unique()
else:
    valid_cips = df_filtered['cip_code'].unique()

selected_cips = st.sidebar.multiselect(
    "2. Select Specific CIP Code(s) (6-digit)",
    options=sorted(valid_cips),
    format_func=lambda x: cip_map.get(x, x)
)

st.sidebar.markdown("""
---
**Definitions & Sources:**
- **Data Source:** NCES [IPEDS Completions Survey](https://nces.ed.gov/ipeds/) (Table `C_A` - Awards Conferred).
- **Metric Scope:** Displays the count of **degrees/awards conferred** (First Major only), not unique student headcounts.
- **CAGR:** 5-year Cumulative Annual Growth Rate (2019 to 2024). Calculated as `((2024 + 1)/(2019 + 1))^(1/5) - 1` (using +1 Laplace smoothing to avoid division by zero).
- **Market Share:** Calculated based on the most recent year (2024) degrees awarded out of the *selected* universities.
""")

# Process data for the selected CIPs
if selected_cips:
    df_cip = df_filtered[df_filtered['cip_code'].isin(selected_cips)]
elif selected_family_codes:
    df_cip = df_filtered[df_filtered['cip_code'].str[:2].isin(selected_family_codes)]
else:
    df_cip = df_filtered.copy()

if df_cip.empty or not selected_schools:
    st.warning("Please select at least one school and ensure data exists for your selection.")
else:
    # Aggregate by institution and year
    df_agg = df_cip.groupby(['institution', 'year'])['total_degrees'].sum().reset_index()

    # Pivot so years are columns
    df_pivot = df_agg.pivot(index='institution', columns='year', values='total_degrees').fillna(0)

    # Ensure all selected schools are present, even if they had 0 degrees
    df_pivot = df_pivot.reindex(selected_schools, fill_value=0)

    for y in ['2019', '2024']:
        if y not in df_pivot.columns:
            df_pivot[y] = 0

    val_2019 = df_pivot['2019']
    val_2024 = df_pivot['2024']
    
    # Calculate true CAGR mathematically:
    # 1. If starting value is > 0 and ending value > 0: true CAGR
    # 2. If starting value is > 0 and ending value is 0: -100% (-1.0)
    # 3. If starting value is 0 and ending value is 0: 0.0
    # 4. If starting value is 0 and ending value is > 0: undefined (NaN)
    cagr = np.where(
        val_2019 > 0,
        np.where(val_2024 > 0, (val_2024 / val_2019) ** 0.2 - 1.0, -1.0),
        np.where(val_2024 == 0, 0.0, np.nan)
    )
    df_pivot['cagr'] = cagr

    total_2024 = df_pivot['2024'].sum()
    if total_2024 > 0:
        df_pivot['market_share'] = df_pivot['2024'] / total_2024
    else:
        df_pivot['market_share'] = 0.0

    plot_data = df_pivot.reset_index()

    if total_2024 == 0:
        st.warning("No degrees awarded in 2024 for this selection across the chosen institutions.")
    else:
        median_cagr = plot_data['cagr'].median()
        median_share = plot_data['market_share'].median()
        
        selection_title = "Multiple CIPs / Families"
        if len(selected_cips) == 1:
            selection_title = cip_map.get(selected_cips[0], selected_cips[0])
        elif not selected_cips and len(selected_family_codes) == 1:
            selection_title = family_map.get(selected_family_codes[0], selected_family_codes[0]) + " (All)"
            
        st.markdown(f"### Performance for: `{selection_title}`")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Degrees (2024) [Selected Schools]", int(total_2024))
        
        median_share_str = f"{median_share:.1%}" if pd.notna(median_share) else "N/A"
        median_cagr_str = f"{median_cagr:.1%}" if pd.notna(median_cagr) else "N/A"
        
        col2.metric("Median Market Share", median_share_str)
        col3.metric("Median CAGR", median_cagr_str)

        # Scale axes dynamically to fit data points exactly (zero=False) with padding to prevent clipping
        scatter = alt.Chart(plot_data).mark_point(filled=True).encode(
            x=alt.X('market_share:Q', title="Market Share (2024)", axis=alt.Axis(format='%'), scale=alt.Scale(zero=False, padding=15)),
            y=alt.Y('cagr:Q', title="5-Year CAGR (2019-2024)", axis=alt.Axis(format='%'), scale=alt.Scale(zero=False, padding=15)),
            color=alt.condition(
                alt.datum.institution == WSU_NAME,
                alt.value(WSU_GREEN),
                alt.value(PEER_GREY)
            ),
            shape=alt.condition(
                alt.datum.institution == WSU_NAME,
                alt.value('diamond'),
                alt.Shape('institution:N', legend=None)
            ),
            size=alt.condition(
                alt.datum.institution == WSU_NAME,
                alt.value(400),
                alt.value(150)
            ),
            opacity=alt.condition(
                alt.datum.institution == WSU_NAME,
                alt.value(1.0),
                alt.value(0.7)
            ),
            tooltip=[
                alt.Tooltip('institution:N', title="Institution"),
                alt.Tooltip('2024:Q', title="Degrees (2024)"),
                alt.Tooltip('market_share:Q', title="Market Share", format=".1%"),
                alt.Tooltip('cagr:Q', title="CAGR", format=".1%")
            ]
        )

        chart_elements = [scatter]
        if pd.notna(median_share):
            vline = alt.Chart(pd.DataFrame({'x': [median_share]})).mark_rule(color='red', strokeDash=[4, 4]).encode(x='x:Q')
            chart_elements.append(vline)
        if pd.notna(median_cagr):
            hline = alt.Chart(pd.DataFrame({'y': [median_cagr]})).mark_rule(color='red', strokeDash=[4, 4]).encode(y='y:Q')
            chart_elements.append(hline)

        chart = alt.layer(*chart_elements).properties(
            height=600,
            title="Market Share vs CAGR (Red lines represent medians of selected schools)"
        ).interactive()

        st.altair_chart(chart, width='stretch')

        with st.expander("♿ Accessible Data Table - Market Share vs CAGR"):
            st.dataframe(plot_data[['institution', '2019', '2024', 'market_share', 'cagr']].style.format({
                'market_share': '{:.1%}',
                'cagr': '{:.1%}'
            }))


# ============================================================================
# SPRINT 2: MICHIGAN OCCUPATIONAL DEMAND
# Runs independently of the supply chart above, keyed to the same sidebar CIP
# selection. This is deliberate: a program with high demand but LOW Wayne State
# supply is exactly the opportunity case, so demand must show even when the
# supply scatter is thin. Openings are shown per occupation and never summed
# (one occupation is shared across many programs via the crosswalk).
# ============================================================================
st.divider()
st.header("Michigan Occupational Demand")

if demand_summary.empty:
    st.info(
        "Demand data not found. In your virtual environment, run "
        "`python build_demand.py` to generate "
        "`data/app/cip_demand_summary.parquet` and "
        "`data/app/cip_demand_itemized.parquet`, then refresh this page."
    )
else:
    st.caption(
        "Where graduates of the selected program(s) tend to work, with projected "
        "Michigan annual openings and annualized median wages. Occupations are "
        "linked to programs via the CIP\u2192SOC crosswalk. Openings are shown per "
        "occupation and are never summed across a program's occupations, because "
        "one occupation is shared by many programs."
    )

    # Resolve which CIPs to show, from the sidebar selection.
    if selected_cips:
        target_cips = list(selected_cips)
    elif selected_family_codes:
        target_cips = sorted(
            demand_summary[demand_summary['cip'].str[:2].isin(selected_family_codes)]['cip'].unique()
        )
    else:
        target_cips = []

    if not target_cips:
        st.info("Select a specific CIP code (or a CIP family) in the sidebar to see occupational demand.")
    else:
        sum_rows = demand_summary[demand_summary['cip'].isin(target_cips)].copy()

        if sum_rows.empty:
            st.warning(
                "No Michigan demand mapping found for this selection. "
                "Some CIP codes have no linked occupations in the crosswalk."
            )
        else:
            # Program-level summary: breadth + growth-share + wage band (never a sum).
            summary_display = pd.DataFrame({
                'CIP': sum_rows['cip'],
                'Program': sum_rows['cip_title'],
                'Linked occupations': sum_rows['n_occ'].astype(int),
                'Growing / mapped': sum_rows.apply(
                    lambda r: f"{int(r['n_growing'])} / {int(r['n_matched'])}", axis=1),
                'Wage band (annual median)': sum_rows.apply(
                    lambda r: (f"${r['wage_lo']:,.0f} \u2013 ${r['wage_hi']:,.0f}"
                               if pd.notna(r['wage_lo']) else "n/a"), axis=1),
            })
            st.dataframe(summary_display, hide_index=True)

            # Itemized occupations for the selected program(s).
            if not demand_itemized.empty:
                items = demand_itemized[demand_itemized['cip'].isin(target_cips)].copy()
                items = items.dropna(subset=['annual_openings'])
                items = items.sort_values('annual_openings', ascending=False)

                with st.expander(f"Linked occupations detail ({len(items)} occupations)"):
                    items_display = pd.DataFrame({
                        'CIP': items['cip'],
                        'Occupation': items['soc_title'],
                        'Annual openings': items['annual_openings'].map(lambda v: f"{v:,.0f}"),
                        'Projected change': items['pct_change'].map(
                            lambda v: f"{v*100:+.1f}%" if pd.notna(v) else "n/a"),
                        'Median wage': items['median_wage'].map(
                            lambda v: f"${v:,.0f}" if pd.notna(v) else "n/a"),
                    })
                    st.dataframe(items_display, hide_index=True)
