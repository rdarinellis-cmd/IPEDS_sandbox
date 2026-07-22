import streamlit as st



st.title("🎓 IPEDS Data Explorer")

st.markdown("""
Welcome to the **IPEDS Data Explorer**! This dashboard provides an intuitive, high-performance interface for analyzing higher education data from the National Center for Education Statistics (NCES).

---

### 🏛️ Data Provenance: IPEDS

The **Integrated Postsecondary Education Data System (IPEDS)** is a system of interrelated surveys conducted annually by the U.S. Department of Education’s NCES. IPEDS gathers information from every college, university, and technical and vocational institution that participates in federal student financial aid programs.

The datasets analyzed here include:
- **Institutional Characteristics (HD):** Directory information, Carnegie classifications, and control (public vs. private).
- **Fall Enrollment (EF):** Full-time equivalent (FTE) student counts.
- **Finance (F1/F2/F3):** Detailed accounting of institutional revenues and core expenses (e.g., Instruction, Academic Support, Student Services).
- **Completions (C):** Degrees awarded, broken down by Classification of Instructional Programs (CIP) codes, award levels, and demographics.

---

### 🧭 Available Dashboards

Use the sidebar navigation on the left to explore the tools:

- **💰 Spending Analyzer**: Evaluate how institutions allocate their funds across core expenses on a per-student (FTE) basis, allowing for peer benchmarking by Carnegie classification and urbanicity.
- **📊 CIP Market Share**: Analyze degrees awarded by 6-digit CIP code for Michigan public universities, featuring a strategic quadrant chart plotting Market Share vs. 5-Year Compound Annual Growth Rate (CAGR).
""")
