# IPEDS Dashboard: Project Status & Architecture Blueprint

## 📜 1. Context & Scope
- **Target Audience:** Higher education data consumers looking for fast, intuitive, multi-page web dashboards to explore the last 5 years of National Center for Education Statistics (NCES) IPEDS institutional data.
- **Developer Mindset:** Re-engaging with coding after a multi-decade hiatus (BASIC/FORTRAN backgrounds). Value simplicity, lean toolsets, local-first environments, and zero-to-low cost footprint.
- **Primary Constraints:** Avoid heavy database infrastructure, container virtualization, or complex cloud authentication overhead. Decouple completely from external cloud databases.

## 🏛️ 2. Local-First Architecture Design
This dashboard is designed to run completely serverlessly on a local-first, file-based execution model:

- **Data Engine:** In-Memory Pandas + Apache Parquet files (`.parquet`), providing extreme compression and lightning-fast read speeds.
- **Dictionary Setup:** Local `.xlsx` NCES lookups in [dictionaries/](file:///Users/ac7940/Antigravity/IPEDS_sandbox/dictionaries).
- **Auth Complexity:** Zero Application-level authentication or credential overhead.
- **Compute Profile:** Fast, local multi-threaded file execution using Pandas and PyArrow.
- **Hosting Strategy:** Deployed directly to Streamlit Community Cloud (GitHub Synced).
- **Financial Cost:** Guaranteed $0.00/month footprint using free hosting tier.
- **ETL Boundary (Data Source Constraint):** Never query raw datasets (`data/raw/`) directly from dashboard pages, as these files are git-ignored and missing in production. All raw data must be aggregated locally using `etl/compile_app_data.py` into lightweight `.parquet` databases inside `data/app/` and read from there in the page views.
- **Single Source of Truth (`etl/common.py`):** Definitions used by more than one script — the CIP normalizer, peer-cohort membership, WSU school/college codes, and the brand palette — live in `etl/common.py` and are imported, never copy-pasted. See section 10 for the rule and its rationale.

## 📁 3. Workspace Layout
The repository is structured as a lightweight Python project:

```plaintext
IPEDS_sandbox/
├── .venv/                  # Hidden: Isolated local Python packages (Never push to Git)
├── .gitignore              # Controls what files are blocked from GitHub
├── ARCHITECTURE.md         # This technical specification blueprint
├── README.md               # User guide and workspace configuration steps
├── app.py                  # Streamlit entry point (Navigation & Main Layout)
├── requirements.txt        # Python package dependencies list
├── clock_in.sh             # Activates virtualenv, pulls main branch, updates pip packages
├── clock_out.sh            # Stages changes, prompts for commit message, pushes to GitHub
├── rebuild_env.sh          # Utility script to clean and reconstruct the .venv environment
├── run_dashboard.sh        # Utility script to boot Streamlit using the .venv Python path
├── app_pages/              # Individual Streamlit dashboard views
│   ├── overview.py         # App landing page & architecture explanation
│   ├── cip_market_share.py # Degrees awarded & CIP market share view
│   ├── nih_grants.py       # NIH Grants analysis page
│   ├── nsf_herd.py         # NSF HERD analysis page
│   ├── spending_analyzer.py# Cost/spending analysis dashboard
│   ├── spending_portfolio_shape.py # Expenditure Shape benchmarking page
│   └── kettering_outcomes.py # Kettering Outcomes view (development branch)
├── build_demand.py         # Builds the Michigan occupational DEMAND marts (CIP x SOC)
├── etl/                    # Raw data ingestion & compilation pipeline
│   ├── common.py           # SHARED definitions (CIP normalizer, cohorts, colleges, brand colors)
│   ├── compile_app_data.py # Local aggregator creating local application Parquet databases
│   ├── ingest_master.py    # Fetches public datasets and converts them to Snappy-Parquet
│   └── ingest_nih_reporter.py # Fetches and structures NIH RePORTER data
├── scripts/                # Data cleaning and pipeline operations
│   ├── build_pipeline.py   # Local ETL pipeline merging Pathfinder, SOC, and cached Parquet data
│   ├── clean_labor_mi_raw.py    # Normalizes a fresh MILMI wage download (run after each re-download)
│   └── clean_crosswalk_raw.py   # Fixes/consolidates data/raw/crosswalks/, archives redundant files
├── data/                   # Data directory (Parquet caches)
│   ├── app/                # Compiled application databases (Parquet files read by dashboard)
│   └── raw/                # Local raw Parquet data lake (Ignored by Git)
│       ├── crosswalks/     # Mappings (e.g. NCES CIP-SOC crosswalk)
│       ├── scorecard/      # College Scorecard Field of Study tables
│       ├── ipeds/          # IPEDS raw tables
│       └── labor_mi/       # Michigan labor projections and wage data
└── dictionaries/           # Variable definition translation tables (*.xlsx, *.csv)
```

> [!NOTE]
> The view `app_pages/wsu_outcomes_matrix.py` now lives in this repository and is the copy
> [app.py](file:///Users/ac7940/Antigravity/IPEDS_sandbox/app.py) loads (the `st.Page` path resolves relative to the project root).
> An older copy still exists at `WSU Data/app_pages/wsu_outcomes_matrix.py` in the sibling
> workspace folder; it is **not** loaded by the app and should be treated as stale.

## 🛠️ 4. Operational Playbooks (zsh Terminal)

### A. Taming the Virtual Environment (Local Run)
To start work, run the workspace initializer script in your terminal:
```bash
# Navigate to the project root and run clock-in script
cd ~/Antigravity/IPEDS_sandbox
./clock_in.sh

# Boot your dashboard locally
./run_dashboard.sh
```

### B. Shipping Code to the Vault (GitHub Sync)
To save your work and push updates to the remote GitHub repository:
```bash
./clock_out.sh "Brief description of the changes you made"
```

### C. Deploying to Production (Streamlit Community Cloud)
Production deployments are fully automated. When you push your code to the `main` branch on GitHub:
1. **GitHub Trigger:** Streamlit Community Cloud detects the commit on the linked repository.
2. **Serverless Deployment:** Streamlit automatically builds and hosts the dashboard using [requirements.txt](file:///Users/ac7940/Antigravity/IPEDS_sandbox/requirements.txt) at a public `*.streamlit.app` URL.
3. **Authentication:** No cloud authorization is required; the application loads pre-compiled, snappy Parquet files directly from local storage.

## 🗺️ 5. Completed Phases & Roadmap

### Phase 1: Interactive Data Lookups (Completed)
- Integrated variable lookup tables in [dictionaries/](file:///Users/ac7940/Antigravity/IPEDS_sandbox/dictionaries) into the metadata search interface.
- Developed dynamic search functionality for full IPEDS database schemas.

### Phase 2: Performance Tuning & DuckDB (Completed)
- Integrated `duckdb` into the dashboard to support high-performance local SQL querying of compiled Parquet tables directly in memory.
- Dramatically accelerated cross-table joins, filters, and dynamic grouping.

### Phase 3: Brand Identity & ADA Accessibility (In Progress)
- Fully implement and audit Wayne State University Brand Colors (`#0C5449` and `#F2A900`) and WCAG 2.1 AA contrast constraints across all charts and pages.
- Ensure screen reader support, descriptive captions, and keyboard accessibility for all dashboard controls.

## 🎨 6. Dashboard Design & Style Guidelines
All dashboards in this project must adhere to the following styling and layout specifications:
- **Data Provenance & Definitions Note:** Provide a source definition note in the sidebar or at the page bottom, confirming whether metrics show awards conferred or unique student headcounts, with active links to [NCES IPEDS](https://nces.ed.gov/ipeds/) or [College Scorecard Data Documentation](https://collegescorecard.ed.gov/data/documentation/).
- **Contextual Subtitles:** Display subtitles under the main titles detailing analysis scopes/cohorts (e.g., "Michigan Public Universities", "Urban Peers", "Public R1 Universities"), timeframes (e.g., "2019 to 2024"), and core metrics.

These rules are formalized for AI developer agents in the workspace rules file at [.agents/AGENTS.md](file:///Users/ac7940/Antigravity/IPEDS_sandbox/.agents/AGENTS.md).

## 🤖 7. Context Anchor for Antigravity Chat
Whenever you start a brand new chat tab in your IDE, paste this paragraph to ground the AI agent:
> "We are working on the IPEDS Streamlit dashboard project located in this workspace root. Our architecture relies purely on local caching via compressed .parquet tables and Excel lookup files inside /dictionaries, running on a local Streamlit server and deployed to Streamlit Community Cloud via GitHub. No external cloud databases or cloud configuration elements exist in our stack. Please read ARCHITECTURE.md in this directory to align your code generation scripts, terminal selections, and prompt styles with our blueprint."

## 🎨 8. UI, Brand Identity & Title II ADA Accessibility Guidelines

All dashboard pages, widgets, and data visualizations must strictly adhere to the Wayne State University Identity Style Guide (2026) and Federal ADA Title II / WCAG 2.1 Level AA compliance standards.

### A. Wayne State Brand Color System
* **Primary WSU Green:** `#0C5449` (PMS 561c) or `#0B4C43` (Digital Web Header). Used for primary buttons, active tabs, header bands, and key metrics.
* **Primary WSU Gold:** `#F2A900` (PMS 1225c). Used exclusively for accents, callout borders, or chart highlights.
* **Neutral Backgrounds:** White (`#FFFFFF`) or Light Gray (`#F8F9FA`).
* **Dark Body Text:** Charcoal/Black (`#111111` or `#222222`).
* **Forbidden Color Combinations:** 
  * ❌ NEVER use Gold text on a Green background (fails WCAG contrast limits).
  * ❌ NEVER use White text on a Gold background.
  * ❌ NEVER use Light Green (`#4A8075`) for body text.

### B. Typography & Brand Styling
* **Font Hierarchy:** Primary web body copy uses `Lato` or `Calibri` (sans-serif fallback). Headlines use `Lato Bold` / `Avenir Heavy`.
* **Header Logos & Branding:**
  * Displays the official WSU Shield/Wordmark as an SVG or high-resolution vector (minimum height **24px**).
  * Required `alt` text on any WSU logo image: `"Wayne State University"`.
  * WSU shield icon must be set as the browser `favicon`.

### C. ADA Title II / WCAG 2.1 AA Accessibility Standards
Under Title II of the ADA, all public university web applications must meet WCAG 2.1 Level AA:
1. **Color Contrast Thresholds (WCAG 1.4.3 & 1.4.11):**
   * Normal text (< 18pt or < 14pt bold): **Minimum 4.5:1 contrast ratio** against its background.
   * Large text (≥ 18pt or ≥ 14pt bold) and UI components/icons: **Minimum 3:0:1 contrast ratio**.
   * Test all custom CSS injected via `st.markdown()` against these ratios.
2. **Information Conveyance Beyond Color (WCAG 1.4.1):**
   * Data charts (Altair / Plotly) must **never rely solely on color** to distinguish data categories or trends.
   * Combine color with **shapes, line patterns (dashed vs. solid), explicit text labels, or direct data annotations**.
3. **Screen Reader & Keyboard Accessibility:**
   * Every Streamlit widget (`st.selectbox`, `st.text_input`, `st.button`) MUST have an explicit label. If a visual label is hidden using `label_visibility="collapsed"`, ensure a clear label exists for assistive screen readers.
   * Interactive charts must include accessible data tables (e.g., using `st.dataframe()` or an expandable data view `st.expander("View Accessible Data Table")`) directly below the visual chart.
4. **Target Sizing & Zoom:**
   * Interactive elements must maintain a minimum touch/click target size of **24x24 pixels**.
   * Layouts must remain fully functional when zoomed up to **200%** in browser settings without breaking grid alignments.

## 🎛️ 9. Unified Cohort Selection & Sidebar Filtering Layout

To ensure all existing and new/forthcoming app pages have a completely consistent sidebar and layout structure, the following guidelines are mandatory:

### A. Sidebar Layout Order
Every dashboard page containing filters must organize its sidebar sequentially as follows:
1. **Sidebar Title/Header:** `st.sidebar.header("Filter Settings")`
2. **Filters & Selectors (Consecutive):** Render all selectboxes, multiselects, sliders, or checkboxes consecutively at the top of the sidebar. Do NOT insert text descriptions, markdown documentation, or external links between selectors.
3. **Cohort Selection Pattern:**
   * **Cohort Selector selectbox:** Allow selecting the group scope (`"Select Cohort Group"`, options: `["Michigan Publics (MASU)", "Urban Peer Publics", "Public R1 Universities"]`).
   * **Cohort Member multiselect:** Populate dynamically with the institutions in the selected cohort, defaulting to all members. Ensure it is named `"Select Universities"` (or `"Select Peer Universities"`).
4. **Markdown Definitions & Sources:** Place the NCES data source attribution markdown block at the very bottom of the sidebar below all interactive widgets, preceded by a horizontal line divider (`---`).

### B. Main Page Title & Captions
1. **Title:** Display a clear main title at the top of the main area (e.g. `st.title("...")`).
2. **Dynamic Context Caption:** Immediately below the title, render a dynamic caption containing the active cohort group, year range, and primary metrics being analyzed (e.g., `st.caption(f"#### Scope: {selected_cohort} | Years: ... | Metrics: ...")`).

## 🧩 10. Shared ETL Definitions (`etl/common.py`)

Anything used by more than one script or page is defined **once**, in [etl/common.py](file:///Users/ac7940/Antigravity/IPEDS_sandbox/etl/common.py), and imported.

### A. What lives there
| Definition | Purpose |
|---|---|
| `normalize_cip()` | Canonical CIP formatter (`XX.XXXX`, leading zeros preserved) |
| `split_college_codes()` | Splits a comma-joined `"BA, EN, LS"` college cell into codes |
| `MICHIGAN_UNIVERSITIES` / `MICHIGAN_UNIVERSITY_IDS` | The 15 Michigan publics, by name and by UNITID |
| `URBAN_PEER_IDS` | Urban peer public cohort |
| `PUBLIC_R1_CONTROL` / `PUBLIC_R1_C21BASIC` | The Public R1 test (CONTROL 1, Carnegie 15) |
| `WSU_UNITID` / `WSU_NAME` | Wayne State identifiers |
| `COLLEGE_NAMES` | WSU school/college code → display name |
| `WSU_GREEN`, `WSU_GOLD`, `PEER_GREY`, `PEER_GREY_LIGHT` | Brand palette (section 8A) |

### B. Why this rule exists
`normalize_cip()` had drifted into three separate copies, and the WSU college-mapping
function existed twice. When the curriculum registry was renamed, the resulting bug had to be
found and fixed **twice in the same day** — once in `scripts/build_pipeline.py` and again in
`etl/compile_app_data.py`, where it sat undetected because the stale mart still held good data.
Duplicated definitions do not fail loudly; they rot in one copy while the other looks fine.

### C. How to import
The project root is the import root. Pages and root-level scripts import directly:

```python
from etl.common import normalize_cip, URBAN_PEER_IDS
```

Scripts executed from a subdirectory (`python etl/compile_app_data.py`, `python scripts/build_pipeline.py`)
put the project root on `sys.path` first, because Python sets `sys.path[0]` to the *script's* folder:

```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.common import normalize_cip  # noqa: E402
```

### D. The one exception
CSS injected through `st.markdown()` keeps its hex colors as literals. CSS is brace-heavy, so
interpolating Python constants would mean escaping every rule for the f-string. Those blocks and
the palette in `etl/common.py` are kept in sync by hand.