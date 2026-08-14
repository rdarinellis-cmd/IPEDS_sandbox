import os
import yaml
import json
import pandas as pd
import numpy as np
from datetime import datetime
import hashlib

APP_DIR = "data/app"
RAW_DIR = "data/raw"

def load_config():
    with open("config/portfolio.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Validate critical keys
    for key in ['evidence', 'benchmarks', 'thresholds', 'program_scope', 'exemptions']:
        if key not in config:
            raise KeyError(f"Missing required config key: {key}")
            
    return config

def compile_dim_program(config):
    # Load Curriculum
    curr = pd.read_excel("dictionaries/Active_Curriculum202604.xlsx")
    
    # Exclude CPLR Levels
    exclude_levels = config['program_scope'].get('exclude_cplr_levels', [])
    curr = curr[~curr['CPLR Level'].isin(exclude_levels)].copy()
    
    # Exclude non-credential programs
    curr = curr[curr['Credential Desc'] != 'Non-credential programs'].copy()
    
    # Ensure CIP is a 6-digit zero-padded string
    curr['CIP'] = curr['CIP'].fillna(0).astype(int).astype(str).str.zfill(6)
    
    # Collapse Honors, Co-Majors, and Online options
    # Rule: Map them to the base program and aggregate (or just drop the duplicates here since we only need the dimension)
    is_honors = curr['Major Desc'].str.contains('Honors', case=False, na=False)
    is_comajor = curr['Major Desc'].str.contains('Co-Major', case=False, na=False)
    is_online = curr['Major Desc'].str.contains('Online', case=False, na=False)
    
    curr['is_variant'] = is_honors | is_comajor | is_online
    curr = curr.sort_values('is_variant') # Base programs first
    
    curr['Major Desc'] = curr['Major Desc'].str.replace(r'\s*-?\s*Online\b', '', regex=True, case=False)
    curr['Major Desc'] = curr['Major Desc'].str.replace(r'\s*Honors\b', '', regex=True, case=False)
    curr['Major Desc'] = curr['Major Desc'].str.replace(r'\s*\(Co-Major\)', '', regex=True, case=False)
    curr['Major Desc'] = curr['Major Desc'].str.strip()
    
    # Create program_key using the cleaned Major Desc
    curr['program_key'] = curr['Program'].astype(str) + "_" + curr['Major Desc'].astype(str).str.upper().str.replace(' ', '_') + "_" + curr['CPLR Level'].astype(str)
    
    # Ensure program_key is unique, keeping the base program
    curr = curr.drop_duplicates(subset=['program_key']).drop(columns=['is_variant'])
    
    # Coerce problematic columns
    curr['Min_Credits'] = pd.to_numeric(curr['Min_Credits'], errors='coerce')
    curr['Length'] = pd.to_numeric(curr['Length'], errors='coerce')
    
    # Write Parquet
    out_path = os.path.join(APP_DIR, "portfolio_dim_program.parquet")
    curr.to_parquet(out_path, engine='pyarrow', compression='snappy')
    return curr

def compile_crosswalk():
    cw = pd.read_parquet("data/raw/crosswalks/cip2020_soc2018_crosswalk.parquet")
    
    # Ensure CIP and SOC are strings
    cw['CIP2020Code'] = cw['CIP2020Code'].astype(str).str.replace('.', '', regex=False).str.zfill(6)
    
    # Check weights sum to 1.0 (assuming column is 'Weight' or we create equal weights)
    # The actual column might be different, let's assume 'CIP2020Code', 'SOC2018Code'
    # For now, we just create equal weights if they don't exist
    if 'Weight' not in cw.columns:
        cw['Weight'] = 1.0 / cw.groupby('CIP2020Code')['CIP2020Code'].transform('count')
        
    sum_weights = cw.groupby('CIP2020Code')['Weight'].sum()
    if not np.allclose(sum_weights, 1.0):
        # Normalize
        cw['Weight'] = cw['Weight'] / cw.groupby('CIP2020Code')['Weight'].transform('sum')

    out_path = os.path.join(APP_DIR, "portfolio_map_cip_soc.parquet")
    cw.to_parquet(out_path, engine='pyarrow', compression='snappy')
    return cw

def compile_screen_marts(dim_program, config):
    # This is a mocked compilation for Screens 2, 3, 4 and bins based on dim_program
    # In reality, this would join Pathfinder, IPEDS, Scorecard, and Labor MI.
    
    n_progs = len(dim_program)
    np.random.seed(42)
    
    # 1. portfolio_value_floor.parquet (Screen 2)
    val = dim_program[['program_key', 'CIP', 'Credential Desc']].copy()
    val['mobility_yield'] = np.random.uniform(20000, 80000, n_progs)
    val['earnings_vs_counterfactual'] = val['mobility_yield'] - config['benchmarks']['hs_only_earnings']
    val['debt_to_earnings'] = np.random.uniform(0.01, 0.25, n_progs)
    val['completion_rate'] = np.random.uniform(0.30, 0.95, n_progs)
    val['n'] = np.random.randint(5, 100, n_progs)
    val['suppressed'] = val['n'] < config['evidence']['min_cohort_n']
    val.to_parquet(os.path.join(APP_DIR, "portfolio_value_floor.parquet"), engine='pyarrow', compression='snappy')
    
    # 2. portfolio_relative_perf.parquet (Screen 3)
    rel = dim_program[['program_key', 'CIP']].copy()
    rel['state_earnings_gap'] = np.random.uniform(-10000, 20000, n_progs)
    rel['peer_earnings_gap'] = np.random.uniform(-5000, 15000, n_progs)
    rel['national_earnings_gap'] = np.random.uniform(-15000, 10000, n_progs)
    
    # Assign interpretation flags
    def assign_flag(gap):
        if gap > config['evidence']['min_material_gap_usd']: return 'above_material'
        if gap < -config['evidence']['min_material_gap_usd']: return 'below_material'
        return 'at_parity'
        
    rel['state_perf_flag'] = rel['state_earnings_gap'].apply(assign_flag)
    rel['n'] = np.random.randint(5, 100, n_progs)
    rel['suppressed'] = rel['n'] < config['evidence']['min_cohort_n']
    rel.to_parquet(os.path.join(APP_DIR, "portfolio_relative_perf.parquet"), engine='pyarrow', compression='snappy')
    
    # 3. portfolio_demand_position.parquet (Screen 4)
    dem = dim_program[['program_key', 'CIP']].copy()
    dem['regional_openings'] = np.random.randint(10, 500, n_progs)
    dem['state_completion_share'] = np.random.uniform(0.01, 0.50, n_progs)
    dem['in_state_retention'] = np.random.uniform(0.40, 0.95, n_progs)
    dem['duplication_cluster'] = np.random.choice(['Monopoly', 'Saturated', 'Niche'], n_progs)
    dem['n'] = np.random.randint(5, 100, n_progs)
    dem['suppressed'] = dem['n'] < config['evidence']['min_cohort_n']
    dem.to_parquet(os.path.join(APP_DIR, "portfolio_demand_position.parquet"), engine='pyarrow', compression='snappy')
    
    # 4. portfolio_bins.parquet (Terminal Assignment)
    bins = dim_program[['program_key']].copy()
    bins['terminal_bin'] = np.random.choice([
        'Mobility engines', 
        'Export programs', 
        'Student risk', 
        'Monitor', 
        'Growth opportunity'
    ], n_progs)
    bins.to_parquet(os.path.join(APP_DIR, "portfolio_bins.parquet"), engine='pyarrow', compression='snappy')
    
def write_audit_log(config):
    config_str = json.dumps(config, sort_keys=True).encode('utf-8')
    config_hash = hashlib.sha256(config_str).hexdigest()
    
    audit = pd.DataFrame([{
        'run_timestamp': datetime.now().isoformat(),
        'config_hash': config_hash
    }])
    audit.to_parquet(os.path.join(APP_DIR, "portfolio_audit.parquet"), engine='pyarrow', compression='snappy')

def main():
    print("Loading Portfolio Config...")
    config = load_config()
    
    print("Compiling Program Dimension...")
    dim_program = compile_dim_program(config)
    
    print("Compiling Crosswalk...")
    compile_crosswalk()
    
    print("Compiling Analytical Screens (Mocked Integration)...")
    compile_screen_marts(dim_program, config)
    
    print("Writing Audit Log...")
    write_audit_log(config)
    
    print("Portfolio ETL Complete.")

if __name__ == "__main__":
    main()
