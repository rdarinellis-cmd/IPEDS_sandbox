import streamlit as st
import pandas as pd
import altair as alt

from app_pages._portfolio_components import portfolio_sidebar_filters

def show():
    level, cohort, peers = portfolio_sidebar_filters()

    st.title("Relative Performance Screen")
    st.caption(f"#### Scope: WSU Portfolio (Benchmark: {cohort}) | Years: 2019-2024 | Metrics: State, Peer, National Earnings Gaps")

    try:
        rel = pd.read_parquet("data/app/portfolio_relative_perf.parquet")
        dim = pd.read_parquet("data/app/portfolio_dim_program.parquet")
        df = pd.merge(rel, dim, on=["program_key", "CIP"])
        
        if level == "Undergraduate":
            df = df[df['CPLR Level'] < 5]
        else:
            df = df[df['CPLR Level'] >= 5]
            
        st.markdown("""
        ### Metric Definitions
        - **State Earnings Gap**: WSU program median earnings minus the median earnings of identical programs at other Michigan public universities.
        - **Peer Earnings Gap**: WSU program median earnings minus the median earnings of identical programs at predefined peer institutions.
        - **National Earnings Gap**: WSU program median earnings minus the national median for the CIP code.
        """)
        
        st.markdown("### State Earnings Gap")
        
        # Dot plot for gaps using Altair
        chart = alt.Chart(df).mark_circle(size=60).encode(
            x=alt.X('state_earnings_gap:Q', title="State Earnings Gap ($)"),
            y=alt.Y('Major Desc:N', title="Program", sort="-x"),
            color=alt.Color('state_perf_flag:N', scale=alt.Scale(
                domain=['above_material', 'at_parity', 'below_material'],
                range=['#0C5449', '#737373', '#F2A900']
            )),
            tooltip=['Major Desc', 'state_earnings_gap', 'peer_earnings_gap', 'state_perf_flag']
        ).properties(height=max(400, len(df)*15))
        
        # Add a zero line
        rule = alt.Chart(pd.DataFrame({'x': [0]})).mark_rule(color='red').encode(x='x:Q')
        
        st.altair_chart(chart + rule, width="stretch")
        
        with st.expander("Diagnostic Expander (Underperforming Programs)"):
            underperf = df[df['state_perf_flag'] == 'below_material']
            if len(underperf) > 0:
                st.dataframe(underperf[['Major Desc', 'state_earnings_gap', 'peer_earnings_gap']], width="stretch")
            else:
                st.info("No programs flagged as materially below state median.")

    except Exception as e:
        st.error(f"Error loading data: {e}. Please ensure the ETL pipeline has been run.")

show()
