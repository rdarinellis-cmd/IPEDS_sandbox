import streamlit as st

# --- CUSTOM CSS FOR PREMIUM WSU BRANDED LOOK ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

/* Apply modern typography */
html, body, [class*="css"], .stMarkdown {
    font-family: 'Outfit', sans-serif;
}

/* Card layout styling */
.card-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    margin-top: 20px;
    margin-bottom: 30px;
}

.dashboard-card {
    background: #ffffff;
    border: 1px solid rgba(12, 84, 73, 0.15); /* Primary WSU Green tint border */
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
    transition: transform 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease;
    display: flex;
    flex-direction: column;
    height: 100%;
}

.dashboard-card:hover {
    transform: translateY(-4px);
    border-color: #0C5449; /* WSU Green */
    box-shadow: 0 10px 25px rgba(12, 84, 73, 0.12);
}

.card-header-flex {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
}

.card-icon {
    font-size: 28px;
    width: 48px;
    height: 48px;
    background: rgba(12, 84, 73, 0.08); /* Light tint of WSU Green */
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #0C5449;
}

.card-title {
    font-size: 18px;
    font-weight: 700;
    color: #0C5449; /* WSU Green */
    margin: 0;
}

.card-desc {
    font-size: 14px;
    color: #333333;
    line-height: 1.5;
    margin-bottom: 16px;
    flex-grow: 1;
}

.source-tag {
    display: inline-block;
    background: rgba(242, 169, 0, 0.12); /* WSU Gold light tint */
    color: #0C5449; /* Green text for contrast */
    border: 1px solid rgba(242, 169, 0, 0.3);
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
    margin-top: auto;
    width: fit-content;
}
</style>
""", unsafe_allow_html=True)

st.title("🎓 IPEDS Data Explorer")
st.caption("#### Scope: Michigan Publics & Peers | Years: 2019–2024 | Metrics: Enrollment, Finance, Completions, R&D Expenditures, and NIH/NSF Grants")

st.markdown("""
Welcome to the **IPEDS Data Explorer**! This platform provides an intuitive, high-performance interface for benchmarking institutional characteristics, finance metrics, student completions, and external research funding.

---

### 🧭 Available Dashboards

Use the sidebar navigation on the left to explore the tools:
""")

# Render beautiful cards for the available dashboard pages
st.markdown("""
<div class="card-container">
    <div class="dashboard-card">
        <div class="card-header-flex">
            <div class="card-icon">💰</div>
            <h4 class="card-title">Spending Analyzer</h4>
        </div>
        <p class="card-desc">Evaluate how peer institutions allocate funds across core expenses (Instruction, Academic Support, Student Services) per FTE student. Benchmark by Carnegie classification and urbanicity.</p>
        <span class="source-tag">IPEDS Finance & Enrollment</span>
    </div>
    <div class="dashboard-card">
        <div class="card-header-flex">
            <div class="card-icon">📈</div>
            <h4 class="card-title">Expenditure Shape</h4>
        </div>
        <p class="card-desc">Compare functional expense categories as a percentage share of total core expenses. Analyze Wayne State's resource allocation trajectory against custom peer cohorts over time.</p>
        <span class="source-tag">IPEDS Finance</span>
    </div>
    <div class="dashboard-card">
        <div class="card-header-flex">
            <div class="card-icon">📊</div>
            <h4 class="card-title">CIP Market Share</h4>
        </div>
        <p class="card-desc">Track degrees awarded by CIP academic programs. Features a growth-share quadrant (CAGR vs. Market Share) and program alignment with Michigan occupational demand projections.</p>
        <span class="source-tag">IPEDS Completions & MI LMI</span>
    </div>
    <div class="dashboard-card">
        <div class="card-header-flex">
            <div class="card-icon">🔬</div>
            <h4 class="card-title">NIH Grants</h4>
        </div>
        <p class="card-desc">Analyze NIH-funded biomedical research activity. Monitor active training grants (T-series) and center/infrastructure grants (P/U-series) by award count and total funding.</p>
        <span class="source-tag">NIH RePORTER API</span>
    </div>
    <div class="dashboard-card">
        <div class="card-header-flex">
            <div class="card-icon">🧪</div>
            <h4 class="card-title">NSF HERD Analysis</h4>
        </div>
        <p class="card-desc">Track institutional R&D expenditures and research personnel. Benchmark total research spending against peer R1s and regional publics using the official HERD survey.</p>
        <span class="source-tag">NSF HERD Survey</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
---

### 🏛️ Data Provenance & Official References

The data pipeline aggregates records from multiple official, public sources to ensure accuracy, comparability, and depth:

*   🏛️ **NCES IPEDS Surveys:** The Integrated Postsecondary Education Data System is the primary database, gathering information annually from every college and university participating in federal student financial aid programs.
    *   **Institutional Characteristics (HD):** Directory data, Carnegie classifications, and control (public vs. private).
    *   **Fall Enrollment (EF):** 12-month instructional activity Full-Time Equivalent (FTE) student headcounts.
    *   **Finance (F1A/F2/F3):** Core expenses (Instruction, Academic Support, Student Services, Institutional Support, Research) under GASB and FASB reporting.
    *   **Completions (C):** Degrees/certificates awarded, categorized by Classification of Instructional Programs (CIP) codes.
    *   *Official Source:* [NCES IPEDS Home](https://nces.ed.gov/ipeds/)
*   🎓 **College Scorecard:** Provides graduate outcomes, including median debt and median earnings 1-year post-graduation, aggregated by field of study (CIP code).
    *   *Official Source:* [U.S. Department of Education College Scorecard](https://collegescorecard.ed.gov/data/documentation/)
*   🔬 **NIH RePORTER:** Data on active National Institutes of Health grants, specifically filtering to institutional training (T-series) and center/infrastructure (P/U-series) awards.
    *   *Official Source:* [NIH RePORTER API v2](https://api.reporter.nih.gov/)
*   🧪 **NSF HERD Survey:** The Higher Education Research and Development Survey, reporting total R&D expenditures (by source of funds) and research personnel headcounts.
    *   *Official Source:* [NSF NCSES HERD Survey](https://ncses.nsf.gov/surveys/higher-education-research-development/)
*   💼 **Michigan Labor Market Information (LMI):** Mapped via NCES CIP-to-SOC (Standard Occupational Classification) crosswalks to align academic completions with 10-year employment projections and regional wage bands.
    *   *Official Source:* [Michigan LMI Data Portal](https://milmi.org/)
""")


