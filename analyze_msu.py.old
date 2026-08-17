import pandas as pd

df = pd.read_csv('msu_om.csv')

print("## Michigan State University - First-Time, Full-Time Cohort (IPEDS Outcome Measures)\n")
print("| Year (Data) | Cohort Start | Adjusted Cohort | 4-Yr Grad | 6-Yr Grad | 8-Yr Grad | Transfer Out (8-yr) | Still Enrolled (8-yr) | No Award/Unknown |")
print("|---|---|---|---|---|---|---|---|---|")

# First-time, full-time, total aid
ftft = df[(df['ftpt'] == 1) & (df['class_level'] == 1) & (df['fed_aid_type'] == 99)].sort_values('year')

for _, row in ftft.iterrows():
    year = int(row['year'])
    # The OM survey typically measures 8-year outcomes for the cohort 8 years prior.
    # So OM year 2021 is usually the 2013 entering cohort.
    # IPEDS OM 2018 = 2010 cohort
    # IPEDS OM 2022 = 2014 cohort
    # IPEDS OM 2023 = 2015 cohort
    cohort_start = year - 8 
    cohort = int(row['cohort_adj_8yr']) if pd.notnull(row['cohort_adj_8yr']) else 0
    grad4 = f"{row['completion_rate_4yr']*100:.1f}%" if pd.notnull(row['completion_rate_4yr']) else "N/A"
    grad6 = f"{row['completion_rate_6yr']*100:.1f}%" if pd.notnull(row['completion_rate_6yr']) else "N/A"
    grad8 = f"{row['completion_rate_8yr']*100:.1f}%" if pd.notnull(row['completion_rate_8yr']) else "N/A"
    transfer = f"{row['transfer_rate_8yr']*100:.1f}%" if pd.notnull(row['transfer_rate_8yr']) else "N/A"
    still_enrolled = f"{row['still_enroll_rate_8yr']*100:.1f}%" if pd.notnull(row['still_enroll_rate_8yr']) else "N/A"
    no_award = 1.0 - (row['completion_rate_8yr'] + row['transfer_rate_8yr'] + row['still_enroll_rate_8yr']) if pd.notnull(row['completion_rate_8yr']) else 0
    no_award_str = f"{no_award*100:.1f}%"
    
    print(f"| {year} | Fall {cohort_start} | {cohort:,} | {grad4} | {grad6} | {grad8} | {transfer} | {still_enrolled} | {no_award_str} |")

print("\n\n## Michigan State University - Total Entering Cohort (All Students)\n")
print("| Year (Data) | Cohort Start | Adjusted Cohort | 6-Yr Grad | 8-Yr Grad | Transfer Out (8-yr) | Still Enrolled (8-yr) | No Award/Unknown |")
print("|---|---|---|---|---|---|---|---|")
total = df[(df['ftpt'] == 99) & (df['class_level'] == 99) & (df['fed_aid_type'] == 99)].sort_values('year')

for _, row in total.iterrows():
    year = int(row['year'])
    cohort_start = year - 8 
    cohort = int(row['cohort_adj_8yr']) if pd.notnull(row['cohort_adj_8yr']) else 0
    grad6 = f"{row['completion_rate_6yr']*100:.1f}%" if pd.notnull(row['completion_rate_6yr']) else "N/A"
    grad8 = f"{row['completion_rate_8yr']*100:.1f}%" if pd.notnull(row['completion_rate_8yr']) else "N/A"
    transfer = f"{row['transfer_rate_8yr']*100:.1f}%" if pd.notnull(row['transfer_rate_8yr']) else "N/A"
    still_enrolled = f"{row['still_enroll_rate_8yr']*100:.1f}%" if pd.notnull(row['still_enroll_rate_8yr']) else "N/A"
    no_award = 1.0 - (row['completion_rate_8yr'] + row['transfer_rate_8yr'] + row['still_enroll_rate_8yr']) if pd.notnull(row['completion_rate_8yr']) else 0
    no_award_str = f"{no_award*100:.1f}%"
    
    print(f"| {year} | Fall {cohort_start} | {cohort:,} | {grad6} | {grad8} | {transfer} | {still_enrolled} | {no_award_str} |")
