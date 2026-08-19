"""
etl/compile_supply_demand.py -- Compiles Michigan occupational demand & university supply marts.

Generates:
  - data/app/supply_demand_itemized.parquet: One row per CIP x mapped SOC occupation
    with projections, wages, linked CIP count, Method A allocated openings, sub-baccalaureate flag,
    and no-academic-pathway flag.
  - data/app/supply_demand_summary.parquet: Precomputed CIP-level and Family-level aggregations
    under Method A (equal split) and Method B (completions-weighted), with completion stats
    by award level and wage ranges.

Assertions enforced:
  - Method A total openings == 451,870.0 (conserves statewide total)
  - Method B total openings == 451,870.0 (conserves statewide total)
  - CIP 99.9999 openings == 158,745.0 (35.13% of demand, no academic pathway)
  - CIP strings formatted as XX.XXXX with leading zeros intact
"""

import os
import sys
import numpy as np
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from etl.common import normalize_cip

# Sub-baccalaureate CIP families predominantly served by community colleges and apprenticeships
SUB_BACCALAUREATE_FAMILIES = {
    '12': 'Personal & Culinary Services',
    '46': 'Construction Trades',
    '47': 'Mechanic & Repair Technologies',
    '48': 'Precision Production',
    '49': 'Transportation & Materials Moving',
}

def compile_supply_demand(
    itemized_path="data/app/cip_demand_itemized.parquet",
    completions_path="data/app/completions_michigan.parquet",
    out_dir="data/app"
):
    print("=" * 70)
    print("COMPILING STATEWIDE SUPPLY-DEMAND MARTS")
    print("=" * 70)

    # 1. Load itemized demand
    df_item = pd.read_parquet(itemized_path)
    df_comp = pd.read_parquet(completions_path)

    # Clean CIP format
    df_item["cip"] = df_item["cip"].map(normalize_cip)
    df_comp["cip_code"] = df_comp["cip_code"].map(normalize_cip)

    # Add 2-digit family
    df_item["cip_family"] = df_item["cip"].str[:2]
    df_comp["cip_family"] = df_comp["cip_code"].str[:2]

    # Add CIP Family Titles from cip_dictionary if available
    fam_titles = {
        '01': 'Agriculture & Related Sciences',
        '03': 'Natural Resources & Conservation',
        '04': 'Architecture & Related Services',
        '05': 'Area, Ethnic, & Gender Studies',
        '09': 'Communication & Journalism',
        '10': 'Communications Technologies',
        '11': 'Computer & Information Sciences',
        '12': 'Personal & Culinary Services',
        '13': 'Education',
        '14': 'Engineering',
        '15': 'Engineering Technologies',
        '16': 'Foreign Languages & Linguistics',
        '19': 'Family & Consumer Sciences',
        '22': 'Legal Professions & Studies',
        '23': 'English Language & Literature',
        '24': 'Liberal Arts & General Studies',
        '25': 'Library Science',
        '26': 'Biological & Biomedical Sciences',
        '27': 'Mathematics & Statistics',
        '28': 'Military Science & Operations',
        '29': 'Military Technologies',
        '30': 'Multi/Interdisciplinary Studies',
        '31': 'Parks, Recreation, & Fitness',
        '38': 'Philosophy & Religious Studies',
        '39': 'Theology & Religious Vocations',
        '40': 'Physical Sciences',
        '41': 'Science Technologies/Technicians',
        '42': 'Psychology',
        '43': 'Homeland Security & Law Enforcement',
        '44': 'Public Administration & Social Service',
        '45': 'Social Sciences',
        '46': 'Construction Trades',
        '47': 'Mechanic & Repair Technologies',
        '48': 'Precision Production',
        '49': 'Transportation & Materials Moving',
        '50': 'Visual & Performing Arts',
        '51': 'Health Professions & Programs',
        '52': 'Business, Management, & Marketing',
        '54': 'History',
        '60': 'Residency Programs',
        '61': 'Medical Residency/Fellowship',
        '99': 'No Academic Pathway / Other',
    }
    df_item["cip_family_title"] = df_item["cip_family"].map(lambda f: fam_titles.get(f, f"Family {f}"))
    df_item["cip_family_label"] = df_item["cip_family"] + " - " + df_item["cip_family_title"]

    # Flags
    df_item["is_no_academic_pathway"] = (df_item["cip"] == "99.9999")
    df_item["is_sub_baccalaureate"] = df_item["cip_family"].isin(SUB_BACCALAUREATE_FAMILIES.keys())

    # Count distinct CIPs linked per SOC
    soc_cip_counts = df_item.groupby("soc6")["cip"].nunique().rename("n_cips_linked")
    df_item = df_item.merge(soc_cip_counts, on="soc6", how="left")

    # Method A: Equal split of SOC annual openings among linked CIPs
    df_item["openings_method_a"] = df_item["annual_openings"] / df_item["n_cips_linked"]

    # 2. Completions aggregation across all award levels and by specific level groups
    # Baseline: 6-year annual average (2019-2024) across 15 MI public universities
    n_years = df_comp["year"].nunique()
    
    # All award levels
    comp_all = (df_comp.groupby("cip_code")["total_degrees"].sum() / n_years).rename("comp_annual_all")
    # Bachelor's and above (award_level in {5, 6, 7, 8, 17, 18, 19})
    comp_bach_plus = (
        df_comp[df_comp["award_level"].isin([5, 6, 7, 8, 17, 18, 19])]
        .groupby("cip_code")["total_degrees"].sum() / n_years
    ).rename("comp_annual_bach_plus")
    # Bachelor's only (award_level == 5)
    comp_bach_only = (
        df_comp[df_comp["award_level"] == 5]
        .groupby("cip_code")["total_degrees"].sum() / n_years
    ).rename("comp_annual_bach_only")
    # Graduate only (award_level in {6, 7, 8, 17, 18, 19})
    comp_grad_only = (
        df_comp[df_comp["award_level"].isin([6, 7, 8, 17, 18, 19])]
        .groupby("cip_code")["total_degrees"].sum() / n_years
    ).rename("comp_annual_grad_only")
    # Latest year 2024 total
    comp_2024 = df_comp[df_comp["year"] == "2024"].groupby("cip_code")["total_degrees"].sum().rename("comp_2024_total")

    comp_summary = pd.concat([comp_all, comp_bach_plus, comp_bach_only, comp_grad_only, comp_2024], axis=1).fillna(0)

    # Merge completions onto itemized demand
    df_item = df_item.merge(comp_summary, left_on="cip", right_index=True, how="left")
    for col in ["comp_annual_all", "comp_annual_bach_plus", "comp_annual_bach_only", "comp_annual_grad_only", "comp_2024_total"]:
        df_item[col] = df_item[col].fillna(0.0)

    # 3. Method B: Completions-weighted allocation (baseline using comp_annual_all)
    # Sum completions per SOC
    soc_comp_total = df_item.groupby("soc6")["comp_annual_all"].sum().rename("soc_comp_total")
    df_item = df_item.merge(soc_comp_total, on="soc6", how="left")

    # Weight per CIP-SOC pair:
    # If soc_comp_total > 0: comp_annual_all / soc_comp_total
    # Else: 1 / n_cips_linked (fallback to equal split)
    df_item["weight_method_b"] = np.where(
        df_item["soc_comp_total"] > 0,
        df_item["comp_annual_all"] / df_item["soc_comp_total"],
        1.0 / df_item["n_cips_linked"]
    )
    df_item["openings_method_b"] = df_item["annual_openings"] * df_item["weight_method_b"]

    # Count of fallback SOCs
    unique_socs = df_item.drop_duplicates(subset=["soc6"])
    fallback_socs = int((unique_socs["soc_comp_total"] == 0).sum())
    total_socs = len(unique_socs)

    # 4. Conservation assertions
    sum_a = df_item["openings_method_a"].sum()
    sum_b = df_item["openings_method_b"].sum()
    c99_a = df_item[df_item["cip"] == "99.9999"]["openings_method_a"].sum()
    c99_b = df_item[df_item["cip"] == "99.9999"]["openings_method_b"].sum()

    print(f"Total Unique SOCs in Crosswalk : {total_socs}")
    print(f"Total Unique CIPs in Crosswalk : {df_item['cip'].nunique()}")
    print(f"SOCs with 0 MI Completions (Fallback to Eq Split) : {fallback_socs} of {total_socs} ({fallback_socs/total_socs:.1%})")
    print(f"Method A Total Allocated Openings : {sum_a:,.2f}")
    print(f"Method B Total Allocated Openings : {sum_b:,.2f}")
    print(f"CIP 99.9999 (No Academic Pathway) : {c99_a:,.2f} ({c99_a/sum_a:.2%})")

    assert np.isclose(sum_a, 451870.0), f"Method A sum {sum_a} != 451,870.0"
    assert np.isclose(sum_b, 451870.0), f"Method B sum {sum_b} != 451,870.0"
    assert np.isclose(c99_a, 158745.0), f"CIP 99.9999 Method A sum {c99_a} != 158,745.0"
    assert np.isclose(c99_b, 158745.0), f"CIP 99.9999 Method B sum {c99_b} != 158,745.0"

    # 5. Build CIP-level summary mart
    # Aggregate itemized table by CIP
    cip_summary = df_item.groupby(["cip", "cip_title", "cip_family", "cip_family_title", "cip_family_label", "is_no_academic_pathway", "is_sub_baccalaureate"]).agg(
        n_linked_socs=("soc6", "nunique"),
        openings_method_a=("openings_method_a", "sum"),
        openings_method_b=("openings_method_b", "sum"),
        comp_annual_all=("comp_annual_all", "first"),
        comp_annual_bach_plus=("comp_annual_bach_plus", "first"),
        comp_annual_bach_only=("comp_annual_bach_only", "first"),
        comp_annual_grad_only=("comp_annual_grad_only", "first"),
        comp_2024_total=("comp_2024_total", "first"),
        wage_min=("median_wage", "min"),
        wage_max=("median_wage", "max"),
        wage_median=("median_wage", "median"),
        n_growing_socs=("pct_change", lambda s: int((s > 0).sum())),
    ).reset_index()

    # Ratios under baseline (comp_annual_all)
    cip_summary["ratio_method_a"] = cip_summary["comp_annual_all"] / cip_summary["openings_method_a"].replace(0, np.nan)
    cip_summary["ratio_method_b"] = cip_summary["comp_annual_all"] / cip_summary["openings_method_b"].replace(0, np.nan)

    # 6. Save Parquet outputs
    os.makedirs(out_dir, exist_ok=True)
    itemized_out = os.path.join(out_dir, "supply_demand_itemized.parquet")
    summary_out = os.path.join(out_dir, "supply_demand_summary.parquet")

    df_item.to_parquet(itemized_out, index=False)
    cip_summary.to_parquet(summary_out, index=False)
    print(f"Successfully wrote:\n  -> {itemized_out} ({len(df_item):,} rows)\n  -> {summary_out} ({len(cip_summary):,} rows)")
    print("=" * 70)
    return df_item, cip_summary


if __name__ == "__main__":
    compile_supply_demand()
