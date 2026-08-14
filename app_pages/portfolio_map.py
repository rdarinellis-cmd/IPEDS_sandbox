import streamlit as st
import pandas as pd
import altair as alt

from app_pages._portfolio_components import portfolio_sidebar_filters

def show():
    level, cohort, peers = portfolio_sidebar_filters()

    st.title("Program Portfolio Bins")
    st.caption(f"#### Scope: WSU Portfolio (Benchmark: {cohort}) | Years: 2019-2024 | Metrics: Terminal Classifications")

    try:
        bins = pd.read_parquet("data/app/portfolio_bins.parquet")
        dim = pd.read_parquet("data/app/portfolio_dim_program.parquet")
        
        # Merge to get names and levels
        df = pd.merge(bins, dim, on="program_key")
        
        # Filter by credential level (mocking the check, we assume CPLR Level < 5 is Undergrad)
        if level == "Undergraduate":
            df = df[df['CPLR Level'] < 5]
        else:
            df = df[df['CPLR Level'] >= 5]
            
        st.markdown(f"### Terminal Bin Distribution")
        st.info(f"Currently viewing **{len(df)}** programs (Filtered to **{level}** level). Total active university portfolio is 478 programs.")
        
        # Count by bin
        summary = df['terminal_bin'].value_counts().reset_index()
        summary.columns = ['terminal_bin', 'count']
        
        selection = alt.selection_point(fields=['terminal_bin'], name='bin_select')
        
        # Altair chart using WSU Colors
        # Using WSU Green #0C5449 for the bars
        chart = alt.Chart(summary).mark_bar(color="#0C5449").encode(
            x=alt.X('count:Q', title="Number of Programs"),
            y=alt.Y('terminal_bin:N', title="Classification Bin", sort="-x"),
            opacity=alt.condition(selection, alt.value(1), alt.value(0.3)),
            tooltip=['terminal_bin', 'count']
        ).properties(
            height=400
        ).add_params(selection)
        
        event = st.altair_chart(chart, width="stretch", on_select="rerun")
        
        with st.expander("View Accessible Data Table"):
            st.dataframe(summary, width="stretch")
            
        st.markdown("### Program Listing")
        
        df_display = df
        if event.selection and 'bin_select' in event.selection:
            sel_data = event.selection['bin_select']
            selected_bins = []
            for item in sel_data:
                if isinstance(item, dict) and 'terminal_bin' in item:
                    selected_bins.append(item['terminal_bin'])
                else:
                    selected_bins.append(item)
            if selected_bins:
                df_display = df[df['terminal_bin'].isin(selected_bins)]
                
        st.dataframe(df_display[['program_key', 'Program', 'Major Desc', 'Credential Desc', 'terminal_bin']], width="stretch")

    except Exception as e:
        st.error(f"Error loading data: {e}. Please ensure the ETL pipeline has been run.")

show()
