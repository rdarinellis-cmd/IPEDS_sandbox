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
│   └── spending_analyzer.py# Cost/spending analysis dashboard (development branch)
├── etl/                    # Raw data ingestion pipeline orchestrators
│   └── ingest_master.py    # Fetches public datasets and converts them to Snappy-Parquet
├── scripts/                # Data cleaning and pipeline operations
│   └── build_pipeline.py   # Local ETL pipeline merging Pathfinder, SOC, and cached Parquet data
├── data/                   # Data directory (Parquet caches)
│   └── raw/                # Local raw Parquet data lake (Ignored by Git)
│       ├── crosswalks/     # Mappings (e.g. NCES CIP-SOC crosswalk)
│       ├── scorecard/      # College Scorecard Field of Study tables
│       ├── ipeds/          # IPEDS raw tables
│       └── labor_mi/       # Michigan labor projections and wage data
└── dictionaries/           # Variable definition translation tables (*.xlsx, *.csv)
```

> [!NOTE]
> The view `app_pages/wsu_outcomes_matrix.py` is configured in [app.py](file:///Users/ac7940/Antigravity/IPEDS_sandbox/app.py) but resides in the sibling folder `WSU Data/app_pages/wsu_outcomes_matrix.py` in the developer's workspace.

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

## 🗺️ 5. Future Project Roadmap

### Phase 1: Interactive Data Lookups (Current Goal)
- Integrate the variable lookup tables in [dictionaries/](file:///Users/ac7940/Antigravity/IPEDS_sandbox/dictionaries) directly into the interface.
- Add human-readable dropdown selections (e.g. displaying "Public, 4-year" instead of the raw database flag `CONTROL = 1`).

### Phase 2: Performance Tuning (DuckDB Upgrade)
- If cross-table joins or grouping operations become slow, integrate `duckdb` into the project requirements.
- DuckDB executes localized serverless SQL queries straight inside the application's memory without requiring external databases or server processes.

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
* **Primary WSU Green:** `#0C5449` (PMS 561c) or `#0B4C43` (Digital Web Header).
* **Primary WSU Gold:** `#FFCC33` (PMS 1225c). Used exclusively for accents and chart highlights.
* **Forbidden Combinations:** Never use Gold text on Green background or White text on Gold background (violates WCAG contrast rules).

### B. Title II ADA / WCAG 2.1 AA Accessibility
* **Color Contrast:** All body text must maintain a minimum **4.5:1 contrast ratio**.
* **Redundant Encoding:** Charts (Altair) must use shapes, dashed lines, or explicit labels alongside color—never color alone.
* **Data Equivalents:** Include an accessible `st.dataframe()` or `st.expander()` data view beneath every graphic visualization for screen reader users.
* **Widget Labeling:** All inputs must have explicit labels for screen reader accessibility.
