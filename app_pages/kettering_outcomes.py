import streamlit as st
import pandas as pd
import duckdb
import altair as alt

def load_kettering_data():
    """Load Kettering outcomes trend data."""
    file_path = 'data/app/kettering_trend.parquet'
    try:
        return duckdb.query(f"SELECT * FROM '{file_path}' ORDER BY year").df()
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

def run_page():
    # --- Sidebar Filtering ---
    st.sidebar.header("Filters")
    
    # Load Data
    df = load_kettering_data()
    
    if df.empty:
        st.warning("No data found for Kettering University.")
        return
        
    min_year = int(df['year'].min())
    max_year = int(df['year'].max())
    
    selected_years = st.sidebar.slider(
        "Select Year Range",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year)
    )
    
    # Filter Data
    filtered_df = df[(df['year'] >= selected_years[0]) & (df['year'] <= selected_years[1])]
    
    # Attribution Note
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    **Definitions & Sources**
    * **Data Source:** [College Scorecard Data](https://collegescorecard.ed.gov/data/documentation/)
    * **Student Size:** Total number of undergraduate degree-seeking students.
    * **Completion Rate:** 150% normal time to completion (4-year institutions).
    * **Cost of Attendance:** Average annual cost of attendance for full-time, first-time degree/certificate-seeking undergraduates.
    """)

    # --- Main Page Layout ---
    st.title("Kettering University Outcomes Trend")
    st.caption(f"#### Scope: Kettering University | Years: {selected_years[0]} - {selected_years[1]} | Metrics: Enrollment, Completion Rate, Cost")

    st.markdown("This dashboard provides a summary of Kettering University's key student outcomes and trends over the selected time period.")
    
    # --- Top Level Metrics ---
    latest_data = filtered_df.iloc[-1]
    prev_data = filtered_df.iloc[0] if len(filtered_df) > 1 else latest_data
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label=f"Total Enrollment ({latest_data['year']})",
            value=f"{int(latest_data['student_size']):,}",
            delta=f"{int(latest_data['student_size'] - prev_data['student_size'])} since {prev_data['year']}"
        )
    with col2:
        st.metric(
            label=f"Completion Rate ({latest_data['year']})",
            value=f"{latest_data['completion_rate_4yr_150nt'] * 100:.1f}%",
            delta=f"{(latest_data['completion_rate_4yr_150nt'] - prev_data['completion_rate_4yr_150nt']) * 100:.1f}% since {prev_data['year']}"
        )
    with col3:
        st.metric(
            label=f"Cost of Attendance ({latest_data['year']})",
            value=f"${int(latest_data['cost_attendance']):,}",
            delta=f"${int(latest_data['cost_attendance'] - prev_data['cost_attendance']):,} since {prev_data['year']}"
        )
        
    st.markdown("---")
    
    # --- Charts ---
    chart_col1, chart_col2 = st.columns(2)
    
    # Kettering colors (Bulldog Gold / Blue-ish) - Using a distinct professional color
    kettering_color = '#1f77b4'
    
    with chart_col1:
        st.subheader("Enrollment Trend")
        enrollment_chart = alt.Chart(filtered_df).mark_line(point=True, color=kettering_color).encode(
            x=alt.X('year:O', title='Year'),
            y=alt.Y('student_size:Q', title='Undergraduate Size', scale=alt.Scale(zero=False)),
            tooltip=['year', 'student_size']
        ).properties(height=350)
        st.altair_chart(enrollment_chart, width="stretch")
        
    with chart_col2:
        st.subheader("Completion Rate Trend")
        completion_chart = alt.Chart(filtered_df).mark_bar(color=kettering_color).encode(
            x=alt.X('year:O', title='Year'),
            y=alt.Y('completion_rate_4yr_150nt:Q', title='Completion Rate (150%)', axis=alt.Axis(format='%')),
            tooltip=['year', alt.Tooltip('completion_rate_4yr_150nt:Q', format='.1%')]
        ).properties(height=350)
        st.altair_chart(completion_chart, width="stretch")
        
    st.subheader("Cost of Attendance")
    cost_chart = alt.Chart(filtered_df).mark_area(opacity=0.4, color=kettering_color).encode(
        x=alt.X('year:O', title='Year'),
        y=alt.Y('cost_attendance:Q', title='Cost ($)', scale=alt.Scale(zero=False)),
        tooltip=['year', 'cost_attendance']
    ).properties(height=350)
    st.altair_chart(cost_chart, width="stretch")

if __name__ == "__main__":
    run_page()
else:
    run_page()
