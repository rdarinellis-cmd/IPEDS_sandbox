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

### 4. Shared Definitions Rule (`etl/common.py`)
Anything used by more than one script or page is defined **once**, in `etl/common.py`, and imported — never copy-pasted:
- `normalize_cip()`, `split_college_codes()`
- Cohort membership: `MICHIGAN_UNIVERSITIES`, `MICHIGAN_UNIVERSITY_IDS`, `URBAN_PEER_IDS`, `PUBLIC_R1_CONTROL`, `PUBLIC_R1_C21BASIC`
- Identity: `WSU_UNITID`, `WSU_NAME`, `COLLEGE_NAMES`
- Brand palette: `WSU_GREEN`, `WSU_GOLD`, `PEER_GREY`, `PEER_GREY_LIGHT`

**Before writing a helper or a constant, check `etl/common.py` first.** If you catch yourself pasting a CIP formatter, a peer-ID list, or a hex color, import it instead. Duplicated definitions here have already produced silent, hard-to-find data bugs.

Scripts run from a subdirectory need the project root on `sys.path` before the import (see ARCHITECTURE.md section 10C). CSS strings inside `st.markdown()` are the one exception and keep literal hex values.

### 5. Unified Cohort Selection & Sidebar Filtering Layout
Every dashboard page containing filters must organize its layout as follows:
- **Sidebar Selector Order:** All interactive widgets (year, cohort group, cohort members) must be defined consecutively at the top of the sidebar.
- **Attribution Note:** Place the "Definitions & Sources" markdown block at the very bottom of the sidebar below all widgets, preceded by a horizontal line divider (`---`).
- **Main Page Title & Dynamic Subtitles:** Draw the main title, followed immediately by a dynamic caption showing the active cohort group, year range, and primary metrics being analyzed (e.g. `st.caption(f"#### Scope: {selected_cohort} | Years: ... | Metrics: ...")`).
- **Selector Naming:** The cohort group selectbox must be named `"Select Cohort Group"` and have the options `["Michigan Publics (MASU)", "Urban Peer Publics", "Public R1 Universities"]`. The cohort member selector must be named `"Select Universities"` (or `"Select Peer Universities"`).

### 6. Institutional Visual Identity (Wayne State vs Peers)
Always represent Wayne State University distinctively using **WSU Green** (`#0C5449`) and **WSU Gold** (`#F2A900`) across all charts. 
All peer institutions or peer medians must be represented uniformly and distinctly from WSU using neutral styling (e.g., Black `#000000` and Grey `#737373` or `#cccccc`), ensuring Wayne State immediately stands out in all visual comparisons.

### 6. Charting Library Consistency (Altair)
All data visualizations **MUST** use **Altair**. Do not use Plotly, Matplotlib, or other charting libraries. This ensures visual consistency, accessible rendering, and unified styling across all pages.

### 7. Streamlit API Deprecations
When creating dataframes, charts, or other elements that span the full container width, **never** use the deprecated `use_container_width=True` argument. Always use `width="stretch"` (or `width="content"` if it should not span the container) as per the latest Streamlit API standards.

*Note: These instructions are loaded as workspace rules and must be adhered to by all developer agents working on this project.*
