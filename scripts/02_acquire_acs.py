#!/usr/bin/env python3
"""
02_acquire_acs.py
Download American Community Survey 5-Year estimates for California Census tracts.

Source: Census Bureau ACS API
  Base URL: https://api.census.gov/data/{year}/acs/acs5
  Documentation: https://www.census.gov/data/developers/data-sets/acs-5year.html
  Free API key: https://api.census.gov/data/key_signup.html

Output:
  data/raw/acs/acs_tracts_ca_{year}.csv   — one file per ACS vintage
  data/raw/acs/acs_tracts_ca_clean.csv    — merged, cleaned across vintages

Geographic unit: Census tract (California, FIPS state = 06)
ACS vintage pulled: 2023 (2019–2023 5-year estimates) — primary
                    2019 (2015–2019 5-year estimates) — secondary (pre-COVID)

Variables pulled:
  B01003_001E  — Total population
  B19013_001E  — Median household income (past 12 months, inflation-adj)
  B15003_022E  — Population with bachelor's degree
  B15003_001E  — Total population 25+ (denominator for education)
  B25077_001E  — Median home value (owner-occupied units)
  B03002_001E  — Total population (race/ethnicity denominator)
  B03002_003E  — Non-Hispanic White alone
  B03002_004E  — Non-Hispanic Black alone
  B03002_006E  — Non-Hispanic Asian alone
  B03002_012E  — Hispanic or Latino (any race)
  B08301_001E  — Workers 16+ (commute denominator)
  B08301_003E  — Drove alone
  B08301_010E  — Public transportation
  B08301_021E  — Worked from home
  B01003_001E  — Population (numerator for density)
  ALAND        — Land area in square meters (from geographies endpoint, for density)

Derived variables (computed in 05_build_panel.py):
  pct_ba_plus     = B15003_022E / B15003_001E
  pct_white       = B03002_003E / B03002_001E
  pct_black       = B03002_004E / B03002_001E
  pct_asian       = B03002_006E / B03002_001E
  pct_hispanic    = B03002_012E / B03002_001E
  pct_transit     = B08301_010E / B08301_001E
  pct_drove_alone = B08301_003E / B08301_001E
  pct_wfh         = B08301_021E / B08301_001E
  pop_density     = B01003_001E / (ALAND / 2.59e6)  [persons per sq mile]

API note: Census API limits to 50 variables per call; we split into batches.
"""

import os
import time
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "acs"
RAW_DIR.mkdir(parents=True, exist_ok=True)

CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")  # set env var or paste key here
CENSUS_BASE = "https://api.census.gov/data/{year}/acs/acs5"
STATE_FIPS = "06"  # California

ACS_VINTAGES = [2023]  # 2020 tract definitions; single cross-section used for all demographic controls
# NOTE: 2019 ACS (2010 tract definitions) dropped — tract boundary change makes direct merge invalid.
# Robustness check using time-varying controls (2019 ACS re-tabulated to 2020 tracts via NHGIS
# crosswalk) is logged in CLAUDE.md and deferred to the appendix.

# Variables split into two batches to stay under 50-var limit
BATCH_1 = [
    "B01003_001E",  # total population
    "B19013_001E",  # median HH income
    "B15003_022E",  # BA degree
    "B15003_001E",  # total 25+ (edu denominator)
    "B25077_001E",  # median home value
    "B03002_001E",  # total pop (race denominator)
    "B03002_003E",  # non-hispanic white
    "B03002_004E",  # non-hispanic black
    "B03002_006E",  # non-hispanic asian
    "B03002_012E",  # hispanic
]
BATCH_2 = [
    "B08301_001E",  # workers 16+ (commute denominator)
    "B08301_003E",  # drove alone
    "B08301_010E",  # public transit
    "B08301_021E",  # worked from home
]

VARIABLE_LABELS = {
    "B01003_001E": "total_pop",
    "B19013_001E": "median_hh_income",
    "B15003_022E": "pop_ba_degree",
    "B15003_001E": "pop_25plus",
    "B25077_001E": "median_home_value",
    "B03002_001E": "pop_race_total",
    "B03002_003E": "pop_nh_white",
    "B03002_004E": "pop_nh_black",
    "B03002_006E": "pop_nh_asian",
    "B03002_012E": "pop_hispanic",
    "B08301_001E": "workers_total",
    "B08301_003E": "workers_drove_alone",
    "B08301_010E": "workers_transit",
    "B08301_021E": "workers_wfh",
}


def fetch_acs_batch(year: int, variables: list[str]) -> pd.DataFrame:
    """Fetch one batch of ACS variables for all California tracts."""
    url = CENSUS_BASE.format(year=year)
    params = {
        "get": "NAME," + ",".join(variables),
        "for": "tract:*",
        "in": f"state:{STATE_FIPS}",
    }
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY

    print(f"    Fetching {len(variables)} variables...")
    resp = requests.get(url, params=params, timeout=60)
    if resp.status_code == 400 and "key" in resp.text.lower():
        print("    NOTE: Census API rate limit hit without key. Consider getting a free key at")
        print("    https://api.census.gov/data/key_signup.html and setting CENSUS_API_KEY env var.")
    resp.raise_for_status()

    data = resp.json()
    headers = data[0]
    rows = data[1:]
    df = pd.DataFrame(rows, columns=headers)
    return df


def fetch_acs_year(year: int) -> pd.DataFrame:
    """Fetch all ACS variables for a given vintage year."""
    print(f"  Fetching ACS {year} (2019–{year} 5-year estimates)...")

    df1 = fetch_acs_batch(year, BATCH_1)
    time.sleep(1)  # be polite to API
    df2 = fetch_acs_batch(year, BATCH_2)

    # Both have state/county/tract columns; merge on those
    geo_cols = ["state", "county", "tract"]
    df = df1.merge(df2.drop(columns=["NAME"], errors="ignore"), on=geo_cols)

    # Build standard GEOID (11-digit: state 2 + county 3 + tract 6)
    df["geoid"] = df["state"] + df["county"] + df["tract"]
    df["acs_year"] = year

    # Rename to human-readable labels
    df = df.rename(columns=VARIABLE_LABELS)

    # Convert to numeric; Census uses -666666666 for missing
    numeric_cols = list(VARIABLE_LABELS.values())
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].where(df[col] >= 0, other=pd.NA)  # mask sentinel values

    keep_cols = ["geoid", "NAME", "acs_year"] + [
        v for v in VARIABLE_LABELS.values() if v in df.columns
    ]
    return df[keep_cols]


def main():
    print("=== ACS Data Acquisition ===\n")

    if not CENSUS_API_KEY:
        print("WARNING: CENSUS_API_KEY not set. Unauthenticated requests are rate-limited.")
        print("Get a free key at https://api.census.gov/data/key_signup.html")
        print("Then: export CENSUS_API_KEY=your_key_here\n")

    all_frames = []
    for year in ACS_VINTAGES:
        out_path = RAW_DIR / f"acs_tracts_ca_{year}.csv"
        if out_path.exists():
            print(f"  [skip] ACS {year} already downloaded: {out_path.name}")
            df = pd.read_csv(out_path, dtype={"geoid": str})
        else:
            try:
                df = fetch_acs_year(year)
                df.to_csv(out_path, index=False)
                print(f"  Saved {len(df):,} tracts → {out_path.name}")
            except Exception as e:
                print(f"  ERROR fetching ACS {year}: {e}")
                continue
        all_frames.append(df)

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        out_path = RAW_DIR / "acs_tracts_ca_clean.csv"
        combined.to_csv(out_path, index=False)
        print(f"\n  Combined ACS saved → {out_path.name}")
        print(f"  Shape: {combined.shape}")
        print(f"  Tracts per vintage: {combined.groupby('acs_year').size().to_dict()}")
    else:
        print("\nERROR: No ACS data fetched. Check API key and connectivity.")

    print("\nDone. Next: run 03_acquire_ideology.py")


if __name__ == "__main__":
    main()
