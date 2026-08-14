import streamlit as st
import pandas as pd

from app_pages._portfolio_components import portfolio_sidebar_filters

def show():
    level, cohort, peers = portfolio_sidebar_filters()

    st.title("Crosswalk Inspector")
    st.caption(f"#### Scope: WSU Portfolio (Benchmark: {cohort}) | Years: 2019-2024 | Metrics: CIP-SOC Mapping")

    st.markdown("""
    This tool allows you to inspect the National Center for Education Statistics (NCES) 
    CIP to SOC crosswalk and the respective weighting used to distribute labor market demand.
    """)

    try:
        cw = pd.read_parquet("data/app/portfolio_map_cip_soc.parquet")
        
        cip_search = st.text_input("Search by CIP2020Code:")
        if cip_search:
            cw = cw[cw['CIP2020Code'].str.contains(cip_search, na=False)]
            
        st.dataframe(cw, width="stretch")

    except Exception as e:
        st.error(f"Error loading data: {e}. Please ensure the ETL pipeline has been run.")

show()
