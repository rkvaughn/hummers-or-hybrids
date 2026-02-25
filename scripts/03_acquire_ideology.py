#!/usr/bin/env python3
"""
03_acquire_ideology.py
Download all ideology and climate belief data sources.

Sources:
  A. Yale Climate Opinion Maps (YCOM) — county-level climate beliefs
     GitHub CSV (YCOM 5.0, 2020 vintage):
     https://github.com/yaleschooloftheenvironment/Yale-Climate-Change-Opinion-Maps

  B. California voter registration by party — precinct-level
     UC Berkeley Statewide Database:
     https://statewidedatabase.org/election.html
     (requires per-county download; this script automates where possible)

  C. California ballot measure returns — precinct-level
     UC Berkeley Statewide Database (same source as B):
     - 2022 General (Prop 30 — EV/clean air): https://statewidedatabase.org/d20/g22.html
     - 2018 Primary (Prop 68 — environment bonds): https://statewidedatabase.org/d10/p18.html

Output:
  data/raw/ycom/ycom_county.csv             — YCOM county-level beliefs
  data/raw/voter_registration/              — per-county voter reg CSVs
  data/raw/ballot_measures/                 — per-county ballot measure CSVs
  data/raw/ycom/ycom_ca_counties.csv        — CA counties only, YCOM variables
  data/raw/voter_registration/votreg_ca_clean.csv   — statewide voter reg
  data/raw/ballot_measures/ballots_ca_clean.csv     — statewide ballot results

YCOM variables used (county-level, 2020 vintage):
  happening       — % who think global warming is happening
  human           — % who think it is mostly human caused
  worried         — % who are worried about global warming
  regulate        — % who support regulating CO2 as a pollutant
  supportRPS      — % who support requiring utilities to use renewable energy
  GeoType         — geographic level (County, State, etc.)
  GEOID           — FIPS code (5-digit for county)
  GeoName         — place name

Limitations:
  - YCOM is county-level. We assign county values to all tracts in that county.
    This is explicit in model caveats — cross-county variation only.
  - YCOM GitHub data is 2020 vintage. Newer estimates (through 2024) are
    available via web registration at climatecommunication.yale.edu.
    If the user obtains a newer CSV, place it in data/raw/ycom/ and re-run.
  - Statewide Database: precinct-level voter registration data requires
    downloading county-specific files. This script iterates over all 58
    California counties. Some files may 404 if the URL pattern changes
    between election cycles — failed counties are logged for manual review.
"""

import time
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
YCOM_DIR = RAW_DIR / "ycom"
VOTREG_DIR = RAW_DIR / "voter_registration"
BALLOT_DIR = RAW_DIR / "ballot_measures"

for d in [YCOM_DIR, VOTREG_DIR, BALLOT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# A. YCOM — Yale Climate Opinion Maps
# ---------------------------------------------------------------------------
YCOM_CSV_URL = (
    "https://raw.githubusercontent.com/yaleschooloftheenvironment/"
    "Yale-Climate-Change-Opinion-Maps/main/"
    "YCOM5.0_2020_webdata_2020-08-19.csv"
)
YCOM_META_URL = (
    "https://raw.githubusercontent.com/yaleschooloftheenvironment/"
    "Yale-Climate-Change-Opinion-Maps/main/"
    "YCOM5.0_2020_webdata_Metadata.csv"
)

YCOM_VARS = [
    "happening",   # % think GW is happening
    "human",       # % think human-caused
    "worried",     # % worried about GW
    "regulate",    # % support CO2 regulation
    "supportRPS",  # % support renewable portfolio standard
]


def acquire_ycom():
    print("--- A. Yale Climate Opinion Maps (YCOM) ---")
    dest = YCOM_DIR / "ycom_county.csv"
    meta_dest = YCOM_DIR / "ycom_metadata.csv"

    if dest.exists():
        print(f"  [skip] YCOM already downloaded: {dest.name}")
        df = pd.read_csv(dest, dtype={"GEOID": str}, encoding="latin-1")
    else:
        print("  Downloading YCOM 5.0 (2020 vintage)...")
        resp = requests.get(YCOM_CSV_URL, timeout=30)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        print(f"  Saved → {dest.name}")

        # metadata
        resp2 = requests.get(YCOM_META_URL, timeout=30)
        if resp2.ok:
            meta_dest.write_bytes(resp2.content)
        df = pd.read_csv(dest, dtype={"GEOID": str}, encoding="latin-1")

    # Filter to California counties (GeoType == "County", GeoName contains "California")
    # Note: YCOM GEOIDs are 4-digit (e.g., "6001"), not zero-padded 5-digit
    ca_counties = df[
        (df["GeoType"] == "County") &
        (df["GeoName"].str.contains("California", na=False))
    ].copy()
    # Zero-pad GEOID to 5-digit county FIPS
    ca_counties["GEOID"] = ca_counties["GEOID"].str.zfill(5)

    # Keep relevant columns
    keep = ["GEOID", "GeoName"] + [v for v in YCOM_VARS if v in df.columns]
    ca_counties = ca_counties[keep].rename(columns={"GEOID": "county_fips", "GeoName": "county_name"})

    out = YCOM_DIR / "ycom_ca_counties.csv"
    ca_counties.to_csv(out, index=False)
    print(f"  CA counties extracted: {len(ca_counties)} rows → {out.name}")
    print(f"  Variables: {[v for v in YCOM_VARS if v in ca_counties.columns]}")
    print(f"  NOTE: YCOM is 2020 vintage. For newer estimates, register at:")
    print(f"        https://climatecommunication.yale.edu/visualizations-data/ycom-us/")
    print(f"        Place the downloaded CSV in {YCOM_DIR}/ and re-run.\n")


# ---------------------------------------------------------------------------
# B. Voter Registration — Statewide Database
# ---------------------------------------------------------------------------
# Statewide Database stores registration data in per-county CSV/DBF files.
# URL pattern for 2022 General registration data (most recent statewide election):
#   https://statewidedatabase.org/pub/data/G22/state/g22_sov_data_by_g22_svprec.zip
# This statewide zip file contains all counties.
SWDB_BASE = "https://statewidedatabase.org/pub/data"

# Statewide zip files (preferred over per-county downloads)
VOTREG_URLS = {
    "g22": f"{SWDB_BASE}/G22/state/state_g22_registration_by_g22_rgprec.zip",  # 2022 General SOR
    "g20": f"{SWDB_BASE}/G20/state/state_g20_registration_by_g20_rgprec.zip",  # 2020 General SOR
}

# Party registration columns vary by file; common names:
PARTY_COLS_CANDIDATES = [
    "DEM", "REP", "GREE", "LIB", "NPP", "OTH",  # short codes
    "DEM_REG", "REP_REG",                          # suffixed
]


def acquire_voter_registration():
    print("--- B. Voter Registration (Statewide Database) ---")
    frames = {}
    for election, url in VOTREG_URLS.items():
        dest = VOTREG_DIR / f"votreg_{election}.zip"
        if dest.exists():
            print(f"  [skip] {election} voter reg already downloaded")
        else:
            print(f"  Downloading {election} voter registration...")
            try:
                resp = requests.get(url, timeout=120, stream=True)
                resp.raise_for_status()
                dest.write_bytes(resp.content)
                print(f"  Saved {dest.stat().st_size / 1e6:.1f} MB → {dest.name}")
            except Exception as e:
                print(f"  ERROR downloading {election} voter reg: {e}")
                print(f"  Manual download: {url}")
                print(f"  Save to: {dest}")
                continue
        frames[election] = dest

    # Parse downloaded zips
    combined_frames = []
    for election, zip_path in frames.items():
        if not zip_path.exists():
            continue
        try:
            df = pd.read_csv(zip_path, compression="zip", dtype=str, low_memory=False)
            df.columns = [c.upper().strip() for c in df.columns]
            df["election"] = election
            combined_frames.append(df)
            print(f"  Parsed {election}: {len(df):,} precincts, columns: {list(df.columns[:10])}...")
        except Exception as e:
            print(f"  ERROR parsing {election}: {e}")
            print(f"  The zip may contain multiple files — inspect manually: {zip_path}")

    if combined_frames:
        combined = pd.concat(combined_frames, ignore_index=True)
        out = VOTREG_DIR / "votreg_ca_raw.csv"
        combined.to_csv(out, index=False)
        print(f"  Combined voter reg → {out.name}, shape: {combined.shape}")
    else:
        print("  No voter registration data parsed. See manual steps above.\n")

    print()


# ---------------------------------------------------------------------------
# C. Ballot Measures — Statewide Database
# ---------------------------------------------------------------------------
# Statewide SOV (Statement of Vote) data by precinct
BALLOT_URLS = {
    "g22_sov": f"{SWDB_BASE}/G22/state/state_g22_sov_data_by_g22_svprec.zip",  # 2022 General
    "p18_sov": f"{SWDB_BASE}/P18/state/state_p18_sov_data_by_p18_svprec.zip",  # 2018 Primary
}

# Proposition identifiers to extract (vary by election file)
# These will be filtered in 04_crosswalk.py once column names are known
TARGET_PROPS = {
    "g22": "PROP_30",   # 2022 Prop 30 — EV/wildfire funding
    "p18": "PROP_68",   # 2018 Prop 68 — parks/water bonds
}


def acquire_ballot_measures():
    print("--- C. Ballot Measures (Statewide Database) ---")
    for election, url in BALLOT_URLS.items():
        dest = BALLOT_DIR / f"ballots_{election}.zip"
        if dest.exists():
            print(f"  [skip] {election} ballot data already downloaded")
            continue
        print(f"  Downloading {election} SOV data...")
        try:
            resp = requests.get(url, timeout=120, stream=True)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
            print(f"  Saved {dest.stat().st_size / 1e6:.1f} MB → {dest.name}")
        except Exception as e:
            print(f"  ERROR downloading {election}: {e}")
            print(f"  Manual download:")
            print(f"    Go to https://statewidedatabase.org/")
            if "g22" in election:
                print(f"    Navigate to 2022 General Election → Statewide data")
            else:
                print(f"    Navigate to 2018 Primary Election → Statewide data")
            print(f"    Download the SOV (Statement of Vote) by precinct zip file")
            print(f"    Save to: {dest}")

    # Parse and extract target propositions
    for election, url in BALLOT_URLS.items():
        dest = BALLOT_DIR / f"ballots_{election}.zip"
        if not dest.exists():
            continue
        try:
            import zipfile
            with zipfile.ZipFile(dest) as z:
                # Pick the CSV file (skip readme or other non-data files)
                csv_names = [n for n in z.namelist() if n.endswith(".csv")]
                if not csv_names:
                    print(f"  ERROR: no CSV found in {dest.name}")
                    continue
                with z.open(csv_names[0]) as f:
                    df = pd.read_csv(f, dtype=str, low_memory=False)
            df.columns = [c.upper().strip() for c in df.columns]
            df["election"] = election

            out = BALLOT_DIR / f"ballots_{election}_raw.csv"
            df.to_csv(out, index=False)
            print(f"  Parsed {election}: {len(df):,} precincts")
            print(f"  Columns (first 20): {list(df.columns[:20])}")

            # Log proposition columns (Statewide DB uses PR_XX_Y / PR_XX_N pattern)
            prop_cols = [c for c in df.columns if c.startswith("PR_") or "PROP" in c or "MEASURE" in c]
            print(f"  Proposition columns found: {prop_cols[:30]}")
        except Exception as e:
            print(f"  ERROR parsing {election}: {e}")

    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=== Ideology Data Acquisition ===\n")
    acquire_ycom()
    time.sleep(1)
    acquire_voter_registration()
    acquire_ballot_measures()

    print("=== Summary ===")
    print("Expected outputs:")
    print(f"  {YCOM_DIR}/ycom_ca_counties.csv   — YCOM beliefs for 58 CA counties")
    print(f"  {VOTREG_DIR}/votreg_ca_raw.csv     — precinct-level party registration")
    print(f"  {BALLOT_DIR}/ballots_g22_raw.csv   — 2022 precinct SOV (incl. Prop 30)")
    print(f"  {BALLOT_DIR}/ballots_p18_raw.csv   — 2018 precinct SOV (incl. Prop 68)")
    print("\nNext: run 04_crosswalk.py to map precincts and zips → Census tracts")


if __name__ == "__main__":
    main()
