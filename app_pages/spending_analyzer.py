import streamlit as st
import pandas as pd
from google.cloud import bigquery

# Removed st.set_page_config as it is now in app.py

# Cache BigQuery Client
@st.cache_resource
def get_bq_client():
    return bigquery.Client()

client = get_bq_client()

# Academic Year Configuration matching the MS Access database tables
YEARS_CONFIG = {
    "2024-25 (Provisional)": {
        "hd": "hd2024",
        "ef": "drvef122024",
        "f1": "f2324_f1a",
        "f2": "f2324_f2",
        "f3": "f2324_f3"
    },
    "2023-24": {
        "hd": "hd2023",
        "ef": "drvef122023",
        "f1": "f2223_f1a",
        "f2": "f2223_f2",
        "f3": "f2223_f3"
    },
    "2022-23": {
        "hd": "hd2022",
        "ef": "drvef122022",
        "f1": "f2122_f1a",
        "f2": "f2122_f2",
        "f3": "f2122_f3"
    },
    "2021-22": {
        "hd": "hd2021",
        "ef": "drvef122021",
        "f1": "f2021_f1a",
        "f2": "f2021_f2",
        "f3": "f2021_f3"
    },
    "2020-21": {
        "hd": "hd2020",
        "ef": "drvef122020",
        "f1": "f1920_f1a",
        "f2": "f1920_f2",
        "f3": "f1920_f3"
    },
    "2019-20": {
        "hd": "hd2019",
        "ef": "drvef122019",
        "f1": "f1819_f1a",
        "f2": "f1819_f2",
        "f3": "f1819_f3"
    }
}

@st.cache_resource
def get_available_years():
    """Detect which years have all required tables in BigQuery."""
    try:
        tables = [t.table_id.lower() for t in client.list_tables("ipeds")]
        available_years = []
        for year, config in YEARS_CONFIG.items():
            if (config['hd'].lower() in tables and 
                config['ef'].lower() in tables and 
                config['f1'].lower() in tables and 
                config['f2'].lower() in tables and 
                config['f3'].lower() in tables):
                available_years.append(year)
        if not available_years:
            return list(YEARS_CONFIG.keys())
        return available_years
    except Exception as e:
        return list(YEARS_CONFIG.keys())

available_years = get_available_years()

# 2. Custom Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

/* Apply modern typography */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif;
}

/* Metric Cards Layout */
.kpi-container {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-bottom: 30px;
}

.kpi-card {
    flex: 1;
    min-width: 220px;
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
    transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}

.kpi-card:hover {
    transform: translateY(-5px);
    border-color: rgba(99, 102, 241, 0.4);
    box-shadow: 0 10px 30px rgba(99, 102, 241, 0.15);
}

.kpi-title {
    font-size: 13px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}

.kpi-value {
    font-size: 32px;
    font-weight: 700;
    background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
</style>
""", unsafe_allow_html=True)

# Title Section
st.title("🎓 Higher Education Spending Analyzer")
st.markdown("Compare and analyze spending on **Instruction**, **Academic Support**, and **Student Services** per FTE student using the full IPEDS Access Database records.")

# 3. Sidebar Filter Configuration
st.sidebar.header("Filter Settings")

# Academic Year Selection
selected_year = st.sidebar.selectbox("Academic Year", available_years, index=0)
year_config = YEARS_CONFIG[selected_year]

st.sidebar.subheader("Control of Institution")
show_public = st.sidebar.checkbox("Public", value=True)
show_private = st.sidebar.checkbox("Private (FASB)", value=True)

st.sidebar.subheader("Carnegie Classification")
show_r1 = st.sidebar.checkbox("R1 (Very High Research)", value=True)
show_r2 = st.sidebar.checkbox("R2 (High Research)", value=True)

st.sidebar.subheader("Location")
urban_only = st.sidebar.toggle("Urban Schools Only", value=False)

# Mappings from Data Dictionary
CONTROL_MAP = {
    1: "Public",
    2: "Private Not-for-Profit",
    3: "Private For-Profit"
}

CARNEGIE_MAP = {
    15: "R1 (Very High Research)",
    16: "R2 (High Research)"
}

LOCALE_MAP = {
    11: "City: Large",
    12: "City: Midsize",
    13: "City: Small",
    21: "Suburb: Large",
    22: "Suburb: Midsize",
    23: "Suburb: Small",
    31: "Town: Fringe",
    32: "Town: Distant",
    33: "Town: Remote",
    41: "Rural: Fringe",
    42: "Rural: Distant",
    43: "Rural: Remote"
}

# Resolve selected lists for SQL query
controls = []
if show_public:
    controls.append(1)
if show_private:
    controls.extend([2, 3])

carnegies = []
if show_r1:
    carnegies.append(15)
if show_r2:
    carnegies.append(16)

# 4. Fetch and Process Data
@st.cache_data(ttl=600)
def load_spending_data(year_cfg, controls_list, carnegies_list, filter_urban):
    if not controls_list or not carnegies_list:
        return pd.DataFrame()
        
    controls_str = ", ".join(map(str, controls_list))
    carnegies_str = ", ".join(map(str, carnegies_list))
    
    hd_table = f"ipeds.{year_cfg['hd']}"
    ef_table = f"ipeds.{year_cfg['ef']}"
    f1_table = f"ipeds.{year_cfg['f1']}"
    f2_table = f"ipeds.{year_cfg['f2']}"
    f3_table = f"ipeds.{year_cfg['f3']}"
    
    query = f"""
    SELECT
      h.UNITID,
      h.INSTNM,
      h.CONTROL,
      h.C21BASIC,
      h.LOCALE,
      e.FTE12MN as fte_enrollment,
      COALESCE(f1.F1C011, f2.F2E011, f3.F3E011) as spend_instruction,
      COALESCE(f1.F1C051, f2.F2E041, f3.F3E03A1) as spend_academic_support,
      COALESCE(f1.F1C061, f2.F2E051, f3.F3E03B1) as spend_student_services
    FROM `{hd_table}` h
    LEFT JOIN `{ef_table}` e ON h.UNITID = e.UNITID
    LEFT JOIN `{f1_table}` f1 ON h.UNITID = f1.UNITID
    LEFT JOIN `{f2_table}` f2 ON h.UNITID = f2.UNITID
    LEFT JOIN `{f3_table}` f3 ON h.UNITID = f3.UNITID
    WHERE h.CONTROL IN ({controls_str})
      AND h.C21BASIC IN ({carnegies_str})
      AND e.FTE12MN IS NOT NULL
      AND e.FTE12MN > 0
    """
    
    if filter_urban:
        query += " AND h.LOCALE IN (11, 12, 13)"
        
    try:
        df = client.query(query).to_dataframe()
        return df
    except Exception as e:
        st.error(f"Failed to query BigQuery tables ({hd_table}, etc.): {e}")
        return pd.DataFrame()

# Load data
with st.spinner(f"Fetching BigQuery records for {selected_year}..."):
    df_raw = load_spending_data(year_config, controls, carnegies, urban_only)

# Tabs Navigation
tab_summary, tab_trends, tab_dictionary = st.tabs([
    "📊 Spending Analyzer", 
    "📈 Trend Analysis", 
    "📖 Data Dictionary"
])

# Process raw dataset
if not df_raw.empty:
    df = df_raw.copy()
    
    # Calculate ratios (Dollars per FTE student)
    df['Instruction per FTE'] = df['spend_instruction'] / df['fte_enrollment']
    df['Academic Support per FTE'] = df['spend_academic_support'] / df['fte_enrollment']
    df['Student Services per FTE'] = df['spend_student_services'] / df['fte_enrollment']
    
    # Translate codes to human-readable strings
    df['Control'] = df['CONTROL'].map(CONTROL_MAP).fillna("Unknown")
    df['Carnegie'] = df['C21BASIC'].map(CARNEGIE_MAP).fillna("Other")
    df['Locale'] = df['LOCALE'].map(LOCALE_MAP).fillna("Unknown")

with tab_summary:
    if df_raw.empty:
        st.warning("No data found matching the selected filters. Please verify you selected at least one Control type and Carnegie Classification.")
    else:
        # Aggregate values for KPI cards
        total_schools = len(df)
        total_fte = df['fte_enrollment'].sum()
        
        overall_inst_fte = df['spend_instruction'].sum() / total_fte if total_fte > 0 else 0
        overall_acad_fte = df['spend_academic_support'].sum() / total_fte if total_fte > 0 else 0
        overall_stud_fte = df['spend_student_services'].sum() / total_fte if total_fte > 0 else 0
        
        # 6. Render KPI Cards
        st.markdown(
            f"""
            <div class="kpi-container">
                <div class="kpi-card">
                    <div class="kpi-title">Institutions</div>
                    <div class="kpi-value">{total_schools:,}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Instruction / FTE</div>
                    <div class="kpi-value">${overall_inst_fte:,.2f}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Academic Support / FTE</div>
                    <div class="kpi-value">${overall_acad_fte:,.2f}</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-title">Student Services / FTE</div>
                    <div class="kpi-value">${overall_stud_fte:,.2f}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Top 10 institutions by Instruction Spend per FTE Chart
        st.subheader("🏆 Top 10 Spending Institutions (Instruction per FTE)")
        top_10 = df.nlargest(10, 'Instruction per FTE')
        chart_data = top_10.set_index('INSTNM')[['Instruction per FTE', 'Academic Support per FTE', 'Student Services per FTE']]
        st.bar_chart(chart_data)
        
        # Render Dataframe
        st.subheader("📊 Institutional Spending Details")
        st.markdown("Showing individual institution spend totals and spending-per-FTE ratios.")
        
        display_cols = [
            "INSTNM",
            "Control",
            "Carnegie",
            "Locale",
            "fte_enrollment",
            "spend_instruction",
            "spend_academic_support",
            "spend_student_services",
            "Instruction per FTE",
            "Academic Support per FTE",
            "Student Services per FTE"
        ]
        
        st.dataframe(
            df[display_cols],
            column_config={
                "INSTNM": st.column_config.TextColumn("Institution Name", width="medium"),
                "Control": "Control",
                "Carnegie": "Carnegie Classification",
                "Locale": "Locale",
                "fte_enrollment": st.column_config.NumberColumn("FTE Students", format="%d"),
                "spend_instruction": st.column_config.NumberColumn("Instruction Spend ($)", format="$%,d"),
                "spend_academic_support": st.column_config.NumberColumn("Academic Support Spend ($)", format="$%,d"),
                "spend_student_services": st.column_config.NumberColumn("Student Services Spend ($)", format="$%,d"),
                "Instruction per FTE": st.column_config.NumberColumn("Instruction per FTE ($)", format="$%,.2f"),
                "Academic Support per FTE": st.column_config.NumberColumn("Academic Support per FTE ($)", format="$%,.2f"),
                "Student Services per FTE": st.column_config.NumberColumn("Student Services per FTE ($)", format="$%,.2f"),
            },
            hide_index=True,
            width="stretch"
        )

with tab_trends:
    st.subheader("📈 Multi-Year Spending Trends")
    st.markdown("Compare selected institutions' spending metrics historically over multiple academic years.")
    
    if df_raw.empty:
        st.info("Please verify data exists for the selected year filter to populate trend analysis options.")
    else:
        # User select institutions to track trends
        trend_schools = st.multiselect(
            "Select Institutions to Plot",
            options=sorted(df['INSTNM'].unique()),
            default=sorted(df['INSTNM'].unique())[:3]
        )
        
        if trend_schools:
            selected_ids = df[df['INSTNM'].isin(trend_schools)]['UNITID'].tolist()
            selected_ids_str = ", ".join(map(str, selected_ids))
            
            # Fetch data across all available years
            trend_queries = []
            for y_name in available_years:
                cfg = YEARS_CONFIG[y_name]
                trend_queries.append(f"""
                SELECT
                  '{y_name}' as academic_year,
                  h.INSTNM,
                  e.FTE12MN as fte_enrollment,
                  COALESCE(f1.F1C011, f2.F2E011, f3.F3E011) as spend_instruction,
                  COALESCE(f1.F1C051, f2.F2E041, f3.F3E03A1) as spend_academic_support,
                  COALESCE(f1.F1C061, f2.F2E051, f3.F3E03B1) as spend_student_services
                FROM `ipeds.{cfg['hd']}` h
                LEFT JOIN `ipeds.{cfg['ef']}` e ON h.UNITID = e.UNITID
                LEFT JOIN `ipeds.{cfg['f1']}` f1 ON h.UNITID = f1.UNITID
                LEFT JOIN `ipeds.{cfg['f2']}` f2 ON h.UNITID = f2.UNITID
                LEFT JOIN `ipeds.{cfg['f3']}` f3 ON h.UNITID = f3.UNITID
                WHERE h.UNITID IN ({selected_ids_str})
                  AND e.FTE12MN IS NOT NULL
                  AND e.FTE12MN > 0
                """)
                
            full_trend_query = "\nUNION ALL\n".join(trend_queries)
            
            try:
                with st.spinner("Compiling historical trends..."):
                    df_trends_raw = client.query(full_trend_query).to_dataframe()
                    
                if not df_trends_raw.empty:
                    # Calculate metric columns
                    df_trends = df_trends_raw.copy()
                    df_trends['Instruction / FTE'] = df_trends['spend_instruction'] / df_trends['fte_enrollment']
                    df_trends['Academic Support / FTE'] = df_trends['spend_academic_support'] / df_trends['fte_enrollment']
                    df_trends['Student Services / FTE'] = df_trends['spend_student_services'] / df_trends['fte_enrollment']
                    
                    metric_to_plot = st.selectbox(
                        "Select Spending Metric to Plot",
                        ["Instruction / FTE", "Academic Support / FTE", "Student Services / FTE"]
                    )
                    
                    # Pivot to align line chart: index=academic_year, columns=INSTNM
                    df_pivot = df_trends.pivot(index='academic_year', columns='INSTNM', values=metric_to_plot)
                    # Sort years correctly
                    df_pivot = df_pivot.sort_index()
                    
                    st.line_chart(df_pivot)
                else:
                    st.warning("No data returned for selected institutions in other academic years.")
            except Exception as e:
                st.error(f"Error querying historical trend data: {e}")
        else:
            st.info("Please select at least one institution in the selector above to visualize trends.")

with tab_dictionary:
    st.subheader("📖 IPEDS Data Dictionary Search")
    st.markdown("Search and view variable definitions across the full IPEDS Access Database schemas.")
    
    search_query = st.text_input("Search variables (e.g. 'instruction', 'fte', 'tuition'):", "")
    
    if search_query:
        query_sql = """
        SELECT year, table_name, table_title, var_name, var_title, long_description, data_type, format
        FROM `ipeds.metadata_dictionary`
        WHERE LOWER(var_name) LIKE @search 
           OR LOWER(var_title) LIKE @search 
           OR LOWER(long_description) LIKE @search
           OR LOWER(table_title) LIKE @search
        ORDER BY year DESC, table_name, var_name
        LIMIT 100
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("search", "STRING", f"%{search_query.lower()}%")
            ]
        )
        
        try:
            with st.spinner("Searching definitions..."):
                df_dict = client.query(query_sql, job_config=job_config).to_dataframe()
                
            if not df_dict.empty:
                st.dataframe(
                    df_dict,
                    column_config={
                        "year": "Year",
                        "table_name": "Table ID",
                        "table_title": "Table Description",
                        "var_name": "Variable ID",
                        "var_title": "Variable Label",
                        "long_description": st.column_config.TextColumn("Long Description", width="large"),
                        "data_type": "Type",
                        "format": "Format"
                    },
                    hide_index=True,
                    width="stretch"
                )
            else:
                st.info("No matching variables found. Try search terms like 'adm', 'enroll', 'tuition', 'instruction', or 'expenditure'.")
        except Exception as e:
            st.error(f"Data dictionary table not found or query failed. Have you run the Access Ingestion script? Details: {e}")
    else:
        st.info("Enter a keyword to query variables and their descriptions from the metadata dictionary.")
