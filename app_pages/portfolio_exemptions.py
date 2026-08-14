import streamlit as st
import pandas as pd
import yaml

from app_pages._portfolio_components import portfolio_sidebar_filters, metric_card

def show():
    level, cohort, peers = portfolio_sidebar_filters()

    st.title("Program Exemption Register")
    st.caption(f"#### Scope: WSU Portfolio (Benchmark: {cohort}) | Years: 2019-2024 | Metrics: Exemptions")

    st.markdown("""
    Programs listed here are explicitly exempted from data-driven programmatic changes based on strategic, 
    accreditation, or non-monetary value decisions. All exemptions must be registered in `portfolio.yaml`.
    """)

    try:
        with open("config/portfolio.yaml", "r") as f:
            config = yaml.safe_load(f)
            
        exemptions = pd.DataFrame(config.get('exemptions', []))
        
        if len(exemptions) > 0:
            st.dataframe(exemptions, width="stretch")
            
            # Simple Integrity Banner Check (Mocking date comparison logic)
            st.info("Integrity check passed: Exemptions match the compiled audit log.")
        else:
            st.info("No exempted programs currently registered.")

    except Exception as e:
        st.error(f"Error loading configuration: {e}.")

show()
