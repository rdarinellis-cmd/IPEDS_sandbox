import streamlit as st

def metric_card(label, value, n_value, source, vintage, suppressed=False):
    """
    Renders a consistent metric card handling suppression and metadata constraints.
    """
    if suppressed:
        st.metric(label=label, value="Insufficient N")
    else:
        st.metric(label=label, value=value)
        
    st.caption(f"*n={n_value} | {source} ({vintage})*")

def portfolio_sidebar_filters():
    """
    Implements the Unified Cohort Selection & Sidebar Filtering Layout.
    Ensures graduate and undergraduate programs are strictly segregated.
    """
    st.sidebar.header("Filter Settings")
    
    level = st.sidebar.selectbox("Select Credential Level", ["Undergraduate", "Graduate"])
    cohort = st.sidebar.selectbox("Select Cohort Group", ["Michigan Publics (MASU)", "Urban Peer Publics", "Public R1 Universities"], help="Selects the peer benchmark group for relative performance comparisons. (WSU internal portfolio is always shown).")
    peers = st.sidebar.multiselect("Select Universities", ["Wayne State University", "Michigan State University", "University of Michigan"])
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    **Definitions & Sources:**
    - **IPEDS**: National Center for Education Statistics (NCES).
    - **Scorecard**: College Scorecard Data Documentation.
    - **Labor MI**: Pathfinder Employment Outcomes.
    
    *Metrics indicate awards conferred, not unique student headcount unless specified.*
    """)
    
    return level, cohort, peers
