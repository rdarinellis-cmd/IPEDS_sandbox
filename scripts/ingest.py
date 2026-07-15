#!/usr/bin/env python3
"""
IPEDS Dashboard BigQuery Ingestion Script
This script reads the IPEDS data dictionaries to map schema types
and uploads CSV files directly to Google Cloud BigQuery.
"""

import os
import sys
import glob
import argparse
import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

def parse_args():
    parser = argparse.ArgumentParser(description="Ingest IPEDS CSVs into BigQuery using Excel data dictionaries.")
    parser.add_argument("--dataset", default="ipeds", help="BigQuery dataset ID (default: ipeds)")
    parser.add_argument("--project", default=None, help="GCP Project ID (defaults to active project)")
    parser.add_argument("--data-dir", default="data", help="Directory containing CSV files (default: data)")
    parser.add_argument("--dict-dir", default="dictionaries", help="Directory containing Excel dictionaries (default: dictionaries)")
    parser.add_argument("--dry-run", action="store_true", help="Print schema and mappings without uploading to BigQuery")
    parser.add_argument("--single-file", default=None, help="Process only a single CSV filename (e.g. adm2024.csv)")
    return parser.parse_args()

def get_bq_type(var_name, var_info):
    """
    Determines the BigQuery field type based on the clean uppercase variable name
    and the metadata dictionary.
    """
    col_upper = var_name.upper()
    
    # Overrides to preserve leading zeros
    if col_upper == "UNITID" or "ZIP" in col_upper or "FIPS" in col_upper or "COUNTY" in col_upper:
        return "STRING"
        
    # Check if marked as imputation variable
    if var_info.get("is_imputation", False):
        return "STRING"
        
    data_type = var_info.get("DataType")
    fmt = var_info.get("format")
    
    if data_type == "A":
        return "STRING"
    elif data_type == "N":
        if fmt == "Disc":
            return "INT64"
        elif fmt == "Cont":
            return "FLOAT64"
        else:
            return "FLOAT64" # numeric fallback
            
    # Default fallback
    return "STRING"

def get_excel_dictionary_path(csv_base_name, dict_dir):
    """
    Locates the corresponding Excel data dictionary for a CSV base name.
    """
    for f in glob.glob(os.path.join(dict_dir, "*.xlsx")):
        base = os.path.splitext(os.path.basename(f))[0]
        if base.lower() == csv_base_name.lower():
            return f
    return None

def parse_data_dictionary(xlsx_path):
    """
    Parses the Varlist sheet from the Excel dictionary and returns a mapping.
    """
    dict_map = {}
    try:
        # Load the Varlist sheet
        df = pd.read_excel(xlsx_path, sheet_name="Varlist")
    except Exception as e:
        print(f"Error reading Varlist sheet from {xlsx_path}: {e}")
        return None
        
    # Process each row in Varlist
    for _, row in df.iterrows():
        var_name = str(row.get("varName", "")).strip().upper()
        if not var_name:
            continue
            
        dict_map[var_name] = {
            "DataType": str(row.get("DataType", "")).strip().upper(),
            "format": str(row.get("format", "")).strip(),
            "is_imputation": False
        }
        
        # Capture the imputation variable if present
        imp_var = row.get("imputationvar")
        if pd.notna(imp_var):
            imp_var_name = str(imp_var).strip().upper()
            if imp_var_name:
                dict_map[imp_var_name] = {
                    "DataType": "A",
                    "is_imputation": True
                }
                
    return dict_map

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
            dataset.location = "US"  # Default location
            client.create_dataset(dataset)
            print(f"Dataset {args.dataset} created successfully.")

    # 2. Get list of CSV files to process
    if args.single_file:
        csv_pattern = os.path.join(args.data_dir, args.single_file)
    else:
        csv_pattern = os.path.join(args.data_dir, "*.csv")
        
    csv_files = sorted(glob.glob(csv_pattern))
    if not csv_files:
        print(f"No CSV files found matching {csv_pattern}")
        sys.exit(1)
        
    print(f"Found {len(csv_files)} CSV files to process.")
    
    # 3. Process each CSV file
    for csv_path in csv_files:
        csv_filename = os.path.basename(csv_path)
        base_name, _ = os.path.splitext(csv_filename)
        
        print("\n" + "="*50)
        print(f"Processing CSV: {csv_filename}")
        
        # Locate corresponding Excel dictionary
        xlsx_path = get_excel_dictionary_path(base_name, args.dict_dir)
        if not xlsx_path:
            print(f"WARNING: No matching Excel dictionary found for {csv_filename}. Skipping file.")
            continue
            
        print(f"Using dictionary: {os.path.basename(xlsx_path)}")
        
        # Parse data dictionary
        dict_map = parse_data_dictionary(xlsx_path)
        if dict_map is None:
            print(f"ERROR: Failed to parse data dictionary for {csv_filename}. Skipping file.")
            continue
            
        # Read the CSV header to get actual column names and their order
        try:
            df_sample = pd.read_csv(csv_path, nrows=0)
            csv_columns = list(df_sample.columns)
        except Exception as e:
            print(f"ERROR: Failed to read CSV header from {csv_path}: {e}")
            continue
            
        # Build BigQuery Schema
        schema = []
        overridden_cols = []
        for col in csv_columns:
            col_upper = col.strip().upper()
            var_info = dict_map.get(col_upper, {})
            
            bq_type = get_bq_type(col.strip(), var_info)
            
            # Record overrides for debugging
            if col_upper == "UNITID" or "ZIP" in col_upper or "FIPS" in col_upper or "COUNTY" in col_upper:
                overridden_cols.append(f"{col}->{bq_type}")
                
            schema.append(bigquery.SchemaField(name=col, field_type=bq_type))
            
        print(f"Built schema with {len(schema)} columns.")
        if overridden_cols:
            print(f"Preserved leading zeros for overrides: {', '.join(overridden_cols)}")
            
        # Show schema sample for dry-run
        if args.dry_run:
            print("Schema Mapping Details (First 15 fields):")
            for field in schema[:15]:
                orig_var = col_upper = field.name.upper()
                info = dict_map.get(orig_var, {})
                dict_dtype = info.get("DataType", "Unknown")
                dict_fmt = info.get("format", "Unknown")
                is_imp = info.get("is_imputation", False)
                print(f"  - {field.name}: BigQuery={field.field_type} | Dict={dict_dtype} (format={dict_fmt}, imp={is_imp})")
            if len(schema) > 15:
                print(f"  ... and {len(schema) - 15} more fields.")
            continue
            
        # 4. Load CSV to BigQuery
        table_id = f"{client.project}.{args.dataset}.{base_name.lower()}"
        print(f"Loading {csv_filename} into {table_id}...")
        
        job_config = bigquery.LoadJobConfig(
            schema=schema,
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
        )
        
        try:
            with open(csv_path, "rb") as source_file:
                load_job = client.load_table_from_file(
                    source_file,
                    table_id,
                    job_config=job_config
                )
            
            # Wait for job to complete
            load_job.result()
            
            # Verify row count
            destination_table = client.get_table(table_id)
            print(f"Successfully loaded {destination_table.num_rows} rows into {table_id}.")
            
        except Exception as e:
            print(f"ERROR: Failed to load {csv_filename} to BigQuery: {e}")
            
    print("\nIngestion process finished.")

if __name__ == "__main__":
    main()
