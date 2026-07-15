# IPEDS Dashboards

This repository contains tools for ingesting and analyzing Higher Education data from the Integrated Postsecondary Education Data System (IPEDS) via Google BigQuery and Streamlit.

## Project Structure

```
.
├── app.py                     # Main Streamlit application entrypoint
├── app_pages/                 # Streamlit dashboard pages
│   ├── overview.py            # Dashboard landing page
│   ├── spending_analyzer.py   # Spending analyzer dashboard
│   └── cip_market_share.py    # Degrees awarded / CIP market share dashboard
├── scripts/                   # Backend and data ingestion scripts
│   ├── ingest.py
│   ├── ingest_access.py
│   └── upload_cip_dict.py
├── data/                      # Raw data files (ignored by Git)
├── environment/               # Python virtual environment (ignored by Git)
├── requirements.txt           # Python package dependencies
├── run_dashboard.sh           # Utility script to launch the Streamlit app
└── rebuild_env.sh             # Utility script to rebuild the Python virtual environment
```

## Setup & Installation

1. **Create the Virtual Environment**:
   Run the provided build script to create the environment and install dependencies:
   ```bash
   ./rebuild_env.sh
   ```
   *(Alternatively, you can manually run `python3 -m venv environment` followed by `pip install -r requirements.txt`).*

2. **Google Cloud Credentials**:
   Ensure you are authenticated with Google Cloud and have access to the BigQuery project (`project-9a1f71b9-7c50-4df5-adb`). 
   If running locally, you can authenticate via:
   ```bash
   gcloud auth application-default login
   ```

## Running the Application

To launch the Streamlit dashboards:
```bash
./run_dashboard.sh
```

Alternatively, you can manually activate the environment and run Streamlit:
```bash
source environment/bin/activate
streamlit run app.py
```
