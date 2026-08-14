import streamlit as st
import pandas as pd
import os
import altair as alt

# --- CUSTOM CSS FOR PREMIUM LOOK ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif;
}
.info-card {
    background: rgba(12, 84, 73, 0.05);
    border: 1px solid rgba(12, 84, 73, 0.15);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}
</style>
""", unsafe_allow_html=True)

# --- CONFIG & PEERS ---
WSU_UNITID = 172644

@st.cache_data(ttl=3600)
def load_trajectory_data():
    file_path = "data/app/institutional_trajectory.parquet"
    if os.path.exists(file_path):
        return pd.read_parquet(file_path)
    return pd.DataFrame()

with st.spinner("Loading trajectory data..."):
    df_all = load_trajectory_data()

# Cohort mappings
cohort_names = ["Michigan Publics (MASU)", "Urban Peer Publics", "Public R1 Universities"]
if not df_all.empty:
    min_yr = int(df_all['YEAR'].min())
    max_yr = int(df_all['YEAR'].max())
else:
    min_yr, max_yr = 2019, 2024

# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Settings")

# 1. Cohort
selected_cohort = st.sidebar.selectbox(
    "Select Cohort Group",
    options=cohort_names,
    index=1
)

# Filter cohort mapping
if not df_all.empty:
    cohort_path = "dictionaries/cohorts.csv"
    if os.path.exists(cohort_path):
        cdbs = pd.read_csv(cohort_path)
        cohort_ids = cdbs[cdbs['cohort_group'] == selected_cohort]['unitid'].unique().tolist()
        df_cohort = df_all[df_all['UNITID'].isin(cohort_ids)].copy()
    else:
        df_cohort = df_all.copy()
else:
    df_cohort = pd.DataFrame()

# 2. Cohort Members
if not df_cohort.empty:
    all_cohort_schools = sorted(df_cohort[df_cohort['UNITID'] != WSU_UNITID]['INSTNM'].unique().tolist())
else:
    all_cohort_schools = []

selected_cohort_members = st.sidebar.multiselect(
    "Select Peer Universities",
    options=all_cohort_schools,
    default=all_cohort_schools
)

wsu_name = "Wayne State University"
if not df_cohort.empty:
    df_frame = df_cohort[df_cohort['INSTNM'].isin([wsu_name] + selected_cohort_members)].copy()
else:
    df_frame = pd.DataFrame()

# 3. Year Range
selected_years = st.sidebar.slider(
    "Select Year Range",
    min_value=min_yr,
    max_value=max_yr,
    value=(min_yr, max_yr),
    step=1
)
if not df_frame.empty:
    df_frame = df_frame[(df_frame['YEAR'] >= selected_years[0]) & (df_frame['YEAR'] <= selected_years[1])]

# 4. Deflator
deflator_choice = st.sidebar.selectbox(
    "Deflator (for Dollar Metrics)",
    options=["HECA", "CPI-U", "Nominal"],
    index=0
)

# 5. Base Year
base_year = st.sidebar.selectbox(
    "Index Base Year",
    options=list(range(selected_years[0], selected_years[1] + 1)),
    index=0
)

# 6. Definitions Note
st.sidebar.markdown("""
---
**Definitions & Sources:**
- **Data Source:** NCES [IPEDS](https://nces.ed.gov/ipeds/).
- **Dollar Conversion:** Uses SHEEO Higher Education Cost Adjustment (HECA) or BLS CPI-U to restate historical dollars to current terms.
- **Core Expenses:** Excludes hospital, auxiliary, and independent operations.
""")

st.title("📈 Institutional Trajectory")
st.caption(f"#### Scope: {selected_cohort} | Years: {selected_years[0]}–{selected_years[1]} | Base: {base_year} = 100 | Deflator: {deflator_choice}")

if df_frame.empty:
    st.warning("No data available for the current selection.")
    st.stop()

# Helpers
def get_metric_col(base_col, deflator):
    if deflator == "Nominal": return base_col
    elif deflator == "HECA": return f"{base_col}_real_heca"
    elif deflator == "CPI-U": return f"{base_col}_real_cpi"

def get_per_fte_col(base_col, deflator):
    if deflator == "Nominal": return f"{base_col}_per_fte"
    elif deflator == "HECA": return f"{base_col}_per_fte_real_heca"
    elif deflator == "CPI-U": return f"{base_col}_per_fte_real_cpi"

def index_to_base(df, metric, group_col, base_yr):
    # Calculates the index to base year
    # Return dataframe with ['YEAR', group_col, 'IndexValue']
    base_vals = df[df['YEAR'] == base_yr][[group_col, metric]].set_index(group_col)[metric].to_dict()
    def calc_idx(row):
        bv = base_vals.get(row[group_col])
        if pd.isna(bv) or bv == 0 or pd.isna(row[metric]):
            return None
        return (row[metric] / bv) * 100.0
    
    res = df[['YEAR', group_col, metric]].copy()
    res['IndexValue'] = res.apply(calc_idx, axis=1)
    return res

# Check Hospital mix
has_hosp = df_frame[df_frame['has_hospital_expenses'] == True]['INSTNM'].unique()
no_hosp = df_frame[df_frame['has_hospital_expenses'] == False]['INSTNM'].unique()
if len(has_hosp) > 0 and len(no_hosp) > 0:
    st.warning("⚠️ **Peer Mix Warning:** The selected cohort mixes institutions with and without hospital operations. Functional expense shares may be structurally distorted due to clinical faculty effort allocations, even after removing hospital direct expenses.")

# --- SECTION 1: TRAJECTORY ---
st.header("Section 1: Indexed Trajectory")

traj_metrics = {
    '12-mo Headcount': 'headcount_12m',
    '12-mo FTE': 'fte_12m',
    'Degrees Conferred': 'degrees_conferred',
    'Instruction per FTE': get_per_fte_col('exp_instruction', deflator_choice),
    'Inst Grant per FTE': get_per_fte_col('inst_grant_aid', deflator_choice),
    'State Approp per FTE': get_per_fte_col('rev_state_approp', deflator_choice)
}

# Compute Indexed Values
traj_data = []
for label, col in traj_metrics.items():
    if col not in df_frame.columns: continue
    idx_df = index_to_base(df_frame, col, 'UNITID', base_year)
    for _, row in idx_df.iterrows():
        if pd.notna(row['IndexValue']):
            traj_data.append({
                'YEAR': row['YEAR'],
                'UNITID': row['UNITID'],
                'Metric': label,
                'IndexValue': row['IndexValue'],
                'RawValue': row[col]
            })

df_traj = pd.DataFrame(traj_data)

if not df_traj.empty:
    df_traj = df_traj.merge(df_frame[['UNITID', 'INSTNM']].drop_duplicates(), on='UNITID', how='left')
    
    # Separate WSU and Peers
    df_traj_wsu = df_traj[df_traj['UNITID'] == WSU_UNITID].copy()
    df_traj_peers = df_traj[df_traj['UNITID'] != WSU_UNITID].copy()
    
    # Peer medians
    df_traj_medians = df_traj_peers.groupby(['YEAR', 'Metric'])['IndexValue'].median().reset_index()
    
    wsu_lines = alt.Chart(df_traj_wsu).mark_line(size=3, point=alt.OverlayMarkDef(filled=True, size=50)).encode(
        x=alt.X('YEAR:O', title='Fiscal Year'),
        y=alt.Y('IndexValue:Q', title=f'Index ({base_year} = 100)'),
        color=alt.Color('Metric:N', scale=alt.Scale(scheme='dark2'), legend=alt.Legend(title="Metric")),
        strokeDash=alt.StrokeDash('Metric:N'),
        tooltip=['YEAR', 'Metric', alt.Tooltip('IndexValue:Q', format='.1f'), alt.Tooltip('RawValue:Q', format=',.0f')]
    )
    
    peer_lines = alt.Chart(df_traj_medians).mark_line(size=1.5, opacity=0.4, strokeDash=[4,4]).encode(
        x='YEAR:O',
        y='IndexValue:Q',
        color='Metric:N',
        detail='Metric:N',
        tooltip=['YEAR', 'Metric', alt.Tooltip('IndexValue:Q', title="Peer Median Index", format='.1f')]
    )
    
    st.altair_chart((peer_lines + wsu_lines).properties(height=500, title="WSU (Solid/Points) vs Peer Median (Faded Dashed)"), width="stretch")
    
    with st.expander("♿ Accessible Data Table - Trajectory"):
        st.dataframe(df_traj_wsu.pivot(index='YEAR', columns='Metric', values='IndexValue').style.format("{:.1f}"))

# --- SECTION 2: PRICE AND SUBSIDY ---
st.header("Section 2: Price and Subsidy")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Discount Rate")
    
    dr_wsu = df_frame[df_frame['UNITID'] == WSU_UNITID][['YEAR', 'discount_rate']].dropna()
    dr_peer = df_frame[df_frame['UNITID'] != WSU_UNITID].groupby('YEAR')['discount_rate'].median().reset_index()
    dr_peer['Group'] = 'Peer Median'
    dr_wsu['Group'] = 'Wayne State'
    
    dr_chart = alt.Chart(pd.concat([dr_wsu, dr_peer])).mark_line(point=True).encode(
        x='YEAR:O',
        y=alt.Y('discount_rate:Q', axis=alt.Axis(format='%')),
        color=alt.Color('Group:N', scale=alt.Scale(domain=['Wayne State', 'Peer Median'], range=['#0C5449', '#737373'])),
        strokeDash=alt.condition(alt.datum.Group == 'Peer Median', alt.value([4,4]), alt.value([0])),
        tooltip=['YEAR', 'Group', alt.Tooltip('discount_rate:Q', format='.1%')]
    ).properties(height=350)
    st.altair_chart(dr_chart, width="stretch")

with col2:
    st.subheader(f"Net Tuition & State Approp per FTE ({deflator_choice})")
    
    nt_col = get_per_fte_col('rev_tuition', deflator_choice)
    sa_col = get_per_fte_col('rev_state_approp', deflator_choice)
    
    ts_wsu = df_frame[df_frame['UNITID'] == WSU_UNITID][['YEAR', nt_col, sa_col]].dropna()
    if not ts_wsu.empty:
        ts_melt = ts_wsu.melt('YEAR', var_name='Metric', value_name='Amount')
        ts_melt['Metric'] = ts_melt['Metric'].replace({nt_col: 'Net Tuition', sa_col: 'State Approp'})
        
        ts_chart = alt.Chart(ts_melt).mark_line(point=True).encode(
            x='YEAR:O',
            y=alt.Y('Amount:Q', title="Dollars per FTE"),
            color=alt.Color('Metric:N', scale=alt.Scale(range=['#0C5449', '#F2A900'])),
            tooltip=['YEAR', 'Metric', alt.Tooltip('Amount:Q', format='$,.0f')]
        ).properties(height=350)
        
        # FY21 HEERF Annotation
        heerf_annotation = alt.Chart(pd.DataFrame({'YEAR': [2021], 'text': ['FY21 HEERF Impact']})).mark_text(
            align='center', baseline='bottom', dy=-15, color='#d9534f', fontSize=12, fontWeight='bold'
        ).encode(x='YEAR:O', y=alt.value(10), text='text')
        
        rule = alt.Chart(pd.DataFrame({'YEAR': [2021]})).mark_rule(color='#d9534f', strokeDash=[2,2]).encode(x='YEAR:O')
        
        st.altair_chart((ts_chart + rule + heerf_annotation), width="stretch")

# --- SECTION 3: EXPENDITURE SHAPE ---
st.header("Section 3: Expenditure Shape")
st.markdown("Functional expense shares as a percent of Adjusted Core Expenses.")

categories = ["exp_instruction", "exp_research", "exp_pub_service", "exp_acad_support", "exp_stud_services", "exp_inst_support", "exp_scholarships"]
labels = ["Instruction", "Research", "Public Service", "Acad Support", "Stud Services", "Inst Support", "Scholarships"]

wsu_shapes = []
peer_shapes = []
for y in df_frame['YEAR'].unique():
    y_df = df_frame[df_frame['YEAR'] == y]
    w_df = y_df[y_df['UNITID'] == WSU_UNITID]
    p_df = y_df[y_df['UNITID'] != WSU_UNITID]
    
    for c, l in zip(categories, labels):
        if not w_df.empty and pd.notna(w_df['adj_core_expenses'].iloc[0]) and w_df['adj_core_expenses'].iloc[0] > 0:
            val = w_df[c].iloc[0] / w_df['adj_core_expenses'].iloc[0]
            wsu_shapes.append({'YEAR': y, 'Category': l, 'Share': val, 'Group': 'Wayne State'})
            
        p_vals = (p_df[c] / p_df['adj_core_expenses']).dropna()
        if not p_vals.empty:
            peer_shapes.append({'YEAR': y, 'Category': l, 'Share': p_vals.median(), 'Group': 'Peer Median'})

df_shapes = pd.DataFrame(wsu_shapes + peer_shapes)
if not df_shapes.empty:
    shape_chart = alt.Chart(df_shapes).mark_line(point=True).encode(
        x=alt.X('YEAR:O', title=None),
        y=alt.Y('Share:Q', axis=alt.Axis(format='%')),
        color=alt.Color('Group:N', scale=alt.Scale(domain=['Wayne State', 'Peer Median'], range=['#0C5449', '#737373'])),
        strokeDash=alt.condition(alt.datum.Group == 'Peer Median', alt.value([4,4]), alt.value([0])),
        facet=alt.Facet('Category:N', columns=4),
        tooltip=['YEAR', 'Group', 'Category', alt.Tooltip('Share:Q', format='.1%')]
    ).properties(height=200, width=150)
    
    st.altair_chart(shape_chart)

# --- SECTION 4: INTENSITY AND COMPLETION ---
st.header("Section 4: Intensity & Completion")

c3, c4 = st.columns(2)
with c3:
    st.subheader("Intensity & Yield")
    # Intensity Index and Production Yield
    iy_wsu = df_frame[df_frame['UNITID'] == WSU_UNITID][['YEAR', 'intensity_index', 'production_yield']].dropna()
    if not iy_wsu.empty:
        iy_melt = iy_wsu.melt('YEAR', var_name='Metric', value_name='Ratio')
        iy_melt['Metric'] = iy_melt['Metric'].replace({'intensity_index': 'Intensity Index', 'production_yield': 'Production Yield'})
        iy_chart = alt.Chart(iy_melt).mark_line(point=True).encode(
            x='YEAR:O',
            y=alt.Y('Ratio:Q', title="Ratio"),
            color=alt.Color('Metric:N', scale=alt.Scale(range=['#0C5449', '#F2A900'])),
            tooltip=['YEAR', 'Metric', alt.Tooltip('Ratio:Q', format='.2f')]
        ).properties(height=350)
        st.altair_chart(iy_chart, width="stretch")
        
with c4:
    st.subheader("6-Year Graduation Rate (Pell/Non-Pell)")
    gr_wsu = df_frame[df_frame['UNITID'] == WSU_UNITID][['YEAR', 'grad_rate_pell', 'grad_rate_nopell']].dropna()
    if not gr_wsu.empty:
        gr_melt = gr_wsu.melt('YEAR', var_name='Cohort', value_name='Rate')
        gr_melt['Cohort'] = gr_melt['Cohort'].replace({'grad_rate_pell': 'Pell Recipients', 'grad_rate_nopell': 'Non-Pell Recipients'})
        gr_chart = alt.Chart(gr_melt).mark_line(point=True).encode(
            x='YEAR:O',
            y=alt.Y('Rate:Q', axis=alt.Axis(format='%')),
            color=alt.Color('Cohort:N', scale=alt.Scale(range=['#0C5449', '#737373'])),
            tooltip=['YEAR', 'Cohort', alt.Tooltip('Rate:Q', format='.1%')]
        ).properties(height=350)
        st.altair_chart(gr_chart, width="stretch")
        st.caption("Note: 6-Year GR tracks Full-Time, First-Time students only.")

st.subheader("Outcome Measures (8-Year Completion)")
om_wsu = df_frame[df_frame['UNITID'] == WSU_UNITID][['YEAR', 'om_awd_ftft', 'om_awd_ptft', 'om_awd_ftnft', 'om_awd_ptnft']].dropna()
if not om_wsu.empty:
    om_melt = om_wsu.melt('YEAR', var_name='Subgroup', value_name='Completion Rate')
    om_melt['Subgroup'] = om_melt['Subgroup'].replace({
        'om_awd_ftft': 'FT First-Time',
        'om_awd_ptft': 'PT First-Time',
        'om_awd_ftnft': 'FT Non-First-Time',
        'om_awd_ptnft': 'PT Non-First-Time'
    })
    om_chart = alt.Chart(om_melt).mark_bar().encode(
        x='YEAR:O',
        y=alt.Y('Completion Rate:Q', axis=alt.Axis(format='%')),
        color=alt.Color('Subgroup:N', scale=alt.Scale(scheme='set2')),
        column='Subgroup:N',
        tooltip=['YEAR', 'Subgroup', alt.Tooltip('Completion Rate:Q', format='.1%')]
    ).properties(height=250, width=120)
    st.altair_chart(om_chart)

# --- SECTION 5: DATA NOTES ---
with st.expander("⚠️ Important Data Notes & Discontinuities"):
    st.markdown("""
    - **FY2021 HEERF:** Federal pandemic relief funds landed in grants/contracts and may artificially depress net tuition dependence while temporarily inflating expense lines.
    - **2020-21 Enrollment Shock:** Be cautious interpreting growth from 2020 or 2021 index bases, as this represents pandemic recovery rather than structural growth.
    - **GASB vs FASB:** Some institutions report under FASB, making functional expense shares incompatible with GASB reporting standards. The core expense adjustment accounts for major differences but does not perfectly align O&M or pensions.
    """)
