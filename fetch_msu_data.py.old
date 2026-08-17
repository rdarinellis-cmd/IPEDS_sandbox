import urllib.request
import json
import pandas as pd
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

unitid = 171100 # Michigan State University

print("Fetching Graduation Rates (GR)...")
gr_data = []
for year in range(2018, 2024):
    url = f"https://educationdata.urban.org/api/v1/college-university/ipeds/graduation-rates/{year}/?unitid={unitid}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        gr_data.extend(data.get('results', []))
    except Exception as e:
        print(f"Error fetching GR {year}: {e}")

if gr_data:
    df_gr = pd.DataFrame(gr_data)
    df_gr.to_csv("msu_gr.csv", index=False)
    print("Saved GR to msu_gr.csv")
    
print("Fetching Outcome Measures (OM)...")
om_data = []
for year in range(2018, 2024):
    url = f"https://educationdata.urban.org/api/v1/college-university/ipeds/outcome-measures/{year}/?unitid={unitid}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode('utf-8'))
        om_data.extend(data.get('results', []))
    except Exception as e:
        print(f"Error fetching OM {year}: {e}")

if om_data:
    df_om = pd.DataFrame(om_data)
    df_om.to_csv("msu_om.csv", index=False)
    print("Saved OM to msu_om.csv")

print("Done fetching.")
