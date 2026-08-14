import streamlit as st
import pandas as pd
import json
import yaml

from app_pages._portfolio_components import portfolio_sidebar_filters

def show():
    # Force layout and sidebar rules
    level, cohort, peers = portfolio_sidebar_filters()

    st.title("Program Portfolio Methodology")
    st.caption(f"#### Scope: WSU Portfolio (Benchmark: {cohort}) | Years: 2019-2024 | Metrics: ETL Configurations")

    st.markdown("""
    This module provides a strictly analytical, descriptive view of the academic portfolio.
    
    ### Analytical Constraints
    - **No Composite Scores**: We do not rank programs or assign a single composite grade.
    - **No Causal Language**: Empirical outcomes are displayed as observed, not attributed directly to program design.
    - **Segregation of Credential Levels**: Graduate and undergraduate programs are evaluated in distinct, mutually exclusive counterfactual pools.
    """)

    st.subheader("Data Processing & Integrity")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("##### ETL Audit Log")
        try:
            audit = pd.read_parquet("data/app/portfolio_audit.parquet")
            st.dataframe(audit, width="stretch")
        except Exception:
            st.warning("Audit log not available. Run ETL.")

    with col2:
        st.markdown("##### Active Configuration (`portfolio.yaml`)")
        try:
            with open("config/portfolio.yaml", "r") as f:
                config = yaml.safe_load(f)
            st.json(config)
        except Exception:
            st.warning("Configuration file not found.")

show()
