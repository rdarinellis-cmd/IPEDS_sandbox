# Workspace Customization Rules

## 🎨 IPEDS Dashboard Style Guidelines

For all dashboards and pages built in this project, the following conventions must be followed to maintain visual consistency and provide clear data context:

### 1. Data Provenance & Definitions Note
Every dashboard page must display a dedicated note detailing data sources and metric definitions:
- **Location:** Place it in the sidebar filters section under a **"Definitions & Sources"** header, or inside an expandable/styled section at the bottom of the page.
- **NCES/Official Links:** Include explicit links to official references (e.g., [NCES IPEDS](https://nces.ed.gov/ipeds/) or [College Scorecard Data](https://collegescorecard.ed.gov/data/documentation/)).
- **Definition Clarification:** Clearly describe the metric definition (such as confirming whether a metric displays **degrees/awards conferred** or **unduplicated student headcount**).

### 2. Contextual Subtitles
Every dashboard must feature a descriptive subtitle directly below the main title. This subtitle must present:
- **Analysis Scope / Cohort:** (e.g., "Michigan Public Universities", "Urban Peers", or "Public R1 Universities").
- **Timeframe / Years:** The range of years represented in the data (e.g., "2019 to 2024").
- **Core Metrics:** A brief mention of the primary variables (e.g., "Completions, CAGR, Market Share").

### 3. ETL Data Access Boundary (Data Integrity Rule)
To prevent runtime crashes and ensure zero-downtime remote deployments (such as Streamlit Community Cloud):
- **Never load or query files inside the `data/raw/` folder directly from page views.** This directory is git-ignored and missing in production.
- **Aggregate all raw inputs locally** using `etl/compile_app_data.py` into lightweight `.parquet` databases inside `data/app/`.
- **Load pre-compiled `.parquet` tables** directly in front-end pages.

*Note: These instructions are loaded as workspace rules and must be adhered to by all developer agents working on this project.*
