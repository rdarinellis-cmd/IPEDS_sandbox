import streamlit as st

st.title("🎓 IPEDS Data Explorer")
st.caption("#### Scope: Michigan Publics & Peers | Years: 2019–2024 | Metrics: Enrollment, Completions, and Finance")

st.markdown("""
Welcome to the **IPEDS Data Explorer**! This dashboard provides an intuitive, high-performance interface for analyzing higher education data from the National Center for Education Statistics (NCES).

---

### 🏛️ Data Provenance & Official References

The **Integrated Postsecondary Education Data System (IPEDS)** is a system of interrelated surveys conducted annually by the U.S. Department of Education’s NCES. IPEDS gathers information from every college, university, and technical and vocational institution that participates in federal student financial aid programs.

- **Official NCES Source Website:** [NCES IPEDS Home](https://nces.ed.gov/ipeds/)
- **College Scorecard Data Documentation:** [U.S. Department of Education College Scorecard](https://collegescorecard.ed.gov/data/documentation/)

The datasets analyzed here include:
- **Institutional Characteristics (HD):** Directory information, Carnegie classifications, and control (public vs. private).
- **Fall Enrollment (EF):** Full-time equivalent (FTE) student counts.
- **Finance (F1/F2/F3):** Detailed accounting of institutional revenues and core expenses (e.g., Instruction, Academic Support, Student Services).
- **Completions (C):** Degrees/certificates awarded, broken down by Classification of Instructional Programs (CIP) codes, award levels, and demographics.

---

### 🧭 Available Dashboards

Use the sidebar navigation on the left to explore the tools:

- **💰 Spending Analyzer**: Evaluate how institutions allocate their funds across core expenses on a per-student (FTE) basis, allowing for peer benchmarking by Carnegie classification and urbanicity.
- **📈 Expenditure Shape**: Compare functional expense categories as a share of total core expenses for Wayne State University against custom peer groups over a 5-year trend.
- **📊 CIP Market Share**: Analyze degrees awarded by 6-digit CIP code for Michigan public universities, featuring a strategic quadrant chart plotting Market Share vs. 5-Year Compound Annual Growth Rate (CAGR).
""")

