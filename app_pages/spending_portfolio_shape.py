import streamlit as st
import pandas as pd
import duckdb
import os
import altair as alt

# --- PAGE CONFIGURATION ---
# Note: Page config is set in app.py globally, but we specify the font and style inline.

# --- CUSTOM CSS FOR PREMIUM LOOK (GLASSMORPHISM & TYPOGRAPHY) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

/* Apply modern typography */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif;
}

/* Info container styling */
.info-card {
    background: rgba(12, 84, 73, 0.05); /* WSU Green Light Tint */
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

PEER_FRAMES = {
    "Frame A: Michigan Publics (MASU)": {
        "name": "Michigan Public Universities",
        "ids": [169248, 169798, 169910, 170082, 170639, 171100, 171128, 171456, 171571, 172051, 170976, 171137, 171146, 172644, 172699]
    },
    "Frame B: Urban Peer Publics": {
        "name": "Urban Peer Publics",
        "ids": [172644, 133951, 225511, 201885, 139940, 216339, 234030, 157289, 187985, 145600, 100663]
    }
}

ALL_PEER_IDS = list(set(
    PEER_FRAMES["Frame A: Michigan Publics (MASU)"]["ids"] + 
    PEER_FRAMES["Frame B: Urban Peer Publics"]["ids"]
))

YEAR_MAPS = {
    2020: {"drvf": "drvf2020.parquet", "raw_gasb": "f1920_f1a.parquet"},
    2021: {"drvf": "drvf2021.parquet", "raw_gasb": "f2021_f1a.parquet"},
    2022: {"drvf": "drvf2022.parquet", "raw_gasb": "f2122_f1a.parquet"},
    2023: {"drvf": "drvf2023.parquet", "raw_gasb": "f2223_f1a.parquet"},
    2024: {"drvf": "drvf2024.parquet", "raw_gasb": "f2324_f1a.parquet"}
}

# --- CACHED DATA LOADER ---
@st.cache_data(ttl=3600)
def load_portfolio_data():
    ids_sql = ", ".join(map(str, ALL_PEER_IDS))
    dfs = []
    
    # 1. Load names and characteristics from hd2024
    hd_path = "data/raw/ipeds/hd2024.parquet"
    if os.path.exists(hd_path):
        hd_df = duckdb.query(f"SELECT UNITID, INSTNM, STABBR FROM '{hd_path}' WHERE UNITID IN ({ids_sql})").df()
        hd_df.columns = hd_df.columns.str.upper()
    else:
        hd_df = pd.DataFrame({
            'UNITID': ALL_PEER_IDS, 
            'INSTNM': [f"Institution {x}" for x in ALL_PEER_IDS], 
            'STABBR': 'US'
        })
    
    # Ensure keys match types
    hd_df['UNITID'] = hd_df['UNITID'].astype(int)
        
    for year, files in YEAR_MAPS.items():
        drvf_path = f"data/raw/ipeds/{files['drvf']}"
        raw_gasb_path = f"data/raw/ipeds/{files['raw_gasb']}"
        
        if not os.path.exists(drvf_path):
            continue
            
        # Load derived table metrics
        drvf_df = duckdb.query(f"SELECT * FROM '{drvf_path}' WHERE UNITID IN ({ids_sql})").df()
        drvf_df.columns = drvf_df.columns.str.upper()
        
        # Load raw GASB for F1C19OM (Operations & Maintenance total)
        raw_om_map = {}
        if os.path.exists(raw_gasb_path):
            try:
                om_df = duckdb.query(f"SELECT UNITID, F1C19OM FROM '{raw_gasb_path}' WHERE UNITID IN ({ids_sql})").df()
                om_df.columns = om_df.columns.str.upper()
                raw_om_map = {int(k): float(v) for k, v in zip(om_df['UNITID'], om_df['F1C19OM']) if pd.notna(v)}
            except Exception:
                pass
                
        for _, row in drvf_df.iterrows():
            unitid = int(row['UNITID'])
            is_gasb = pd.notna(row.get('F1COREXP')) and row.get('F1COREXP') > 0
            
            if is_gasb:
                core_exp = float(row.get('F1COREXP', 0))
                instruction = float(row.get('F1INSTPC', 0))
                research = float(row.get('F1RSRCPC', 0))
                public_service = float(row.get('F1PBSVPC', 0))
                academic_support = float(row.get('F1ACSPPC', 0))
                student_services = float(row.get('F1STSVPC', 0))
                institutional_support = float(row.get('F1INSUPC', 0))
                other_core = float(row.get('F1OTEXPC', 0))
                
                raw_om = raw_om_map.get(unitid, 0.0)
                om_share = (raw_om / core_exp * 100.0) if core_exp > 0 else 0.0
                reporting = 'GASB'
            else:
                core_exp = float(row.get('F2COREXP', 0))
                instruction = float(row.get('F2INSTPC', 0))
                research = float(row.get('F2RSRCPC', 0))
                public_service = float(row.get('F2PBSVPC', 0))
                academic_support = float(row.get('F2ACSPPC', 0))
                student_services = float(row.get('F2STSVPC', 0))
                institutional_support = float(row.get('F2INSUPC', 0))
                other_core = float(row.get('F2OTEXPC', 0))
                
                om_share = None # FASB doesn't report separate O&M
                reporting = 'FASB'
                
            dfs.append({
                'UNITID': unitid,
                'YEAR': year,
                'REPORTING': reporting,
                'CORE_EXPENSES': core_exp,
                'Instruction': instruction,
                'Research': research,
                'Public Service': public_service,
                'Academic Support': academic_support,
                'Student Services': student_services,
                'Institutional Support': institutional_support,
                'Other Core Expenses': other_core,
                'O&M Share (Contextual)': om_share
            })
            
    if not dfs:
        return pd.DataFrame()
        
    df_metrics = pd.DataFrame(dfs)
    df_metrics['UNITID'] = df_metrics['UNITID'].astype(int)
    
    df_merged = df_metrics.merge(hd_df, on='UNITID', how='inner')
    return df_merged

# --- LOAD DATA ---
with st.spinner("Loading portfolio finance data..."):
    df_all = load_portfolio_data()

# --- TITLE SECTION ---
st.title("🎓 Spending Portfolio Shape Analysis")

# --- SIDEBAR FILTERS ---
st.sidebar.header("Peer & Analysis Settings")

# 1. Peer Frame Toggle
selected_frame_key = st.sidebar.selectbox(
    "Select Peer Frame",
    options=list(PEER_FRAMES.keys())
)
active_frame = PEER_FRAMES[selected_frame_key]
active_ids = active_frame["ids"]
active_name = active_frame["name"]

# Filter data to active frame
df_frame = df_all[df_all['UNITID'].isin(active_ids)].copy()

# Add a subtitle immediately below title conforming to guidelines
st.caption(f"#### Scope: {active_name} · Years: FY2020–FY2024 · Metrics: Functional expense as % of core expenses")

# 2. Select Individual Peers for direct line comparison
all_peers_in_frame = sorted(
    df_frame[df_frame['UNITID'] != WSU_UNITID]['INSTNM'].unique().tolist()
)
selected_peers_names = st.sidebar.multiselect(
    "Direct Comparison Peers",
    options=all_peers_in_frame,
    help="Select specific peer institutions to draw their individual trend lines on the chart."
)
selected_peers_ids = df_frame[df_frame['INSTNM'].isin(selected_peers_names)]['UNITID'].unique().tolist()

# 3. Style Guide Provenance Note in Sidebar
st.sidebar.markdown("""
---
**Definitions & Sources:**
- **Data Source:** NCES [IPEDS Finance Survey](https://nces.ed.gov/ipeds/) (GASB: Table `F1A`, FASB: Table `F2`) and derived metrics.
- **Reporting Scope:** Core expenses only. **Hospitals, auxiliary enterprises, and independent operations are excluded** to ensure comparable benchmarks.
- **O&M Allocation:** Per NCES standard (since FY2017), Operations & Maintenance (O&M) costs are pre-allocated across functional categories. O&M shares shown are for context and represent total O&M as % of Core.
- **Comparison Warning:** Functional classifications are institution-coded and subject to accounting differences. Treat differences under **~2 percentage points** as structural noise rather than signal.
- **Neutral Interpretation:** Institutional support shares represent structural/management footprints; compare neutrally as orientation rather than absolute efficiency judgment.
""")

# Check if data exists
if df_frame.empty:
    st.warning("No data found for the selected peer set. Please verify local parquet files in data/raw/ipeds/.")
else:
    # Check for FASB schools in active set to show notification
    fasb_schools = df_frame[df_frame['REPORTING'] == 'FASB']['INSTNM'].unique().tolist()
    if fasb_schools:
        st.info(f"💡 **FASB Reporting Standard Note:** The peer set includes **{', '.join(fasb_schools)}** which reports under FASB. Standardized derived core expense shares are mapped automatically. Operations & Maintenance (O&M) is pre-allocated and cannot be separated for FASB reporting; O&M contextual charts will exclude these schools.")

    # --- TABS CREATION ---
    tab_trends, tab_shape, tab_data = st.tabs([
        "📈 Spending Portfolio Trend (by Category)",
        "📊 Full Portfolio Shape Comparison",
        "📄 Tabular Share Data & Export"
    ])

    categories = [
        "Instruction",
        "Research",
        "Public Service",
        "Academic Support",
        "Student Services",
        "Institutional Support",
        "Other Core Expenses",
        "O&M Share (Contextual)"
    ]

    with tab_trends:
        st.subheader("Functional Expense Shares Over Time")
        st.markdown("Analyze how the proportion of core budget spent on a selected category has evolved over the last 5 years. The shaded area represents the middle 50% (25th to 75th percentiles) of the peer distribution.")

        selected_cat = st.selectbox(
            "Select Expense Category to Trend",
            options=categories
        )

        # Prepare trend statistics for the peer set (excluding WSU)
        df_peers_only = df_frame[(df_frame['UNITID'] != WSU_UNITID) & (df_frame[selected_cat].notna())]
        
        # Calculate stats per year
        stats_list = []
        for year in sorted(df_frame['YEAR'].unique()):
            year_data = df_peers_only[df_peers_only['YEAR'] == year][selected_cat]
            if not year_data.empty:
                stats_list.append({
                    'YEAR': year,
                    'Min': float(year_data.min()),
                    'P25': float(year_data.quantile(0.25)),
                    'Median': float(year_data.median()),
                    'P75': float(year_data.quantile(0.75)),
                    'Max': float(year_data.max())
                })
        df_peer_stats = pd.DataFrame(stats_list)

        # WSU data
        df_wsu = df_frame[(df_frame['UNITID'] == WSU_UNITID) & (df_frame[selected_cat].notna())][['YEAR', selected_cat, 'INSTNM']]

        # Selected peers data
        df_selected_peers = df_frame[(df_frame['UNITID'].isin(selected_peers_ids)) & (df_frame[selected_cat].notna())][['YEAR', selected_cat, 'INSTNM', 'UNITID']]

        if df_peer_stats.empty:
            st.warning("Insufficient data to plot trend line for this category.")
        else:
            # Build Altair Chart
            # 1. Peer Shaded Band (25th to 75th percentiles)
            band = alt.Chart(df_peer_stats).mark_area(opacity=0.2, color='#818cf8').encode(
                x=alt.X('YEAR:O', title="Fiscal Year"),
                y=alt.Y('P25:Q', title=f"{selected_cat} (% of Core Expenses)"),
                y2=alt.Y2('P75:Q'),
                tooltip=[
                    alt.Tooltip('YEAR:O', title="Year"),
                    alt.Tooltip('P25:Q', title="25th Percentile", format=".1f"),
                    alt.Tooltip('P75:Q', title="77th Percentile", format=".1f")
                ]
            )

            # 2. Peer Median Line
            median_line = alt.Chart(df_peer_stats).mark_line(strokeDash=[4, 4], color='#4f46e5', strokeWidth=1.5).encode(
                x='YEAR:O',
                y='Median:Q',
                tooltip=[
                    alt.Tooltip('YEAR:O', title="Year"),
                    alt.Tooltip('Median:Q', title="Peer Median", format=".1f")
                ]
            )

            # 3. WSU Line (Target Bold Highlight)
            wsu_chart = alt.Chart(df_wsu).mark_line(color='#0C5449', strokeWidth=4).encode(
                x='YEAR:O',
                y=f'{selected_cat}:Q',
                tooltip=[
                    alt.Tooltip('INSTNM:N', title="Institution"),
                    alt.Tooltip('YEAR:O', title="Year"),
                    alt.Tooltip(f'{selected_cat}:Q', title="Share %", format=".1f")
                ]
            )
            wsu_points = alt.Chart(df_wsu).mark_point(color='#0C5449', size=90, filled=True, shape='diamond').encode(
                x='YEAR:O',
                y=f'{selected_cat}:Q'
            )

            # Combine elements
            chart_list = [band, median_line, wsu_chart, wsu_points]

            # 4. Individual Peer Lines (Direct Comparison)
            if not df_selected_peers.empty:
                peer_lines = alt.Chart(df_selected_peers).mark_line(opacity=0.7, strokeWidth=2).encode(
                    x='YEAR:O',
                    y=f'{selected_cat}:Q',
                    color=alt.Color('INSTNM:N', legend=alt.Legend(title="Direct Comparison Peers")),
                    strokeDash=alt.StrokeDash('INSTNM:N', legend=alt.Legend(title="Direct Comparison Peers")),
                    tooltip=[
                        alt.Tooltip('INSTNM:N', title="Institution"),
                        alt.Tooltip('YEAR:O', title="Year"),
                        alt.Tooltip(f'{selected_cat}:Q', title="Share %", format=".1f")
                    ]
                )
                peer_points = alt.Chart(df_selected_peers).mark_point(filled=True, size=60).encode(
                    x='YEAR:O',
                    y=f'{selected_cat}:Q',
                    color=alt.Color('INSTNM:N', legend=alt.Legend(title="Direct Comparison Peers")),
                    shape=alt.Shape('INSTNM:N', legend=alt.Legend(title="Direct Comparison Peers")),
                    tooltip=[
                        alt.Tooltip('INSTNM:N', title="Institution"),
                        alt.Tooltip('YEAR:O', title="Year"),
                        alt.Tooltip(f'{selected_cat}:Q', title="Share %", format=".1f")
                    ]
                )
                chart_list.extend([peer_lines, peer_points])

            # Create interactive final chart
            chart = alt.layer(*chart_list).properties(
                height=450,
                title=f"WSU vs Peer {selected_cat} Share Trend"
            ).resolve_scale(y='shared')

            st.altair_chart(chart, use_container_width=True)

            with st.expander("♿ Accessible Data Table - Share Trend Details"):
                df_trend_pivot = df_frame.pivot(index='YEAR', columns='INSTNM', values=selected_cat)
                cols_ordered = ['Wayne State University'] + [c for c in df_trend_pivot.columns if c != 'Wayne State University']
                cols_ordered = [c for c in cols_ordered if c in df_trend_pivot.columns]
                st.dataframe(
                    df_trend_pivot[cols_ordered],
                    width="stretch"
                )
            
            # Interactive legend details
            st.markdown("""
            * **Bold Green Diamond Line:** Wayne State University (Target)
            * **Blue Dashed Line:** Peer Group Median
            * **Shaded Blue Area:** Peer Group 25th to 75th Percentile Band (Middle 50% of schools)
            """)

    with tab_shape:
        st.subheader("Spending Portfolio Shape Comparison")
        st.markdown("Compare the entire 'shape' of WSU's spending portfolio against the peer group's median spending portfolio. This visualizes budget prioritization rather than overall spending levels.")

        selected_year = st.selectbox(
            "Select Fiscal Year for Comparison",
            options=sorted(df_frame['YEAR'].unique(), reverse=True)
        )

        # Filter data to selected year
        df_year = df_frame[df_frame['YEAR'] == selected_year].copy()
        
        # 1. Calculate WSU values for that year
        df_wsu_year = df_year[df_year['UNITID'] == WSU_UNITID]
        
        # 2. Calculate Peer Medians for that year
        df_peers_year = df_year[df_year['UNITID'] != WSU_UNITID]
        
        if df_wsu_year.empty:
            st.warning(f"No WSU data available for year {selected_year}.")
        else:
            wsu_data = []
            peer_data = []
            
            # Exclude O&M from the 100% stack since it is pre-allocated
            core_categories = [c for c in categories if "O&M" not in c]
            
            for cat in core_categories:
                # WSU
                wsu_val = float(df_wsu_year[cat].values[0]) if not df_wsu_year[cat].empty and pd.notna(df_wsu_year[cat].values[0]) else 0.0
                wsu_data.append({
                    'Category': cat,
                    'Share %': wsu_val,
                    'Group': 'Wayne State University'
                })
                
                # Peer Median
                peer_vals = df_peers_year[cat].dropna()
                peer_median = float(peer_vals.median()) if not peer_vals.empty else 0.0
                peer_data.append({
                    'Category': cat,
                    'Share %': peer_median,
                    'Group': f'Peer Medians ({active_name})'
                })
                
            df_plot = pd.DataFrame(wsu_data + peer_data)

            # Render Grouped Bar Chart
            bar_chart = alt.Chart(df_plot).mark_bar().encode(
                x=alt.X('Group:N', title=None, axis=alt.Axis(labels=False)),
                y=alt.Y('Share %:Q', title="Share of Core Expenses (%)", scale=alt.Scale(domain=[0, 100])),
                color=alt.Color('Group:N', scale=alt.Scale(domain=['Wayne State University', f'Peer Medians ({active_name})'], range=['#0C5449', '#FFCC33']), legend=alt.Legend(title="Portfolio Group")),
                column=alt.Column('Category:N', title="Functional Expense Category", header=alt.Header(labelOrient='bottom', titleOrient='bottom', labelAngle=-45, labelPadding=10)),
                tooltip=[
                    alt.Tooltip('Group:N', title="Group"),
                    alt.Tooltip('Category:N', title="Category"),
                    alt.Tooltip('Share %:Q', title="Share %", format=".1f")
                ]
            ).properties(
                height=350,
                width=100
            )

            # Redundant encoding: add text labels on top of bars
            bar_text = bar_chart.mark_text(
                align='center',
                baseline='bottom',
                dy=-3,
                fontSize=9,
                fontWeight='bold'
            ).encode(
                text=alt.Text('Share %:Q', format='.1f')
            )

            final_bar_chart = (bar_chart + bar_text)
            st.altair_chart(final_bar_chart)

            # Accessible Data Fallback expander
            with st.expander("♿ Accessible Data Table - Portfolio Shape Comparison"):
                df_pivot_shape = df_plot.pivot(index='Category', columns='Group', values='Share %')
                st.dataframe(
                    df_pivot_shape,
                    column_config={
                        "Category": "Expense Category",
                        "Wayne State University": st.column_config.NumberColumn("Wayne State (%)", format="%.1f%%"),
                        f"Peer Medians ({active_name})": st.column_config.NumberColumn("Peer Median (%)", format="%.1f%%")
                    },
                    width="stretch"
                )
            
            st.info("💡 **Interpretation:** The chart above shows how Wayne State University slices its 'core budget pie' across departments compared to the average peer. A higher bar indicates a higher relative priority placed on that function, independent of the institution's overall budget size.")

    with tab_data:
        st.subheader("Tabular Spending Shares (%)")
        st.markdown("Inspect and export the underlying raw shares for all institutions in the active peer frame.")
        
        # Format the dataframe for display
        df_display = df_frame.copy()
        df_display = df_display.sort_values(['YEAR', 'INSTNM'], ascending=[False, True])
        
        columns_to_show = [
            'YEAR', 'INSTNM', 'REPORTING', 'CORE_EXPENSES',
            'Instruction', 'Research', 'Public Service', 'Academic Support', 
            'Student Services', 'Institutional Support', 'Other Core Expenses', 
            'O&M Share (Contextual)'
        ]
        
        st.dataframe(
            df_display[columns_to_show],
            column_config={
                "YEAR": "Year",
                "INSTNM": "Institution",
                "REPORTING": "Standard",
                "CORE_EXPENSES": st.column_config.NumberColumn("Core Expenses ($)", format="$%,.0f"),
                "Instruction": st.column_config.NumberColumn("Instruction (%)", format="%.1f%%"),
                "Research": st.column_config.NumberColumn("Research (%)", format="%.1f%%"),
                "Public Service": st.column_config.NumberColumn("Public Service (%)", format="%.1f%%"),
                "Academic Support": st.column_config.NumberColumn("Academic Support (%)", format="%.1f%%"),
                "Student Services": st.column_config.NumberColumn("Student Services (%)", format="%.1f%%"),
                "Institutional Support": st.column_config.NumberColumn("Institutional Support (%)", format="%.1f%%"),
                "Other Core Expenses": st.column_config.NumberColumn("Other Core (%)", format="%.1f%%"),
                "O&M Share (Contextual)": st.column_config.NumberColumn("O&M Share (%)", format="%.1f%%")
            },
            hide_index=True,
            width="stretch"
        )
        
        # CSV Export
        csv_data = df_display[columns_to_show].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Table as CSV",
            data=csv_data,
            file_name=f"ipeds_expenditure_shares_{active_name.lower().replace(' ', '_')}.csv",
            mime="text/csv"
        )
