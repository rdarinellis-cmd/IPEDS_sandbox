import streamlit as st
import duckdb
import pandas as pd
import os

st.set_page_config(
    page_title="IPEDS Dashboards",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=3600)
def load_completions_scorecard_merged():
    """
    Executes a high-performance DuckDB SQL join between IPEDS Completions 
    and College Scorecard Field of Study Parquet datasets.
    """
    comp_file = 'data/app/completions_benchmark.parquet'
    scorecard_file = 'data/raw/scorecard/most_recent_cohorts_field_of_study.parquet'
    
    if not os.path.exists(comp_file) or not os.path.exists(scorecard_file):
        return pd.DataFrame()
        
    query = f"""
        SELECT 
            c.year,
            c.unitid,
            c.institution,
            c.cip_code,
            REPLACE(SUBSTRING(c.cip_code, 1, 5), '.', '') AS cip_4digit,
            c.award_level,
            c.total_degrees,
            s.CIPDESC AS scorecard_cip_desc,
            s.DEBT_ALL_STGP_EVAL_MDN AS median_debt,
            s.EARN_MDN_HI_1YR AS median_earnings_1yr
        FROM '{comp_file}' c
        LEFT JOIN '{scorecard_file}' s
            ON CAST(c.unitid AS VARCHAR) = CAST(s.UNITID AS VARCHAR)
           AND REPLACE(SUBSTRING(c.cip_code, 1, 5), '.', '') = LPAD(CAST(s.CIPCODE AS VARCHAR), 4, '0')
    """
    return duckdb.query(query).df()

pg = st.navigation([
    st.Page("app_pages/overview.py", title="Overview", icon="🏠"),
    st.Page("app_pages/spending_analyzer.py", title="Spending Analyzer", icon="💰"),
    st.Page("app_pages/spending_portfolio_shape.py", title="Expenditure Shape", icon="📈"),
    st.Page("app_pages/cip_market_share.py", title="CIP Market Share", icon="📊"),
    st.Page("app_pages/nih_grants.py", title="NIH Grants", icon="🔬"),
    #st.Page("app_pages/wsu_outcomes_matrix.py", title="WSU Outcomes Matrix", icon="🎓")
])

pg.run()

