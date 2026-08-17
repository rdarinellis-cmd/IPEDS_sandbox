import pandas as pd
import numpy as np
import glob
import os
import sys

# Run directly as `python scripts/build_pipeline.py`, so sys.path[0] is scripts/ --
# put the project root on the path before importing the shared ETL definitions.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.common import normalize_cip  # noqa: E402


def clean_cip_code(cip_series):
    """Clean and normalize CIP codes in a series to 'XX.XXXX' format."""
    return cip_series.map(normalize_cip)


def clean_soc_code(soc_series):
    """Normalize SOC codes in a series to bare 6-digit digits format."""
    import re
    def norm_s(s):
        if pd.isna(s):
            return None
        s_clean = str(s).split('.')[0]
        return re.sub(r'[^0-9]', '', s_clean).strip()
    return soc_series.map(norm_s)

def main():
    print("Loading data files...")
    # Read files
    df_pathfinder = pd.read_excel('data/raw/labor_mi/Pathfinder-Employment_Outcome_Report-Wayne_State_University.xlsx', sheet_name='Wayne State University')
    df_cip = pd.read_csv('data/raw/crosswalks/CIPCode2020_CIPTitle.csv', encoding='latin1')
    df_crosswalk = pd.read_excel('data/raw/crosswalks/CIP2020_SOC2018_Crosswalk.xlsx', sheet_name='CIP-SOC')
    df_wage = pd.read_csv('data/raw/labor_mi/IOWage_data.csv', encoding='latin1')

    print("Cleaning Pathfinder data...")
    # Clean Pathfinder CIP codes
    df_pathfinder['CIP Code'] = clean_cip_code(df_pathfinder['CIP Code'])
    
    # Replace * with np.nan globally
    df_pathfinder = df_pathfinder.replace('*', np.nan)
    
    # Handle Suppressions (*) and coerce to numeric
    numeric_cols = [
        'Total Students (Year 1)', 'Median Salary in Michigan (Year 1)', '% Employed in Michigan (Year 1)',
        'Total Students (Year 5)', 'Median Salary in Michigan (Year 5)', '% Employed in Michigan (Year 5)'
    ]
    
    df_pathfinder['is_suppressed'] = False
    
    for col in numeric_cols:
        # Check if '*' is present to mark suppression
        has_suppressions = df_pathfinder[col].astype(str).str.strip() == '*'
        df_pathfinder.loc[has_suppressions, 'is_suppressed'] = True
        
        # Replace * with NaN
        df_pathfinder[col] = pd.to_numeric(
            df_pathfinder[col].replace('*', np.nan), errors='coerce'
        )

    print("Cleaning Wage data...")
    # Filter for Median Wage and Entry Level Wage
    df_wage_filtered = df_wage[df_wage['Measure Names'].isin(['Median Wage', 'Entry Level Wage'])].copy()
    
    # Pivot so we have SOC, Entry Level Wage, Median Wage
    df_wage_pivot = df_wage_filtered.pivot_table(
        index=['SOC Occupation Code', 'Occupation'], 
        columns='Measure Names', 
        values='Measure Values',
        aggfunc='first'
    ).reset_index()
    
    # Convert hourly to annual
    df_wage_pivot['State_Annual_Entry_Wage'] = df_wage_pivot['Entry Level Wage'] * 2080
    df_wage_pivot['State_Annual_Median_Wage'] = df_wage_pivot['Median Wage'] * 2080

    print("Aggregating State Wages by CIP...")
    # Clean Crosswalk CIP codes
    df_crosswalk['CIP2020Code'] = clean_cip_code(df_crosswalk['CIP2020Code'])
    
    # Normalize SOC codes before joining to avoid hyphen mismatches
    df_crosswalk['soc_clean'] = clean_soc_code(df_crosswalk['SOC2018Code'])
    df_wage_pivot['soc_clean'] = clean_soc_code(df_wage_pivot['SOC Occupation Code'])
    
    # Join Crosswalk with Wage Data
    df_mapped = pd.merge(df_crosswalk, df_wage_pivot, on='soc_clean', how='inner')
    
    # Group by CIP and calculate mean wages
    cip_state_benchmarks = df_mapped.groupby('CIP2020Code').agg({
        'State_Annual_Entry_Wage': 'mean',
        'State_Annual_Median_Wage': 'mean'
    }).reset_index()

    # Create a mapping for drilldown
    # We will export the full mapped SOC benchmarks for View 3 drill down
    df_soc_benchmarks = df_mapped[['CIP2020Code', 'CIP2020Title', 'SOC2018Code', 'Occupation', 'State_Annual_Entry_Wage', 'State_Annual_Median_Wage']]

    print("Merging WSU Data with Benchmarks...")
    # Merge CIP Titles
    df_cip['CIPCode'] = clean_cip_code(df_cip['CIPCode'])
    df_pathfinder = pd.merge(df_pathfinder, df_cip[['CIPCode', 'CIPTitle']], left_on='CIP Code', right_on='CIPCode', how='left')
    
    # Merge with State Benchmarks
    df_final = pd.merge(df_pathfinder, cip_state_benchmarks, left_on='CIP Code', right_on='CIP2020Code', how='left')

    print("Calculating Metrics and Quadrants...")
    # Baseline comparison is Statewide Entry Level Wage for both years.
    
    # Year 1 Metrics
    df_final['Y1_Wage_Premium_$'] = df_final['Median Salary in Michigan (Year 1)'] - df_final['State_Annual_Entry_Wage']
    df_final['Y1_Wage_Premium_%'] = (df_final['Median Salary in Michigan (Year 1)'] / df_final['State_Annual_Entry_Wage']) - 1
    
    # Year 5 Metrics
    df_final['Y5_Wage_Premium_$'] = df_final['Median Salary in Michigan (Year 5)'] - df_final['State_Annual_Entry_Wage']
    df_final['Y5_Wage_Premium_%'] = (df_final['Median Salary in Michigan (Year 5)'] / df_final['State_Annual_Entry_Wage']) - 1

    # Quadrant Assignment Function
    def assign_quadrant(emp_rate, wage_premium, median_emp):
        if pd.isna(emp_rate) or pd.isna(wage_premium):
            return 'Unknown'
        if emp_rate >= median_emp and wage_premium >= 0:
            return 'Star'
        elif emp_rate < median_emp and wage_premium < 0:
            return 'Strategic Opportunity'
        elif emp_rate < median_emp and wage_premium >= 0:
            return 'Hidden Gem'
        else: # emp_rate >= median_emp and wage_premium < 0
            return 'Workhorse'

    median_emp_y1 = df_final['% Employed in Michigan (Year 1)'].median()
    df_final['Y1_Quadrant'] = df_final.apply(
        lambda row: assign_quadrant(row['% Employed in Michigan (Year 1)'], row['Y1_Wage_Premium_$'], median_emp_y1), 
        axis=1
    )

    median_emp_y5 = df_final['% Employed in Michigan (Year 5)'].median()
    df_final['Y5_Quadrant'] = df_final.apply(
        lambda row: assign_quadrant(row['% Employed in Michigan (Year 5)'], row['Y5_Wage_Premium_$'], median_emp_y5), 
        axis=1
    )

    rename_dict = {
        'Total Students (Year 1)': 'Total graduates (Year 1)',
        'Total Students (Year 5)': 'Total graduates (Year 5)',
        '% Employed in Michigan (Year 1)': '% Graduates Employed in Michigan (Year 1)',
        '% Employed in Michigan (Year 5)': '% Graduates Employed in Michigan (Year 5)',
        'Median Salary in Michigan (Year 1)': 'Median Graduate Salary in Michigan (Year 1)',
        'Median Salary in Michigan (Year 5)': 'Median Graduate Salary in Michigan (Year 5)'
    }
    df_final = df_final.rename(columns=rename_dict)

    print("Integrating IPEDS Completions data...")
    try:
        # Load HD to get WSU UNITID
        hd = pd.read_parquet('data/raw/ipeds/hd2024.parquet', columns=['UNITID', 'INSTNM'])
        hd.columns = hd.columns.str.upper()
        wsu_unitid = str(hd[hd['INSTNM'] == 'Wayne State University']['UNITID'].iloc[0])
        
        # Load c2024_a
        c24 = pd.read_parquet('data/raw/ipeds/c2024_a.parquet', columns=['unitid', 'CIPCODE', 'MAJORNUM', 'AWLEVEL', 'CTOTALT'])
        c24.columns = c24.columns.str.upper()
        
        wsu_comp = c24[(c24['UNITID'] == wsu_unitid) & (c24['MAJORNUM'] == 1)].copy()
        # Clean CIP codes first using the robust clean_cip_code function
        wsu_comp['CIPCODE'] = clean_cip_code(wsu_comp['CIPCODE'])
        # Keep only valid 6-digit CIPs (length == 7, e.g. "XX.XXXX")
        wsu_comp = wsu_comp[wsu_comp['CIPCODE'].astype(str).str.len() == 7]
        # Filter out 2-digit and 4-digit summary rollup rows (which end in '00')
        wsu_comp = wsu_comp[~wsu_comp['CIPCODE'].astype(str).str.endswith('00')]
        
        # AWLEVEL to Pathfinder Award mapping
        awlevel_map = {
            5: "Bachelor's Degree",
            7: "Master's Degree",
            17: "Doctoral Degree",
            19: "Doctoral Degree",
            18: "Professional Degree",
            3: "Associate's Degree",
            1: "Certificate", 2: "Certificate", 4: "Certificate", 
            6: "Certificate", 8: "Certificate", 20: "Certificate", 21: "Certificate"
        }
        wsu_comp['Award'] = wsu_comp['AWLEVEL'].map(awlevel_map)
        wsu_comp = wsu_comp.dropna(subset=['Award'])
        
        # Aggregate by CIPCODE and Award
        ipeds_agg = wsu_comp.groupby(['CIPCODE', 'Award'])['CTOTALT'].sum().reset_index()
        ipeds_agg = ipeds_agg.rename(columns={'CTOTALT': 'IPEDS_Total_Degrees'})
        
        # Clean CIPCODE to match df_final
        ipeds_agg['CIPCODE'] = clean_cip_code(ipeds_agg['CIPCODE'])
        
        # Merge into df_final
        df_final = pd.merge(df_final, ipeds_agg, left_on=['CIP Code', 'Award'], right_on=['CIPCODE', 'Award'], how='left')
        df_final['IPEDS_Total_Degrees'] = df_final['IPEDS_Total_Degrees'].fillna(0)
        
        # Flagging Logic
        # 1. High IPEDS degrees (e.g. > 30)
        # 2. Positive Wage Premium in either Year 1 or Year 5
        # 3. Pathfinder cohort is < 30% of IPEDS cohort
        
        has_positive_premium = (df_final['Y1_Wage_Premium_$'] > 0) | (df_final['Y5_Wage_Premium_$'] > 0)
        high_ipeds = df_final['IPEDS_Total_Degrees'] > 30
        
        pf_grads_y1 = df_final['Total graduates (Year 1)'].fillna(0)
        pf_grads_y5 = df_final['Total graduates (Year 5)'].fillna(0)
        max_pf_grads = np.maximum(pf_grads_y1, pf_grads_y5)
        
        low_pathfinder = max_pf_grads < (0.3 * df_final['IPEDS_Total_Degrees'])
        
        df_final['is_underrepresented'] = has_positive_premium & high_ipeds & low_pathfinder

        # Drop the redundant CIPCODE column from the merge
        if 'CIPCODE' in df_final.columns:
            df_final = df_final.drop(columns=['CIPCODE'])

    except Exception as e:
        print(f"Warning: Failed to integrate IPEDS data: {e}")
        df_final['IPEDS_Total_Degrees'] = 0
        df_final['is_underrepresented'] = False

    print("Integrating WSU College mappings...")
    try:
        # Registry filename carries a date stamp (e.g. Curricula_CIP_2026-06.xlsx), so match
        # the newest rather than pinning a version. '~$' files are Excel lock files, not data.
        candidates = sorted(
            p for p in glob.glob('data/raw/crosswalks/Curricula_CIP_*.xlsx')
            if not os.path.basename(p).startswith('~$')
        )
        catalog_path = candidates[-1] if candidates else None
        if catalog_path:
            # dtype=str is load-bearing: CIP6 parses as float64 otherwise, dropping the
            # leading zero for families 03/04/05/09 (42 of 859 rows in the 2026-06 registry).
            df_curric = pd.read_excel(catalog_path, dtype=str)

            # The registry lists non-degree entries alongside real majors -- 'pre-' tracks,
            # exploratory/undeclared, seminary and other ND_* programs. They legitimately have
            # no CIP code, so they are skipped rather than treated as an error. Match on a
            # well-formed 6-digit code instead of just dropping blanks, so a placeholder
            # string ('N/A', 'TBD') is skipped too rather than becoming a junk mapping key.
            usable = (
                df_curric['CIP6'].fillna('').str.strip().str.fullmatch(r'\d{6}')
                & df_curric['College'].notna()
            )
            skipped = int((~usable).sum())
            df_curric = df_curric[usable]
            if skipped:
                print(f"   Skipped {skipped:,} registry row(s) with no usable CIP code "
                      "(non-degree/exploratory programs) -- expected, not an error.")
            
            def clean_curric_cip(val):
                val_str = str(val).strip()
                if '.' in val_str:
                    try:
                        val_float = float(val_str)
                        val_int = int(val_float)
                        if val_float == val_int:
                            val_str = str(val_int)
                    except ValueError:
                        pass
                return normalize_cip(val_str)
                
            df_curric['cip_clean'] = df_curric['CIP6'].map(clean_curric_cip)
            df_curric = df_curric.dropna(subset=['cip_clean'])
            
            wsu_mapping = df_curric.groupby('cip_clean')['College'].apply(
                lambda x: ", ".join(sorted(list(set(str(col).strip() for col in x if pd.notna(col)))))
            ).to_dict()
            
            df_final['College'] = df_final['CIP Code'].map(wsu_mapping)
            matched = int(df_final['College'].notna().sum())
            print(f"   WSU College mappings assigned from {os.path.basename(catalog_path)}: "
                  f"{matched:,}/{len(df_final):,} rows matched "
                  f"({df_curric['cip_clean'].nunique():,} distinct CIPs in registry).")
        else:
            print("Warning: Curricula Catalog not found. College column will be empty.")
            df_final['College'] = None
    except Exception as e:
        print(f"Warning: Failed to integrate Curricula Catalog: {e}")
        df_final['College'] = None

    print("Saving to Parquet...")
    os.makedirs('data/app', exist_ok=True)
    # Save outputs
    df_final.to_parquet('data/app/wsu_cip_outcomes.parquet', index=False)
    df_soc_benchmarks.to_parquet('data/app/statewide_soc_benchmarks.parquet', index=False)
    
    print("ETL Pipeline completed successfully!")

if __name__ == "__main__":
    main()
