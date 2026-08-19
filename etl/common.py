"""
common.py -- shared definitions for the IPEDS dashboard's ETL scripts and page views.

This module is the single source of truth for the things that were previously
copy-pasted across the pipeline: the CIP normalizer, the peer-cohort membership
lists, the WSU school/college lookup, and the brand colors.

Why it exists: `normalize_cip` had drifted into three separate copies, and
`get_wsu_college_mapping()` existed twice -- which meant the same catalog-path bug
had to be found and fixed twice on 2026-08-17. Anything defined here should be
imported, never re-pasted.

Import style (all callers use the project root as the import root):

    from etl.common import normalize_cip, URBAN_PEER_IDS

Scripts that are executed directly from a subdirectory (etl/, scripts/) need the
project root on sys.path first; see the bootstrap at the top of those files.
Streamlit pages need no bootstrap, because `streamlit run app.py` already puts the
project root on sys.path.
"""

import pandas as pd

# --- Wayne State brand palette (ARCHITECTURE.md section 8A) ------------------
# Note: the CSS blocks injected via st.markdown() still carry these hex values as
# literals. That is deliberate -- CSS is brace-heavy, so interpolating Python
# constants into it would require escaping every rule. Keep the two in sync by hand.
WSU_GREEN = "#0C5449"        # PMS 561c -- primary; use for WSU marks and key metrics
WSU_GREEN_WEB = "#0B4C43"    # digital web header variant
WSU_GOLD = "#F2A900"         # PMS 1225c -- accents and highlights only
PEER_GREY = "#737373"        # peer institutions / medians
PEER_GREY_LIGHT = "#CCCCCC"  # de-emphasized peers, unknown categories

# --- Peer cohorts ------------------------------------------------------------
# The 15 Michigan public universities. Both representations below describe the
# same institutions -- verified against hd2024 on 2026-08-17, exact match in both
# directions. Prefer the UNITID form for joins; the name form exists because the
# IPEDS completions/finance compilers filter on INSTNM.
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
    'Western Michigan University',
]

MICHIGAN_UNIVERSITY_IDS = [
    169248, 169798, 169910, 170082, 170639, 171100, 171128, 171456,
    171571, 172051, 170976, 171137, 171146, 172644, 172699,
]

URBAN_PEER_IDS = [
    172644, 133951, 225511, 201885, 139940, 216339,
    234030, 157289, 187985, 145600, 100663,
]

WSU_UNITID = 172644
WSU_NAME = 'Wayne State University'

# Public R1 = IPEDS CONTROL 1 (public) AND Carnegie C21BASIC 15 (R1: very high research)
PUBLIC_R1_CONTROL = 1
PUBLIC_R1_C21BASIC = 15

# --- WSU school/college codes ------------------------------------------------
# Codes as they appear in the curriculum registry's `College` column.
COLLEGE_NAMES = {
    'BA': 'Business (Mike Ilitch School of Business)',
    'ED': 'Education (College of Education)',
    'EN': 'Engineering (College of Engineering)',
    'FA': 'CFPCA (Fine, Performing & Communication Arts)',
    'GS': 'Graduate School',
    'IS': 'Information Sciences (School of Information Sciences)',
    'LS': 'CLAS (Liberal Arts and Sciences)',
    'LW': 'Law (Law School)',
    'MD': 'Medicine (School of Medicine)',
    'NU': 'Nursing (College of Nursing)',
    'PA': 'EACPHS (Pharmacy & Health Sciences)',
    'SW': 'Social Work (School of Social Work)',
}

# --- Sub-baccalaureate CIP families ------------------------------------------
# Predominantly trained through community colleges and registered apprenticeships;
# 4-year public university completions file does not represent this pipeline.
SUB_BACCALAUREATE_FAMILIES = {
    '12': 'Personal & Culinary Services',
    '46': 'Construction Trades',
    '47': 'Mechanic & Repair Technologies',
    '48': 'Precision Production',
    '49': 'Transportation & Materials Moving',
}



def normalize_cip(cip):
    """Normalize a CIP code string to XX.XXXX format with leading zeros and dot.

    Accepts the several shapes CIP codes arrive in across sources: already-dotted
    ("52.0301"), bare 6-digit ("520301"), Excel-mangled 5-digit where the leading
    zero was dropped ("10101" -> "01.0101"), and values wrapped in the ="..."
    formula artifact that IPEDS CSV exports sometimes carry.
    """
    if pd.isna(cip):
        return None
    s = str(cip).strip().replace('="', '').replace('"', '')
    if not s:
        return None

    # Split by dot
    if '.' in s:
        parts = s.split('.')
        family = parts[0]
        prog = parts[1] if len(parts) > 1 else ""
    else:
        # No dot, e.g. "010101" or "1"
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

    # Format family to 2 digits
    try:
        family_int = int(family)
        family_str = f"{family_int:02d}"
    except ValueError:
        family_str = family.zfill(2)

    # Format prog to 4 digits (pad right with zeros)
    prog_clean = prog.replace('.', '').strip()
    if len(prog_clean) < 4:
        prog_str = prog_clean.ljust(4, '0')
    else:
        prog_str = prog_clean[:4]

    return f"{family_str}.{prog_str}"


def split_college_codes(value):
    """Split a stored 'BA, EN, LS' college cell into a list of bare codes.

    The curriculum registry maps one CIP to several colleges, stored comma-joined,
    so both the page filters and the ETL need the same split rule.
    """
    if pd.isna(value):
        return []
    return [c.strip() for c in str(value).split(',') if c.strip()]
