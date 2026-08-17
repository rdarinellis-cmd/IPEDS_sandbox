#!/usr/bin/env python3
"""
compile_app_data.py

Compiles and extracts lightweight, filtered, and aggregated tables from the raw
data lake (./data/raw/) to the application data directory (./data/app/).

This ensures the public Streamlit app on GitHub has a tiny footprint (< 1 MB total)
and does not require downloading or processing 300+ MB of raw census databases.
"""

import glob
import os
import sys

import pandas as pd
import pyarrow.parquet as pq

# This module is run directly (`python etl/compile_app_data.py`) and also imported
# by ingest_master.py, so put the project root on sys.path before the shared import.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.common import (  # noqa: E402
    MICHIGAN_UNIVERSITIES,
    PUBLIC_R1_C21BASIC,
    PUBLIC_R1_CONTROL,
    URBAN_PEER_IDS,
    WSU_NAME,
    normalize_cip,
)

RAW_DIR = "./data/raw/ipeds"
APP_DIR = "./data/app"


def read_parquet_upper(file_path, cols):
    """Read Parquet file mapping requested uppercase columns to actual columns."""
    schema = pq.read_schema(file_path)
    col_map = {name.upper(): name for name in schema.names}
    actual_cols = [col_map.get(c, c) for c in cols]
    
    df = pd.read_parquet(file_path, columns=actual_cols)
    df.columns = df.columns.str.upper()
    return df


def get_wsu_college_mapping():
    """Reads the WSU Curricula Catalog and builds a dict mapping CIP to comma-separated WSU colleges."""
    # Registry filename carries a date stamp (e.g. Curricula_CIP_2026-06.xlsx), so match the
    # newest rather than pinning a version. '~$' files are Excel lock files, not data.
    candidates = sorted(
        p for p in glob.glob("data/raw/crosswalks/Curricula_CIP_*.xlsx")
        if not os.path.basename(p).startswith("~$")
    )
    if not candidates:
        print("   ⚠️ Warning: no Curricula_CIP_*.xlsx registry found in data/raw/crosswalks/. "
              "The wsu_college column will be EMPTY, which silently disables the "
              "'WSU School/College' filter on the CIP Market Share page.")
        return {}
    catalog_path = candidates[-1]

    try:
        # dtype=str is load-bearing: CIP6 parses as float64 otherwise, dropping the leading
        # zero for families 03/04/05/09 (42 of 859 rows in the 2026-06 registry).
        df = pd.read_excel(catalog_path, dtype=str)

        # The registry lists non-degree entries alongside real majors -- 'pre-' tracks,
        # exploratory/undeclared, seminary and other ND_* programs. They legitimately have no
        # CIP code, so they are skipped rather than treated as an error. Match on a well-formed
        # 6-digit code instead of just dropping blanks, so a placeholder string ('N/A', 'TBD')
        # is skipped too rather than becoming a junk mapping key.
        usable = (
            df['CIP6'].fillna('').str.strip().str.fullmatch(r'\d{6}')
            & df['College'].notna()
        )
        skipped = int((~usable).sum())
        df = df[usable]
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
            
        df['cip_clean'] = df['CIP6'].map(clean_curric_cip)
        df = df.dropna(subset=['cip_clean'])

        # Group by CIP and collect colleges as comma-separated unique values
        mapping = df.groupby('cip_clean')['College'].apply(
            lambda x: ", ".join(sorted(list(set(str(col).strip() for col in x if pd.notna(col)))))
        ).to_dict()

        print(f"   WSU College mapping built from {os.path.basename(catalog_path)}: "
              f"{len(mapping):,} distinct CIPs.")
        return mapping
    except Exception as e:
        print(f"   ⚠️ Error reading WSU Curricula Catalog: {e}")
        return {}


def compile_completions():
    """Extract completions and directories for Michigan public universities, Urban Peers, and Public R1s."""
    print("📦 Compiling completions datasets...")
    
    # 1. Directory HD2024 filter
    hd2024_path = os.path.join(RAW_DIR, "hd2024.parquet")
    if not os.path.exists(hd2024_path):
        print(f"⚠️ Warning: Missing {hd2024_path}. Skipping Completions compilation.")
        return
        
    schema = pq.read_schema(hd2024_path)
    carnegie_col = 'C21BASIC'
    for col_candidate in ['C21BASIC', 'C18BASIC', 'C15BASIC', 'CCBASIC', 'CARNEGIE']:
        if any(name.upper() == col_candidate for name in schema.names):
            carnegie_col = col_candidate
            break
            
    hd = read_parquet_upper(hd2024_path, ['UNITID', 'INSTNM', 'CONTROL', carnegie_col])
    hd['UNITID'] = hd['UNITID'].astype(int)
    hd = hd.rename(columns={carnegie_col: 'C21BASIC'})
    
    # Define cohorts
    # a. Michigan publics:
    mi_names = MICHIGAN_UNIVERSITIES
    hd_mi = hd[hd['INSTNM'].isin(mi_names)].copy()
    
    # b. Urban peers:
    hd_urban = hd[hd['UNITID'].isin(URBAN_PEER_IDS)].copy()
    
    # c. Public R1s:
    hd['CONTROL'] = pd.to_numeric(hd['CONTROL'], errors='coerce')
    hd['C21BASIC'] = pd.to_numeric(hd['C21BASIC'], errors='coerce')
    hd_r1 = hd[(hd['CONTROL'] == PUBLIC_R1_CONTROL) & (hd['C21BASIC'] == PUBLIC_R1_C21BASIC)].copy()
    
    # Merge and build flags
    hd_all = pd.concat([hd_mi, hd_urban, hd_r1]).drop_duplicates(subset=['UNITID']).copy()
    hd_all['is_mi_public'] = hd_all['INSTNM'].isin(mi_names).astype(int)
    hd_all['is_urban_peer'] = hd_all['UNITID'].isin(URBAN_PEER_IDS).astype(int)
    hd_all['is_public_r1'] = ((hd_all['CONTROL'] == PUBLIC_R1_CONTROL) & (hd_all['C21BASIC'] == PUBLIC_R1_C21BASIC)).astype(int)
    
    # Audit artifact, not a dashboard input: no page reads this. It records which
    # institutions landed in which cohort for a given run, which is what you want when a
    # cohort count looks wrong. Regenerated every run, so don't hand-edit it.
    hd_all.to_parquet(os.path.join(APP_DIR, "hd_completions.parquet"), index=False)
    print(f"   Saved: hd_completions.parquet ({len(hd_all)} institutions, audit artifact)")
    
    selected_unitids = hd_all['UNITID'].tolist()
    
    # 2. Completions merge (2019-2024)
    comp_dfs = []
    for year in ['2019', '2020', '2021', '2022', '2023', '2024']:
        c_path = os.path.join(RAW_DIR, f"c{year}_a.parquet")
        if not os.path.exists(c_path):
            print(f"   (Skipping missing year {year} completions)")
            continue
            
        c_df = read_parquet_upper(c_path, ['UNITID', 'CIPCODE', 'MAJORNUM', 'AWLEVEL', 'CTOTALT'])
        c_df['UNITID'] = c_df['UNITID'].astype(int)
        
        # Filter: first major, selected IDs
        c_df = c_df[c_df['UNITID'].isin(selected_unitids)]
        c_df = c_df[c_df['MAJORNUM'] == 1]
        
        c_df['cip_code'] = c_df['CIPCODE'].map(normalize_cip)
        c_df = c_df[c_df['cip_code'].astype(str).str.len() == 7]
        c_df = c_df[~c_df['cip_code'].astype(str).str.endswith('00')]
        
        c_df['year'] = year
        c_df = c_df.rename(columns={
            'AWLEVEL': 'award_level',
            'CTOTALT': 'total_degrees'
        })
        
        c_df['total_degrees'] = pd.to_numeric(c_df['total_degrees'], errors='coerce').fillna(0).astype(int)
        comp_dfs.append(c_df[['year', 'UNITID', 'cip_code', 'award_level', 'total_degrees']])
        
    if comp_dfs:
        all_comp = pd.concat(comp_dfs, ignore_index=True)
        # Inner join with directory and add flags
        all_comp = all_comp.merge(
            hd_all[['UNITID', 'INSTNM', 'is_mi_public', 'is_urban_peer', 'is_public_r1']], 
            on='UNITID', 
            how='inner'
        )
        all_comp = all_comp.rename(columns={'INSTNM': 'institution', 'UNITID': 'unitid'})
        
        # Get WSU college mapping and assign it
        wsu_mapping = get_wsu_college_mapping()
        
        def map_college(row):
            if row['institution'] == WSU_NAME:
                return wsu_mapping.get(row['cip_code'], None)
            return None
            
        all_comp['wsu_college'] = all_comp.apply(map_college, axis=1)
        
        comp_dest = os.path.join(APP_DIR, "completions_benchmark.parquet")
        all_comp.to_parquet(comp_dest, index=False)
        print(f"   Saved: completions_benchmark.parquet ({len(all_comp)} rows)")
    else:
        print("   ❌ No completions datasets found to merge.")


def compile_dictionaries():
    """Copy and clean the variable metadata and CIP dictionaries."""
    print("📦 Compiling Metadata & CIP Dictionaries...")
    
    # 1. CIP Dictionary
    cip_dict_raw = os.path.join(RAW_DIR, "cip_dictionary.parquet")
    if os.path.exists(cip_dict_raw):
        df = pd.read_parquet(cip_dict_raw)
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Clean Excel formula wrapper artifacts
        if 'cipcode' in df.columns:
            df['cipcode'] = df['cipcode'].astype(str).str.replace(r'^="', '', regex=True).str.replace(r'"$', '', regex=True)
        if 'cipfamily' in df.columns:
            df['cipfamily'] = df['cipfamily'].astype(str).str.replace(r'^="', '', regex=True).str.replace(r'"$', '', regex=True)
            
        df.to_parquet(os.path.join(APP_DIR, "cip_dictionary.parquet"), index=False)
        print("   Saved: cip_dictionary.parquet")
    else:
        print("   ⚠️ Warning: cip_dictionary.parquet not found in raw.")

    # 2. Metadata Dictionary
    meta_dict_raw = os.path.join(RAW_DIR, "metadata_dictionary.parquet")
    if os.path.exists(meta_dict_raw):
        df = pd.read_parquet(meta_dict_raw)
        df.to_parquet(os.path.join(APP_DIR, "metadata_dictionary.parquet"), index=False)
        print("   Saved: metadata_dictionary.parquet")
    else:
        print("   ⚠️ Warning: metadata_dictionary.parquet not found in raw.")


def compile_spending():
    """Aggregate spending and FTE data for Michigan publics, Urban Peers, and Public R1s."""
    print("📦 Compiling Spending Benchmarks (Michigan Publics, Urban Peers, Public R1s)...")
    
    YEARS_CONFIG = {
        "2024-25 (Provisional)": {"hd": "hd2024", "ef": "drvef122024", "f1": "f2324_f1a", "f2": "f2324_f2", "f3": "f2324_f3"},
        "2023-24": {"hd": "hd2023", "ef": "drvef122023", "f1": "f2223_f1a", "f2": "f2223_f2", "f3": "f2223_f3"},
        "2022-23": {"hd": "hd2022", "ef": "drvef122022", "f1": "f2122_f1a", "f2": "f2122_f2", "f3": "f2122_f3"},
        "2021-22": {"hd": "hd2021", "ef": "drvef122021", "f1": "f2021_f1a", "f2": "f2021_f2", "f3": "f2021_f3"},
        "2020-21": {"hd": "hd2020", "ef": "drvef122020", "f1": "f1920_f1a", "f2": "f1920_f2", "f3": "f1920_f3"},
        "2019-20": {"hd": "hd2019", "ef": "drvef122019", "f1": "f1819_f1a", "f2": "f1819_f2", "f3": "f1819_f3"}
    }
    
    spending_dfs = []
    for label, cfg in YEARS_CONFIG.items():
        hd_path = os.path.join(RAW_DIR, f"{cfg['hd']}.parquet")
        ef_path = os.path.join(RAW_DIR, f"{cfg['ef']}.parquet")
        f1_path = os.path.join(RAW_DIR, f"{cfg['f1']}.parquet")
        f2_path = os.path.join(RAW_DIR, f"{cfg['f2']}.parquet")
        f3_path = os.path.join(RAW_DIR, f"{cfg['f3']}.parquet")
        
        if not all(os.path.exists(p) for p in [hd_path, ef_path, f1_path, f2_path, f3_path]):
            print(f"   (Skipping missing year {label} spending files)")
            continue
            
        # Determine which Carnegie classification column exists in the schema
        schema = pq.read_schema(hd_path)
        carnegie_col = 'C21BASIC'
        for col_candidate in ['C21BASIC', 'C18BASIC', 'C15BASIC', 'CCBASIC', 'CARNEGIE']:
            if any(name.upper() == col_candidate for name in schema.names):
                carnegie_col = col_candidate
                break
                
        hd = read_parquet_upper(hd_path, ['UNITID', 'INSTNM', 'CONTROL', carnegie_col, 'LOCALE'])
        hd['UNITID'] = hd['UNITID'].astype(int)
        hd = hd.rename(columns={carnegie_col: 'C21BASIC'})
        ef = read_parquet_upper(ef_path, ['UNITID', 'FTE12MN'])
        ef['UNITID'] = ef['UNITID'].astype(int)
        f1 = read_parquet_upper(f1_path, ['UNITID', 'F1C011', 'F1C051', 'F1C061'])
        f1['UNITID'] = f1['UNITID'].astype(int)
        f2 = read_parquet_upper(f2_path, ['UNITID', 'F2E011', 'F2E041', 'F2E051'])
        f2['UNITID'] = f2['UNITID'].astype(int)
        f3 = read_parquet_upper(f3_path, ['UNITID', 'F3E011', 'F3E03A1', 'F3E03B1'])
        f3['UNITID'] = f3['UNITID'].astype(int)
        
        # Define cohorts
        mi_names = MICHIGAN_UNIVERSITIES
            
        hd['CONTROL'] = pd.to_numeric(hd['CONTROL'], errors='coerce')
        hd['C21BASIC'] = pd.to_numeric(hd['C21BASIC'], errors='coerce')
        
        hd_mi = hd[hd['INSTNM'].isin(mi_names)].copy()
        hd_urban = hd[hd['UNITID'].isin(URBAN_PEER_IDS)].copy()
        hd_r1 = hd[(hd['CONTROL'] == PUBLIC_R1_CONTROL) & (hd['C21BASIC'] == PUBLIC_R1_C21BASIC)].copy()
        
        # Merge all selected cohort schools
        hd_all_selected = pd.concat([hd_mi, hd_urban, hd_r1]).drop_duplicates(subset=['UNITID']).copy()
        hd_all_selected['is_mi_public'] = hd_all_selected['INSTNM'].isin(mi_names).astype(int)
        hd_all_selected['is_urban_peer'] = hd_all_selected['UNITID'].isin(URBAN_PEER_IDS).astype(int)
        hd_all_selected['is_public_r1'] = ((hd_all_selected['CONTROL'] == PUBLIC_R1_CONTROL) & (hd_all_selected['C21BASIC'] == PUBLIC_R1_C21BASIC)).astype(int)
        
        # Merge
        m_df = hd_all_selected.merge(ef, on='UNITID', how='left')
        m_df = m_df.merge(f1, on='UNITID', how='left')
        m_df = m_df.merge(f2, on='UNITID', how='left')
        m_df = m_df.merge(f3, on='UNITID', how='left')
        
        m_df['fte_enrollment'] = pd.to_numeric(m_df['FTE12MN'], errors='coerce')
        m_df = m_df[m_df['fte_enrollment'].notna() & (m_df['fte_enrollment'] > 0)]
        
        # Coalesce public/private spending columns
        m_df['spend_instruction'] = pd.to_numeric(m_df['F1C011'].combine_first(m_df['F2E011']).combine_first(m_df['F3E011']), errors='coerce')
        m_df['spend_academic_support'] = pd.to_numeric(m_df['F1C051'].combine_first(m_df['F2E041']).combine_first(m_df['F3E03A1']), errors='coerce')
        m_df['spend_student_services'] = pd.to_numeric(m_df['F1C061'].combine_first(m_df['F2E051']).combine_first(m_df['F3E03B1']), errors='coerce')
        
        m_df['year_label'] = label
        
        spending_dfs.append(m_df[[
            'year_label', 'UNITID', 'INSTNM', 'CONTROL', 'C21BASIC', 'LOCALE', 'fte_enrollment',
            'spend_instruction', 'spend_academic_support', 'spend_student_services',
            'is_mi_public', 'is_urban_peer', 'is_public_r1'
        ]])
        
    if spending_dfs:
        all_spend = pd.concat(spending_dfs, ignore_index=True)
        # Standardize column casing for easier loading
        all_spend.columns = all_spend.columns.str.lower()
        
        spend_dest = os.path.join(APP_DIR, "spending_benchmarks.parquet")
        all_spend.to_parquet(spend_dest, index=False)
        print(f"   Saved: spending_benchmarks.parquet ({len(all_spend)} rows)")
    else:
        print("   ❌ No spending datasets found to compile.")


def compile_portfolio_shape():
    """Compile the portfolio shape metrics for Michigan publics, Urban Peers, and Public R1s for 2020-2024."""
    print("📦 Compiling Portfolio Shape (Michigan Publics + Urban Peers + Public R1s)...")
    
    # Load names and characteristics from hd2024
    import duckdb
    hd_path = os.path.join(RAW_DIR, "hd2024.parquet")
    if os.path.exists(hd_path):
        schema = pq.read_schema(hd_path)
        carnegie_col = 'C21BASIC'
        for col_candidate in ['C21BASIC', 'C18BASIC', 'C15BASIC', 'CCBASIC', 'CARNEGIE']:
            if any(name.upper() == col_candidate for name in schema.names):
                carnegie_col = col_candidate
                break
        hd = read_parquet_upper(hd_path, ['UNITID', 'INSTNM', 'CONTROL', carnegie_col, 'STABBR'])
        hd['UNITID'] = hd['UNITID'].astype(int)
        hd = hd.rename(columns={carnegie_col: 'C21BASIC'})
    else:
        print("   ❌ Error: hd2024.parquet not found in raw. Cannot compile portfolio shape.")
        return

    # Define cohorts
    mi_names = MICHIGAN_UNIVERSITIES
    
    hd['CONTROL'] = pd.to_numeric(hd['CONTROL'], errors='coerce')
    hd['C21BASIC'] = pd.to_numeric(hd['C21BASIC'], errors='coerce')
    
    hd_mi = hd[hd['INSTNM'].isin(mi_names)].copy()
    hd_urban = hd[hd['UNITID'].isin(URBAN_PEER_IDS)].copy()
    hd_r1 = hd[(hd['CONTROL'] == PUBLIC_R1_CONTROL) & (hd['C21BASIC'] == PUBLIC_R1_C21BASIC)].copy()
    
    # Merge and build flags
    hd_all = pd.concat([hd_mi, hd_urban, hd_r1]).drop_duplicates(subset=['UNITID']).copy()
    hd_all['is_mi_public'] = hd_all['INSTNM'].isin(mi_names).astype(int)
    hd_all['is_urban_peer'] = hd_all['UNITID'].isin(URBAN_PEER_IDS).astype(int)
    hd_all['is_public_r1'] = ((hd_all['CONTROL'] == PUBLIC_R1_CONTROL) & (hd_all['C21BASIC'] == PUBLIC_R1_C21BASIC)).astype(int)
    
    ALL_PEER_IDS = hd_all['UNITID'].tolist()
    ids_sql = ", ".join(map(str, ALL_PEER_IDS))
    
    YEAR_MAPS = {
        2020: {"drvf": "drvf2020.parquet", "raw_gasb": "f1920_f1a.parquet"},
        2021: {"drvf": "drvf2021.parquet", "raw_gasb": "f2021_f1a.parquet"},
        2022: {"drvf": "drvf2022.parquet", "raw_gasb": "f2122_f1a.parquet"},
        2023: {"drvf": "drvf2023.parquet", "raw_gasb": "f2223_f1a.parquet"},
        2024: {"drvf": "drvf2024.parquet", "raw_gasb": "f2324_f1a.parquet"}
    }
    
    dfs = []
    for year, files in YEAR_MAPS.items():
        drvf_path = os.path.join(RAW_DIR, files['drvf'])
        raw_gasb_path = os.path.join(RAW_DIR, files['raw_gasb'])
        
        if not os.path.exists(drvf_path):
            print(f"   (Skipping missing year {year} derived table)")
            continue
            
        drvf_df = duckdb.query(f"SELECT * FROM '{drvf_path}' WHERE UNITID IN ({ids_sql})").df()
        drvf_df.columns = drvf_df.columns.str.upper()
        drvf_df['UNITID'] = drvf_df['UNITID'].astype(int)
        
        raw_om_map = {}
        if os.path.exists(raw_gasb_path):
            try:
                om_df = duckdb.query(f"SELECT UNITID, F1C19OM FROM '{raw_gasb_path}' WHERE UNITID IN ({ids_sql})").df()
                om_df.columns = om_df.columns.str.upper()
                om_df['UNITID'] = om_df['UNITID'].astype(int)
                raw_om_map = {int(k): float(v) for k, v in zip(om_df['UNITID'], om_df['F1C19OM']) if pd.notna(v)}
            except Exception:
                pass
                
        for _, row in drvf_df.iterrows():
            unitid = int(row['UNITID'])
            is_gasb = pd.notna(row.get('F1COREXP')) and row.get('F1COREXP') > 0
            
            if is_gasb:
                core_exp = float(row.get('F1COREXP', 0))
                instruction = float(row.get('F1INSTPC', 0))
                research = float(row.get('F1RSRCPC', 0))
                public_service = float(row.get('F1PBSVPC', 0))
                academic_support = float(row.get('F1ACSPPC', 0))
                student_services = float(row.get('F1STSVPC', 0))
                institutional_support = float(row.get('F1INSUPC', 0))
                other_core = float(row.get('F1OTEXPC', 0))
                
                raw_om = raw_om_map.get(unitid, 0.0)
                om_share = (raw_om / core_exp * 100.0) if core_exp > 0 else 0.0
                reporting = 'GASB'
            else:
                core_exp = float(row.get('F2COREXP', 0))
                instruction = float(row.get('F2INSTPC', 0))
                research = float(row.get('F2RSRCPC', 0))
                public_service = float(row.get('F2PBSVPC', 0))
                academic_support = float(row.get('F2ACSPPC', 0))
                student_services = float(row.get('F2STSVPC', 0))
                institutional_support = float(row.get('F2INSUPC', 0))
                other_core = float(row.get('F2OTEXPC', 0))
                
                om_share = None
                reporting = 'FASB'
                
            dfs.append({
                'UNITID': unitid,
                'YEAR': year,
                'REPORTING': reporting,
                'CORE_EXPENSES': core_exp,
                'Instruction': instruction,
                'Research': research,
                'Public Service': public_service,
                'Academic Support': academic_support,
                'Student Services': student_services,
                'Institutional Support': institutional_support,
                'Other Core Expenses': other_core,
                'O&M Share (Contextual)': om_share
            })
            
    if not dfs:
        print("   ❌ No data compiled for portfolio shape.")
        return
        
    df_metrics = pd.DataFrame(dfs)
    df_metrics['UNITID'] = df_metrics['UNITID'].astype(int)
    
    df_merged = df_metrics.merge(
        hd_all[['UNITID', 'INSTNM', 'STABBR', 'is_mi_public', 'is_urban_peer', 'is_public_r1']], 
        on='UNITID', 
        how='inner'
    )
    
    dest_path = os.path.join(APP_DIR, "spending_portfolio_shape.parquet")
    df_merged.to_parquet(dest_path, index=False)
    print(f"   Saved: spending_portfolio_shape.parquet ({len(df_merged)} rows)")


def compile_nih_grants():
    """Extract NIH RePORTER data for our peer set."""
    print("📦 Compiling NIH RePORTER data...")
    raw_path = os.path.join("data/raw/nih", "nih_reporter_training_vs_center.csv")
    itemized_raw_path = os.path.join("data/raw/nih", "nih_reporter_itemized.csv")
    
    if not os.path.exists(raw_path) or not os.path.exists(itemized_raw_path):
        print(f"⚠️ Warning: Missing NIH raw files. Skipping NIH compilation.")
        return
        
    df_nih = pd.read_csv(raw_path)
    df_itemized = pd.read_csv(itemized_raw_path)
    
    # Load base metadata to get UNITID, is_mi_public, is_urban_peer, is_public_r1
    base_path = os.path.join(APP_DIR, "spending_portfolio_shape.parquet")
    if not os.path.exists(base_path):
        print(f"⚠️ Warning: Missing {base_path}. Cannot merge peer flags. Skipping.")
        return
        
    df_meta = pd.read_parquet(base_path)[['UNITID', 'INSTNM', 'is_mi_public', 'is_urban_peer', 'is_public_r1']].drop_duplicates()
    
    # Merge on institution name for aggregated
    df_merged = df_nih.merge(df_meta, left_on='institution', right_on='INSTNM', how='inner')
    
    dest_path = os.path.join(APP_DIR, "nih_grants.parquet")
    df_merged.to_parquet(dest_path, index=False)
    print(f"   Saved: nih_grants.parquet ({len(df_merged)} rows)")

    # Merge on institution name for itemized
    df_itemized_merged = df_itemized.merge(df_meta, left_on='institution', right_on='INSTNM', how='inner')
    itemized_dest_path = os.path.join(APP_DIR, "nih_grants_itemized.parquet")
    df_itemized_merged.to_parquet(itemized_dest_path, index=False)
    print(f"   Saved: nih_grants_itemized.parquet ({len(df_itemized_merged)} rows)")


def compile_nsf_herd():
    """Extract NSF HERD data for our peer set, handling missing UnitIDs for multicampus systems."""
    print("📦 Compiling NSF HERD data...")
    raw_path = os.path.join("data/raw/nsf_herd", "herd2024.csv")
    
    if not os.path.exists(raw_path):
        print(f"⚠️ Warning: Missing {raw_path}. Skipping NSF HERD compilation.")
        return
        
    # Read the dataset
    df_herd = pd.read_csv(raw_path, low_memory=False)
    
    # Map missing IPEDS UnitIDs for known systems in our peer cohorts
    HERD_UNITID_MAP = {
        'University of Colorado Anschutz Medical Campus': 126562,
        'University of Colorado Denver': 126562,
        'University of Connecticut': 129020,
        'University of Maryland': 163286,
        'Western Michigan University and Homer Stryker M.D. School of Medicine': 172699,
        'University of Mississippi': 176017,
        'University of Nebraska, Lincoln and Medical Center': 181464,
        'University of New Hampshire': 183044,
        'University of Cincinnati': 201885,
        'Kent State University': 203517,
        'Ohio State University, The': 204796,
        'Ohio University': 204857,
        'Oregon State University': 209542,
        'Texas A&M University, College Station and Health Science Center': 228723
    }
    
    mask = df_herd['ipeds_unitid'].isna() & df_herd['inst_name_long'].isin(HERD_UNITID_MAP.keys())
    df_herd.loc[mask, 'ipeds_unitid'] = df_herd.loc[mask, 'inst_name_long'].map(HERD_UNITID_MAP)
    
    # Load base metadata to filter to our peer set and merge peer flags
    base_path = os.path.join(APP_DIR, "spending_portfolio_shape.parquet")
    if not os.path.exists(base_path):
        print(f"⚠️ Warning: Missing {base_path}. Cannot merge peer flags. Skipping.")
        return
        
    df_meta = pd.read_parquet(base_path)[['UNITID', 'INSTNM', 'is_mi_public', 'is_urban_peer', 'is_public_r1']].drop_duplicates()
    
    # Filter HERD to our peers
    df_herd = df_herd[df_herd['ipeds_unitid'].isin(df_meta['UNITID'])]
    
    # Extract Metrics
    # 01.a = Federal, 01.b = State, 01.c = Business, 01.d = Nonprofit, 01.e = Institution, 01.f = All other, 01.g = Total
    # 15 = Personnel Headcount (Total = Total, Researchers = Researchers, Support Staff = Support Staff, Technicians = Technicians)
    
    # Expenditures
    q1 = df_herd[df_herd['questionnaire_no'].astype(str).str.startswith('01.')].copy()
    q1['data'] = pd.to_numeric(q1['data'], errors='coerce').fillna(0)
    
    # Pivot expenditures
    expenditures = q1.pivot_table(
        index=['ipeds_unitid', 'year'], 
        columns='questionnaire_no', 
        values='data', 
        aggfunc='sum'
    ).reset_index()
    
    exp_rename_map = {
        '01.a': 'rd_federal',
        '01.b': 'rd_state',
        '01.c': 'rd_business',
        '01.d': 'rd_nonprofit',
        '01.e': 'rd_institution',
        '01.f': 'rd_other',
        '01.g': 'rd_total'
    }
    expenditures = expenditures.rename(columns=exp_rename_map)
    # Fill missing columns if some categories had no data
    for col in exp_rename_map.values():
        if col not in expenditures.columns:
            expenditures[col] = 0.0
            
    # Personnel
    q15 = df_herd[df_herd['questionnaire_no'].astype(str) == '15'].copy()
    q15['data'] = pd.to_numeric(q15['data'], errors='coerce').fillna(0)
    
    personnel = q15.pivot_table(
        index=['ipeds_unitid', 'year'],
        columns='column',
        values='data',
        aggfunc='sum'
    ).reset_index()
    
    pers_rename_map = {
        'Researchers': 'personnel_researchers',
        'Support Staff': 'personnel_support',
        'Technicians': 'personnel_technicians',
        'Total': 'personnel_total'
    }
    personnel = personnel.rename(columns=pers_rename_map)
    for col in pers_rename_map.values():
        if col not in personnel.columns:
            personnel[col] = 0.0
            
    # Merge expenditures and personnel
    final_df = expenditures.merge(personnel, on=['ipeds_unitid', 'year'], how='outer').fillna(0)
    final_df['ipeds_unitid'] = final_df['ipeds_unitid'].astype(int)
    
    # Merge with peer flags
    final_df = final_df.merge(df_meta, left_on='ipeds_unitid', right_on='UNITID', how='inner')
    final_df = final_df.drop(columns=['ipeds_unitid'])
    
    # Save
    dest_path = os.path.join(APP_DIR, "nsf_herd_metrics.parquet")
    final_df.to_parquet(dest_path, index=False)
    print(f"   Saved: nsf_herd_metrics.parquet ({len(final_df)} rows)")


def main():
    os.makedirs(APP_DIR, exist_ok=True)
    print("Starting App Data compilation pipeline...")
    compile_completions()
    compile_dictionaries()
    compile_spending()
    compile_portfolio_shape()
    compile_nih_grants()
    compile_nsf_herd()
    print("🏁 App Data compilation complete!")


if __name__ == "__main__":
    main()
