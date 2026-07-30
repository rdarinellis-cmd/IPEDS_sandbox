import streamlit as st
import pandas as pd
import os
import duckdb

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
    """Detect which years have all required parquet files in the data directory."""
    try:
        file_path = "data/app/spending_benchmarks.parquet"
        if os.path.exists(file_path):
            df = duckdb.query(f"SELECT DISTINCT year_label FROM '{file_path}'").df()
            return df['year_label'].tolist()
        return list(YEARS_CONFIG.keys())
    except Exception:
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
    background: #ffffff;
    border: 1px solid rgba(12, 84, 73, 0.15);
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
    transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
}

.kpi-card:hover {
    transform: translateY(-5px);
    border-color: #0C5449; /* WSU Green */
    box-shadow: 0 10px 30px rgba(12, 84, 73, 0.12);
}

.kpi-title {
    font-size: 13px;
    font-weight: 600;
    color: #555555;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}

.kpi-value {
    font-size: 32px;
    font-weight: 700;
    color: #0C5449; /* WSU Green */
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_spending_data(year_label):
    try:
        file_path = "data/app/spending_benchmarks.parquet"
        if not os.path.exists(file_path):
            return pd.DataFrame()
            
        year_clause = f"WHERE year_label = '{year_label}'" if year_label else ""
        
        query = f"""
            SELECT 
                unitid AS UNITID,
                instnm AS INSTNM,
                control AS CONTROL,
                c21basic AS C21BASIC,
                locale AS LOCALE,
                fte_enrollment,
                spend_instruction,
                spend_academic_support,
                spend_student_services,
                is_mi_public,
                is_urban_peer,
                is_public_r1
            FROM '{file_path}'
            {year_clause}
        """
        return duckdb.query(query).df()
    except Exception as e:
        st.error(f"Failed to load spending data: {e}")
        return pd.DataFrame()

# 3. Sidebar Filter Configuration
st.sidebar.header("Filter Settings")

# Academic Year Selection
selected_year = st.sidebar.selectbox("Academic Year", available_years, index=0)
year_config = YEARS_CONFIG[selected_year]

# Cohort selector
selected_cohort = st.sidebar.selectbox(
    "Select Cohort Group",
    options=["Michigan Publics (MASU)", "Urban Peer Publics", "Public R1 Universities"],
    index=1
)

# Load data early to populate selectors consecutively
with st.spinner(f"Fetching local records for {selected_year}..."):
    df_all = load_spending_data(selected_year)

if not df_all.empty:
    if selected_cohort == "Michigan Publics (MASU)":
        df_cohort = df_all[df_all['is_mi_public'] == 1].copy()
    elif selected_cohort == "Urban Peer Publics":
        df_cohort = df_all[df_all['is_urban_peer'] == 1].copy()
    else:
        df_cohort = df_all[df_all['is_public_r1'] == 1].copy()
        
    all_cohort_schools = sorted(df_cohort['INSTNM'].unique().tolist())
    selected_schools = st.sidebar.multiselect(
        "Select Universities",
        options=all_cohort_schools,
        default=all_cohort_schools
    )
    df_raw = df_cohort[df_cohort['INSTNM'].isin(selected_schools)].copy()
else:
    selected_schools = []
    df_raw = pd.DataFrame()

# Definitions and sources markdown at the very bottom of the sidebar
st.sidebar.markdown("""
---
**Definitions & Sources:**
- **Data Sources:** NCES [IPEDS Finance Survey](https://nces.ed.gov/ipeds/) (Tables `F1A`/`F2`/`F3`) and [IPEDS Fall Enrollment Survey](https://nces.ed.gov/ipeds/) (Table `EF12`).
- **FTE Enrollment:** 12-month instructional activity Full-Time Equivalent (FTE) enrollment.
- **Spending Metrics:** Calculated as raw expense divided by 12-month FTE.
""")

# Title Section on Main Page
st.title("🎓 Higher Education Spending Analyzer")
st.caption(f"#### Scope: {selected_cohort} | Years: 2019–2024 | Metrics: Spending / FTE student")
st.markdown("Compare and analyze spending on **Instruction**, **Academic Support**, and **Student Services** per FTE student using the full IPEDS Access Database records.")


# Tabs Navigation
tab_summary, tab_trends, tab_dictionary = st.tabs([
    "📊 Spending Analyzer", 
    "📈 Trend Analysis", 
    "📖 Data Dictionary"
])

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
        st.warning("No data found matching the selected filters. Please select at least one university in the sidebar.")
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
        
        df_tidy = top_10[['INSTNM', 'Instruction per FTE', 'Academic Support per FTE', 'Student Services per FTE']].melt(
            id_vars='INSTNM',
            var_name='Spending Category',
            value_name='Spend per FTE'
        )
        
        # Grouped Bar Chart in Altair
        bar_chart = alt.Chart(df_tidy).mark_bar().encode(
            x=alt.X('Spending Category:N', title=None, axis=alt.Axis(labels=False)),
            y=alt.Y('Spend per FTE:Q', title="Spend per FTE ($)"),
            color=alt.Color('Spending Category:N', scale=alt.Scale(domain=['Instruction per FTE', 'Academic Support per FTE', 'Student Services per FTE'], range=['#0C5449', '#FFCC33', '#111111']), legend=alt.Legend(title="Category")),
            column=alt.Column('INSTNM:N', title="Institution", header=alt.Header(labelOrient='bottom', titleOrient='bottom', labelAngle=-45, labelPadding=10)),
            tooltip=['INSTNM', 'Spending Category', alt.Tooltip('Spend per FTE:Q', format='$,.2f')]
        )
        
        # Redundant encoding: exact value labels on top of bars
        text_labels = bar_chart.mark_text(
            align='center',
            baseline='bottom',
            dy=-3,
            fontSize=9,
            fontWeight='bold'
        ).encode(
            text=alt.Text('Spend per FTE:Q', format='$,.0f')
        )
        
        final_bar_chart = (bar_chart + text_labels).properties(width=70)
        st.altair_chart(final_bar_chart)
        
        # Accessible Data Fallback expander
        with st.expander("♿ Accessible Data Table - Top 10 Spending Institutions"):
            st.dataframe(
                top_10[['INSTNM', 'Instruction per FTE', 'Academic Support per FTE', 'Student Services per FTE']],
                column_config={
                    "INSTNM": "Institution",
                    "Instruction per FTE": st.column_config.NumberColumn("Instruction / FTE ($)", format="$%,.2f"),
                    "Academic Support per FTE": st.column_config.NumberColumn("Academic Support / FTE ($)", format="$%,.2f"),
                    "Student Services per FTE": st.column_config.NumberColumn("Student Services / FTE ($)", format="$%,.2f")
                },
                hide_index=True,
                width="stretch"
            )
        
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
            
            # Fetch data across all available years using DuckDB
            try:
                with st.spinner("Compiling historical trends from local files..."):
                    file_path = "data/app/spending_benchmarks.parquet"
                    if os.path.exists(file_path) and selected_ids:
                        ids_sql = ", ".join(map(str, selected_ids))
                        query = f"""
                            SELECT 
                                year_label AS academic_year,
                                instnm AS INSTNM,
                                spend_instruction,
                                spend_academic_support,
                                spend_student_services,
                                fte_enrollment
                            FROM '{file_path}'
                            WHERE unitid IN ({ids_sql})
                        """
                        df_trends_raw = duckdb.query(query).df()
                        
                        if not df_trends_raw.empty:
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
                            df_pivot = df_pivot.sort_index()
                            
                            df_plot_trends = df_pivot.reset_index().melt(
                                id_vars='academic_year',
                                var_name='Institution',
                                value_name='Spend'
                            )
                            
                            # Line chart with strokeDash for redundant encoding
                            trend_lines = alt.Chart(df_plot_trends).mark_line().encode(
                                x=alt.X('academic_year:O', title="Academic Year"),
                                y=alt.Y('Spend:Q', title=f"{metric_to_plot} ($)"),
                                color=alt.Color('Institution:N', legend=alt.Legend(title="Institution")),
                                strokeDash=alt.StrokeDash('Institution:N', legend=alt.Legend(title="Institution")),
                                tooltip=['Institution', 'academic_year', alt.Tooltip('Spend:Q', format='$,.2f')]
                            )
                            
                            # Points with shape encoding for redundant encoding
                            trend_points = alt.Chart(df_plot_trends).mark_point(filled=True, size=60).encode(
                                x='academic_year:O',
                                y='Spend:Q',
                                color='Institution:N',
                                shape=alt.Shape('Institution:N', legend=alt.Legend(title="Institution")),
                                tooltip=['Institution', 'academic_year', alt.Tooltip('Spend:Q', format='$,.2f')]
                            )
                            
                            trend_chart = alt.layer(trend_lines, trend_points).properties(
                                height=400,
                                title=f"Historical Trends: {metric_to_plot}"
                            ).interactive()
                            
                            st.altair_chart(trend_chart, width="stretch")
                            
                            with st.expander("♿ Accessible Data Table - Historical Trends"):
                                st.dataframe(
                                    df_pivot,
                                    width="stretch"
                                )
                        else:
                            st.warning("No data returned for selected institutions in other academic years.")
                    else:
                        st.warning("Spending benchmarks dataset is missing on disk.")
            except Exception as e:
                st.error(f"Error querying historical trend data: {e}")
        else:
            st.info("Please select at least one institution in the selector above to visualize trends.")

with tab_dictionary:
    st.subheader("📖 IPEDS Data Dictionary Search")
    st.markdown("Search and view variable definitions across the full IPEDS Access Database schemas.")
    
    search_query = st.text_input("Search variables (e.g. 'instruction', 'fte', 'tuition'):", "")
    
    if search_query:
        try:
            with st.spinner("Searching definitions..."):
                file_path = 'data/app/metadata_dictionary.parquet'
                if os.path.exists(file_path):
                    q_clean = search_query.replace("'", "''").lower()
                    query = f"""
                        SELECT year, table_name, table_title, var_name, var_title, long_description, data_type, format
                        FROM '{file_path}'
                        WHERE LOWER(COALESCE(var_name, '')) LIKE '%{q_clean}%'
                           OR LOWER(COALESCE(var_title, '')) LIKE '%{q_clean}%'
                           OR LOWER(COALESCE(long_description, '')) LIKE '%{q_clean}%'
                           OR LOWER(COALESCE(table_title, '')) LIKE '%{q_clean}%'
                        ORDER BY year DESC, table_name ASC, var_name ASC
                        LIMIT 100
                    """
                    df_dict = duckdb.query(query).df()
                else:
                    df_dict = pd.DataFrame()
                
            if not df_dict.empty:
                st.dataframe(
                    df_dict[['year', 'table_name', 'table_title', 'var_name', 'var_title', 'long_description', 'data_type', 'format']],
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
            st.error(f"Data dictionary file not found or search failed. Details: {e}")
    else:
        st.info("Enter a keyword to query variables and their descriptions from the metadata dictionary.")

