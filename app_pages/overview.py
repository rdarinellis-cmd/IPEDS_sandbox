import streamlit as st

st.title("🎓 IPEDS Dashboard Overview")

st.markdown("""
Welcome to the **IPEDS Dashboard**! This application allows you to explore and analyze higher education data from the Integrated Postsecondary Education Data System (IPEDS) using Google BigQuery.

### Available Dashboards

Use the sidebar navigation on the left to explore the different tools:

- **💰 Spending Analyzer**: Compare and analyze spending on Instruction, Academic Support, and Student Services per FTE student.
- **📊 CIP Market Share**: Analyze degrees awarded by 6-digit CIP code for Michigan public universities, featuring a quadrant chart for Market Share vs. 5-Year CAGR.

---

### How to Run This App Locally

If you need to restart this application or run it on another machine, follow these steps in your terminal:

1. **Activate the Virtual Environment**:
   ```bash
   source environment/bin/activate
   ```

2. **Run the Streamlit App**:
   ```bash
   streamlit run app.py
   ```

*(Alternatively, you can simply run the provided `run_dashboard.sh` script, which automatically handles the environment and launches the app!)*

### Prerequisites
- Ensure your Google Cloud credentials are set up for BigQuery access (to `project-9a1f71b9-7c50-4df5-adb`).
- Required Python packages are installed in the `environment` directory (`streamlit`, `pandas`, `google-cloud-bigquery`, `altair`, etc.).
""")
