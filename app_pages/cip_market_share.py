import streamlit as st
import pandas as pd
import altair as alt
import os
import numpy as np
import duckdb

# Cache the data load
@st.cache_data(ttl=3600)
def load_completions_data():
    try:
        file_path = 'data/app/completions_michigan.parquet'
        if not os.path.exists(file_path):
            return pd.DataFrame()
        query = """
            SELECT year, institution, cip_code, award_level, total_degrees
            FROM 'data/app/completions_michigan.parquet'
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
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_demand_itemized():
    try:
        file_path = 'data/app/cip_demand_itemized.parquet'
        if not os.path.exists(file_path):
            return pd.DataFrame()
        return duckdb.query(f"SELECT * FROM '{file_path}'").df()
    except Exception:
        return pd.DataFrame()



st.title("Michigan Public Universities: CIP Market Share & CAGR")
st.caption("#### Scope: Michigan Public Universities | Years: 2019 to 2024 | Metrics: Degrees Conferred, Market Share, CAGR")

with st.spinner("Loading local data..."):
    df = load_completions_data()
    cip_dict = load_cip_dictionary()
    demand_summary = load_demand_summary()
    demand_itemized = load_demand_itemized()

# Data cleaning
df['cip_code'] = df['cip_code'].astype(str)
df['total_degrees'] = pd.to_numeric(df['total_degrees'], errors='coerce').fillna(0)

# Sidebar filters
st.sidebar.header("Filters")

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

    val_2019 = df_pivot['2019'] + 1
    val_2024 = df_pivot['2024'] + 1
    cagr = (val_2024 / val_2019) ** (1/5) - 1
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
        col2.metric("Median Market Share", f"{median_share:.1%}")
        col3.metric("Median CAGR", f"{median_cagr:.1%}")

        scatter = alt.Chart(plot_data).mark_point(size=150, opacity=0.8, filled=True).encode(
            x=alt.X('market_share:Q', title="Market Share (2024)", axis=alt.Axis(format='%')),
            y=alt.Y('cagr:Q', title="5-Year CAGR (2019-2024)", axis=alt.Axis(format='%')),
            color=alt.Color('institution:N', legend=None),
            shape=alt.Shape('institution:N', legend=None),
            tooltip=[
                alt.Tooltip('institution:N', title="Institution"),
                alt.Tooltip('2024:Q', title="Degrees (2024)"),
                alt.Tooltip('market_share:Q', title="Market Share", format=".1%"),
                alt.Tooltip('cagr:Q', title="CAGR", format=".1%")
            ]
        )

        vline = alt.Chart(pd.DataFrame({'x': [median_share]})).mark_rule(color='red', strokeDash=[4, 4]).encode(x='x:Q')
        hline = alt.Chart(pd.DataFrame({'y': [median_cagr]})).mark_rule(color='red', strokeDash=[4, 4]).encode(y='y:Q')

        chart = (scatter + vline + hline).properties(
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
