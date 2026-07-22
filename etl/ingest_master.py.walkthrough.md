# Walkthrough - Academic Portfolio Intelligence Ingestion Layer

We have successfully constructed the initial scaffolding for the Academic Portfolio Intelligence Workspace's local ingestion layer, creating the `./data/raw/` data lake directory structure and writing the modular, RAM-efficient `etl/ingest_master.py` orchestrator script.

---

## 📁 Scaffolding the Data Lake Directory

We created the local raw data lake folders:
- `./data/raw/crosswalks/` (for mapping tables)
- `./data/raw/scorecard/` (for College Scorecard files)
- `./data/raw/ipeds/` (reserved for future IPEDS ingestion tasks)
- `./data/raw/labor_mi/` (reserved for future Michigan employment projection tasks)

---

## ⚙️ Ingestion & Conversion Architecture

We implemented [etl/ingest_master.py](file:///Users/ac7940/Antigravity/IPEDS_sandbox/etl/ingest_master.py) with the following features:
1. **Low-Memory Streaming Downloads:** Uses chunked HTTP streaming (via `requests`) to download large remote archives directly to a temporary folder `./data/temp/` without consuming excess system RAM.
2. **Selective Zip Extraction:** Programmatically extracts only the target CSV file from downloaded ZIP archives using standard `zipfile` streams, keeping the filesystem clean.
3. **Chunked Parquet Conversion:** 
   - Uses Pandas `pd.read_csv` in a chunk-by-chunk generator loop.
   - Forces all columns to read as strings (`dtype=str`) to bypass type mismatch warnings in dirty CSV datasets (e.g., privacy suppressed cell markings like `"PS"` or `"*"` appearing in otherwise numeric columns).
   - Writes Parquet files incrementally using the `pyarrow.parquet.ParquetWriter` Snappy-compressed format.
4. **Auto-Cleanup:** Cleans up temporary download artifacts upon completion (or script failure) using a `try-finally` block.
5. **Command-Line Interface:** Implements `--only <task>` CLI flags to run specific ingestions independently.

---

## 🧪 Verification & Results

We successfully executed and verified both initial datasets:

### 1. NCES CIP-to-SOC Crosswalk Ingestion
- **Execution:** `python etl/ingest_master.py --only crosswalk`
- **Output:** Successfully fetched the official NCES Excel file, parsed sheet `CIP-SOC`, and exported it to [data/raw/crosswalks/cip2020_soc2018_crosswalk.parquet](file:///Users/ac7940/Antigravity/IPEDS_sandbox/data/raw/crosswalks/cip2020_soc2018_crosswalk.parquet) (0.09 MB).

### 2. College Scorecard Field of Study Ingestion
- **Execution:** `python etl/ingest_master.py --only scorecard`
- **Output:** Successfully streamed the 16.4 MB zip file from the Department of Education S3 server, extracted the CSV, parsed it in chunks, and saved it to [data/raw/scorecard/most_recent_cohorts_field_of_study.parquet](file:///Users/ac7940/Antigravity/IPEDS_sandbox/data/raw/scorecard/most_recent_cohorts_field_of_study.parquet) (23.46 MB).
- **Validation:** Confirmed readability using a Python snippet to load the first few rows:
  ```python
  import pandas as pd
  print(pd.read_parquet('data/raw/scorecard/most_recent_cohorts_field_of_study.parquet').head())
  ```
  This loaded and displayed the 178 variables correctly (including strings like `PS`).
