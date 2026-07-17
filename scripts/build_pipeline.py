import pandas as pd
import numpy as np
import os

def clean_cip_code(cip_series):
    """Clean CIP codes to string format 'XX.XXXX'."""
    # Convert to string, strip whitespace and any excel formula artifacts like ="01.0000"
    cleaned = cip_series.astype(str).str.replace(r'^[="]+', '', regex=True).str.replace(r'["\s]+$', '', regex=True)
    # Ensure it's a float-like string, then format to 2.4 digits
    def format_cip(x):
        try:
            return f"{float(x):07.4f}"
        except ValueError:
            return x
    return cleaned.apply(format_cip)

def main():
    print("Loading data files...")
    # Read files
    df_pathfinder = pd.read_excel('processing_dropbox/Pathfinder-Employment_Outcome_Report-Wayne_State_University.xlsx', sheet_name='Wayne State University')
    df_cip = pd.read_csv('processing_dropbox/CIPCode2020.csv', encoding='latin1')
    df_crosswalk = pd.read_excel('processing_dropbox/CIP2020_SOC2018_Crosswalk.xlsx', sheet_name='CIP-SOC')
    df_wage = pd.read_csv('processing_dropbox/IOWage_data.csv', encoding='latin1')

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
    
    df_pathfinder['is_imputed'] = False
    
    for col in numeric_cols:
        # Check if '*' is present to mark imputation
        has_suppressions = df_pathfinder[col].astype(str).str.strip() == '*'
        df_pathfinder.loc[has_suppressions, 'is_imputed'] = True
        
        # Replace * with NaN
        df_pathfinder[col] = pd.to_numeric(
            df_pathfinder[col].replace('*', np.nan), errors='coerce'
        )
        
        # Impute missing values with the median of the column
        col_median = df_pathfinder[col].median()
        df_pathfinder[col] = df_pathfinder[col].fillna(col_median)

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
    
    # Join Crosswalk with Wage Data
    df_mapped = pd.merge(df_crosswalk, df_wage_pivot, left_on='SOC2018Code', right_on='SOC Occupation Code', how='inner')
    
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

    print("Saving to Parquet...")
    os.makedirs('data', exist_ok=True)
    # Save outputs
    df_final.to_parquet('data/wsu_cip_outcomes.parquet', index=False)
    df_soc_benchmarks.to_parquet('data/statewide_soc_benchmarks.parquet', index=False)
    
    print("ETL Pipeline completed successfully!")

if __name__ == "__main__":
    main()
