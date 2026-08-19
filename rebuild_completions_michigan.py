"""
rebuild_completions_michigan.py -- rebuild data/app/completions_michigan.parquet
correctly, straight from the raw per-year IPEDS Completions files in
data/raw/ipeds/c{year}_a.parquet, bypassing whatever built the current version.

THE BUG THIS FIXES

The raw IPEDS "CIP Data" completions file (c{year}_a.parquet) reports the same
underlying completions THREE separate ways in the same table, and the current
completions_michigan.parquet appears to sum across all of them indiscriminately,
compounding into a large overcount (confirmed example: WSU Psychology 2019 shows
999 in the current mart; the true figure is 333):

  1. CIP HIERARCHY DUPLICATION. CIPCODE appears at three granularities in the same
     table -- 2-digit ("42"), 4-digit ("42.01"), and 6-digit ("42.0101") -- and
     every coarser level is an exact rollup of the finer one (confirmed: WSU's
     2019 bachelor's completions sum to 3,532 at BOTH the 4-digit and 6-digit
     level, because every 4-digit row's value is nothing but the sum of its
     6-digit children; the 2-digit level rolls up further still, and CIPCODE "99"
     at that level is literally the university-wide grand total). Only the 6-digit
     level is the actual, non-redundant detail.

  2. AWLEVEL TOTAL-CODE DUPLICATION. Within a single CIPCODE, AWLEVEL 12 and
     AWLEVEL 15 are not real, distinct award levels -- each one independently
     equals the sum of the real award levels (1,2,3,4,5,6,7,8,17,18,19) for that
     CIP. Confirmed across every CIP checked. Codes 13/14/16/20/21 showed up as
     small residual values in spot checks and are excluded here too, since they
     aren't part of the documented 11-level real scheme (1-8, 17-19) either --
     if you find real, undocumented completions hiding in one of those, they will
     show up as a gap versus the current buggy total, not silently.

  3. MAJORNUM (first vs. second major). A student who completes a double major
     is reported once under MAJORNUM=1 (first major) and again under MAJORNUM=2
     (second major) -- against different CIP codes, ordinarily. This script
     defaults to MAJORNUM==1 only, which avoids double-counting a single student's
     combined completion, but also means a second-major program gets no credit
     for that student. That's a genuine methodological choice, not just a bug fix
     -- see MAJORNUM_FILTER below if you want to include second majors too.

FIX: filter to CIPCODE length 7 (the "XX.XXXX" 6-digit form only), AWLEVEL in
the real 11-level set, and MAJORNUM==1 (by default), before summing.

SCHEMA NOTE: c2024_a.parquet uses a lowercase "unitid" column while 2019-2023
use uppercase "UNITID" -- everything else is consistent. This script normalizes
column names case-insensitively and aborts if any year is missing a needed
column outright, rather than silently skipping it.

Usage (run from the project root, e.g. ~/Antigravity/IPEDS_sandbox):
    python rebuild_completions_michigan.py
"""

import os
import shutil
import sys
from datetime import datetime

import pandas as pd

IPEDS_RAW_DIR = "data/raw/ipeds"
OUTPUT_PATH = "data/app/completions_michigan.parquet"
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

REAL_AWLEVELS = {1, 2, 3, 4, 5, 6, 7, 8, 17, 18, 19}
MAJORNUM_FILTER = {1}  # first major only; add 2 here if you want second majors counted too

# Michigan's 15 public universities, same scope as the current completions_michigan.parquet
MI_UNITIDS = {
    "169248": "Central Michigan University",
    "169798": "Eastern Michigan University",
    "169910": "Ferris State University",
    "170082": "Grand Valley State University",
    "170639": "Lake Superior State University",
    "171100": "Michigan State University",
    "171128": "Michigan Technological University",
    "171456": "Northern Michigan University",
    "171571": "Oakland University",
    "172051": "Saginaw Valley State University",
    "170976": "University of Michigan-Ann Arbor",
    "171137": "University of Michigan-Dearborn",
    "171146": "University of Michigan-Flint",
    "172644": "Wayne State University",
    "172699": "Western Michigan University",
}

REQUIRED_COLS = ["UNITID", "CIPCODE", "MAJORNUM", "AWLEVEL", "CTOTALT"]


def _fail(msg):
    print(f"\nABORTED: {msg}")
    print("No files were modified.")
    sys.exit(1)


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_year(year):
    path = os.path.join(IPEDS_RAW_DIR, f"c{year}_a.parquet")
    if not os.path.exists(path):
        _fail(f"{path} not found.")
    df = pd.read_parquet(path)

    # normalize column names case-insensitively; abort if something is genuinely missing
    upper_map = {c.upper(): c for c in df.columns}
    missing = [c for c in REQUIRED_COLS if c not in upper_map]
    if missing:
        _fail(f"c{year}_a.parquet is missing required column(s): {missing} "
              f"(has: {list(df.columns)}). Schema has drifted beyond a simple case "
              "difference -- inspect this year's file by hand.")
    df = df.rename(columns={upper_map[c]: c for c in REQUIRED_COLS})[REQUIRED_COLS]

    df = df[df["UNITID"].isin(MI_UNITIDS.keys())]
    n_before = len(df)
    df = df[df["CIPCODE"].str.len() == 7]
    n_after_cip = len(df)
    df = df[df["AWLEVEL"].isin(REAL_AWLEVELS)]
    n_after_awlevel = len(df)
    df = df[df["MAJORNUM"].isin(MAJORNUM_FILTER)]
    n_after_majornum = len(df)

    print(f"  {year}: {n_before:,} MI rows -> {n_after_cip:,} after 6-digit-CIP filter "
          f"-> {n_after_awlevel:,} after real-AWLEVEL filter -> {n_after_majornum:,} "
          "after MAJORNUM filter")

    out = df.groupby(["UNITID", "CIPCODE", "AWLEVEL"], as_index=False)["CTOTALT"].sum()
    out["year"] = str(year)
    out = out.rename(columns={"UNITID": "unitid", "CIPCODE": "cip_code",
                               "AWLEVEL": "award_level", "CTOTALT": "total_degrees"})
    out["institution"] = out["unitid"].map(MI_UNITIDS)
    return out[["year", "unitid", "cip_code", "award_level", "total_degrees", "institution"]]


def main():
    if not os.path.isdir(IPEDS_RAW_DIR):
        _fail(f"'{IPEDS_RAW_DIR}' not found. Run this script from the project root.")

    print("Rebuilding completions_michigan.parquet from raw IPEDS files...")
    frames = [load_year(y) for y in YEARS]
    result = pd.concat(frames, ignore_index=True)
    result["total_degrees"] = result["total_degrees"].astype(int)

    print(f"\nTotal rows: {len(result):,}")

    # spot-check against the diagnosed bug: WSU Psychology 2019 should now be 333, not 999
    check = result[(result.unitid == "172644") & (result.cip_code == "42.0101") & (result.year == "2019")]
    total = check["total_degrees"].sum()
    print(f"Verification -- WSU Psychology (42.0101), 2019, summed across real award levels: "
          f"{total} (expected 333; was 999 in the current buggy mart)")
    if total != 333:
        _fail(f"Expected 333 for this known check case, got {total}. Something about this "
              "rebuild doesn't match the diagnosed bug -- do not trust this output. Inspect "
              "before proceeding.")

    if os.path.exists(OUTPUT_PATH):
        backup_path = f"{OUTPUT_PATH}.bak_{_timestamp()}"
        shutil.copy2(OUTPUT_PATH, backup_path)
        print(f"Existing file backed up to: {backup_path}")

    result.to_parquet(OUTPUT_PATH, index=False)
    print(f"Wrote corrected file: {OUTPUT_PATH}")
    print("\nNote: data/app/completions_michigan.parquet.old (the previously-renamed, buggy "
          "version) was left untouched -- delete it by hand once you've confirmed this "
          "rebuild is being used correctly by anything downstream (e.g. build_demand.py, "
          "the portfolio_* pipeline) that reads completions_michigan.parquet.")


if __name__ == "__main__":
    main()
