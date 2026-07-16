import streamlit as st
import pandas as pd
import altair as alt
import os
import numpy as np



# Cache the data load
@st.cache_data(ttl=3600)
def load_completions_data():
    # Target 15 Michigan public 4-year universities
    schools = [
        'Central Michigan University',
        'Eastern Michigan University',
        'Ferris State University',
        'Grand Valley State University',
        'Lake Superior State University',
        'Michigan State University',
        'Michigan Technological University',
        'Northern Michigan University',
        'Oakland University',
        'Saginaw Valley State University',
        'University of Michigan-Ann Arbor',
        'University of Michigan-Dearborn',
        'University of Michigan-Flint',
        'Wayne State University',
        'Western Michigan University'
    ]
    
    try:
        # Load hd2024 to get the UNITIDs for these schools
        inst_df = pd.read_parquet('data/hd2024.parquet')
        inst_df.columns = inst_df.columns.str.upper()
        inst_df = inst_df[['UNITID', 'INSTNM']]
        
        inst_df = inst_df[inst_df['INSTNM'].isin(schools)]
        
        valid_unitids = inst_df['UNITID'].tolist()
        
        comp_dfs = []
        for year in ['2019', '2020', '2021', '2022', '2023', '2024']:
            file_path = f"data/c{year}_a.parquet"
            if not os.path.exists(file_path):
                continue
                
            df = pd.read_parquet(file_path)
            df.columns = df.columns.str.upper()
            df = df[['UNITID', 'CIPCODE', 'MAJORNUM', 'AWLEVEL', 'CTOTALT']]
            
            # MAJORNUM = 1 and length(CIPCODE) = 7
            df = df[df['MAJORNUM'] == 1]
            df = df[df['CIPCODE'].astype(str).str.len() == 7]
            
            # Filter to our targeted institutions early to save memory
            df = df[df['UNITID'].isin(valid_unitids)]
            df['year'] = year
            
            comp_dfs.append(df)
            
        if not comp_dfs:
            return pd.DataFrame()
            
        comp_all = pd.concat(comp_dfs, ignore_index=True)
        
        # Merge with institution names
        final_df = comp_all.merge(inst_df, on='UNITID', how='inner')
        final_df = final_df.rename(columns={
            'INSTNM': 'institution',
            'CIPCODE': 'cip_code',
            'AWLEVEL': 'award_level',
            'CTOTALT': 'total_degrees'
        })
        
        return final_df[['year', 'institution', 'cip_code', 'award_level', 'total_degrees']]
    except Exception as e:
        st.error(f"Failed to load completions data from local files: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_cip_dictionary():
    try:
        df = pd.read_parquet('data/cip_dictionary.parquet')
        
        if 'cipfamily' in df.columns:
            df['cip_family'] = df['cipfamily'].astype(str).str.replace('="', '', regex=False).str.replace('"', '', regex=False)
        else:
            df['cip_family'] = ""
            
        if 'cipcode' in df.columns:
            df['cip_code'] = df['cipcode'].astype(str).str.replace('="', '', regex=False).str.replace('"', '', regex=False)
        else:
            df['cip_code'] = ""
            
        return df[['cip_family', 'cip_code', 'ciptitle']]
    except Exception as e:
        st.error(f"Failed to load CIP dictionary from local files: {e}")
        return pd.DataFrame()

st.title("Michigan Public Universities: CIP Market Share & CAGR")

with st.spinner("Loading local data..."):
    df = load_completions_data()
    cip_dict = load_cip_dictionary()

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
**Definitions:**
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

        scatter = alt.Chart(plot_data).mark_circle(size=150, opacity=0.8).encode(
            x=alt.X('market_share:Q', title="Market Share (2024)", axis=alt.Axis(format='%')),
            y=alt.Y('cagr:Q', title="5-Year CAGR (2019-2024)", axis=alt.Axis(format='%')),
            color=alt.Color('institution:N', legend=None),
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

        with st.expander("View Underlying Data"):
            st.dataframe(plot_data[['institution', '2019', '2024', 'market_share', 'cagr']].style.format({
                'market_share': '{:.1%}',
                'cagr': '{:.1%}'
            }))
