# IPEDS Dashboards

This repository contains tools for analyzing Higher Education data from the Integrated Postsecondary Education Data System (IPEDS) using a fast, local-first Streamlit web application.

---

## 🏗️ Project Structure

```plaintext
.
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
│   ├── common.py           # SHARED definitions - import these, never re-paste them
│   ├── compile_app_data.py # Local aggregator creating local application Parquet databases
│   ├── ingest_master.py    # Fetches public datasets and converts them to Snappy-Parquet
│   └── ingest_nih_reporter.py # Fetches and structures NIH RePORTER data
├── scripts/                # Data cleaning and pipeline operations
│   ├── build_pipeline.py   # Local ETL pipeline merging Pathfinder, SOC, and cached Parquet data
│   ├── clean_labor_mi_raw.py    # Normalizes a fresh MILMI wage download
│   └── clean_crosswalk_raw.py   # Fixes/consolidates data/raw/crosswalks/
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
> The dashboard page `app_pages/wsu_outcomes_matrix.py` is configured in [app.py](file:///Users/ac7940/Antigravity/IPEDS_sandbox/app.py) but resides in the sibling workspace folder `WSU Data/app_pages/wsu_outcomes_matrix.py`.

---

## ⚙️ Setup & Installation

### 1. Developer Synchronization (Recommended)
Every time you open your terminal to start coding, navigate to this project folder and run the developer synchronization script:
```bash
# Navigate to project root
cd ~/Antigravity/IPEDS_sandbox

# Pull latest commits, verify environment, and install dependencies
./clock_in.sh
```

### 2. Manual Environment Build
If you need to rebuild your environment from scratch:
```bash
./rebuild_env.sh
```
*(Alternatively, you can manually run `python3 -m venv .venv` followed by `./.venv/bin/pip install -r requirements.txt`).*

### 3. Populating the Raw Data Lake
To fetch the public raw datasets (NCES crosswalk and College Scorecard) and convert them to local Snappy-compressed Parquet files, run the master ingestion script:
```bash
./.venv/bin/python etl/ingest_master.py
```
To run only a specific ingestion task, use the `--only` option:
```bash
# Ingest only the CIP-SOC crosswalk
./.venv/bin/python etl/ingest_master.py --only crosswalk

# Ingest only the College Scorecard Field of Study dataset
./.venv/bin/python etl/ingest_master.py --only scorecard
```

> [!IMPORTANT]
> Run every ETL script **from the project root**. They resolve data paths relative to the
> current working directory, and they import shared definitions from `etl/common.py`.

### 4. Refreshing the Michigan Labor Market Data
The MILMI wage export changes shape between downloads (comma vs. tab, latin-1 vs. UTF-16,
statewide-only vs. 31 geographies). After re-downloading `IOWage_data.csv`, normalize it first:
```bash
./.venv/bin/python scripts/clean_labor_mi_raw.py
```
Then rebuild the marts that depend on it:
```bash
./.venv/bin/python build_demand.py
./.venv/bin/python scripts/build_pipeline.py
```

> [!WARNING]
> Never open `IOWage_data.csv` in Excel before running the cleaner. Excel autocorrects SOC
> codes in major group 11 (Management) into dates — `11-1011` becomes `Nov-11` — which silently
> drops every Management wage from the marts.

### 5. Shared ETL Definitions
The CIP normalizer, peer-cohort lists, WSU college codes, and brand colors live in
[etl/common.py](etl/common.py). Import them rather than re-declaring them:
```python
from etl.common import normalize_cip, URBAN_PEER_IDS, WSU_GREEN
```
See ARCHITECTURE.md section 10 for the full rule, including the `sys.path` bootstrap that
scripts in `etl/` and `scripts/` use.

---

## 🚀 Running the Application

To launch the Streamlit dashboards locally:
```bash
./run_dashboard.sh
```

Alternatively, you can manually activate the virtual environment and run Streamlit directly:
```bash
source .venv/bin/activate
streamlit run app.py
```

To sync your code and push updates back to GitHub when finishing work:
```bash
./clock_out.sh "Your commit description here"
```

---

## ☁️ Publishing to Production

This dashboard is built to deploy automatically to **Streamlit Community Cloud** straight from GitHub:
1. Push your latest code changes to the `main` branch on GitHub (via `./clock_out.sh`).
2. Log into [Streamlit Community Cloud](https://streamlit.io/cloud) and connect this repository.
3. Configure the main file path as `app.py`.
4. Streamlit will build your app serverlessly. Since all datasets are compiled into highly compressed, local Parquet tables in [data/](file:///Users/ac7940/Antigravity/IPEDS_sandbox/data), the dashboard does not require any cloud credentials or database connections at runtime.
