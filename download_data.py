import os
import pandas as pd
from google.cloud import bigquery

# Initialize the BigQuery client with your specific project ID
PROJECT_ID = "project-9a1f71b9-7c50-4df5-adb"
DATASET_ID = "ipeds"

client = bigquery.Client(project=PROJECT_ID)

# Ensure a local directory exists to save the files
output_dir = "./data"
os.makedirs(output_dir, exist_ok=True)

print(f"Connecting to BigQuery project: {PROJECT_ID}")
print(f"Looking for tables in dataset: {DATASET_ID}...\n")

try:
    # List all tables in the dataset
    tables = client.list_tables(DATASET_ID)
    
    for table in tables:
        table_name = table.table_id
        print(f" -> Found table: {table_name}. Downloading...")
        
        # Query the entire table
        query = f"SELECT * FROM `{PROJECT_ID}.{DATASET_ID}.{table_name}`"
        
        # Download directly into a Pandas DataFrame
        df = client.query(query).to_dataframe()
        
        # Define the local parquet filename
        output_file = os.path.join(output_dir, f"{table_name}.parquet")
        
        # Save to Parquet format using snappy compression
        df.to_parquet(output_file, index=False, compression="snappy")
        
        # Get file size for verification
        file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
        print(f"    Saved to {output_file} ({file_size_mb:.2f} MB, {len(df)} rows)")
        
    print("\nAll tables downloaded and converted to Parquet successfully!")

except Exception as e:
    print(f"\nAn error occurred: {e}")
    print("Double check that 'gcloud auth application-default login' ran successfully.")