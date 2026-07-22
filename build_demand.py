"""
build_demand.py  --  Michigan occupational DEMAND layer for the IPEDS dashboard.

Reads three staged public files and produces two cached parquet tables that the
Streamlit pages join to IPEDS completions on the (dotted, 7-char) CIP code:

    data/cip_demand_itemized.parquet   one row per CIP x mapped SOC occupation
    data/cip_demand_summary.parquet    one row per CIP (dashboard-ready summary)

Design decisions baked in (see chat thread for rationale):
  * Aggregation = OPTION (a): itemized occupation set is the source of truth.
    The summary is DERIVED from it, and the rule differs by measure:
       - wages  -> a RANGE (band) is honest (intensity measure)
       - openings-> NEVER summed (volume measure, many-to-many crosswalk would
         create phantom demand). We report BREADTH + GROWTH-SHARE instead.
  * SOC codes normalized to 6-digit, no hyphen, to join across sources that
    disagree on format (crosswalk/wage use "11-1011", projections use "111011").
  * Wages in the MILMI extract are HOURLY only -> converted to annual x 2080.
  * '% Change' in the MILMI projections is already a FRACTION (e.g. 0.12 = 12%).

Run:  python build_demand.py       (from project root, with paths below present)
"""

import os
import numpy as np
import pandas as pd

# ---- paths (edit if you relocate the staged files) -------------------------
XWALK_PATH  = "processing_dropbox/CIP2020_SOC2018_Crosswalk.xlsx"
MATRIX_PATH = "processing_dropbox/IOMatrix_data.csv"   # MILMI occupation projections
WAGE_PATH   = "processing_dropbox/IOWage_data.csv"     # MILMI occupation wages
OUT_DIR     = "data"
HOURS_PER_YEAR = 2080


def _norm_soc(s):
    """Strip to a bare 6-digit SOC string so all three sources join."""
    if pd.isna(s):
        return None
    return str(s).replace("-", "").strip()


def load_crosswalk(path=XWALK_PATH):
    """NCES CIP2020 -> SOC2018 crosswalk (many-to-many)."""
    df = pd.read_excel(path, sheet_name="CIP-SOC", dtype=str).rename(columns={
        "CIP2020Code": "cip", "CIP2020Title": "cip_title",
        "SOC2018Code": "soc", "SOC2018Title": "soc_title",
    })
    df["cip"] = df["cip"].str.strip()
    df["soc6"] = df["soc"].map(_norm_soc)
    return df.dropna(subset=["cip", "soc6"])[["cip", "cip_title", "soc6", "soc_title"]]


def load_projections(path=MATRIX_PATH):
    """MILMI occupation-level projections (UTF-16, tab-delimited, long/Tableau)."""
    df = pd.read_csv(path, dtype=str, encoding="utf-16", sep="\t")
    df["soc6"] = df["Occupation Code"].map(_norm_soc)
    df["val"] = pd.to_numeric(df["Measure Values"], errors="coerce")
    wide = df.pivot_table(index="soc6", columns="Measure Names",
                          values="val", aggfunc="first")
    wide = wide[["Projected Employment", "% Change", "Total Annual Openings"]].reset_index()
    wide.columns = ["soc6", "proj_emp", "pct_change", "annual_openings"]
    return wide


def load_wages(path=WAGE_PATH):
    """MILMI occupation-level wages (latin-1, comma; HOURLY -> annualized)."""
    df = pd.read_csv(path, dtype=str, encoding="latin-1")
    df["soc6"] = df["SOC Occupation Code"].map(_norm_soc)
    df["val"] = pd.to_numeric(df["Measure Values"], errors="coerce")
    wide = df.pivot_table(index="soc6", columns="Measure Names",
                          values="val", aggfunc="first").reset_index()
    for out, src in [("median_wage", "Median Wage"),
                     ("entry_wage", "Entry Level Wage"),
                     ("exp_wage", "ExperienceWage")]:
        wide[out] = pd.to_numeric(wide.get(src), errors="coerce") * HOURS_PER_YEAR
    return wide[["soc6", "median_wage", "entry_wage", "exp_wage"]]


def build():
    xw = load_crosswalk()
    soc = load_projections().merge(load_wages(), on="soc6", how="left")

    # (a) itemized: one row per CIP x mapped occupation, with demand + wage
    itemized = xw.merge(soc, on="soc6", how="left")

    # summary DERIVED from itemized -- breadth/growth for openings, band for wages
    g = itemized.groupby(["cip", "cip_title"])
    summary = g.agg(
        n_occ=("soc6", "nunique"),
        n_matched=("annual_openings", lambda s: int(s.notna().sum())),
        n_growing=("pct_change", lambda s: int((s > 0).sum())),
        wage_lo=("median_wage", "min"),
        wage_hi=("median_wage", "max"),
        wage_median_of_occs=("median_wage", "median"),
    ).reset_index()
    summary["share_growing"] = (
        summary["n_growing"] / summary["n_matched"].replace(0, np.nan)
    ).round(2)

    os.makedirs(OUT_DIR, exist_ok=True)
    itemized.to_parquet(os.path.join(OUT_DIR, "cip_demand_itemized.parquet"), index=False)
    summary.to_parquet(os.path.join(OUT_DIR, "cip_demand_summary.parquet"), index=False)

    matched = int((summary["n_matched"] > 0).sum())
    print(f"itemized rows : {len(itemized):,}")
    print(f"CIPs total    : {summary['cip'].nunique():,}")
    print(f"CIPs w/ MI demand match : {matched:,} "
          f"({matched / summary['cip'].nunique():.0%})")
    print(f"wrote -> {OUT_DIR}/cip_demand_itemized.parquet, "
          f"{OUT_DIR}/cip_demand_summary.parquet")
    return itemized, summary


if __name__ == "__main__":
    build()
