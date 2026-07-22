#!/usr/bin/env python3
"""
compile_app_data.py

Compiles and extracts lightweight, filtered, and aggregated tables from the raw
data lake (./data/raw/) to the application data directory (./data/app/).

This ensures the public Streamlit app on GitHub has a tiny footprint (< 1 MB total)
and does not require downloading or processing 300+ MB of raw census databases.
"""

import os
import pandas as pd
import pyarrow.parquet as pq

RAW_DIR = "./data/raw/ipeds"
APP_DIR = "./data/app"

# 15 Michigan public universities for Completions Market Share
MICHIGAN_UNIVERSITIES = [
    'Central Michigan University',
    'Eastern Michigan University',
    'Ferris State University',
    'Grand Valley State University',
    'Lake Superior State University',
    'Michigan State University',
    'Michigan Technological University',
    'Northern Michigan University',
    'Oakland University',
    'Saginaw Valley State University',
    'University of Michigan-Ann Arbor',
    'University of Michigan-Dearborn',
    'University of Michigan-Flint',
    'Wayne State University',
    'Western Michigan University'
]


def normalize_cip(cip):
    """Normalize a CIP code string to XX.XXXX format with leading zeros and dot."""
    if pd.isna(cip):
        return None
    s = str(cip).strip().replace('="', '').replace('"', '')
    if not s:
        return None
    
    if '.' in s:
        parts = s.split('.')
        family = parts[0]
        prog = parts[1] if len(parts) > 1 else ""
    else:
        if len(s) == 6:
            family = s[:2]
            prog = s[2:]
        elif len(s) == 5:
            family = "0" + s[0]
            prog = s[1:]
        elif len(s) <= 2:
            family = s
            prog = ""
        else:
            family = s
            prog = ""
            
    try:
        family_int = int(family)
        family_str = f"{family_int:02d}"
    except ValueError:
        family_str = family.zfill(2)
        
    prog_clean = prog.replace('.', '').strip()
    if len(prog_clean) < 4:
        prog_str = prog_clean.ljust(4, '0')
    else:
        prog_str = prog_clean[:4]
        
    return f"{family_str}.{prog_str}"


def read_parquet_upper(file_path, cols):
    """Read Parquet file mapping requested uppercase columns to actual columns."""
    schema = pq.read_schema(file_path)
    col_map = {name.upper(): name for name in schema.names}
    actual_cols = [col_map.get(c, c) for c in cols]
    
    df = pd.read_parquet(file_path, columns=actual_cols)
    df.columns = df.columns.str.upper()
    return df


def compile_completions():
    """Extract completions and directories for Michigan public universities only."""
    print("📦 Compiling Michigan Completions datasets...")
    
    # 1. Directory HD2024 filter
    hd2024_path = os.path.join(RAW_DIR, "hd2024.parquet")
    if not os.path.exists(hd2024_path):
        print(f"⚠️ Warning: Missing {hd2024_path}. Skipping Completions compilation.")
        return
        
    hd = read_parquet_upper(hd2024_path, ['UNITID', 'INSTNM'])
    hd_mi = hd[hd['INSTNM'].isin(MICHIGAN_UNIVERSITIES)].copy()
    
    hd_mi.to_parquet(os.path.join(APP_DIR, "hd_michigan.parquet"), index=False)
    print(f"   Saved: hd_michigan.parquet ({len(hd_mi)} institutions)")
    
    mi_unitids = hd_mi['UNITID'].tolist()
    
    # 2. Completions merge (2019-2024)
    comp_dfs = []
    for year in ['2019', '2020', '2021', '2022', '2023', '2024']:
        c_path = os.path.join(RAW_DIR, f"c{year}_a.parquet")
        if not os.path.exists(c_path):
            print(f"   (Skipping missing year {year} completions)")
            continue
            
        c_df = read_parquet_upper(c_path, ['UNITID', 'CIPCODE', 'MAJORNUM', 'AWLEVEL', 'CTOTALT'])
        
        # Filter: WSU and peers, first major, 6-digit CIPs
        c_df = c_df[c_df['UNITID'].isin(mi_unitids)]
        c_df = c_df[c_df['MAJORNUM'] == 1]
        
        # Normalize CIP codes to standard format
        c_df['cip_code'] = c_df['CIPCODE'].map(normalize_cip)
        
        # Filter for 6-digit CIPs (length == 7, e.g. "XX.XXXX")
        c_df = c_df[c_df['cip_code'].astype(str).str.len() == 7]
        # Filter out 2-digit and 4-digit summary rollup rows (which end in '00')
        c_df = c_df[~c_df['cip_code'].astype(str).str.endswith('00')]
        
        c_df['year'] = year
        c_df = c_df.rename(columns={
            'AWLEVEL': 'award_level',
            'CTOTALT': 'total_degrees'
        })
        
        # Convert types to avoid mismatch
        c_df['total_degrees'] = pd.to_numeric(c_df['total_degrees'], errors='coerce').fillna(0).astype(int)
        
        comp_dfs.append(c_df[['year', 'UNITID', 'cip_code', 'award_level', 'total_degrees']])
        
    if comp_dfs:
        all_comp = pd.concat(comp_dfs, ignore_index=True)
        # Inner join with names to keep it clean and validated
        all_comp = all_comp.merge(hd_mi, on='UNITID', how='inner')
        all_comp = all_comp.rename(columns={'INSTNM': 'institution', 'UNITID': 'unitid'})
        
        comp_dest = os.path.join(APP_DIR, "completions_michigan.parquet")
        all_comp.to_parquet(comp_dest, index=False)
        print(f"   Saved: completions_michigan.parquet ({len(all_comp)} rows)")
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
    """Aggregate spending and FTE data for R1 and R2 institutions globally."""
    print("📦 Compiling Spending Benchmarks (R1/R2)...")
    
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
        hd = hd.rename(columns={carnegie_col: 'C21BASIC'})
        ef = read_parquet_upper(ef_path, ['UNITID', 'FTE12MN'])
        f1 = read_parquet_upper(f1_path, ['UNITID', 'F1C011', 'F1C051', 'F1C061'])
        f2 = read_parquet_upper(f2_path, ['UNITID', 'F2E011', 'F2E041', 'F2E051'])
        f3 = read_parquet_upper(f3_path, ['UNITID', 'F3E011', 'F3E03A1', 'F3E03B1'])
        
        # Filter to R1 (15) and R2 (16) institutions only (keeps size tiny!)
        # Coerce types for robustness
        hd['C21BASIC'] = pd.to_numeric(hd['C21BASIC'], errors='coerce')
        hd_r12 = hd[hd['C21BASIC'].isin([15, 16])].copy()
        
        # Merge
        m_df = hd_r12.merge(ef, on='UNITID', how='left')
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
            'spend_instruction', 'spend_academic_support', 'spend_student_services'
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


def main():
    os.makedirs(APP_DIR, exist_ok=True)
    print("Starting App Data compilation pipeline...")
    compile_completions()
    compile_dictionaries()
    compile_spending()
    print("🏁 App Data compilation complete!")


if __name__ == "__main__":
    main()
