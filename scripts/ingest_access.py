#!/usr/bin/env python3
"""
IPEDS Microsoft Access Ingestion Script
This script extracts tables from IPEDS Microsoft Access databases (.accdb)
using mdbtools and loads them directly to Google Cloud BigQuery.
It also parses the consolidated Excel data dictionaries (*Tablesdoc.xlsx)
and uploads a global metadata dictionary to BigQuery.
"""

import os
import sys
import glob
import argparse
import zipfile
import subprocess
import tempfile
import shutil
import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

def parse_args():
    parser = argparse.ArgumentParser(description="Ingest IPEDS MS Access databases into BigQuery.")
    parser.add_argument("--dataset", default="ipeds", help="BigQuery dataset ID (default: ipeds)")
    parser.add_argument("--project", default=None, help="GCP Project ID (defaults to active project)")
    parser.add_argument("--access-dir", default="Access_files", help="Directory containing zip/excel Access files (default: Access_files)")
    parser.add_argument("--dry-run", action="store_true", help="Parse files and schemas without uploading to BigQuery")
    parser.add_argument("--year", default=None, help="Process only a specific academic year (e.g. 2023-24)")
    parser.add_argument("--table", default=None, help="Process only a specific table name (e.g. HD2023)")
    return parser.parse_args()

def clean_name(name):
    """Clean table or variable names to match BigQuery naming standard (lowercase, alphanumeric + underscores)."""
    return name.strip().lower()

def get_bq_type(var_name, var_info):
    """
    Determines the BigQuery field type based on the variable metadata.
    """
    col_upper = var_name.upper()
    
    # Overrides to preserve leading zeros
    if col_upper == "UNITID" or "ZIP" in col_upper or "FIPS" in col_upper or "COUNTY" in col_upper:
        return "STRING"
        
    data_type = var_info.get("DataType", "A")
    fmt = var_info.get("Format", "ALPHA").upper()
    
    if data_type == "A" or fmt == "ALPHA":
        return "STRING"
    elif data_type == "N":
        if "DISC" in fmt:
            return "INT64"
        elif "CONT" in fmt:
            return "FLOAT64"
        else:
            return "FLOAT64" # fallback numeric
            
    return "STRING"

def parse_tables_metadata(excel_path, year_str):
    """
    Parses the Tables sheet from the Excel dictionary to get table titles and descriptions.
    """
    xl = pd.ExcelFile(excel_path)
    # Find tables sheet case-insensitively
    table_sheet = next((s for s in xl.sheet_names if s.lower().startswith("tables")), None)
    if not table_sheet:
        print(f"Warning: No tables sheet found in {excel_path}")
        return {}
        
    df = pd.read_excel(xl, table_sheet)
    df.columns = [c.strip() for c in df.columns]
    
    # Map sheet columns case-insensitively
    col_map = {c.lower(): c for c in df.columns}
    name_col = col_map.get("tablename")
    title_col = col_map.get("tabletitle") or col_map.get("description")
    
    if not name_col:
        print(f"Warning: tablename col not found in {table_sheet} sheet of {excel_path}")
        return {}
        
    table_titles = {}
    for _, row in df.iterrows():
        t_name = str(row[name_col]).strip().upper()
        if not t_name:
            continue
        title = str(row[title_col]).strip() if title_col and pd.notna(row[title_col]) else ""
        table_titles[t_name] = title
        
    return table_titles

def parse_vartable_metadata(excel_path, table_titles, year_str):
    """
    Parses the varTable sheet from the Excel dictionary and returns a nested schema map.
    """
    xl = pd.ExcelFile(excel_path)
    var_sheet = next((s for s in xl.sheet_names if s.lower().startswith("vartable")), None)
    if not var_sheet:
        print(f"Warning: No vartable sheet found in {excel_path}")
        return {}, []
        
    df = pd.read_excel(xl, var_sheet)
    df.columns = [c.strip() for c in df.columns]
    
    col_map = {c.lower(): c for c in df.columns}
    t_col = col_map.get("tablename")
    v_col = col_map.get("varname")
    dt_col = col_map.get("datatype")
    fmt_col = col_map.get("format")
    title_col = col_map.get("vartitle")
    desc_col = col_map.get("longdescription")
    
    if not (t_col and v_col):
        print(f"Warning: tablename or varname col not found in {var_sheet} of {excel_path}")
        return {}, []
        
    schema_map = {}
    metadata_list = []
    
    for _, row in df.iterrows():
        table_name = str(row[t_col]).strip().upper()
        var_name = str(row[v_col]).strip().upper()
        if not table_name or not var_name:
            continue
            
        data_type = str(row[dt_col]).strip().upper() if dt_col and pd.notna(row[dt_col]) else "A"
        fmt = str(row[fmt_col]).strip().upper() if fmt_col and pd.notna(row[fmt_col]) else "ALPHA"
        title = str(row[title_col]).strip() if title_col and pd.notna(row[title_col]) else ""
        long_desc = str(row[desc_col]).strip() if desc_col and pd.notna(row[desc_col]) else ""
        
        # Build nested schema mapping
        if table_name not in schema_map:
            schema_map[table_name] = {}
        schema_map[table_name][var_name] = {
            "DataType": data_type,
            "Format": fmt,
            "Title": title,
            "LongDescription": long_desc
        }
        
        # Build flat list for metadata dictionary upload
        metadata_list.append({
            "year": year_str,
            "table_name": table_name.lower(),
            "table_title": table_titles.get(table_name, ""),
            "var_name": var_name.lower(),
            "var_title": title,
            "long_description": long_desc,
            "data_type": data_type,
            "format": fmt
        })
        
    return schema_map, metadata_list

def main():
    args = parse_args()
    
    # 1. Initialize BigQuery Client
    if args.dry_run:
        print("--- RUNNING IN DRY-RUN MODE ---")
        client = None
    else:
        client = bigquery.Client(project=args.project)
        project_id = client.project
        dataset_ref = bigquery.DatasetReference(project_id, args.dataset)
        
        # Ensure the dataset exists
        try:
            client.get_dataset(dataset_ref)
            print(f"Dataset {project_id}.{args.dataset} already exists.")
        except NotFound:
            print(f"Dataset {project_id}.{args.dataset} not found. Creating it...")
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"
            client.create_dataset(dataset)
            print(f"Dataset {args.dataset} created successfully.")

    # 2. Get list of Zip files to process
    zip_pattern = os.path.join(args.access_dir, "*.zip")
    zip_files = sorted(glob.glob(zip_pattern))
    if not zip_files:
        print(f"No zip files found matching {zip_pattern}")
        sys.exit(1)
        
    # Compile a list of years we can process
    all_metadata_records = []
    
    # Process each zip file
    for zip_path in zip_files:
        zip_filename = os.path.basename(zip_path)
        # Parse academic year from filename, e.g. IPEDS_2023-24_Final.zip -> 2023-24
        # Filename formats: IPEDS_2023-24_Final.zip or IPEDS_2024-25_Provisional.zip
        parts = zip_filename.split("_")
        if len(parts) >= 2:
            year_str = parts[1]
        else:
            year_str = os.path.splitext(zip_filename)[0]
            
        if args.year and args.year != year_str:
            print(f"Skipping year {year_str} (requested: {args.year})")
            continue
            
        print("\n" + "="*60)
        print(f"Processing Academic Year: {year_str}")
        print(f"Zip File: {zip_filename}")
        
        # Find the unzipped Tablesdoc Excel dictionary
        # e.g., IPEDS_2023-24_Tablesdoc.xlsx
        excel_name = f"IPEDS_{year_str}_Tablesdoc.xlsx"
        excel_path = os.path.join(args.access_dir, excel_name)
        if not os.path.exists(excel_path):
            # Try finding alternate name inside zip
            excel_path = None
            for f in glob.glob(os.path.join(args.access_dir, f"*_{year_str}_Tablesdoc.xlsx")):
                excel_path = f
                break
                
        if not excel_path or not os.path.exists(excel_path):
            print(f"WARNING: Metadata dictionary {excel_name} not found in {args.access_dir}. Skipping year {year_str}.")
            continue
            
        print(f"Using dictionary Excel: {os.path.basename(excel_path)}")
        
        # Parse Metadata dictionaries
        table_titles = parse_tables_metadata(excel_path, year_str)
        schema_map, metadata_records = parse_vartable_metadata(excel_path, table_titles, year_str)
        if not schema_map:
            print(f"ERROR: Failed to parse metadata schema map for {year_str}. Skipping year.")
            continue
            
        all_metadata_records.extend(metadata_records)
        
        # Create a temp directory to unzip the Access ACCDB file
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Extracting zip contents to temp directory...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Find the .accdb file in the zip
                accdb_internal_name = next((name for name in zip_ref.namelist() if name.lower().endswith(".accdb")), None)
                if not accdb_internal_name:
                    print(f"ERROR: No .accdb file found inside {zip_filename}. Skipping.")
                    continue
                zip_ref.extract(accdb_internal_name, temp_dir)
                accdb_path = os.path.join(temp_dir, accdb_internal_name)
                
            print(f"Extracted MS Access database: {accdb_internal_name}")
            
            # Use mdbtools to get table list
            try:
                tables_raw = subprocess.check_output(["mdb-tables", "-1", accdb_path]).decode("utf-8")
                tables = [t.strip() for t in tables_raw.split("\n") if t.strip()]
            except Exception as e:
                print(f"ERROR: Failed to run mdb-tables on {accdb_internal_name}: {e}")
                continue
                
            # Filter out internal/system tables
            tables = [t for t in tables if not (t.startswith("MSys") or t.startswith("~") or t.startswith("_"))]
            print(f"Found {len(tables)} data tables in database.")
            
            # Ingest tables
            for table_name in tables:
                table_upper = table_name.upper()
                if args.table and args.table.upper() != table_upper:
                    continue
                    
                print(f"\n  --> Table: {table_name}")
                
                # Export the table from ACCDB to a temp CSV file
                csv_temp_fd, csv_temp_path = tempfile.mkstemp(suffix=".csv")
                os.close(csv_temp_fd) # close file descriptor to let subprocess write to it
                
                try:
                    with open(csv_temp_path, "w") as f_out:
                        subprocess.run(["mdb-export", accdb_path, table_name], stdout=f_out, check=True)
                except Exception as e:
                    print(f"  ERROR: Failed to export table {table_name} via mdb-export: {e}")
                    if os.path.exists(csv_temp_path):
                        os.unlink(csv_temp_path)
                    continue
                    
                # Read header to find columns
                try:
                    df_sample = pd.read_csv(csv_temp_path, nrows=1)
                    table_cols = list(df_sample.columns)
                except Exception as e:
                    # Empty or invalid table
                    print(f"  Warning: Empty or unreadable exported table {table_name}: {e}")
                    if os.path.exists(csv_temp_path):
                        os.unlink(csv_temp_path)
                    continue
                    
                # Build BigQuery schema
                bq_schema = []
                overrides = []
                for col in table_cols:
                    col_upper = col.strip().upper()
                    # Find metadata info
                    var_info = schema_map.get(table_upper, {}).get(col_upper, {})
                    bq_type = get_bq_type(col, var_info)
                    
                    if col_upper == "UNITID" or "ZIP" in col_upper or "FIPS" in col_upper or "COUNTY" in col_upper:
                        overrides.append(f"{col}->{bq_type}")
                        
                    bq_schema.append(bigquery.SchemaField(name=col, field_type=bq_type))
                    
                print(f"  Columns: {len(bq_schema)} | Overrides: {len(overrides)}")
                
                if args.dry_run:
                    print("  [Dry-Run] Skipped BigQuery ingestion.")
                    os.unlink(csv_temp_path)
                    continue
                    
                # Ingest to BigQuery
                # BigQuery table ID is named like dataset.tablename, e.g. ipeds.hd2023
                bq_table_name = table_name.lower()
                bq_table_id = f"{client.project}.{args.dataset}.{bq_table_name}"
                
                job_config = bigquery.LoadJobConfig(
                    schema=bq_schema,
                    source_format=bigquery.SourceFormat.CSV,
                    skip_leading_rows=1,
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
                )
                
                try:
                    with open(csv_temp_path, "rb") as source_file:
                        load_job = client.load_table_from_file(
                            source_file,
                            bq_table_id,
                            job_config=job_config
                        )
                    load_job.result() # Wait for job
                    
                    # Verify row count
                    bq_table = client.get_table(bq_table_id)
                    print(f"  SUCCESS: Ingested {bq_table.num_rows} rows into BigQuery table: {bq_table_name}")
                except Exception as e:
                    print(f"  ERROR: Failed to load table {table_name} into BigQuery: {e}")
                finally:
                    os.unlink(csv_temp_path)

    # 3. Upload Metadata Dictionary to BigQuery
    if all_metadata_records and not args.dry_run:
        print("\n" + "="*60)
        print("Uploading global Metadata Dictionary to BigQuery...")
        
        metadata_df = pd.DataFrame(all_metadata_records)
        metadata_table_id = f"{client.project}.{args.dataset}.metadata_dictionary"
        
        metadata_schema = [
            bigquery.SchemaField(name="year", field_type="STRING"),
            bigquery.SchemaField(name="table_name", field_type="STRING"),
            bigquery.SchemaField(name="table_title", field_type="STRING"),
            bigquery.SchemaField(name="var_name", field_type="STRING"),
            bigquery.SchemaField(name="var_title", field_type="STRING"),
            bigquery.SchemaField(name="long_description", field_type="STRING"),
            bigquery.SchemaField(name="data_type", field_type="STRING"),
            bigquery.SchemaField(name="format", field_type="STRING")
        ]
        
        job_config = bigquery.LoadJobConfig(
            schema=metadata_schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
        )
        
        try:
            load_job = client.load_table_from_dataframe(
                metadata_df,
                metadata_table_id,
                job_config=job_config
            )
            load_job.result()
            print(f"SUCCESS: Uploaded {len(all_metadata_records)} metadata definitions to table: metadata_dictionary")
        except Exception as e:
            print(f"ERROR: Failed to load metadata dictionary to BigQuery: {e}")
            
    print("\nAccess Database Ingestion finished.")

if __name__ == "__main__":
    main()
