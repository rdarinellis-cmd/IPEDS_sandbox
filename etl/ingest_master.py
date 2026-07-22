#!/usr/bin/env python3
"""
ingest_master.py

Central orchestrator for downloading raw higher education datasets and converting
them into Snappy-compressed Parquet tables under ./data/raw/.

Designed with low RAM overhead (streaming downloads, chunked CSV to Parquet conversion).
"""

import os
import shutil
import zipfile
import argparse
import requests
import pandas as pd
import sys

# ---- Configuration & URLs ----------------------------------------------------
DATA_DIR = "./data/raw"
TEMP_DIR = "./data/temp"

URL_CIP_SOC_XWALK = "https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx"
URL_SCORECARD_FOS  = "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Field-of-Study_06102026.zip"

PATH_CROSSWALKS_DIR = os.path.join(DATA_DIR, "crosswalks")
PATH_SCORECARD_DIR   = os.path.join(DATA_DIR, "scorecard")
PATH_IPEDS_DIR       = os.path.join(DATA_DIR, "ipeds")
PATH_LABOR_MI_DIR    = os.path.join(DATA_DIR, "labor_mi")

# ---- Helper Functions --------------------------------------------------------

def init_folders():
    """Create raw data lake directory structure."""
    for folder in [PATH_CROSSWALKS_DIR, PATH_SCORECARD_DIR, PATH_IPEDS_DIR, PATH_LABOR_MI_DIR, TEMP_DIR]:
        os.makedirs(folder, exist_ok=True)


def cleanup_temp():
    """Remove the temporary extraction folder."""
    if os.path.exists(TEMP_DIR):
        print(f"🧹 Cleaning up temp directory: {TEMP_DIR}...")
        shutil.rmtree(TEMP_DIR)


def download_file(url, dest_path, chunk_size=1024 * 1024):
    """Downloads a file from url to dest_path using chunked streaming to save RAM."""
    print(f"📡 Downloading: {url}")
    print(f"   Saving to:  {dest_path}")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                
    file_size_mb = os.path.getsize(dest_path) / (1024 * 1024)
    print(f"✅ Download complete ({file_size_mb:.2f} MB)")


def convert_csv_to_parquet(csv_path, parquet_path, chunksize=100000):
    """Memory-efficient incremental CSV-to-Parquet conversion using PyArrow."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    print(f"🔄 Converting CSV to Snappy-Parquet...")
    print(f"   Source: {csv_path}")
    print(f"   Target: {parquet_path}")
    
    writer = None
    try:
        # Read in chunks, forcing all columns to strings to prevent schema type conflicts across chunks
        chunks = pd.read_csv(csv_path, chunksize=chunksize, dtype=str)
        for chunk in chunks:
            # Clean column names (strip whitespace)
            chunk.columns = [c.strip() for c in chunk.columns]
            
            # Convert Pandas chunk to PyArrow Table
            table = pa.Table.from_pandas(chunk, preserve_index=False)
            
            if writer is None:
                writer = pq.ParquetWriter(parquet_path, table.schema, compression="snappy")
            
            writer.write_table(table)
            
    finally:
        if writer:
            writer.close()
            
    parquet_size_mb = os.path.getsize(parquet_path) / (1024 * 1024)
    print(f"✅ Conversion complete ({parquet_size_mb:.2f} MB)")


def extract_zip_member(zip_path, target_pattern, extract_to):
    """Locate and extract a single file from a zip matching a text pattern."""
    print(f"📦 Scanning zip archive: {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if target_pattern.lower() in name.lower() and name.endswith(".csv"):
                base_name = os.path.basename(name)
                dest = os.path.join(extract_to, base_name)
                print(f"   Found match: {name} -> Extracting to: {dest}")
                
                with z.open(name) as source, open(dest, "wb") as target:
                    shutil.copyfileobj(source, target)
                return dest
                
    raise FileNotFoundError(f"Could not find any CSV matching '{target_pattern}' in zip {zip_path}")

# ---- Ingestion Tasks ---------------------------------------------------------

def ingest_crosswalk():
    """NCES CIP-to-SOC Crosswalk ingestion task (Excel sheet to Parquet)."""
    print("\n==================================================")
    print("🚀 Task: Ingesting CIP2020-to-SOC2018 Crosswalk")
    print("==================================================")
    
    temp_xlsx = os.path.join(TEMP_DIR, "cip_soc_xwalk.xlsx")
    parquet_dest = os.path.join(PATH_CROSSWALKS_DIR, "cip2020_soc2018_crosswalk.parquet")
    
    # Download the Excel file
    download_file(URL_CIP_SOC_XWALK, temp_xlsx)
    
    # Read sheet "CIP-SOC" and save directly to Snappy Parquet (file is small, fits in RAM easily)
    print("🔄 Processing Excel spreadsheet...")
    df = pd.read_excel(temp_xlsx, sheet_name="CIP-SOC")
    df.columns = [str(c).strip() for c in df.columns]
    
    df.to_parquet(parquet_dest, index=False, compression="snappy")
    parquet_size_mb = os.path.getsize(parquet_dest) / (1024 * 1024)
    print(f"✅ Task complete: saved to {parquet_dest} ({parquet_size_mb:.2f} MB)")


def ingest_scorecard():
    """College Scorecard Field of Study ingestion task (ZIP -> CSV -> Parquet)."""
    print("\n==================================================")
    print("🚀 Task: Ingesting College Scorecard Field of Study")
    print("==================================================")
    
    temp_zip = os.path.join(TEMP_DIR, "scorecard_fos.zip")
    parquet_dest = os.path.join(PATH_SCORECARD_DIR, "most_recent_cohorts_field_of_study.parquet")
    
    # Download ZIP file
    download_file(URL_SCORECARD_FOS, temp_zip)
    
    # Extract the CSV file
    temp_csv = extract_zip_member(temp_zip, "Field-of-Study", TEMP_DIR)
    
    # Chunked convert to Parquet
    convert_csv_to_parquet(temp_csv, parquet_dest)
    print(f"✅ Task complete: saved to {parquet_dest}")


# ---- Orchestrator Main -------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Orchestrator for raw data lake ingestion.")
    parser.add_argument(
        "--only", 
        choices=["crosswalk", "scorecard"], 
        help="Run only a specific task. Runs all by default."
    )
    args = parser.parse_args()
    
    init_folders()
    
    try:
        if args.only == "crosswalk":
            ingest_crosswalk()
        elif args.only == "scorecard":
            ingest_scorecard()
        else:
            ingest_crosswalk()
            ingest_scorecard()
            
    finally:
        cleanup_temp()
        
    print("\n📦 Triggering App Data compilation...")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import compile_app_data
        compile_app_data.main()
    except Exception as e:
        print(f"⚠️ Warning: App data compilation failed: {e}")
        
    print("\n🏁 Master Ingestion Pipeline completed successfully!")


if __name__ == "__main__":
    main()
