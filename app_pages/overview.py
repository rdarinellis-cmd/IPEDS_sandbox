import streamlit as st



st.title("🎓 IPEDS Data Explorer")

st.markdown("""
Welcome to the **IPEDS Data Explorer**! This dashboard provides an intuitive, high-performance interface for analyzing higher education data from the National Center for Education Statistics (NCES).

---

### 🏛️ Data Provenance: What is IPEDS?

The **Integrated Postsecondary Education Data System (IPEDS)** is a system of interrelated surveys conducted annually by the U.S. Department of Education’s NCES. IPEDS gathers information from every college, university, and technical and vocational institution that participates in federal student financial aid programs.

The datasets analyzed here include:
- **Institutional Characteristics (HD):** Directory information, Carnegie classifications, and control (public vs. private).
- **Fall Enrollment (EF):** Full-time equivalent (FTE) student counts.
- **Finance (F1/F2/F3):** Detailed accounting of institutional revenues and core expenses (e.g., Instruction, Academic Support, Student Services).
- **Completions (C):** Degrees awarded, broken down by Classification of Instructional Programs (CIP) codes, award levels, and demographics.

---

### ⚡ Architectural Approach

To maximize performance, portability, and user experience, this dashboard is built on a **modern local-first data architecture**:

1. **Parquet Storage:** Instead of using cloud data warehouses (like BigQuery) we are using local Apache Parquet files (`.parquet`). Parquet is a columnar storage format that provides extreme compression and lightning-fast read speeds.
2. **In-Memory Pandas & PyArrow:** Data is ingested directly into Pandas DataFrames backed by the PyArrow engine. 
3. **Streamlit Caching:** Using Streamlit's `@st.cache_data`, the heavy datasets are only loaded into memory once. Subsequent filtering and page navigations hit the memory cache instantly.

Because the data is entirely local and decoupled from cloud credentials, this application is highly portable and resilient to network disruptions.

---

### 🧭 Available Dashboards

Use the sidebar navigation on the left to explore the tools:

- **💰 Spending Analyzer**: Evaluate how institutions allocate their funds across core expenses on a per-student (FTE) basis, allowing for peer benchmarking by Carnegie classification and urbanicity.
- **📊 CIP Market Share**: Analyze degrees awarded by 6-digit CIP code for Michigan public universities, featuring a strategic quadrant chart plotting Market Share vs. 5-Year Compound Annual Growth Rate (CAGR).
""")
