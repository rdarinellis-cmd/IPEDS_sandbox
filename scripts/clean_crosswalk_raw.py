"""
clean_crosswalk_raw.py -- fix and consolidate data/raw/crosswalks/, in place.

Findings this addresses (from hand-inspecting the six files in that folder):

  1. cip2020_soc2018_crosswalk.parquet has CIP2020Code stored as float64, which
     drops the leading zero for CIP families 01, 03, 04, 05, and 09 (553 of 6,097
     rows -- e.g. "01.0000" becomes 1.0). The source file it was built from,
     CIP2020_SOC2018_Crosswalk.xlsx, is clean when read with dtype=str -- this is
     a read-time bug in whatever built the parquet, not a source-data problem.
     This script rebuilds it correctly from the .xlsx.

  2. CIPCode2020.csv and CIPCode2020_CIPTitle.csv are byte-identical duplicates
     (confirmed by checksum). This script keeps CIPCode2020_CIPTitle.csv (the more
     descriptive name) and archives the other, after checking nothing in the
     codebase references the one being retired.

  3. cip_code_to_title.parquet (in this raw/ folder) and data/app/cip_dictionary.parquet
     (the properly-located app-tier artifact) contain identical data -- same rows,
     same order, just different parquet file metadata. This script archives the
     raw/ copy as redundant, after checking for references, PROVIDED it can find
     data/app/cip_dictionary.parquet and confirm the two still match (it will not
     archive on an assumption).

  4. Curricula_Catalog_with_CPLR-1.xlsx is a stale, earlier snapshot of the WSU
     curriculum registry -- not a crosswalk file at all, and it doesn't belong in
     this folder. This script looks for the current registry (Active_Curriculum*.xlsx)
     elsewhere in the project, and if it finds one where the great majority of rows
     match, archives the stale snapshot. If it can't find a clear match, it leaves
     the file alone and tells you why.

Nothing is ever deleted. Anything retired is moved to data/raw/crosswalks/_archive/
with a timestamp, and the original file being rebuilt is backed up the same way
before being overwritten. Anything the script finds still referenced elsewhere in
the codebase is left in place, flagged, and not archived automatically.

Usage (run from the project root, e.g. ~/Antigravity/IPEDS_sandbox):
    python scripts/clean_crosswalk_raw.py
"""

import hashlib
import os
import re
import shutil
import sys
from datetime import datetime

import pandas as pd

CROSSWALK_DIR = "data/raw/crosswalks"
ARCHIVE_DIR = os.path.join(CROSSWALK_DIR, "_archive")
APP_DICTIONARY_PATH = "data/app/cip_dictionary.parquet"

XLSX_CROSSWALK = os.path.join(CROSSWALK_DIR, "CIP2020_SOC2018_Crosswalk.xlsx")
PARQUET_CROSSWALK = os.path.join(CROSSWALK_DIR, "cip2020_soc2018_crosswalk.parquet")
CSV_KEEP = os.path.join(CROSSWALK_DIR, "CIPCode2020_CIPTitle.csv")
CSV_RETIRE = os.path.join(CROSSWALK_DIR, "CIPCode2020.csv")
PARQUET_TITLE_RETIRE = os.path.join(CROSSWALK_DIR, "cip_code_to_title.parquet")
XLSX_CURRICULA_RETIRE = os.path.join(CROSSWALK_DIR, "Curricula_Catalog_with_CPLR-1.xlsx")

CIP_CODE_RE = re.compile(r"^\d{2}\.\d{4}$")

# directories to skip when searching the codebase for references to a filename
SKIP_DIRS = {".venv", ".git", "__pycache__", "node_modules", ".streamlit", ARCHIVE_DIR}
# only search text-ish source/config files -- not the data files themselves
SEARCHABLE_EXTS = {".py", ".md", ".toml", ".cfg", ".ini", ".yaml", ".yml", ".sh", ".txt"}


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _archive(path, reason):
    """Move a file to _archive/ with a timestamp, never delete."""
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    base = os.path.basename(path)
    dest = os.path.join(ARCHIVE_DIR, f"{_timestamp()}__{base}")
    shutil.move(path, dest)
    print(f"    ARCHIVED -> {dest}")
    print(f"    reason: {reason}")


def find_references(filename, project_root="."):
    """Grep the codebase (excluding data/, venv, git, etc.) for a bare filename."""
    hits = []
    self_path = os.path.abspath(__file__)
    for dirpath, dirnames, filenames in os.walk(project_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        if os.path.abspath(dirpath).startswith(os.path.abspath(CROSSWALK_DIR)):
            continue  # don't count the data files themselves as "references"
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in SEARCHABLE_EXTS:
                continue
            fpath = os.path.join(dirpath, fn)
            if os.path.abspath(fpath) == self_path:
                continue  # this script's own docstring/variables mention every filename by design
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for lineno, line in enumerate(f, start=1):
                        if filename in line:
                            hits.append((fpath, lineno, line.strip()))
            except OSError:
                continue
    return hits


def rebuild_crosswalk_parquet():
    print("\n--- 1. Rebuilding cip2020_soc2018_crosswalk.parquet ---")
    if not os.path.exists(XLSX_CROSSWALK):
        print(f"  SKIPPED: source {XLSX_CROSSWALK} not found.")
        return
    df = pd.read_excel(XLSX_CROSSWALK, sheet_name="CIP-SOC", dtype=str)
    bad = sorted(c for c in df["CIP2020Code"].dropna().unique() if not CIP_CODE_RE.match(c))
    if bad:
        print(f"  ABORTED: {len(bad)} CIP2020Code values don't match the expected XX.XXXX "
              f"format after reading as text: {bad[:10]}. The source file's format has "
              "changed -- inspect it by hand before rebuilding.")
        return
    print(f"  Read {len(df):,} rows from CIP-SOC sheet; all CIP2020Code values are well-formed text.")

    if os.path.exists(PARQUET_CROSSWALK):
        old = pd.read_parquet(PARQUET_CROSSWALK)
        if old["CIP2020Code"].dtype != object and old["CIP2020Code"].dtype.name != "string":
            print(f"  Confirmed existing file has CIP2020Code as {old['CIP2020Code'].dtype} "
                  "(the bug being fixed).")
        backup = os.path.join(ARCHIVE_DIR, f"{_timestamp()}__cip2020_soc2018_crosswalk.parquet.bak")
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        shutil.copy2(PARQUET_CROSSWALK, backup)
        print(f"  Existing parquet backed up to: {backup}")

    df.to_parquet(PARQUET_CROSSWALK, index=False)
    print(f"  Wrote corrected parquet: {PARQUET_CROSSWALK} (CIP2020Code as text, leading zeros intact)")


def retire_duplicate_csv():
    print("\n--- 2. Checking CIPCode2020.csv vs CIPCode2020_CIPTitle.csv ---")
    if not (os.path.exists(CSV_KEEP) and os.path.exists(CSV_RETIRE)):
        print("  SKIPPED: one or both files not found.")
        return
    if _md5(CSV_KEEP) != _md5(CSV_RETIRE):
        print("  NOT ARCHIVING: these two files are no longer byte-identical -- they may have "
              "diverged since I last checked. Leaving both in place; compare them by hand.")
        return
    print("  Confirmed byte-identical. Keeping CIPCode2020_CIPTitle.csv as canonical.")
    refs = find_references(os.path.basename(CSV_RETIRE))
    if refs:
        print(f"  NOT ARCHIVING: {os.path.basename(CSV_RETIRE)} is referenced in the codebase:")
        for fpath, lineno, line in refs:
            print(f"    {fpath}:{lineno}: {line}")
        print("  Update those references to CIPCode2020_CIPTitle.csv, then rerun this script.")
        return
    _archive(CSV_RETIRE, "byte-identical duplicate of CIPCode2020_CIPTitle.csv; no codebase references found")


def retire_duplicate_title_parquet():
    print("\n--- 3. Checking cip_code_to_title.parquet vs data/app/cip_dictionary.parquet ---")
    if not os.path.exists(PARQUET_TITLE_RETIRE):
        print("  SKIPPED: cip_code_to_title.parquet not found.")
        return
    if not os.path.exists(APP_DICTIONARY_PATH):
        print(f"  NOT ARCHIVING: couldn't find {APP_DICTIONARY_PATH} to confirm this file is "
              "actually redundant. Leaving it in place.")
        return
    a = pd.read_parquet(PARQUET_TITLE_RETIRE)
    b = pd.read_parquet(APP_DICTIONARY_PATH)
    same_shape = a.shape == b.shape and list(a.columns) == list(b.columns)
    same_content = same_shape and a.reset_index(drop=True).equals(b.reset_index(drop=True))
    if not same_content:
        print("  NOT ARCHIVING: content differs from data/app/cip_dictionary.parquet -- "
              "this may not actually be redundant. Leaving it in place for manual review.")
        return
    print("  Confirmed identical content to data/app/cip_dictionary.parquet.")
    refs = find_references(os.path.basename(PARQUET_TITLE_RETIRE))
    if refs:
        print(f"  NOT ARCHIVING: {os.path.basename(PARQUET_TITLE_RETIRE)} is referenced in the codebase:")
        for fpath, lineno, line in refs:
            print(f"    {fpath}:{lineno}: {line}")
        print("  Update those references to data/app/cip_dictionary.parquet, then rerun this script.")
        return
    _archive(PARQUET_TITLE_RETIRE,
             "identical content to data/app/cip_dictionary.parquet (the correctly-located "
             "app-tier version); no codebase references found")


def retire_stale_curricula_snapshot():
    print("\n--- 4. Checking Curricula_Catalog_with_CPLR-1.xlsx against the current registry ---")
    if not os.path.exists(XLSX_CURRICULA_RETIRE):
        print("  SKIPPED: file not found.")
        return

    candidates = []
    for dirpath, dirnames, filenames in os.walk("."):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn.lower().startswith("active_curriculum") and fn.lower().endswith(".xlsx"):
                candidates.append(os.path.join(dirpath, fn))
    if not candidates:
        print("  NOT ARCHIVING: couldn't find an Active_Curriculum*.xlsx registry anywhere in "
              "the project to compare against. Leaving this file in place -- if you know where "
              "the current registry lives, point this script at it and rerun.")
        return
    current_path = sorted(candidates)[-1]  # most recent by name (e.g. date-stamped filename)
    print(f"  Comparing against: {current_path}")

    old = pd.read_excel(XLSX_CURRICULA_RETIRE, dtype=str)
    current = pd.read_excel(current_path, dtype=str)
    key_cols = [c for c in ["College", "Dept", "Program", "Major", "CIP"] if c in old.columns and c in current.columns]
    if len(key_cols) < 5:
        print(f"  NOT ARCHIVING: could not find all expected key columns to compare "
              f"(found: {key_cols}). Leaving this file in place for manual review.")
        return
    old_keys = set(old[key_cols].apply(tuple, axis=1))
    current_keys = set(current[key_cols].apply(tuple, axis=1))
    matched = len(old_keys & current_keys)
    pct = matched / len(old_keys) * 100 if old_keys else 0
    print(f"  {matched:,} of {len(old_keys):,} rows ({pct:.1f}%) match the current registry exactly.")

    if pct < 90:
        print("  NOT ARCHIVING: match rate below 90% -- not confident this is simply a stale "
              "snapshot of the same registry. Leaving it in place for manual review.")
        return
    missing = old_keys - current_keys
    if missing:
        print(f"  Note: {len(missing)} row(s) in the old snapshot have no match in the current "
              "registry (likely discontinued/renamed programs) -- listed below for reference "
              "before this file is archived:")
        for k in sorted(missing):
            print(f"    {k}")

    refs = find_references(os.path.basename(XLSX_CURRICULA_RETIRE))
    if refs:
        print(f"  NOT ARCHIVING: {os.path.basename(XLSX_CURRICULA_RETIRE)} is referenced in the codebase:")
        for fpath, lineno, line in refs:
            print(f"    {fpath}:{lineno}: {line}")
        print("  Review those references, then rerun this script.")
        return
    _archive(XLSX_CURRICULA_RETIRE,
             f"{pct:.1f}% row match with {current_path} -- stale earlier snapshot of the same "
             "registry; not a crosswalk file; no codebase references found. Discontinued/renamed "
             f"program rows preserved above in this run's output before archiving.")


def main():
    if not os.path.isdir(CROSSWALK_DIR):
        print(f"ABORTED: '{CROSSWALK_DIR}' not found. Run this script from the project root "
              "(the directory containing data/raw/crosswalks/).")
        sys.exit(1)

    rebuild_crosswalk_parquet()
    retire_duplicate_csv()
    retire_duplicate_title_parquet()
    retire_stale_curricula_snapshot()

    print(f"\nDone. Anything archived is in {ARCHIVE_DIR}/ with a timestamp -- nothing was deleted.")
    print("Nothing referenced elsewhere in the codebase was archived automatically; see any "
          "flagged references above.")


if __name__ == "__main__":
    main()
