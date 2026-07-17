import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# WSU Colors
WSU_GREEN = "#0C5449"
WSU_GOLD = "#FFCC00"
COLOR_MAP = {
    'Star': WSU_GOLD,
    'Workhorse': WSU_GREEN,
    'Hidden Gem': '#5D9B9B',
    'Strategic Opportunity': '#808080',
    'Unknown': '#CCCCCC'
}

@st.cache_data
def load_data():
    # Cache busted to load new column names and IPEDS flags
    df = pd.read_parquet('data/wsu_cip_outcomes.parquet')
    df_soc = pd.read_parquet('data/statewide_soc_benchmarks.parquet')
    return df, df_soc

df, df_soc = load_data()

st.title("WSU Post-Graduation Outcomes BCG Matrix")
st.markdown("Evaluate WSU's Classification of Instructional Programs (CIP) against Michigan statewide labor market averages.")

# --- Sidebar Controls ---
st.sidebar.header("Controls")

timeline = st.sidebar.radio("Timeline", ["Year 1 Outcomes", "Year 5 Outcomes"])
is_y1 = timeline == "Year 1 Outcomes"

available_awards = df['Award'].dropna().unique().tolist()
default_awards = [a for a in available_awards if "Bachelor" in a or "Master" in a]
if not default_awards:
    default_awards = available_awards

selected_awards = st.sidebar.multiselect("Degree Award Level", available_awards, default=default_awards)

# Filter out aggregate 2-digit CIP families (e.g. 52.0000) to avoid double counting totals
filtered_df = df[~df['CIP Code'].astype(str).str.endswith('.0000')].copy()

# Filter by award first
filtered_df = filtered_df[filtered_df['Award'].isin(selected_awards)]

size_col = 'Total graduates (Year 1)' if is_y1 else 'Total graduates (Year 5)'

# Calculate max size based on the specific programs selected
max_size = int(filtered_df[size_col].max()) if not filtered_df.empty and not pd.isna(filtered_df[size_col].max()) else 100

# Ensure default doesn't exceed max
default_min = min(30, max_size)

# Histogram of cohort sizes
if not filtered_df.empty:
    st.sidebar.markdown("**Cohort Size Distribution**")
    fig_hist = px.histogram(
        filtered_df, 
        x=size_col, 
        nbins=20, 
        color_discrete_sequence=[WSU_GREEN]
    )
    fig_hist.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=80,
        xaxis_title=None,
        yaxis_title=None,
        xaxis=dict(showticklabels=False),
        yaxis=dict(showticklabels=False),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.sidebar.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})

cohort_range = st.sidebar.slider("Cohort Size Range", 0, max_size, (default_min, max_size))

hide_outliers = st.sidebar.checkbox("Hide Chart Outliers", value=True, help="Removes extreme values to improve axis scaling.")

search_term = st.sidebar.text_input("Search CIP Code or Title", "")

# Apply cohort size filter
filtered_df = filtered_df[(filtered_df[size_col] >= cohort_range[0]) & (filtered_df[size_col] <= cohort_range[1])]

if search_term:
    search_mask = filtered_df['CIP Code'].str.contains(search_term, case=False, na=False) | \
                  filtered_df['CIPTitle'].str.contains(search_term, case=False, na=False)
    filtered_df = filtered_df[search_mask]

# Define columns based on timeline
emp_col = '% Graduates Employed in Michigan (Year 1)' if is_y1 else '% Graduates Employed in Michigan (Year 5)'
wage_col = 'Median Graduate Salary in Michigan (Year 1)' if is_y1 else 'Median Graduate Salary in Michigan (Year 5)'
quad_col = 'Y1_Quadrant' if is_y1 else 'Y5_Quadrant'
prem_doll_col = 'Y1_Wage_Premium_$' if is_y1 else 'Y5_Wage_Premium_$'
prem_pct_col = 'Y1_Wage_Premium_%' if is_y1 else 'Y5_Wage_Premium_%'

metric_type = st.sidebar.radio("Wage Premium Metric", ["Absolute ($)", "Percentage (%)"])
y_col = prem_doll_col if metric_type == "Absolute ($)" else prem_pct_col
y_label = "Wage Premium ($)" if metric_type == "Absolute ($)" else "Wage Premium (%)"

# View 1: BCG Matrix
st.subheader("Stars & Opportunities Matrix")

if filtered_df.empty:
    st.warning("No data matches the current filters.")
else:
    # Drop NaNs for plotting
    plot_df = filtered_df.dropna(subset=[emp_col, y_col, size_col])
    
    # Calculate medians for reference lines
    median_emp = plot_df[emp_col].median()
    
    # Handle outliers if checked
    chart_df = plot_df.copy()
    if hide_outliers and not chart_df.empty:
        Q1 = chart_df[y_col].quantile(0.25)
        Q3 = chart_df[y_col].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        chart_df = chart_df[(chart_df[y_col] >= lower_bound) & (chart_df[y_col] <= upper_bound)]
    
    fig = px.scatter(
        chart_df,
        x=emp_col,
        y=y_col,
        size=size_col,
        color=quad_col,
        color_discrete_map=COLOR_MAP,
        hover_name="CIPTitle",
        hover_data={
            "CIP Code": True,
            "Award": True,
            size_col: ":,.0f",
            wage_col: ":$,.0f",
            "State_Annual_Entry_Wage": ":$,.0f",
            emp_col: ":.1%",
            y_col: ":$,.0f" if metric_type == "Absolute ($)" else ":.1%",
            quad_col: False
        },
        labels={
            emp_col: "WSU % Graduates Employed in Michigan",
            y_col: y_label,
            size_col: "Total Graduates"
        },
        title=f"WSU CIP Performance ({timeline})"
    )
    
    fig.add_vline(x=median_emp, line_dash="dash", line_color="gray", annotation_text=f"Median Emp: {median_emp:.1%}")
    fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="Break-even Premium")
    
    if metric_type == "Absolute ($)":
        fig.update_layout(yaxis_tickformat="$,.0f")
    else:
        fig.update_layout(yaxis_tickformat=".1%")
        
    fig.update_layout(xaxis_tickformat=".0%", height=600)
    st.plotly_chart(fig, use_container_width=True)

# View 2: Quadrant Deep-Dive
st.markdown("---")
st.subheader("Quadrant Deep-Dive & Data Explorer")

if not filtered_df.empty:
    quad_counts = filtered_df.groupby(quad_col)[size_col].sum().fillna(0)
    ghost_students = int(filtered_df[filtered_df['is_underrepresented']]['IPEDS_Total_Degrees'].sum())
    
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("⭐ Stars Students", int(quad_counts.get("Star", 0)))
    with c2:
        st.metric("🚜 Workhorses", int(quad_counts.get("Workhorse", 0)))
    with c3:
        st.metric("💎 Hidden Gems", int(quad_counts.get("Hidden Gem", 0)))
    with c4:
        st.metric("🌱 Opportunities", int(quad_counts.get("Strategic Opportunity", 0)))
    with c5:
        st.metric("👻 Ghost Degrees", ghost_students, help="High-wage degrees produced by WSU (per IPEDS) that are largely missing or suppressed in Pathfinder tracking.")

    st.markdown("### Data Explorer")
    quad_filter = st.selectbox("Filter by Quadrant", ["All"] + list(COLOR_MAP.keys()))
    
    display_df = filtered_df.copy()
    if quad_filter != "All":
        display_df = display_df[display_df[quad_col] == quad_filter]
        
    display_cols = [
        'CIP Code', 'CIPTitle', 'Award', size_col, 'IPEDS_Total_Degrees', emp_col, wage_col, 
        'State_Annual_Entry_Wage', prem_doll_col, prem_pct_col, quad_col, 'is_suppressed', 'is_underrepresented'
    ]
    
    # Download button
    csv = display_df[display_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        "Download Data as CSV",
        csv,
        "wsu_outcomes_data.csv",
        "text/csv",
        key='download-csv'
    )
    
    def highlight_underrepresented(row):
        color = 'background-color: rgba(255, 69, 0, 0.2)' if row.get('is_underrepresented', False) else ''
        return [color] * len(row)
    
    st.dataframe(display_df[display_cols].style.apply(highlight_underrepresented, axis=1).format({
        emp_col: "{:.1%}",
        wage_col: "${:,.0f}",
        'State_Annual_Entry_Wage': "${:,.0f}",
        prem_doll_col: "${:,.0f}",
        prem_pct_col: "{:.1%}",
        size_col: "{:,.0f}",
        'IPEDS_Total_Degrees': "{:,.0f}"
    }), use_container_width=True)

# View 3: SOC Alignment Inspector
st.markdown("---")
st.subheader("CIP to SOC Alignment Inspector")
st.markdown("Drill down into specific CIPs to see the underlying SOC occupations and their statewide wages.")

if not filtered_df.empty:
    wsu_cips = filtered_df['CIP Code'].dropna().unique()
    available_socs = df_soc[df_soc['CIP2020Code'].isin(wsu_cips)]
    
    if not available_socs.empty:
        cip_options = available_socs[['CIP2020Code', 'CIP2020Title']].drop_duplicates()
        cip_options['Display'] = cip_options['CIP2020Code'] + " - " + cip_options['CIP2020Title']
        
        selected_cip_display = st.selectbox("Select a CIP Code", cip_options['Display'])
        selected_cip_code = selected_cip_display.split(" - ")[0]
        
        wsu_actuals = filtered_df[filtered_df['CIP Code'] == selected_cip_code]
        if not wsu_actuals.empty:
            st.markdown(f"**WSU Outcomes for {selected_cip_display}**")
            st.dataframe(wsu_actuals[['Award', size_col, emp_col, wage_col]].style.format({
                emp_col: "{:.1%}",
                wage_col: "${:,.0f}",
                size_col: "{:,.0f}"
            }))
        
        st.markdown("**Underlying Target Occupations (SOC) in Michigan**")
        soc_drilldown = available_socs[available_socs['CIP2020Code'] == selected_cip_code]
        st.dataframe(soc_drilldown[['SOC2018Code', 'Occupation', 'State_Annual_Entry_Wage', 'State_Annual_Median_Wage']].style.format({
            'State_Annual_Entry_Wage': "${:,.0f}",
            'State_Annual_Median_Wage': "${:,.0f}"
        }), use_container_width=True)
    else:
        st.info("No SOC mapping data available for the selected filters.")
