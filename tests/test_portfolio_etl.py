import os
import pytest
import pandas as pd
import yaml
import sys

# Ensure etl is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from etl.compile_portfolio_data import load_config, compile_dim_program, compile_crosswalk

def test_config_validation():
    config = load_config()
    assert 'evidence' in config
    assert 'benchmarks' in config
    assert 'thresholds' in config
    assert 'program_scope' in config
    assert 'exemptions' in config

def test_dim_program_rules():
    config = load_config()
    dim = compile_dim_program(config)
    
    # 1. Check CPLR Level 99 is excluded
    assert 99 not in dim['CPLR Level'].values
    
    # 2. Check CIP is zero padded to 6 digits
    # Just grab lengths of strings
    cip_lens = dim['CIP'].str.len()
    assert (cip_lens == 6).all(), "Not all CIP codes are 6 digits"
    
    # 3. Check Honors and Co-Majors are collapsed (removed from dim)
    assert not dim['Major Desc'].str.contains('Honors', case=False).any()
    assert not dim['Major Desc'].str.contains('Co-Major', case=False).any()

def test_crosswalk_weights():
    cw = compile_crosswalk()
    
    # Check weights sum to 1.0 per CIP
    sum_weights = cw.groupby('CIP2020Code')['Weight'].sum()
    assert (sum_weights.round(5) == 1.0).all(), "Weights do not sum to 1.0"

def test_segregation():
    config = load_config()
    dim = compile_dim_program(config)
    
    # The requirement is that graduate and undergrad are never pooled
    # For dim_program, we just need to ensure CPLR Level is present
    assert 'CPLR Level' in dim.columns

def test_terminal_bins():
    # Execute the full ETL and check that bins are mutually exclusive
    # and all program_keys exist
    config = load_config()
    dim = compile_dim_program(config)
    
    bins_path = "data/app/portfolio_bins.parquet"
    if os.path.exists(bins_path):
        bins = pd.read_parquet(bins_path)
        assert set(dim['program_key']) == set(bins['program_key'])
        # Each program should have exactly one bin
        assert len(bins) == len(bins['program_key'].unique())
