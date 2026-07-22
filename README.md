# IPEDS Dashboards

This repository contains tools for analyzing Higher Education data from the Integrated Postsecondary Education Data System (IPEDS) using a fast, local-first Streamlit web application.

---

## 🏗️ Project Structure

```plaintext
.
├── .venv/                     # Python virtual environment (ignored by Git)
├── app.py                     # Main Streamlit application entrypoint & routing
├── app_pages/                 # Streamlit dashboard pages
│   ├── overview.py            # Dashboard landing page & architecture explanation
│   ├── spending_analyzer.py   # Spending analyzer dashboard
│   └── cip_market_share.py    # Degrees awarded / CIP market share dashboard
├── etl/                       # Raw data ingestion pipeline orchestrators
│   └── ingest_master.py       # Fetches public datasets and converts them to Snappy-Parquet
├── scripts/                   # Local pipeline and processing scripts
│   └── build_pipeline.py      # Cleans and merges Pathfinder, SOC, and Parquet data
├── data/                      # Local data directory (ignored by Git)
│   └── raw/                   # Raw data lake Parquet files
│       ├── crosswalks/        # Mappings (NCES CIP-SOC Crosswalk)
│       ├── scorecard/         # College Scorecard Field of Study tables
│       ├── ipeds/             # IPEDS raw tables
│       └── labor_mi/          # Michigan labor projections and wages
├── dictionaries/              # Variable definitions and Excel dictionaries
├── requirements.txt           # Python package dependencies
├── clock_in.sh                # Script to sync main branch and set up the .venv environment
├── clock_out.sh               # Script to stage, commit, and push work to GitHub
├── run_dashboard.sh           # Utility script to launch the Streamlit app
└── rebuild_env.sh             # Utility script to clean and recreate the Python virtual environment
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
