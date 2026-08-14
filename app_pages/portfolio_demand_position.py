import streamlit as st
import pandas as pd
import altair as alt

from app_pages._portfolio_components import portfolio_sidebar_filters

def show():
    level, cohort, peers = portfolio_sidebar_filters()

    st.title("Demand Position Screen")
    st.caption(f"#### Scope: WSU Portfolio (Benchmark: {cohort}) | Years: 2019-2024 | Metrics: Openings, Share, Retention")

    try:
        dem = pd.read_parquet("data/app/portfolio_demand_position.parquet")
        dim = pd.read_parquet("data/app/portfolio_dim_program.parquet")
        df = pd.merge(dem, dim, on=["program_key", "CIP"])
        
        if level == "Undergraduate":
            df = df[df['CPLR Level'] < 5]
        else:
            df = df[df['CPLR Level'] >= 5]
            
        st.markdown("""
        ### Metric Definitions
        - **Regional Openings**: Projected annual job openings in Michigan for occupations directly mapped to this program's CIP code.
        - **State Completion Share**: WSU's share of total degrees awarded in this CIP code across all Michigan institutions.
        - **In-State Retention**: The percentage of WSU graduates from this program who remain employed in Michigan post-graduation.
        - **Duplication Cluster**: Classifies the program's competitive environment (e.g., Monopoly, Saturated, Niche) based on the number of other state institutions offering it.
        """)
        
        st.markdown("### Regional Openings vs State Completion Share")
        
        scatter = alt.Chart(df).mark_circle().encode(
            x=alt.X('state_completion_share:Q', title="State Completion Share", axis=alt.Axis(format='%')),
            y=alt.Y('regional_openings:Q', title="Regional Openings"),
            color=alt.Color('duplication_cluster:N', scale=alt.Scale(scheme='dark2')),
            size=alt.Size('n:Q', legend=None),
            tooltip=['Major Desc', 'state_completion_share', 'regional_openings', 'duplication_cluster']
        ).properties(height=500)
        
        st.altair_chart(scatter, width="stretch")
        
        with st.expander("View Accessible Data Table"):
            st.dataframe(df[['Major Desc', 'state_completion_share', 'regional_openings', 'in_state_retention', 'duplication_cluster']], width="stretch")

    except Exception as e:
        st.error(f"Error loading data: {e}. Please ensure the ETL pipeline has been run.")

show()
