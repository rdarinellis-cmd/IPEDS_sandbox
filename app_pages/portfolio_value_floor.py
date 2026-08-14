import streamlit as st
import pandas as pd
import altair as alt

from app_pages._portfolio_components import portfolio_sidebar_filters

def show():
    level, cohort, peers = portfolio_sidebar_filters()

    st.title("Value Floor Screen")
    st.caption(f"#### Scope: WSU Portfolio (Benchmark: {cohort}) | Years: 2019-2024 | Metrics: Completion, Debt, Earnings")

    try:
        val = pd.read_parquet("data/app/portfolio_value_floor.parquet")
        dim = pd.read_parquet("data/app/portfolio_dim_program.parquet")
        df = pd.merge(val, dim, on=["program_key", "CIP"])
        
        if level == "Undergraduate":
            df = df[df['CPLR Level'] < 5]
        else:
            df = df[df['CPLR Level'] >= 5]
            
        st.markdown("""
        ### Metric Definitions
        - **Counterfactual Baseline**: The estimated earnings a student would have achieved if they had not enrolled in the program (e.g., $35k/year for a high-school graduate in Michigan).
        - **Earnings Gap (vs Counterfactual)**: The program's median alumni earnings minus the Counterfactual Baseline.
        - **Mobility Yield**: A program's completion rate multiplied by its Earnings Gap. It represents the *expected* economic value added for an enrolling student.
        - **Debt-to-Earnings**: The ratio of median debt at graduation to median early-career earnings.
        - **Completion Rate**: The percentage of entering students who graduate within the 150% standard timeframe.
        """)
        
        st.markdown("### Earnings vs. Counterfactual")
        
        # We plot earnings vs counterfactual gap (bullet chart or bar chart style in Altair)
        # Using WSU Green for positive gap, WSU Gold for negative gap (flagged)
        chart_val = alt.Chart(df).mark_bar().encode(
            x=alt.X('earnings_vs_counterfactual:Q', title="Earnings Gap (vs Counterfactual)"),
            y=alt.Y('Major Desc:N', title="Program", sort="-x"),
            color=alt.condition(
                alt.datum.earnings_vs_counterfactual > 0,
                alt.value("#0C5449"),  # WSU Green
                alt.value("#F2A900")   # WSU Gold (Warning)
            ),
            tooltip=['Program', 'Major Desc', 'earnings_vs_counterfactual', 'n']
        ).properties(height=max(400, len(df)*15))
        
        st.altair_chart(chart_val, width="stretch")
        
        with st.expander("View Accessible Data Table"):
            st.dataframe(df[['Major Desc', 'earnings_vs_counterfactual', 'debt_to_earnings', 'completion_rate', 'n', 'suppressed']], width="stretch")

    except Exception as e:
        st.error(f"Error loading data: {e}. Please ensure the ETL pipeline has been run.")

show()
