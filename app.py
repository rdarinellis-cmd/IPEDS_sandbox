import streamlit as st

st.set_page_config(
    page_title="IPEDS Dashboards",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

pg = st.navigation([
    st.Page("app_pages/overview.py", title="Overview", icon="🏠"),
    st.Page("app_pages/spending_analyzer.py", title="Spending Analyzer", icon="💰"),
    st.Page("app_pages/cip_market_share.py", title="CIP Market Share", icon="📊")
])

pg.run()
