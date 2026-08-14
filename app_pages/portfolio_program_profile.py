import streamlit as st
import pandas as pd

from app_pages._portfolio_components import portfolio_sidebar_filters, metric_card

def show():
    level, cohort, peers = portfolio_sidebar_filters()

    st.title("Program Profile Card")
    st.caption(f"#### Scope: WSU Portfolio (Benchmark: {cohort}) | Years: 2019-2024 | Metrics: Comprehensive Profile")

    try:
        dim = pd.read_parquet("data/app/portfolio_dim_program.parquet")
        val = pd.read_parquet("data/app/portfolio_value_floor.parquet")
        rel = pd.read_parquet("data/app/portfolio_relative_perf.parquet")
        dem = pd.read_parquet("data/app/portfolio_demand_position.parquet")
        bins = pd.read_parquet("data/app/portfolio_bins.parquet")
        
        if level == "Undergraduate":
            dim = dim[dim['CPLR Level'] < 5]
        else:
            dim = dim[dim['CPLR Level'] >= 5]
            
        selected_program = st.selectbox("Select Program", dim['program_key'].unique())
        
        if selected_program:
            prog_dim = dim[dim['program_key'] == selected_program].iloc[0]
            prog_bin = bins[bins['program_key'] == selected_program].iloc[0]['terminal_bin'] if selected_program in bins['program_key'].values else "Unknown"
            prog_val = val[val['program_key'] == selected_program].iloc[0] if selected_program in val['program_key'].values else None
            prog_rel = rel[rel['program_key'] == selected_program].iloc[0] if selected_program in rel['program_key'].values else None
            prog_dem = dem[dem['program_key'] == selected_program].iloc[0] if selected_program in dem['program_key'].values else None
            
            st.markdown(f"### {prog_dim['Major Desc']} ({prog_dim['Credential Desc']})")
            st.markdown(f"**Terminal Bin:** {prog_bin}")
            
            st.markdown("""
            **Metric Definitions:**
            - **Mobility Yield**: Expected economic value added per enrolled student (Completion Rate × Earnings vs Counterfactual).
            - **State Earnings Gap**: WSU median earnings minus median earnings of identical programs at other MI public universities.
            - **Regional Openings**: Projected annual job openings in Michigan for mapped occupations.
            """)
            
            st.subheader("Key Metrics")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if prog_val is not None:
                    metric_card("Mobility Yield", f"${prog_val['mobility_yield']:,.0f}", prog_val['n'], "Pathfinder/IPEDS", "2024", prog_val['suppressed'])
            with col2:
                if prog_rel is not None:
                    metric_card("State Earnings Gap", f"${prog_rel['state_earnings_gap']:,.0f}", prog_rel['n'], "Pathfinder/IPEDS", "2024", prog_rel['suppressed'])
            with col3:
                if prog_dem is not None:
                    metric_card("Regional Openings", f"{prog_dem['regional_openings']}", prog_dem['n'], "Pathfinder", "2024", prog_dem['suppressed'])
                    
            st.subheader("Qualitative Input")
            st.text_area("Department Chair Comments / Strategic Value Narrative", height=150)
            
            st.button("Print Profile Card")

    except Exception as e:
        st.error(f"Error loading data: {e}. Please ensure the ETL pipeline has been run.")

show()
