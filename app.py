import streamlit as st

st.set_page_config(
    page_title="IPEDS Dashboards",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Core Analysis Pages
overview_page = st.Page("app_pages/overview.py", title="Overview", icon="🏠")
spending_analyzer = st.Page("app_pages/spending_analyzer.py", title="Spending Analyzer", icon="💰")
spending_portfolio_shape = st.Page("app_pages/spending_portfolio_shape.py", title="Expenditure Shape", icon="📈")
cip_market_share = st.Page("app_pages/cip_market_share.py", title="CIP Market Share", icon="📊")
nih_grants = st.Page("app_pages/nih_grants.py", title="NIH Grants", icon="🔬")
nsf_herd = st.Page("app_pages/nsf_herd.py", title="NSF HERD Analysis", icon="🔬")

# Portfolio Analysis Pages
portfolio_methods = st.Page("app_pages/portfolio_methods.py", title="1. Methodology & Rules", icon="⚖️")
portfolio_map = st.Page("app_pages/portfolio_map.py", title="2. Portfolio Bins Map", icon="🗺️")
portfolio_value = st.Page("app_pages/portfolio_value_floor.py", title="3. Value Floor Screen", icon="💰")
portfolio_relative = st.Page("app_pages/portfolio_relative_perf.py", title="4. Relative Performance Screen", icon="📊")
portfolio_demand = st.Page("app_pages/portfolio_demand_position.py", title="5. Demand Position Screen", icon="📈")
portfolio_equity = st.Page("app_pages/portfolio_equity.py", title="6. Equity Lens", icon="⚖️")
portfolio_profile = st.Page("app_pages/portfolio_program_profile.py", title="7. Program Profile", icon="📄")
portfolio_crosswalk = st.Page("app_pages/portfolio_crosswalk.py", title="8. CIP-SOC Crosswalk", icon="🔍")
portfolio_exemptions = st.Page("app_pages/portfolio_exemptions.py", title="9. Exemptions Register", icon="🛡️")

pg = st.navigation({
    "Overview": [overview_page],
    "Institutional Analysis": [
        spending_analyzer,
        spending_portfolio_shape,
        cip_market_share,
        nih_grants,
        nsf_herd,
    ],
    "Program Portfolio": [
        portfolio_methods,
        portfolio_map,
        portfolio_value,
        portfolio_relative,
        portfolio_demand,
        portfolio_equity,
        portfolio_profile,
        portfolio_crosswalk,
        portfolio_exemptions
    ]
})

pg.run()
