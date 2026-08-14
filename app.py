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
    st.Page("app_pages/spending_portfolio_shape.py", title="Expenditure Shape", icon="📈"),
    st.Page("app_pages/cip_market_share.py", title="CIP Market Share", icon="📊"),
    st.Page("app_pages/nih_grants.py", title="NIH Grants", icon="🔬"),
    st.Page("app_pages/nsf_herd.py", title="NSF HERD Analysis", icon="🔬"),
    st.Page("app_pages/institutional_trajectory.py", title="Institutional Trajectory", icon="📈"),
    #st.Page("app_pages/wsu_outcomes_matrix.py", title="WSU Outcomes Matrix", icon="🎓")
    #st.Page("app_pages/kettering_outcomes.py", title="Kettering Outcomes", icon="📊"),
])

pg.run()

