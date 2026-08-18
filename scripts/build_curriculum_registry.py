"""
build_curriculum_registry.py -- turn a raw WSU curriculum export into the registry
that etl/ and scripts/build_pipeline.py consume, at dictionaries/wsu_program_cip_<YYYYMMDD>.xlsx.

Why this exists: the exports we get from the curriculum system have not been stable,
and two separate defects have already reached the pipeline.

  1. CIP arrives as an Excel NUMBER, so 03.0104 is stored as 30104 and the leading
     zero is already gone before anything downstream sees it. Slicing that with a
     LEFT()-style operation silently relabels CIP family 03 as 30, 05 as 50, 09 as
     90 -- 42 of 859 rows in the 2026-08 export, spanning CLAS and CFPCA. This
     script zero-pads to 6 FIRST, then derives CIP4/CIP2, and writes all three as
     TEXT cells so reopening the file in Excel cannot re-strip them.

  2. The export named "Curricula Catalog with CPLR-1.xlsx" (2026-08-17) contained
     NO CPLR columns at all -- just the 10 catalog columns. Assume the next export
     is also mislabeled and verify the columns yourself before trusting the name.

CPLR carry-over (the part to re-check every time):
When the catalog export lacks CPLR, this script back-fills it from the previous
registry (--cplr-from). That is only safe because of a property verified on the
2026-08 data: `CPLR Level` and `Credential Desc` are strictly 1:1 per `Program`
(0 of 215 programs carried more than one value), so a Program-level join loses
nothing. `Min_Credits` is NOT program-level -- it varies by major in 57 of 215
programs (Accounting 120 vs Accounting Honors 132) -- so it joins on Program+Major
and is left blank where the pair is new. Those two properties are re-asserted at
runtime below; if a future export violates them, this script ABORTS rather than
silently producing a wrong registry.

Rows whose CPLR was not inherited from a real registry row are marked in the
`cplr_source` column, so provenance stays visible in the output file.

Usage (from the project root):
    python scripts/build_curriculum_registry.py \
        --catalog "/path/to/Curricula Catalog.xlsx" \
        --cplr-from dictionaries/Active_Curriculum202604.xlsx

If the catalog export already carries its own CPLR columns, omit --cplr-from and
they are used as-is (the preferred case -- no inference at all).
"""

import argparse
import os
import sys
from datetime import datetime

import pandas as pd
from openpyxl.styles import Alignment

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CPLR_COLUMNS = ["CPLR Rule", "CPLR Level", "Credential Desc", "Length", "Min_Credits"]
BASE_COLUMNS = ["Prog Rule", "Prog Term", "College", "Dept", "Program",
                "Major Rule", "Major Term", "Major", "Major Desc"]

# All UGC* programs in the 2026-04 registry were unanimously level 1 / undergraduate
# certificate. Used only to fill a genuinely new program with no row to inherit.
UGC_LEVEL = 1
UGC_CREDENTIAL = "Undergraduate certificate or diploma program"


def _fail(msg):
    print(f"\nABORTED: {msg}")
    print("No file was written.")
    sys.exit(1)


def add_cip_columns(df):
    """Derive CIP6/CIP4/CIP2, restoring the leading zero before any slicing."""
    if "CIP" not in df.columns:
        _fail("catalog has no 'CIP' column -- check the export.")
    cip6 = df["CIP"].dropna().astype(float).astype(int).astype(str).str.zfill(6)
    if not cip6.str.fullmatch(r"\d{6}").all():
        _fail("some CIP values did not normalize to 6 digits.")
    df = df.drop(columns=["CIP"]).copy()
    df["CIP6"], df["CIP4"], df["CIP2"] = cip6, cip6.str[:4], cip6.str[:2]
    n_lz = int(cip6.str.startswith("0").sum())
    print(f"  CIP6/CIP4/CIP2 derived; {n_lz} row(s) in leading-zero families (03-09) preserved.")
    return df


def verify_cplr_grain(prev):
    """Re-assert the properties that make a Program-level CPLR carry-over safe."""
    for col in ("CPLR Level", "Credential Desc"):
        varying = (prev.groupby("Program")[col].nunique(dropna=True) > 1).sum()
        if varying:
            _fail(
                f"'{col}' is no longer 1:1 per Program ({varying} program(s) carry more "
                "than one value). The Program-level carry-over this script relies on is "
                "no longer valid -- get an export with real CPLR columns instead."
            )
    print("  verified: CPLR Level and Credential Desc are 1:1 per Program.")
    varying_mc = (prev.groupby("Program")["Min_Credits"].nunique(dropna=True) > 1).sum()
    print(f"  note: Min_Credits varies by major in {varying_mc} program(s) -- joined on Program+Major.")


def carry_cplr(new, prev):
    verify_cplr_grain(prev)
    prog = (prev.sort_values("Major Rule").groupby("Program")
                .agg({"CPLR Rule": "first", "CPLR Level": "first",
                      "Credential Desc": "first", "Length": "first"}))
    out = new.join(prog, on="Program")

    mc = prev.set_index(["Program", "Major"])["Min_Credits"]
    mc = mc[~mc.index.duplicated()]
    out["Min_Credits"] = pd.MultiIndex.from_frame(out[["Program", "Major"]]).map(mc)

    out["cplr_source"] = out["CPLR Level"].notna().map({True: "registry", False: ""})

    # Programs new since the previous registry have nothing to inherit. Only the
    # UGC* convention is well-established enough to fill; anything else is left
    # blank and reported, so it gets a human decision rather than a silent guess.
    orphan = out["CPLR Level"].isna()
    ugc = orphan & out["Program"].str.startswith("UGC", na=False)
    out.loc[ugc, ["CPLR Level", "Credential Desc", "Length"]] = [UGC_LEVEL, UGC_CREDENTIAL, 1.0]
    out.loc[ugc, "cplr_source"] = "inferred (new program, UGC* convention)"

    still = out["CPLR Level"].isna()
    if still.any():
        print(f"  ⚠️  {int(still.sum())} row(s) have NO CPLR and no convention to infer from:")
        for _, r in out[still][["Program", "Major Desc"]].drop_duplicates().iterrows():
            print(f"       {r['Program']:16s} {r['Major Desc']}")
        print("     Fill these by hand, or get an export with real CPLR columns.")
    if ugc.any():
        print(f"  {int(ugc.sum())} new UGC* row(s) filled from convention (marked in cplr_source).")
    print(f"  CPLR carried from registry for {int((out['cplr_source'] == 'registry').sum())} row(s).")
    return out


def write_registry(df, out_path):
    cols = [c for c in BASE_COLUMNS if c in df.columns] + \
           ["CIP6", "CIP4", "CIP2"] + \
           [c for c in CPLR_COLUMNS if c in df.columns]
    if "cplr_source" in df.columns:
        cols.append("cplr_source")
    df = df[cols]
    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="Sheet1")
        ws = xw.sheets["Sheet1"]
        hdr = {c.value: c.column_letter for c in ws[1]}
        for name in ("CIP6", "CIP4", "CIP2"):
            for cell in ws[hdr[name]][1:]:
                cell.number_format = "@"      # text, so Excel can't re-strip zeros
                cell.alignment = Alignment(horizontal="left")
    print(f"\nWrote {out_path}: {len(df):,} rows, {len(df.columns)} columns")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True, help="raw curriculum export (.xlsx)")
    ap.add_argument("--cplr-from", help="previous registry to carry CPLR from, if the catalog lacks it")
    ap.add_argument("--out", help="output path (default dictionaries/wsu_program_cip_<today>.xlsx)")
    args = ap.parse_args()

    print(f"--- Reading catalog: {args.catalog} ---")
    new = pd.read_excel(args.catalog)
    print(f"  {len(new):,} rows, {len(new.columns)} columns")

    missing = [c for c in CPLR_COLUMNS if c not in new.columns]
    if missing:
        print(f"  catalog is MISSING CPLR columns: {missing}")
        if not args.cplr_from:
            _fail("catalog has no CPLR columns and no --cplr-from was given.")
    else:
        print("  catalog carries its own CPLR columns -- no carry-over needed.")

    new = add_cip_columns(new)

    if missing:
        print(f"\n--- Carrying CPLR from: {args.cplr_from} ---")
        prev = pd.read_excel(args.cplr_from)
        new = carry_cplr(new, prev)

    out = args.out or f"dictionaries/wsu_program_cip_{datetime.now():%Y%m%d}.xlsx"
    write_registry(new, out)
    print("\nNext: rerun scripts/build_pipeline.py so data/app/ picks up the new registry.")


if __name__ == "__main__":
    main()
