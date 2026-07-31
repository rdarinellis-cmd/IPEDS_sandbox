import streamlit as st
import pandas as pd
import altair as alt
import os

@st.cache_data(ttl=3600)
def load_nih_data():
    agg_path = "data/app/nih_grants.parquet"
    itemized_path = "data/app/nih_grants_itemized.parquet"
    
    df_agg = pd.read_parquet(agg_path) if os.path.exists(agg_path) else pd.DataFrame()
    df_itemized = pd.read_parquet(itemized_path) if os.path.exists(itemized_path) else pd.DataFrame()
    
    return df_agg, df_itemized

df, df_itemized_all = load_nih_data()

# ==========================================
# SIDEBAR FILTERS (Rule 4: Unified Layout)
# ==========================================

cohort_options = ["Michigan Publics (MASU)", "Urban Peer Publics", "Public R1 Universities"]
selected_cohort = st.sidebar.selectbox("Select Cohort Group", options=cohort_options)

if not df.empty:
    if selected_cohort == "Michigan Publics (MASU)":
        df_cohort = df[df['is_mi_public'] == 1].copy()
    elif selected_cohort == "Urban Peer Publics":
        df_cohort = df[df['is_urban_peer'] == 1].copy()
    elif selected_cohort == "Public R1 Universities":
        df_cohort = df[df['is_public_r1'] == 1].copy()
    else:
        df_cohort = df.copy()
        
    available_schools = sorted(df_cohort['institution'].unique())
    selected_schools = st.sidebar.multiselect(
        "Select Universities",
        options=available_schools,
        default=available_schools
    )

    if selected_schools:
        df_filtered = df_cohort[df_cohort['institution'].isin(selected_schools)]
        df_itemized_filtered = df_itemized_all[df_itemized_all['institution'].isin(selected_schools)] if not df_itemized_all.empty else pd.DataFrame()
    else:
        df_filtered = df_cohort
        df_itemized_filtered = df_itemized_all
else:
    df_filtered = pd.DataFrame()
    df_itemized_filtered = pd.DataFrame()

# Attribution Note at bottom of sidebar (Rule 1 & 4)
st.sidebar.markdown("""
---
**Definitions & Sources:**
- **Data Source:** [NIH RePORTER API v2](https://api.reporter.nih.gov/)
- **Metric Scope:** Displays active Training Grants (T32, T90, TL1, T35) and Center/Infrastructure Grants (P30, P50, P20, U54) by volume and total award funding.
- **Note:** Matches are based on NIH's `org_name` classifications. Zero values may indicate missing exact name matches in the API payload.
""")

# ==========================================
# SELECTION SYNC LOGIC
# ==========================================

# Prepare display_df early for selection mapping
display_df = df_filtered[[
    'institution', 
    'training_grant_count', 'training_grant_funding',
    'center_grant_count', 'center_grant_funding'
]].copy()

display_df = display_df.rename(columns={
    'institution': 'Institution',
    'training_grant_count': 'Training Count',
    'training_grant_funding': 'Training Funding',
    'center_grant_count': 'Center Count',
    'center_grant_funding': 'Center Funding'
})

# Initialization
if 'prev_chart_sel' not in st.session_state:
    st.session_state.prev_chart_sel = set()
if 'prev_table_rows' not in st.session_state:
    st.session_state.prev_table_rows = []
if 'selected_institutions' not in st.session_state:
    st.session_state.selected_institutions = set()
    
# Read current events from session state
chart_sel = set()
if "funding_chart" in st.session_state:
    sel = st.session_state.funding_chart.get("selection", {}).get("Select", [])
    for item in sel:
        if "institution" in item:
            chart_sel.add(item["institution"])

if "count_chart" in st.session_state:
    sel = st.session_state.count_chart.get("selection", {}).get("Select", [])
    for item in sel:
        if "institution" in item:
            chart_sel.add(item["institution"])

table_rows = []
if "summary_table" in st.session_state:
    table_rows = st.session_state.summary_table.get("selection", {}).get("rows", [])
    
# Determine what changed
if chart_sel != st.session_state.prev_chart_sel:
    # Chart was clicked!
    st.session_state.selected_institutions = chart_sel
elif table_rows != st.session_state.prev_table_rows:
    # Table was clicked!
    st.session_state.selected_institutions = {display_df.iloc[i]['Institution'] for i in table_rows}

# Compute synchronized table rows
new_table_rows = [i for i, inst in enumerate(display_df['Institution']) if inst in st.session_state.selected_institutions]

# Update previous states for NEXT run
st.session_state.prev_chart_sel = st.session_state.selected_institutions.copy()
st.session_state.prev_table_rows = new_table_rows

# FORCE table selection via override
st.session_state.summary_table = {"selection": {"rows": new_table_rows, "columns": []}}

# ==========================================
# MAIN PAGE (Rule 2: Contextual Subtitles)
# ==========================================

st.title("NIH Training & Center Grants")

if df.empty:
    st.error("No NIH Grants data found. Please ensure the ETL pipeline has been run.")
    st.stop()
    
# Subtitle strictly formatted
st.caption(f"#### Scope: {selected_cohort} | Years: FY24-25 | Metrics: Grant Counts & Total Funding")

st.markdown("""
This dashboard compares the institutional capacity for advanced research infrastructure and training.
**Training Grants** indicate institutional capacity to support doctoral and post-doctoral trainees, while 
**Center Grants** represent major multi-project research infrastructure investments.
""")

st.divider()

# ==========================================
# VISUALIZATIONS
# ==========================================

col1, col2 = st.columns(2)

with col1:
    st.subheader("Funding Volume Comparison")
    
    # Melt for grouped bar chart
    df_funding = df_filtered[['institution', 'training_grant_funding', 'center_grant_funding']].melt(
        id_vars='institution', var_name='Grant Type', value_name='Funding'
    )
    df_funding['Grant Type'] = df_funding['Grant Type'].map({
        'training_grant_funding': 'Training Grants',
        'center_grant_funding': 'Center Grants'
    })
    
    df_funding['Chart Color'] = df_funding.apply(
        lambda x: f"WSU - {x['Grant Type']}" if x['institution'] == 'Wayne State University' else f"Peers - {x['Grant Type']}", 
        axis=1
    )
    
    click_selection = alt.selection_point(name='Select', fields=['institution'])
    
    # Python override for bi-directional opacity
    python_selection = alt.FieldOneOfPredicate(field='institution', oneOf=list(st.session_state.selected_institutions))
    if st.session_state.selected_institutions:
        opacity_cond = alt.condition(click_selection | python_selection, alt.value(1.0), alt.value(0.3))
    else:
        opacity_cond = alt.condition(click_selection, alt.value(1.0), alt.value(0.3))
    
    funding_chart = alt.Chart(df_funding).mark_bar().encode(
        x=alt.X('Funding:Q', title="Total Funding ($)", axis=alt.Axis(format='$,.0f')),
        y=alt.Y('institution:N', title=None, sort='-x'),
        color=alt.Color(
            'Chart Color:N', 
            scale=alt.Scale(
                domain=['WSU - Training Grants', 'WSU - Center Grants', 'Peers - Training Grants', 'Peers - Center Grants'],
                range=['#0C5449', '#F2A900', '#000000', '#737373']
            ),
            legend=alt.Legend(title="Institution & Grant Type")
        ),
        opacity=opacity_cond,
        tooltip=[
            alt.Tooltip('institution', title="Institution"),
            alt.Tooltip('Grant Type', title="Type"),
            alt.Tooltip('Funding:Q', title="Funding", format='$,.0f')
        ]
    ).properties(height=400).add_params(click_selection)
    
    funding_event = st.altair_chart(funding_chart, use_container_width=True, on_select="rerun", key="funding_chart")

with col2:
    st.subheader("Grant Count Comparison")
    
    df_count = df_filtered[['institution', 'training_grant_count', 'center_grant_count']].melt(
        id_vars='institution', var_name='Grant Type', value_name='Count'
    )
    df_count['Grant Type'] = df_count['Grant Type'].map({
        'training_grant_count': 'Training Grants',
        'center_grant_count': 'Center Grants'
    })
    
    df_count['Chart Color'] = df_count.apply(
        lambda x: f"WSU - {x['Grant Type']}" if x['institution'] == 'Wayne State University' else f"Peers - {x['Grant Type']}", 
        axis=1
    )
    
    count_chart = alt.Chart(df_count).mark_bar().encode(
        x=alt.X('Count:Q', title="Number of Grants"),
        y=alt.Y('institution:N', title=None, sort='-x'),
        color=alt.Color(
            'Chart Color:N', 
            scale=alt.Scale(
                domain=['WSU - Training Grants', 'WSU - Center Grants', 'Peers - Training Grants', 'Peers - Center Grants'],
                range=['#0C5449', '#F2A900', '#000000', '#737373']
            ),
            legend=alt.Legend(title="Institution & Grant Type")
        ),
        opacity=opacity_cond,
        tooltip=[
            alt.Tooltip('institution', title="Institution"),
            alt.Tooltip('Grant Type', title="Type"),
            alt.Tooltip('Count:Q', title="Count")
        ]
    ).properties(height=400).add_params(click_selection)
    
    count_event = st.altair_chart(count_chart, use_container_width=True, on_select="rerun", key="count_chart")

st.divider()

st.subheader("Summary by Institution")
st.markdown("Click on a row below, or a bar in the charts above, to drill down into the itemized grants.")

table_event = st.dataframe(
    display_df,
    hide_index=True,
    on_select="rerun",
    selection_mode="multi-row",
    key="summary_table",
    column_config={
        "Training Funding": st.column_config.NumberColumn(format="$%.0f"),
        "Center Funding": st.column_config.NumberColumn(format="$%.0f")
    },
    use_container_width=True
)

st.divider()

if st.session_state.selected_institutions:
    st.subheader(f"Itemized Grants Detail: {', '.join(st.session_state.selected_institutions)}")
    df_itemized_display = df_itemized_filtered[df_itemized_filtered['institution'].isin(st.session_state.selected_institutions)]
else:
    st.subheader("Itemized Grants Detail")
    st.info("Showing all grants. Select specific institutions above to drill down.")
    df_itemized_display = df_itemized_filtered

if not df_itemized_display.empty:
    display_itemized = df_itemized_display[[
        'institution', 'grant_type', 'core_project_num', 'project_title', 
        'contact_pi_name', 'award_amount', 'fiscal_year', 'budget_start', 'budget_end', 'is_no_cost_extension',
        'agency_ic', 'project_start_date', 'project_end_date', 'project_detail_url'
    ]].copy()
    
    display_itemized = display_itemized.rename(columns={
        'institution': 'Institution',
        'grant_type': 'Type',
        'core_project_num': 'Project #',
        'project_title': 'Title',
        'contact_pi_name': 'PI Name',
        'award_amount': 'Award Amount',
        'fiscal_year': 'FY',
        'budget_start': 'Budget Start',
        'budget_end': 'Budget End',
        'is_no_cost_extension': 'NCE',
        'agency_ic': 'Agency',
        'project_start_date': 'Project Start',
        'project_end_date': 'Project End',
        'project_detail_url': 'URL'
    })
    
    # Sort for better readability
    display_itemized = display_itemized.sort_values(['Institution', 'Type', 'Award Amount'], ascending=[True, True, False])
    
    st.dataframe(
        display_itemized,
        hide_index=True,
        column_config={
            "Award Amount": st.column_config.NumberColumn(format="$%.0f"),
            "FY": st.column_config.NumberColumn(format="%d"),
            "Budget Start": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "Budget End": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "NCE": st.column_config.CheckboxColumn("No-Cost Extension"),
            "URL": st.column_config.LinkColumn("View on RePORTER"),
            "Project Start": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "Project End": st.column_config.DateColumn(format="YYYY-MM-DD")
        },
        use_container_width=True
    )
else:
    st.info("No itemized grant data available for the current selection.")
