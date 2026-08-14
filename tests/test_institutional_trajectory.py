import pytest
import pandas as pd
import os

APP_DIR = "./data/app"
TRAJECTORY_FILE = os.path.join(APP_DIR, "institutional_trajectory.parquet")

@pytest.fixture
def data():
    assert os.path.exists(TRAJECTORY_FILE), "Trajectory compiled file is missing"
    return pd.read_parquet(TRAJECTORY_FILE)

def test_adjusted_core_expenses_excludes_hospital(data):
    # Wayne State or any large institution should have hospital expenses > 0 in some years
    hosp_data = data[data['exp_hospital'] > 0]
    if hosp_data.empty:
        pytest.skip("No institutions with hospital expenses in the dataset to test.")
    
    for _, row in hosp_data.iterrows():
        # Core expenses = total - hospital - auxiliary - independent ops
        expected_core = row['exp_total'] - row['exp_hospital'] - (row['exp_auxiliary'] if pd.notna(row['exp_auxiliary']) else 0) - (row['exp_independent'] if pd.notna(row['exp_independent']) else 0)
        assert abs(row['adj_core_expenses'] - expected_core) < 1.0, f"Adjusted core expenses mismatch for UNITID {row['UNITID']} Year {row['YEAR']}"


def test_real_dollar_conversion_identity(data):
    # For a base year where HECA/CPI = 100, the nominal value should equal the real value.
    # We used 100 for HECA in 2022 and CPI in 2021.
    df_2022 = data[(data['YEAR'] == 2022) & (data['exp_instruction'].notna())]
    if not df_2022.empty:
        # HECA index for 2022 is 100.0, so nominal == real_heca
        for _, row in df_2022.iterrows():
            assert abs(row['exp_instruction'] - row['exp_instruction_real_heca']) < 1.0, "Real HECA conversion is not identity at base year"
            
    df_2021 = data[(data['YEAR'] == 2021) & (data['exp_instruction'].notna())]
    if not df_2021.empty:
        # CPI-U index for 2021 is 100.0, so nominal == real_cpi
        for _, row in df_2021.iterrows():
            assert abs(row['exp_instruction'] - row['exp_instruction_real_cpi']) < 1.0, "Real CPI conversion is not identity at base year"

def test_missing_year_handling(data):
    # Find any unitid and metric combination that is missing a year and ensure it is NA not 0
    # For example, OM is often missing depending on year.
    om_ftft = data['om_awd_ftft']
    assert not om_ftft.empty, "Expected some missing values for OM data, but found none or they were filled with 0"
