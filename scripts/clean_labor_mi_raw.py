"""
clean_labor_mi_raw.py -- normalize a freshly-downloaded MILMI IOWage_data.csv in place,
in data/raw/labor_mi/, so build_demand.py needs NO changes to keep working.

Why this exists: MILMI's Data Search tool (milmi.org/datasearch/OCCPROJ) has, at
different times, exported IOWage_data.csv in different shapes -- comma vs. tab
delimited, latin-1 vs. UTF-16, "SOC Occupation Code" vs. "Occupation Code" as the
column name, and statewide-only vs. 31-geography scope. build_demand.py's
load_wages() was written against one specific shape (comma, latin-1,
"SOC Occupation Code", statewide-only) and will either fail to parse or silently
pull the wrong data if a future export doesn't match that shape. This script is a
one-time-per-download normalization step: point it at whatever MILMI just gave you,
and it rewrites data/raw/labor_mi/IOWage_data.csv back into the exact shape
build_demand.py already expects, with two additional data-quality fixes applied:

  1. Restrict to statewide Michigan only. MILMI's wage export can include up to 31
     geographies (10 Prosperity Regions, Balance-of-State regions, 20 metro areas,
     plus statewide). build_demand.py's load_wages() does not filter by geography --
     it relies on pivot_table(..., aggfunc="first") to pick whichever row comes
     first, which is statewide Michigan for most but not all occupations. This
     script filters to Area == "Michigan" explicitly, so that ambiguity can't
     happen regardless of what order the source file lists rows in.

  2. Neutralize the 9999.99 suppressed-wage sentinel. MILMI uses 9999.99 as a
     placeholder for a suppressed/unavailable hourly wage. build_demand.py
     annualizes every hourly figure by multiplying by 2080 without checking for
     this sentinel first, turning it into a fake wage of $20,799,979.20. This
     script blanks out that sentinel in the raw file, so build_demand.py's
     existing pd.to_numeric(errors="coerce") call already turns it into NaN with
     no code change needed there.

This script also does a read-only sanity check of IOMatrix_data.csv (the
projections file) and reports if its shape has drifted from what build_demand.py
expects. It does not modify IOMatrix_data.csv.

Usage (run from the project root, e.g. ~/Antigravity/IPEDS_sandbox):
    python scripts/clean_labor_mi_raw.py

What it does NOT do: it does not touch build_demand.py, and it does not run the
dashboard's build pipeline. Run build_demand.py yourself afterward, as usual.
"""

import os
import re
import shutil
import sys
from datetime import datetime

import pandas as pd

RAW_DIR = "data/raw/labor_mi"
WAGE_PATH = os.path.join(RAW_DIR, "IOWage_data.csv")
MATRIX_PATH = os.path.join(RAW_DIR, "IOMatrix_data.csv")

SENTINEL = "9999.99"
SOC_CODE_RE = re.compile(r"^\d{2}-\d{4}$")       # format used in IOWage_data.csv
BARE_SOC_CODE_RE = re.compile(r"^\d{6}$")        # format used in IOMatrix_data.csv

# Smart punctuation that shows up in occupation titles (e.g. "Sheriff's") and isn't
# representable in latin-1 -- the encoding build_demand.py's load_wages() expects.
# Replaced with plain ASCII equivalents rather than silently dropped/mangled.
_SMART_PUNCT = {
    "\u2018": "'", "\u2019": "'",   # curly single quotes
    "\u201c": '"', "\u201d": '"',   # curly double quotes
    "\u2013": "-", "\u2014": "-",   # en/em dash
    "\u2026": "...",                # ellipsis
}

# Column names build_demand.py's load_wages() actually reads. Everything else is
# carried through unchanged for traceability, but these are the load-bearing ones.
REQUIRED_OUTPUT_COLUMNS = ["SOC Occupation Code", "Measure Names", "Measure Values"]


def _fail(msg):
    print(f"\nABORTED: {msg}")
    print("No files were modified.")
    sys.exit(1)


def sniff_and_read(path, label):
    """Read a MILMI export whether it's comma/latin-1 or tab/UTF-16, and say which."""
    with open(path, "rb") as f:
        head = f.read(4)
    if head[:2] in (b"\xff\xfe", b"\xfe\xff"):
        encoding, sep, shape = "utf-16", "\t", "tab-delimited / UTF-16"
    else:
        encoding, sep, shape = "latin-1", ",", "comma-delimited / latin-1"
    df = pd.read_csv(path, dtype=str, encoding=encoding, sep=sep)
    print(f"[{label}] read as {shape}: {len(df):,} rows, {len(df.columns)} columns")
    return df


def check_matrix(path):
    print("\n--- Checking IOMatrix_data.csv (read-only, no changes made) ---")
    if not os.path.exists(path):
        print(f"  Not found at {path} -- skipping check.")
        return
    df = sniff_and_read(path, "IOMatrix_data.csv")
    if "Area" in df.columns:
        areas = df["Area"].dropna().unique()
        if list(areas) == ["Michigan"]:
            print("  Area: statewide Michigan only, as expected.")
        else:
            print(f"  WARNING: expected only 'Michigan', found {len(areas)} area(s): {list(areas)[:10]}")
            print("  This file has drifted from what build_demand.py expects. Consider re-running")
            print("  this script's logic against IOMatrix_data.csv too before rebuilding.")
    if "Occupation Code" in df.columns:
        bad = [c for c in df["Occupation Code"].dropna().unique() if not BARE_SOC_CODE_RE.match(c)]
        if bad:
            print(f"  WARNING: {len(bad)} malformed occupation code(s) found: {bad[:10]}")
        else:
            print("  Occupation codes: all well-formed.")


def clean_wage_file(path):
    print(f"\n--- Cleaning {path} ---")
    if not os.path.exists(path):
        _fail(f"{path} not found. Run this script from the project root.")

    df = sniff_and_read(path, "IOWage_data.csv")

    # --- locate the occupation-code column under either name ---
    code_col = None
    for candidate in ("SOC Occupation Code", "Occupation Code"):
        if candidate in df.columns:
            code_col = candidate
            break
    if code_col is None:
        _fail("Neither 'SOC Occupation Code' nor 'Occupation Code' found in this file's "
              f"columns: {list(df.columns)}. The export schema has changed again -- "
              "inspect the file by hand before proceeding.")

    for required in ("Area", "Measure Names", "Measure Values"):
        if required not in df.columns:
            _fail(f"Expected column '{required}' not found in this file's columns: "
                  f"{list(df.columns)}. The export schema has changed again -- "
                  "inspect the file by hand before proceeding.")

    # --- 1. restrict to statewide Michigan ---
    areas = df["Area"].value_counts()
    print(f"  Areas found in file: {len(areas)}")
    if len(areas) > 1:
        print(f"    {dict(areas.head(5))}{' ...' if len(areas) > 5 else ''}")
    if "Michigan" not in areas.index:
        _fail("No 'Michigan' statewide rows found in this file's Area column -- "
              f"found: {list(areas.index)}. Cannot proceed without a statewide row to keep.")
    before = len(df)
    df = df[df["Area"] == "Michigan"].copy()
    print(f"  Filtered to Area == 'Michigan': {before:,} -> {len(df):,} rows")

    # --- validate occupation codes are well-formed after filtering ---
    bad_codes = sorted(c for c in df[code_col].dropna().unique() if not SOC_CODE_RE.match(c))
    if bad_codes:
        _fail(
            f"{len(bad_codes)} malformed occupation code(s) found after filtering to Michigan: "
            f"{bad_codes[:15]}. This looks like the Excel date-corruption issue seen before "
            "(e.g. a code like 11-2011 becoming 'Nov-11'). Do not proceed automatically -- "
            "re-download the file without opening it in Excel first, or handle these rows by hand."
        )
    print(f"  Occupation codes: all {df[code_col].nunique()} distinct codes are well-formed.")

    # --- 2. neutralize the suppressed-wage sentinel ---
    is_sentinel = df["Measure Values"].astype(str).str.strip() == SENTINEL
    n_sentinel = int(is_sentinel.sum())
    df.loc[is_sentinel, "Measure Values"] = ""
    print(f"  Suppressed-wage sentinel ({SENTINEL}): {n_sentinel:,} rows blanked out.")

    # --- normalize the code column name for build_demand.py ---
    if code_col != "SOC Occupation Code":
        df = df.rename(columns={code_col: "SOC Occupation Code"})
        print(f"  Renamed column '{code_col}' -> 'SOC Occupation Code'.")

    missing = [c for c in REQUIRED_OUTPUT_COLUMNS if c not in df.columns]
    if missing:
        _fail(f"Internal check failed -- output is missing required column(s): {missing}")

    # --- normalize smart punctuation so the file can actually be written as latin-1 ---
    # (e.g. occupation titles like "Sheriff's" sometimes use a curly apostrophe that
    # doesn't exist in latin-1; build_demand.py hardcodes encoding="latin-1" on read,
    # so the file written here has to actually be valid latin-1, not just close to it)
    n_replaced = 0
    for col in df.select_dtypes(include=["object", "string"]).columns:
        for bad_char, replacement in _SMART_PUNCT.items():
            has_char = df[col].astype(str).str.contains(bad_char, regex=False, na=False)
            if has_char.any():
                n_replaced += int(has_char.sum())
                df[col] = df[col].astype(str).str.replace(bad_char, replacement, regex=False)
    if n_replaced:
        print(f"  Normalized {n_replaced} cell(s) with smart-punctuation characters "
              "(curly quotes/dashes) to plain ASCII equivalents, for latin-1 compatibility.")

    # --- back up the original file, then overwrite with the cleaned version ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.bak_{timestamp}"
    shutil.copy2(path, backup_path)
    print(f"  Original backed up to: {backup_path}")

    try:
        df.to_csv(path, index=False, encoding="latin-1")
    except UnicodeEncodeError as e:
        _fail(
            f"Could not write the cleaned file as latin-1 -- unhandled character: {e}. "
            "Add it to the _SMART_PUNCT replacement table at the top of this script and "
            "rerun (the original file is safe, untouched, and already backed up above)."
        )
    print(f"  Wrote cleaned file (comma-delimited, latin-1): {path}")
    print(f"  Final row count: {len(df):,}, all Area == 'Michigan', "
          f"0 malformed codes, 0 unhandled sentinel values.")


def main():
    if not os.path.isdir(RAW_DIR):
        _fail(f"'{RAW_DIR}' not found. Run this script from the project root "
              "(the directory containing data/raw/labor_mi/).")
    check_matrix(MATRIX_PATH)
    clean_wage_file(WAGE_PATH)
    print("\nDone. data/raw/labor_mi/IOWage_data.csv is now in the shape build_demand.py "
          "expects -- no changes needed there. Run build_demand.py next as usual.")


if __name__ == "__main__":
    main()
