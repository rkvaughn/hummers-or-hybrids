#!/usr/bin/env python3
"""
01_acquire_cec.py
Download California vehicle registration data by ZIP code, all years 2018–2024.

Sources:
  CA Open Data Portal — annual CSV snapshots (separate file per year):
  https://data.ca.gov/dataset/vehicle-fuel-type-count-by-zip-code

  CEC Vehicle Population Excel (all years combined, ZEVs only):
  https://www.energy.ca.gov/filebrowser/download/7591?fid=7591

Output:
  data/raw/cec_zev/annual/vehicles_{year}.csv   — raw annual CSVs (as downloaded)
  data/raw/cec_zev/cec_panel_raw.csv            — stacked 2018–2024, all fuel types
  data/raw/cec_zev/cec_panel_zev.csv            — ZEV rows only (BEV, PHEV, FCEV)
  data/raw/cec_zev/cec_panel_light.csv          — light-duty rows only (incl. ICE)

Geographic unit: ZIP code (5-digit)
Snapshot date: Each file is a December 31 end-of-year snapshot.

Column names in raw CSV:
  Date        → data_year (extracted as integer)
  ZIP Code    → zip_code
  Model Year  → model_year
  Fuel        → fuel_type
  Make        → make
  Duty        → duty (Light / Heavy)
  Vehicles    → vehicle_count

Fuel type values (raw → standardized code):
  'Battery Electric'           → BEV
  'Plug-in Hybrid'             → PHEV
  'Hydrogen Fuel Cell'         → FCEV
  'Gasoline'                   → GAS
  'Diesel and Diesel Hybrid'   → DIESEL
  'Hybrid Gasoline'            → HEV
  'Flex-Fuel'                  → FLEX
  'Natural Gas'                → CNG
  'Other'                      → OTHER

Vehicle make annotations:
  is_tesla      — make == 'TESLA'
  is_light_truck — make in common light truck brands (F-Series, RAM, Silverado, etc.)

Privacy note: Counts < 10 per ZIP/year/fuel/make are suppressed as 'OTHER/UNK'.
"""

from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "cec_zev"
ANNUAL_DIR = RAW_DIR / "annual"
RAW_DIR.mkdir(parents=True, exist_ok=True)
ANNUAL_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Annual CSV URLs — CA Open Data Portal
# ---------------------------------------------------------------------------
ANNUAL_URLS = {
    2024: "https://data.ca.gov/dataset/15179472-adeb-4df6-920a-20640d02b08c/resource/66b0121e-5eab-4fcf-aa0d-2b1dfb5510ab/download/vehicle-fuel-type-counts-2024.csv",
    2023: "https://data.ca.gov/dataset/15179472-adeb-4df6-920a-20640d02b08c/resource/d599c3d3-87af-4e8c-8694-9c01f49e3d93/download/vehicle-fuel-type-count-by-zip-code-20231.csv",
    2022: "https://data.ca.gov/dataset/15179472-adeb-4df6-920a-20640d02b08c/resource/9aa5b4c5-252c-4d68-b1be-ffe19a2f1d26/download/vehicle-fuel-type-count-by-zip-code-2022.csv",
    2021: "https://data.ca.gov/dataset/15179472-adeb-4df6-920a-20640d02b08c/resource/1856386b-a196-4e7c-be81-44174e29ad50/download/vehicle-fuel-type-count-by-zip-code-2022.csv",
    2020: "https://data.ca.gov/dataset/15179472-adeb-4df6-920a-20640d02b08c/resource/888bbb6c-09b4-469c-82e6-1b2a47439736/download/vehicle-fuel-type-count-by-zip-code-2021.csv",
    2019: "https://data.ca.gov/dataset/15179472-adeb-4df6-920a-20640d02b08c/resource/4254a06d-9937-4083-9441-65597dd267e8/download/vehicle-count-as-of-1-1-2020.csv",
    2018: "https://data.ca.gov/dataset/15179472-adeb-4df6-920a-20640d02b08c/resource/d304108a-06c1-462f-a144-981dd0109900/download/vehicle-fuel-type-count-by-zip-code.csv",
}

# CEC Excel (ZEVs only, all years combined) — use as cross-check
CEC_EXCEL_URL = "https://www.energy.ca.gov/filebrowser/download/7591?fid=7591"

FUEL_RECODE = {
    "battery electric": "BEV",
    "plug-in hybrid": "PHEV",
    "hydrogen fuel cell": "FCEV",
    "gasoline": "GAS",
    "diesel and diesel hybrid": "DIESEL",
    "hybrid gasoline": "HEV",
    "flex-fuel": "FLEX",
    "natural gas": "CNG",
    "other": "OTHER",
}

TESLA_MAKES = {"TESLA"}
LIGHT_TRUCK_MAKES = {
    "FORD", "RAM", "CHEVROLET", "GMC",          # domestic trucks
    "TOYOTA", "NISSAN", "HONDA",                 # import trucks
    "JEEP", "DODGE",                             # other common truck/SUV brands
}


def download(url: str, dest: Path, label: str) -> bool:
    if dest.exists():
        print(f"  [skip] {label} already exists")
        return True
    print(f"  Downloading {label}...")
    try:
        resp = requests.get(url, timeout=180, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        mb = dest.stat().st_size / 1e6
        print(f"  Saved {mb:.1f} MB → {dest.name}")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def parse_annual_csv(path: Path, year: int) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip() for c in df.columns]

    # Normalize column names (handle minor variations across vintages)
    col_map = {}
    for c in df.columns:
        cl = c.lower().replace(" ", "_")
        if "zip" in cl:
            col_map[c] = "zip_code"
        elif "model" in cl and "year" in cl:
            col_map[c] = "model_year"
        elif "fuel" in cl:
            col_map[c] = "fuel_raw"
        elif "make" in cl:
            col_map[c] = "make"
        elif "duty" in cl:
            col_map[c] = "duty"
        elif "vehicle" in cl or "count" in cl or cl == "vehicles":
            col_map[c] = "vehicle_count"
        elif "date" in cl:
            col_map[c] = "date_raw"
    df = df.rename(columns=col_map)
    df["data_year"] = year

    # Standardize fuel type
    df["fuel_type"] = df["fuel_raw"].str.lower().str.strip().map(FUEL_RECODE).fillna("OTHER")

    # Standardize make
    df["make"] = df["make"].str.upper().str.strip()
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5).str[:5]
    df["vehicle_count"] = pd.to_numeric(df["vehicle_count"], errors="coerce").fillna(0).astype(int)

    # Annotations
    df["is_tesla"] = df["make"] == "TESLA"
    df["is_light_truck"] = df["make"].isin(LIGHT_TRUCK_MAKES)

    keep = ["zip_code", "data_year", "model_year", "fuel_type", "fuel_raw",
            "make", "duty", "vehicle_count", "is_tesla", "is_light_truck"]
    return df[[c for c in keep if c in df.columns]]


def main():
    print("=== CEC / CA DMV Vehicle Data Acquisition ===\n")

    # 1. Download all annual CSVs
    frames = []
    for year, url in sorted(ANNUAL_URLS.items()):
        dest = ANNUAL_DIR / f"vehicles_{year}.csv"
        ok = download(url, dest, f"vehicles {year}")
        if ok and dest.exists():
            try:
                df = parse_annual_csv(dest, year)
                frames.append(df)
                print(f"  Parsed {year}: {len(df):,} rows, "
                      f"BEV={df[df.fuel_type=='BEV']['vehicle_count'].sum():,}, "
                      f"Tesla={df[df.is_tesla]['vehicle_count'].sum():,}")
            except Exception as e:
                print(f"  Parse error {year}: {e}")

    if not frames:
        print("ERROR: No annual data downloaded.")
        return

    # 2. Stack into panel
    panel = pd.concat(frames, ignore_index=True)
    panel_path = RAW_DIR / "cec_panel_raw.csv"
    panel.to_csv(panel_path, index=False)
    print(f"\n  Full panel: {len(panel):,} rows → {panel_path.name}")

    # 3. ZEV subset
    zev = panel[panel["fuel_type"].isin({"BEV", "PHEV", "FCEV"})]
    zev_path = RAW_DIR / "cec_panel_zev.csv"
    zev.to_csv(zev_path, index=False)
    print(f"  ZEV panel:  {len(zev):,} rows → {zev_path.name}")

    # 4. Light-duty subset (all fuel types, for denominator and truck analysis)
    light = panel[panel.get("duty", pd.Series("Light", index=panel.index)).str.upper().str.startswith("L", na=True)]
    light_path = RAW_DIR / "cec_panel_light.csv"
    light.to_csv(light_path, index=False)
    print(f"  Light-duty: {len(light):,} rows → {light_path.name}")

    # 5. Summary
    print("\n  === Panel summary ===")
    summary = (
        zev[zev["fuel_type"] == "BEV"]
        .groupby(["data_year", "is_tesla"])["vehicle_count"]
        .sum()
        .unstack(fill_value=0)
        .rename(columns={False: "non_tesla_bev", True: "tesla_bev"})
    )
    print(summary.to_string())

    # 6. Try CEC Excel as cross-check
    print("\n  Attempting CEC Excel download (ZEVs only, cross-check)...")
    excel_dest = RAW_DIR / "vehicle_population_cec.xlsx"
    download(CEC_EXCEL_URL, excel_dest, "CEC Vehicle Population Excel")

    print("\nDone. Next: run 02_acquire_acs.py")


if __name__ == "__main__":
    main()
