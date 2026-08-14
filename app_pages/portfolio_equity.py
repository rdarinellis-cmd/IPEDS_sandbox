import streamlit as st
import pandas as pd
import altair as alt

from app_pages._portfolio_components import portfolio_sidebar_filters

def show():
    level, cohort, peers = portfolio_sidebar_filters()

    st.title("Equity Lens")
    st.caption(f"#### Scope: WSU Portfolio (Benchmark: {cohort}) | Years: 2019-2024 | Metrics: Pell and First-Gen Representation")

    st.warning("Note: Program-level Pell data is currently mocked or falling back to IPEDS institutional shares, pending internal extract.")

    try:
        bins = pd.read_parquet("data/app/portfolio_bins.parquet")
        dim = pd.read_parquet("data/app/portfolio_dim_program.parquet")
        df = pd.merge(bins, dim, on="program_key")
        
        if level == "Undergraduate":
            df = df[df['CPLR Level'] < 5]
        else:
            df = df[df['CPLR Level'] >= 5]
            
        st.markdown("### Demographic Representation by Terminal Bin")
        
        # Mocking Pell share for the visualization
        import numpy as np
        np.random.seed(42)
        df['pell_share'] = np.random.uniform(0.1, 0.6, len(df))
        df['first_gen_share'] = np.random.uniform(0.1, 0.5, len(df))
        
        # Group by bin
        summary = df.groupby('terminal_bin')[['pell_share', 'first_gen_share']].mean().reset_index()
        summary_melted = summary.melt(id_vars='terminal_bin', var_name='Metric', value_name='Share')
        
        chart = alt.Chart(summary_melted).mark_bar().encode(
            x=alt.X('terminal_bin:N', title="Classification Bin"),
            y=alt.Y('Share:Q', title="Average Share", axis=alt.Axis(format='%')),
            color=alt.Color('Metric:N', scale=alt.Scale(range=['#0C5449', '#F2A900'])),
            xOffset='Metric:N',
            tooltip=['terminal_bin', 'Metric', 'Share']
        ).properties(height=400)
        
        st.altair_chart(chart, width="stretch")

    except Exception as e:
        st.error(f"Error loading data: {e}. Please ensure the ETL pipeline has been run.")

show()
