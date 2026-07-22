# IPEDS Dashboard: Project Status & Architecture Blueprint

## 📜 1. Context & Scope
- **Target Audience:** Higher education data consumers looking for fast, intuitive, multi-page web dashboards to explore the last 5 years of National Center for Education Statistics (NCES) IPEDS institutional data.
- **Developer Mindset:** Re-engaging with coding after a multi-decade hiatus (BASIC/FORTRAN backgrounds). Value simplicity, lean toolsets, local-first environments, and zero-to-low cost footprint.
- **Primary Constraints:** Avoid heavy database infrastructure, container virtualization, or complex cloud authentication overhead. Decouple completely from external cloud databases.

## 🏗️ 2. Architectural Evolution
We transitioned from a legacy, cloud-hosted distributed pipeline to a pure local-memory, file-based execution model:

| Attribute | Legacy Cloud Pipeline | Current Local-First Architecture |
| :--- | :--- | :--- |
| **Data Engine** | Google BigQuery (Client-Server SQL) | In-Memory Pandas + Apache Parquet |
| **Dictionary Setup** | Stored remotely in BigQuery | Local `.xlsx` NCES lookups in [dictionaries/](file:///Users/ac7940/Antigravity/IPEDS_sandbox/dictionaries) |
| **Auth Complexity** | Strict GCP Service Account Keys & OAuth | Zero Application-level authentication |
| **Compute Profile** | External Cloud Data Warehousing | Fast, local multi-threaded file execution |
| **Hosting Strategy** | Google Cloud Run Container (Retired) | Streamlit Community Cloud (GitHub Synced) |
| **Financial Cost** | Variable cloud fees ($) | Guaranteed $0.00/month (Free tier) |

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
├── scripts/                # Data cleaning and pipeline operations
│   └── build_pipeline.py   # Local ETL pipeline merging Pathfinder, SOC, and cached Parquet data
├── data/                   # Cached local Parquet tables (*.parquet)
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

## 🤖 6. Context Anchor for Antigravity Chat
Whenever you start a brand new chat tab in your IDE, paste this paragraph to ground the AI agent:
> "We are working on the IPEDS Streamlit dashboard project located in this workspace root. Our architecture relies purely on local caching via compressed .parquet tables and Excel lookup files inside /dictionaries, running on a local Streamlit server and deployed to Streamlit Community Cloud via GitHub. No GCP/BigQuery elements exist in our stack. Please read ARCHITECTURE.md in this directory to align your code generation scripts, terminal selections, and prompt styles with our blueprint."