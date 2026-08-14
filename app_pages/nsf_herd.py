import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

APP_DIR = "./data/app"

st.set_page_config(layout="wide", page_title="NSF HERD Analysis")

# --- 1. Load Data ---
@st.cache_data
def load_herd_data():
    path = os.path.join(APP_DIR, "nsf_herd_metrics.parquet")
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_parquet(path)

df = load_herd_data()

if df.empty:
    st.error("No NSF HERD data found. Please run the ETL pipeline first.")
    st.stop()

# Ensure we have year and drop missing years
df['year'] = pd.to_numeric(df['year'], errors='coerce')
df = df.dropna(subset=['year'])

# --- 2. Unified Sidebar Filtering ---
st.sidebar.header("Filters")

# Year Range Selector
min_year = int(df['year'].min())
max_year = int(df['year'].max())
if min_year == max_year:
    selected_year = st.sidebar.selectbox("Select Year", [min_year])
    years_range = [selected_year, selected_year]
else:
    years_range = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))

# Cohort Group Selector
cohort_options = ["Michigan Publics (MASU)", "Urban Peer Publics", "Public R1 Universities"]
selected_cohort = st.sidebar.selectbox("Select Cohort Group", cohort_options, index=1)

# Filter dataset by cohort
if selected_cohort == "Michigan Publics (MASU)":
    df_cohort = df[df['is_mi_public'] == 1].copy()
elif selected_cohort == "Urban Peer Publics":
    df_cohort = df[df['is_urban_peer'] == 1].copy()
else:
    df_cohort = df[df['is_public_r1'] == 1].copy()

df_cohort = df_cohort[(df_cohort['year'] >= years_range[0]) & (df_cohort['year'] <= years_range[1])]

# University Members Selector
universities = sorted(df_cohort['INSTNM'].unique())
selected_universities = st.sidebar.multiselect("Select Universities", universities, default=universities)
df_filtered = df_cohort[df_cohort['INSTNM'].isin(selected_universities)].copy()

# Data Provenance Note
st.sidebar.markdown("---")
st.sidebar.markdown("### Definitions & Sources")
st.sidebar.info(
    "**Data Source**: [NSF Higher Education Research and Development (HERD) Survey](https://ncses.nsf.gov/surveys/higher-education-research-development/)\n\n"
    "**Definitions**:\n"
    "- **Total R&D Expenditures**: Total competitively awarded internal and external funding for research & development.\n"
    "- **Personnel**: Headcount of Principal Investigators and other R&D personnel (from Question 15).\n"
    "- **Cohort Multi-Campus Note**: Some systems (like University of Houston, University of Colorado, Texas A&M) report aggregated data in HERD. These have been mapped appropriately to their primary IPEDS IDs."
)

# --- 3. Main Page Header & Subtitles ---
st.title("NSF HERD Analysis")

year_str = str(years_range[0]) if years_range[0] == years_range[1] else f"{years_range[0]} to {years_range[1]}"
st.caption(f"#### Scope: {selected_cohort} | Years: {year_str} | Metrics: R&D Expenditures & Personnel Headcount")

# WSU Colors for charts
WSU_GREEN = '#0C5449'
WSU_GOLD = '#F2A900'
NEUTRAL_COLOR = '#737373'

def get_color_map(institutions):
    """Assign WSU distinct colors and neutral colors to peers."""
    return {inst: WSU_GREEN if "Wayne State" in inst else NEUTRAL_COLOR for inst in institutions}

def highlight_wsu_bars(fig):
    """Adds a bold WSU Gold border to the bars corresponding to Wayne State University."""
    for trace in fig.data:
        if hasattr(trace, 'x') and trace.x is not None:
            # Check if trace is a bar chart (some might be lines, but we only apply this to bars)
            if trace.type == 'bar':
                widths = [3 if "Wayne State" in str(x_val) else 0 for x_val in trace.x]
                colors = [WSU_GOLD if "Wayne State" in str(x_val) else 'rgba(0,0,0,0)' for x_val in trace.x]
                trace.marker.line.width = widths
                trace.marker.line.color = colors
    return fig

st.markdown("---")

# --- 4. Total R&D Expenditures ---
st.subheader("Total R&D Expenditures")

if df_filtered.empty:
    st.warning("No data available for the selected filters.")
else:
    df_latest = df_filtered[df_filtered['year'] == years_range[1]].copy()
    df_latest = df_latest.sort_values(by='rd_total', ascending=False)
    
    # Bar Chart for Latest Year
    fig1 = px.bar(
        df_latest,
        x='INSTNM',
        y='rd_total',
        color='INSTNM',
        color_discrete_map=get_color_map(df_latest['INSTNM']),
        title=f"Total R&D Expenditures ({years_range[1]})",
        labels={'rd_total': 'Total Expenditures ($)', 'INSTNM': 'Institution'}
    )
    fig1.update_layout(showlegend=False, xaxis_tickangle=-45)
    fig1 = highlight_wsu_bars(fig1)
    st.plotly_chart(fig1, width="stretch")
    
    # Trend Chart if multiple years
    if years_range[0] != years_range[1]:
        # Group by year for WSU and Peer Median
        trend_data = []
        for yr in range(years_range[0], years_range[1] + 1):
            yr_df = df_filtered[df_filtered['year'] == yr]
            if yr_df.empty: continue
            
            wsu_data = yr_df[yr_df['INSTNM'].str.contains("Wayne State", na=False)]
            wsu_val = wsu_data['rd_total'].sum() if not wsu_data.empty else None
            
            peer_data = yr_df[~yr_df['INSTNM'].str.contains("Wayne State", na=False)]
            peer_median = peer_data['rd_total'].median() if not peer_data.empty else None
            
            if wsu_val is not None:
                trend_data.append({'year': yr, 'value': wsu_val, 'group': 'Wayne State University'})
            if peer_median is not None:
                trend_data.append({'year': yr, 'value': peer_median, 'group': 'Peer Median'})
                
        if trend_data:
            df_trend = pd.DataFrame(trend_data)
            fig2 = px.line(
                df_trend, 
                x='year', 
                y='value', 
                color='group',
                color_discrete_map={'Wayne State University': WSU_GREEN, 'Peer Median': NEUTRAL_COLOR},
                title="R&D Expenditures Trend: WSU vs Peer Median",
                markers=True,
                labels={'value': 'Total Expenditures ($)', 'year': 'Year'}
            )
            fig2.update_xaxes(dtick=1)
            st.plotly_chart(fig2, width="stretch")

st.markdown("---")

# --- 5. R&D Expenditures by Source ---
st.subheader(f"R&D Expenditures by Source ({years_range[1]})")

# Create stacked bar chart for funding sources
sources = ['rd_federal', 'rd_state', 'rd_business', 'rd_nonprofit', 'rd_institution', 'rd_other']
source_names = ['Federal', 'State/Local', 'Business', 'Nonprofit', 'Institution', 'Other']

# Format for stacked bar
df_latest_sources = df_latest[['INSTNM'] + sources].melt(id_vars='INSTNM', value_vars=sources, var_name='Source', value_name='Amount')
df_latest_sources['Source'] = df_latest_sources['Source'].replace(dict(zip(sources, source_names)))

fig3 = px.bar(
    df_latest_sources,
    x='INSTNM',
    y='Amount',
    color='Source',
    title="Funding Sources Breakdown",
    labels={'Amount': 'Expenditures ($)', 'INSTNM': 'Institution'}
)
# Highlight WSU x-axis label or just use default plotly colors for sources, 
# since we can't easily color the bars by institution AND source.
fig3.update_layout(xaxis_tickangle=-45)
fig3 = highlight_wsu_bars(fig3)
st.plotly_chart(fig3, width="stretch")

st.markdown("---")

# --- 6. Personnel Headcount ---
st.subheader(f"Personnel Headcount ({years_range[1]})")

# Show Researchers vs Support Staff vs Technicians
pers_cols = ['personnel_researchers', 'personnel_support', 'personnel_technicians']
pers_names = ['Researchers (PIs)', 'Support Staff', 'Technicians']

# Create a grouped bar chart
df_pers = df_latest[['INSTNM'] + pers_cols].melt(id_vars='INSTNM', value_vars=pers_cols, var_name='Type', value_name='Headcount')
df_pers['Type'] = df_pers['Type'].replace(dict(zip(pers_cols, pers_names)))

fig4 = px.bar(
    df_pers,
    x='INSTNM',
    y='Headcount',
    color='Type',
    barmode='group',
    title="R&D Personnel Composition",
    labels={'Headcount': 'Number of Personnel', 'INSTNM': 'Institution'}
)
fig4.update_layout(xaxis_tickangle=-45)
fig4 = highlight_wsu_bars(fig4)
st.plotly_chart(fig4, width="stretch")

# Raw Data Table
with st.expander("View Raw Data"):
    st.dataframe(df_filtered)
