import pandas as pd
from google.cloud import bigquery
import requests
import io

def upload_cip_dictionary():
    print("Downloading CIPCode2020.csv...")
    url = "https://nces.ed.gov/ipeds/cipcode/Files/CIPCode2020.csv"
    
    # Download the CSV
    response = requests.get(url)
    response.raise_for_status()
    
    # NCES CSVs might have different encodings, latin1 is safe for IPEDS
    df = pd.read_csv(io.StringIO(response.content.decode('latin1')))
    
    # Standardize column names
    df.columns = [c.strip().lower() for c in df.columns]
    
    print(f"Downloaded {len(df)} rows. Columns: {list(df.columns)}")
    
    # We need CIPCode, CIPTitle, CIPFamily. 
    # In CIP2020, columns are typically: 'cipfamily', 'cipcode', 'action', 'textchange', 'ciptitle', 'cipdefinition', etc.
    # We will just upload the whole thing to bigquery.
    
    client = bigquery.Client(project="project-9a1f71b9-7c50-4df5-adb")
    table_id = "project-9a1f71b9-7c50-4df5-adb.ipeds.cip_dictionary"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
    )
    
    print(f"Uploading to {table_id}...")
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Wait for the job to complete.
    
    print(f"Loaded {job.output_rows} rows into {table_id}.")

if __name__ == "__main__":
    upload_cip_dictionary()
