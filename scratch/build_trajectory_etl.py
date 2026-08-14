import os
import pandas as pd
import pyarrow.parquet as pq
import duckdb

RAW_DIR = "./data/raw/ipeds"
APP_DIR = "./data/app"

def compile_institutional_trajectory():
    print("📦 Compiling Institutional Trajectory...")
    
    # Load cohorts
    cohorts_path = "dictionaries/cohorts.csv"
    if not os.path.exists(cohorts_path):
        print(f"   ❌ Missing {cohorts_path}")
        return
    cohorts_df = pd.read_csv(cohorts_path)
    unitids = cohorts_df['unitid'].unique().tolist()
    ids_sql = ", ".join(map(str, unitids))
    
    # Load deflator
    deflator_path = "dictionaries/deflator.csv"
    if not os.path.exists(deflator_path):
        print(f"   ❌ Missing {deflator_path}")
        return
    deflator_df = pd.read_csv(deflator_path)
    deflator_map = deflator_df.set_index('fiscal_year').to_dict('index')
    
    YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
    
    all_data = []
    
    for year in YEARS:
        y2 = str(year)[2:]
        y2_prev = str(year - 1)[2:]
        f_yr = f"f{y2_prev}{y2}_f1a"
        
        files = {
            'hd': f"hd{year}.parquet",
            'drvef': f"drvef{year}.parquet",
            'effy': f"effy{year}.parquet",
            'efia': f"efia{year}.parquet",
            'drvc': f"drvc{year}.parquet",
            'drvgr': f"drvgr{year}.parquet",
            'om': f"om{year}.parquet",
            'f1a': f"{f_yr}.parquet",
            'sfa': f"sfa{year}_p1.parquet" if year >= 2018 else f"sfa{year}.parquet",
            's_is': f"s{year}_is.parquet",
            's_oc': f"s{year}_oc.parquet"
        }
        
        # We will build a unified dataframe for this year
        # First, grab HD for the cohort
        hd_path = os.path.join(RAW_DIR, files['hd'])
        if not os.path.exists(hd_path):
            print(f"   ⚠️ Missing {files['hd']}")
            continue
            
        q_hd = f"SELECT UNITID, INSTNM, STABBR, SECTOR, CONTROL FROM '{hd_path}' WHERE UNITID IN ({ids_sql})"
        df_year = duckdb.query(q_hd).df()
        df_year.columns = df_year.columns.str.upper()
        df_year['YEAR'] = year
        df_year['UNITID'] = df_year['UNITID'].astype(int)
        
        # EFFY (12-month headcount)
        # We want EFYTOTLT where EFFYLEV == 1 (All students)
        effy_path = os.path.join(RAW_DIR, files['effy'])
        if os.path.exists(effy_path):
            q_effy = f"SELECT UNITID, EFYTOTLT as headcount_12m FROM '{effy_path}' WHERE UNITID IN ({ids_sql}) AND EFFYLEV = 1"
            df_effy = duckdb.query(q_effy).df(); df_effy['UNITID'] = df_effy['UNITID'].astype(int)
            df_year = df_year.merge(df_effy, on='UNITID', how='left')
        else:
            df_year['headcount_12m'] = None
            
        # EFIA (12-month FTE)
        efia_path = os.path.join(RAW_DIR, files['efia'])
        if os.path.exists(efia_path):
            q_efia = f"SELECT UNITID, FTEUG, FTEGD FROM '{efia_path}' WHERE UNITID IN ({ids_sql})"
            df_efia = duckdb.query(q_efia).df(); df_efia['UNITID'] = df_efia['UNITID'].astype(int)
            df_efia['fte_12m'] = df_efia['FTEUG'].fillna(0) + df_efia['FTEGD'].fillna(0)
            df_year = df_year.merge(df_efia[['UNITID', 'fte_12m']], on='UNITID', how='left')
        else:
            df_year['fte_12m'] = None
            
        # DRVEF (Fall headcount, UG/GR, FT/PT, retention)
        drvef_path = os.path.join(RAW_DIR, files['drvef'])
        if os.path.exists(drvef_path):
            q_drvef = f"SELECT UNITID, ENRTOT as headcount_fall, ENRFT as fall_ft, ENRPT as fall_pt, EFUG as fall_ug, FTE as fall_fte FROM '{drvef_path}' WHERE UNITID IN ({ids_sql})"
            df_drvef = duckdb.query(q_drvef).df(); df_drvef['UNITID'] = df_drvef['UNITID'].astype(int)
            df_year = df_year.merge(df_drvef, on='UNITID', how='left')
        else:
            for c in ['headcount_fall', 'fall_ft', 'fall_pt', 'fall_ug', 'fall_fte']:
                df_year[c] = None
                
        # DRVC (Degrees conferred)
        drvc_path = os.path.join(RAW_DIR, files['drvc'])
        if os.path.exists(drvc_path):
            q_drvc = f"SELECT * FROM '{drvc_path}' WHERE UNITID IN ({ids_sql})"
            df_drvc = duckdb.query(q_drvc).df(); df_drvc['UNITID'] = df_drvc['UNITID'].astype(int)
            # Sum up degree columns
            deg_cols = ['ASCDEG', 'BASDEG', 'MASDEG', 'DOCDEGRS', 'DOCDEGPP', 'DOCDEGOT', 'CERT1', 'CERT2', 'CERT4', 'PBACERT', 'PMACERT']
            valid_cols = [c for c in deg_cols if c in df_drvc.columns]
            df_drvc['degrees_conferred'] = df_drvc[valid_cols].fillna(0).sum(axis=1)
            df_year = df_year.merge(df_drvc[['UNITID', 'degrees_conferred']], on='UNITID', how='left')
        else:
            df_year['degrees_conferred'] = None
            
        # DRVGR (6-year graduation rate)
        drvgr_path = os.path.join(RAW_DIR, files['drvgr'])
        if os.path.exists(drvgr_path):
            q_drvgr = f"SELECT UNITID, GBA6RTT as grad_rate_6yr, PGBA6RT as grad_rate_pell, NRBA6RT as grad_rate_nopell FROM '{drvgr_path}' WHERE UNITID IN ({ids_sql})"
            try:
                df_drvgr = duckdb.query(q_drvgr).df(); df_drvgr['UNITID'] = df_drvgr['UNITID'].astype(int)
                df_year = df_year.merge(df_drvgr, on='UNITID', how='left')
            except:
                print(f"Warning: Columns missing in {drvgr_path}")
                df_year['grad_rate_6yr'] = None
                df_year['grad_rate_pell'] = None
                df_year['grad_rate_nopell'] = None
        else:
            df_year['grad_rate_6yr'] = None
            df_year['grad_rate_pell'] = None
            df_year['grad_rate_nopell'] = None
            
        # OM (Outcome measures)
        om_path = os.path.join(RAW_DIR, files['om'])
        if os.path.exists(om_path):
            q_om = f"SELECT UNITID, OMCHRT, OMAWDP8 FROM '{om_path}' WHERE UNITID IN ({ids_sql})"
            try:
                df_om = duckdb.query(q_om).df(); df_om['UNITID'] = df_om['UNITID'].astype(int)
                # Pivot om
                om_pivot = df_om.pivot(index='UNITID', columns='OMCHRT', values='OMAWDP8').reset_index()
                om_pivot = om_pivot.rename(columns={
                    1: 'om_awd_ftft',
                    2: 'om_awd_ptft',
                    3: 'om_awd_ftnft',
                    4: 'om_awd_ptnft'
                })
                df_year = df_year.merge(om_pivot, on='UNITID', how='left')
            except Exception as e:
                print(f"Warning: {e} in {om_path}")
                for c in ['om_awd_ftft', 'om_awd_ptft', 'om_awd_ftnft', 'om_awd_ptnft']:
                    df_year[c] = None
        else:
            for c in ['om_awd_ftft', 'om_awd_ptft', 'om_awd_ftnft', 'om_awd_ptnft']:
                df_year[c] = None
                
        # Finance F1A
        f1a_path = os.path.join(RAW_DIR, files['f1a'])
        if os.path.exists(f1a_path):
            # Revenues: F1B01 (Tuition), F1B11 (State appropriations) - Note: Need to verify exact F1B* names
            # Expenses: F1C011 (instruction), F1C021 (research), F1C031 (public service), F1C051 (academic support), F1C061 (student services), F1C071 (institutional support), F1C101 (scholarships), F1C111 (auxiliaries), F1C121 (hospital), F1C131 (independent ops), F1C191 (total)
            # Discounts: F1N01 (tuition), F1N02 (auxiliary)
            cols = "UNITID, F1B01, F1B11, F1C011, F1C021, F1C031, F1C051, F1C061, F1C071, F1C101, F1C111, F1C121, F1C131, F1C191, F1N01, F1N02"
            q_f1a = f"SELECT * FROM '{f1a_path}' WHERE UNITID IN ({ids_sql})"
            df_f1a = duckdb.query(q_f1a).df(); df_f1a['UNITID'] = df_f1a['UNITID'].astype(int)
            
            req_cols = ['F1B01', 'F1B11', 'F1C011', 'F1C021', 'F1C031', 'F1C051', 'F1C061', 'F1C071', 'F1C101', 'F1C111', 'F1C121', 'F1C131', 'F1C191', 'F1N01', 'F1N02']
            for rc in req_cols:
                if rc not in df_f1a.columns:
                    df_f1a[rc] = 0.0
                    
            df_f1a = df_f1a[['UNITID'] + req_cols].copy()
            df_f1a.columns = ['UNITID', 'rev_tuition', 'rev_state_approp', 'exp_instruction', 'exp_research', 'exp_pub_service', 'exp_acad_support', 'exp_stud_services', 'exp_inst_support', 'exp_scholarships', 'exp_auxiliary', 'exp_hospital', 'exp_independent', 'exp_total', 'allowance_tuition', 'allowance_auxiliary']
            df_year = df_year.merge(df_f1a, on='UNITID', how='left')
        else:
            f1a_cols = ['rev_tuition', 'rev_state_approp', 'exp_instruction', 'exp_research', 'exp_pub_service', 'exp_acad_support', 'exp_stud_services', 'exp_inst_support', 'exp_scholarships', 'exp_auxiliary', 'exp_hospital', 'exp_independent', 'exp_total', 'allowance_tuition', 'allowance_auxiliary']
            for c in f1a_cols:
                df_year[c] = None
                
        # SFA (Institutional Grants)
        sfa_path = os.path.join(RAW_DIR, files['sfa'])
        if os.path.exists(sfa_path):
            q_sfa = f"SELECT UNITID, IGRNT_T as inst_grant_aid FROM '{sfa_path}' WHERE UNITID IN ({ids_sql})"
            try:
                df_sfa = duckdb.query(q_sfa).df(); df_sfa['UNITID'] = df_sfa['UNITID'].astype(int)
                df_year = df_year.merge(df_sfa, on='UNITID', how='left')
            except:
                df_year['inst_grant_aid'] = None
        else:
            df_year['inst_grant_aid'] = None
            
        # Staff S_IS and S_OC
        s_is_path = os.path.join(RAW_DIR, files['s_is'])
        if os.path.exists(s_is_path):
            # Typically FACSTAT = 0 for all instructional staff
            q_sis = f"SELECT UNITID, SUM(HRTOTLT) as inst_staff_total FROM '{s_is_path}' WHERE UNITID IN ({ids_sql}) GROUP BY UNITID"
            try:
                df_sis = duckdb.query(q_sis).df(); df_sis['UNITID'] = df_sis['UNITID'].astype(int)
                df_year = df_year.merge(df_sis, on='UNITID', how='left')
            except:
                df_year['inst_staff_total'] = None
        else:
            df_year['inst_staff_total'] = None

        all_data.append(df_year)
        
    df_all = pd.concat(all_data, ignore_index=True)
    
    # Calculations
    df_all['has_hospital_expenses'] = df_all['exp_hospital'] > 0
    df_all['adj_core_expenses'] = df_all['exp_total'] - df_all['exp_hospital'].fillna(0) - df_all['exp_independent'].fillna(0) - df_all['exp_auxiliary'].fillna(0)
    
    df_all['gross_tuition'] = df_all['rev_tuition'].fillna(0) + df_all['allowance_tuition'].fillna(0)
    df_all['discount_rate'] = df_all['allowance_tuition'] / df_all['gross_tuition'].replace(0, pd.NA)
    
    df_all['intensity_index'] = df_all['fte_12m'] / df_all['headcount_12m'].replace(0, pd.NA)
    df_all['production_yield'] = df_all['degrees_conferred'] / df_all['fte_12m'].replace(0, pd.NA)
    
    df_all['net_tuition_dependence'] = df_all['rev_tuition'] / (df_all['rev_tuition'].fillna(0) + df_all['rev_state_approp'].fillna(0)).replace(0, pd.NA)
    
    # Per-FTE metrics and Deflators
    financial_metrics = [
        'exp_instruction', 'exp_research', 'exp_pub_service', 'exp_acad_support', 
        'exp_stud_services', 'exp_inst_support', 'exp_scholarships', 
        'rev_tuition', 'rev_state_approp', 'inst_grant_aid'
    ]
    
    def apply_deflator(row, metric, deflator_type):
        val = row[metric]
        if pd.isna(val):
            return val
        yr = row['YEAR']
        idx = deflator_map.get(yr, {}).get(deflator_type)
        if not idx:
            return val
        return val / (idx / 100.0)
        
    for metric in financial_metrics:
        # 1. Per FTE
        df_all[f'{metric}_per_fte'] = df_all[metric] / df_all['fte_12m'].replace(0, pd.NA)
        
        # 2. Deflate
        df_all[f'{metric}_real_heca'] = df_all.apply(lambda r: apply_deflator(r, metric, 'heca_index'), axis=1)
        df_all[f'{metric}_real_cpi'] = df_all.apply(lambda r: apply_deflator(r, metric, 'cpi_u_index'), axis=1)
        
        df_all[f'{metric}_per_fte_real_heca'] = df_all.apply(lambda r: apply_deflator(r, f'{metric}_per_fte', 'heca_index'), axis=1)
        df_all[f'{metric}_per_fte_real_cpi'] = df_all.apply(lambda r: apply_deflator(r, f'{metric}_per_fte', 'cpi_u_index'), axis=1)

    out_path = os.path.join(APP_DIR, "institutional_trajectory.parquet")
    df_all.to_parquet(out_path, index=False)
    print(f"   Saved: institutional_trajectory.parquet ({len(df_all)} rows)")

if __name__ == '__main__':
    compile_institutional_trajectory()
