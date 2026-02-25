#!/usr/bin/env python3
"""
04_crosswalk.py — Build geographic crosswalk tables.

Produces three crosswalk files in data/processed/:
  1. crosswalk_zip_tract.csv     — ZCTA → 2020 Census tract (area-proportional weights)
  2. crosswalk_prec_tract_g22.csv — 2022 precinct → 2020 Census tract (spatial overlay)
  3. crosswalk_prec_tract_p18.csv — 2018 precinct → 2020 Census tract (spatial overlay)
  4. crosswalk_county_tract.csv  — County FIPS → 2020 Census tract (GEOID prefix)

Data sources:
  - Census ZCTA520-to-tract20 relationship file (tab-delimited):
      https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tract20_natl.zip
  - CA 2020 Census tracts (TIGER/Line):
      https://www2.census.gov/geo/tiger/TIGER2020/TRACT/tl_2020_06_tract.zip
  - 2022 CA statewide precinct shapefile (UC Berkeley Statewide Database):
      https://statewidedatabase.org/pub/data/G22/state/mprec_state_g22_v01_shp.zip
  - 2018 CA statewide precinct shapefile (UC Berkeley Statewide Database):
      https://statewidedatabase.org/pub/data/P18/state/mprec_p18_v01_shp.zip
"""

import io
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
SHAPES = RAW / "shapefiles"

PROCESSED.mkdir(exist_ok=True)
SHAPES.mkdir(exist_ok=True)

# ── URLs ───────────────────────────────────────────────────────────────────────
ZCTA_REL_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/"
    "zcta520/tab20_zcta520_tract20_natl.txt"
)
TIGER_TRACT_URL = (
    "https://www2.census.gov/geo/tiger/TIGER2020/TRACT/tl_2020_06_tract.zip"
)
PREC_2022_URL = (
    "https://statewidedatabase.org/pub/data/G22/state/mprec_state_g22_v01_shp.zip"
)
PREC_2018_URL = (
    "https://statewidedatabase.org/pub/data/P18/state/mprec_p18_v01_shp.zip"
)

# CA Albers Equal Area — accurate area computation for California
CRS_CA = "EPSG:3310"


# ── Utilities ──────────────────────────────────────────────────────────────────

def download_zip(url: str, dest_dir: Path, name: str) -> Path:
    """
    Download a zip file from url and extract it to dest_dir/name/.
    Skips download if the directory already exists and is non-empty.
    Returns the extraction directory path.
    """
    out_dir = dest_dir / name
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"  [skip] {name} already downloaded")
        return out_dir

    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"  [download] {name} from {url} ...")
    resp = requests.get(url, timeout=300, stream=True)
    resp.raise_for_status()

    content = b"".join(resp.iter_content(chunk_size=1 << 20))
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        zf.extractall(out_dir)

    print(f"  [ok] extracted to {out_dir}")
    return out_dir


def _check_weights(df: pd.DataFrame, unit_col: str, weight_col: str, label: str):
    """Print weight-sum diagnostics per source unit."""
    sums = df.groupby(unit_col)[weight_col].sum()
    print(f"  {label} weight-sum stats (should be ≈1.0 per unit):")
    print(f"    n_units={len(sums):,}  "
          f"mean={sums.mean():.4f}  "
          f"min={sums.min():.4f}  "
          f"max={sums.max():.4f}  "
          f"pct_within_1pct={(abs(sums - 1.0) < 0.01).mean()*100:.1f}%")


# ── Crosswalk 1: ZCTA → Census tract ──────────────────────────────────────────

def build_zip_tract():
    """
    Load Census ZCTA520-to-tract20 relationship file, filter to CA tracts,
    compute area-proportional weights, and save to data/processed/.

    Weight = AREALAND_PART / AREALAND_ZCTA5_20  (area of overlap / total ZCTA area).
    Weights are re-normalized per ZCTA to sum exactly to 1.0.

    Output: crosswalk_zip_tract.csv  (columns: zcta5, tract_geoid_20, weight)
    """
    print("\n=== Crosswalk 1: ZCTA → Census tract ===")
    out_path = PROCESSED / "crosswalk_zip_tract.csv"

    # The Census relationship file is a plain .txt (pipe-delimited), not a zip
    txt_file = SHAPES / "tab20_zcta520_tract20_natl.txt"
    if not txt_file.exists():
        print(f"  [download] ZCTA-tract relationship file ...")
        resp = requests.get(ZCTA_REL_URL, timeout=300, stream=True)
        resp.raise_for_status()
        txt_file.write_bytes(b"".join(resp.iter_content(chunk_size=1 << 20)))
        print(f"  [ok] saved to {txt_file}")
    else:
        print(f"  [skip] {txt_file.name} already downloaded")
    print(f"  Reading {txt_file.name} ...")

    df = pd.read_csv(txt_file, sep="|", dtype=str, low_memory=False)
    print(f"  Columns: {list(df.columns)}")
    print(f"  Raw rows: {len(df):,}")

    # Normalize column names to upper
    df.columns = [c.strip().upper() for c in df.columns]

    # Identify key columns (handle minor naming variants)
    col_map = {}
    for col in df.columns:
        # ZCTA GEOID: must have GEOID + ZCTA5 + 20 (not OID)
        if "GEOID" in col and "ZCTA5" in col and "20" in col:
            col_map.setdefault("zcta", col)
        if "TRACT" in col and "20" in col and "GEOID" in col:
            col_map.setdefault("tract", col)
        if col == "AREALAND_PART":
            col_map["area_part"] = col
        if "AREALAND" in col and "ZCTA" in col and "PART" not in col:
            col_map.setdefault("area_zcta", col)

    print(f"  Mapped columns: {col_map}")
    required = ["zcta", "tract", "area_part", "area_zcta"]
    missing = [k for k in required if k not in col_map]
    if missing:
        raise KeyError(f"Could not identify columns for: {missing}. Available: {list(df.columns)}")

    df = df.rename(columns={
        col_map["zcta"]: "zcta5",
        col_map["tract"]: "tract_geoid_20",
        col_map["area_part"]: "area_part",
        col_map["area_zcta"]: "area_zcta",
    })

    # Filter to CA tracts
    df = df[df["tract_geoid_20"].str.startswith("06")].copy()
    print(f"  CA rows after filter: {len(df):,}")

    # Compute area-proportional weights
    df["area_part"] = pd.to_numeric(df["area_part"], errors="coerce").fillna(0)
    df["area_zcta"] = pd.to_numeric(df["area_zcta"], errors="coerce")

    df["weight"] = df["area_part"] / df["area_zcta"]

    # Re-normalize per ZCTA (handles rounding; also catches ZCTAs entirely in CA)
    df["weight_sum"] = df.groupby("zcta5")["weight"].transform("sum")
    df.loc[df["weight_sum"] > 0, "weight"] = (
        df.loc[df["weight_sum"] > 0, "weight"] / df.loc[df["weight_sum"] > 0, "weight_sum"]
    )
    df = df.drop(columns=["area_part", "area_zcta", "weight_sum"])

    # Drop rows with zero weight (water-only overlaps, etc.)
    df = df[df["weight"] > 0].reset_index(drop=True)

    out = df[["zcta5", "tract_geoid_20", "weight"]].copy()
    _check_weights(out, "zcta5", "weight", "ZIP→tract")
    print(f"  Output rows: {len(out):,}  unique ZCTAs: {out['zcta5'].nunique():,}")
    print(f"  Sample:\n{out.head(3).to_string(index=False)}")

    out.to_csv(out_path, index=False)
    print(f"  Saved → {out_path}")


# ── Crosswalk 2: Precinct → Census tract ──────────────────────────────────────

def build_prec_tract(vintage: str, url: str):
    """
    Build precinct→tract crosswalk using GeoPandas spatial overlay.

    Both shapefiles are projected to EPSG:3310 (CA Albers Equal Area) before
    overlay to ensure accurate area computation.

    Weight = intersection_area / precinct_total_area, re-normalized per precinct.

    Output: crosswalk_prec_tract_{vintage}.csv  (columns: pctkey, tract_geoid_20, weight)
    """
    print(f"\n=== Crosswalk 2: Precinct → tract ({vintage}) ===")
    out_path = PROCESSED / f"crosswalk_prec_tract_{vintage}.csv"

    # ── Download shapefiles ──
    prec_dir = download_zip(url, SHAPES, f"prec_{vintage}")
    tract_dir = download_zip(TIGER_TRACT_URL, SHAPES, "tl_2020_06_tract")

    # ── Load tracts ──
    shp_files = list(tract_dir.rglob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"No .shp in {tract_dir}")
    tracts = gpd.read_file(shp_files[0])
    print(f"  Tracts loaded: {len(tracts):,} rows, CRS={tracts.crs}")

    # Keep only needed columns
    # TIGER tract GEOID column is 'GEOID'
    geoid_col = next((c for c in tracts.columns if c.upper() == "GEOID"), None)
    if geoid_col is None:
        raise KeyError(f"No GEOID column in tracts. Columns: {list(tracts.columns)}")
    tracts = tracts[[geoid_col, "geometry"]].rename(columns={geoid_col: "tract_geoid_20"})

    # ── Load precincts ──
    prec_shp = list(prec_dir.rglob("*.shp"))
    if not prec_shp:
        raise FileNotFoundError(f"No .shp in {prec_dir}")
    precincts = gpd.read_file(prec_shp[0])
    print(f"  Precincts loaded: {len(precincts):,} rows, CRS={precincts.crs}")
    print(f"  Precinct columns: {list(precincts.columns)}")

    # ── Identify precinct key column ──
    key_candidates = ["PCTKEY", "PCTFIPS", "PCT_KEY", "PREC_KEY", "MPREC_KEY", "PRECINCT_ID", "PRECKEY"]
    pct_key_col = None
    for c in precincts.columns:
        if c.upper() in [k.upper() for k in key_candidates]:
            pct_key_col = c
            break
    if pct_key_col is None:
        # Fall back to first non-geometry string-like column
        for c in precincts.columns:
            if c != "geometry" and precincts[c].dtype == object:
                pct_key_col = c
                print(f"  WARNING: No standard key column found; using '{c}' as pctkey")
                break
    print(f"  Precinct key column: {pct_key_col!r}  "
          f"  sample values: {precincts[pct_key_col].head(3).tolist()}")

    precincts = precincts[[pct_key_col, "geometry"]].rename(
        columns={pct_key_col: "pctkey"}
    )

    # ── Project to CA Albers for accurate area ──
    tracts = tracts.to_crs(CRS_CA)
    precincts = precincts.to_crs(CRS_CA)

    # Compute precinct total areas BEFORE overlay (kept separate to avoid column conflicts)
    prec_areas = (
        precincts[["pctkey"]]
        .copy()
        .assign(prec_area_total=precincts.geometry.area)
        .drop_duplicates("pctkey")
    )

    # ── Spatial overlay (pass only pctkey + geometry to avoid column conflicts) ──
    prec_for_overlay = precincts[["pctkey", "geometry"]].copy()
    print(f"  Running overlay ({len(prec_for_overlay):,} precincts × {len(tracts):,} tracts)...")
    overlay = gpd.overlay(prec_for_overlay, tracts, how="intersection", keep_geom_type=False)
    print(f"  Overlay rows: {len(overlay):,}")

    overlay["area_part"] = overlay.geometry.area

    # Bring in precinct total area
    overlay = overlay.merge(prec_areas, on="pctkey", how="left")

    # Compute raw weight
    overlay["weight"] = overlay["area_part"] / overlay["prec_area_total"]

    # Re-normalize per precinct
    weight_sum = overlay.groupby("pctkey")["weight"].transform("sum")
    overlay.loc[weight_sum > 0, "weight"] = (
        overlay.loc[weight_sum > 0, "weight"] / weight_sum[weight_sum > 0]
    )

    # Drop slivers (weight < 0.001% of precinct)
    overlay = overlay[overlay["weight"] > 1e-5].copy()

    out = overlay[["pctkey", "tract_geoid_20", "weight"]].reset_index(drop=True)

    _check_weights(out, "pctkey", "weight", f"precinct({vintage})→tract")
    print(f"  Output rows: {len(out):,}  unique precincts: {out['pctkey'].nunique():,}")
    print(f"  Sample:\n{out.head(3).to_string(index=False)}")

    out.to_csv(out_path, index=False)
    print(f"  Saved → {out_path}")


# ── Crosswalk 3: County → Census tract ────────────────────────────────────────

def build_county_tract():
    """
    Build county FIPS → tract lookup from already-downloaded ACS tract CSV.
    Each row in the ACS file represents one Census tract; county FIPS = first 5 digits.

    Output: crosswalk_county_tract.csv  (columns: county_fips, tract_geoid_20)
    """
    print("\n=== Crosswalk 3: County → Census tract ===")
    out_path = PROCESSED / "crosswalk_county_tract.csv"

    acs_path = RAW / "acs" / "acs_tracts_ca_2023.csv"
    if not acs_path.exists():
        raise FileNotFoundError(f"ACS tracts file not found: {acs_path}")

    df = pd.read_csv(acs_path, dtype=str, nrows=5)
    print(f"  ACS columns (first 5 rows): {list(df.columns)}")

    df = pd.read_csv(acs_path, dtype=str, low_memory=False)
    print(f"  ACS rows: {len(df):,}")

    # Identify GEOID column (tract GEOID, 11 chars for 2020 definitions)
    geoid_col = None
    for c in df.columns:
        if c.upper() in ("GEOID", "GEO_ID", "TRACT_GEOID", "FIPS"):
            geoid_col = c
            break
    if geoid_col is None:
        # Try to find a column with values starting with "06" and length 11
        for c in df.columns:
            sample = df[c].dropna().iloc[0] if len(df) > 0 else ""
            if str(sample).startswith("06") and len(str(sample)) >= 11:
                geoid_col = c
                print(f"  Inferred GEOID column: '{c}'  sample={sample!r}")
                break
    if geoid_col is None:
        raise KeyError(f"Could not identify GEOID column. Columns: {list(df.columns)}")

    geoids = df[geoid_col].dropna().astype(str).str.strip()

    # Strip leading "1400000US" prefix if present (Census API format)
    geoids = geoids.str.replace(r"^1400000US", "", regex=True)

    # Keep only CA tracts
    ca_geoids = geoids[geoids.str.startswith("06")]
    print(f"  CA tract GEOIDs: {len(ca_geoids):,}")

    out = pd.DataFrame({
        "county_fips": ca_geoids.str[:5].values,
        "tract_geoid_20": ca_geoids.values,
    }).drop_duplicates().reset_index(drop=True)

    n_counties = out["county_fips"].nunique()
    n_tracts = len(out)
    print(f"  Unique county FIPS: {n_counties}  (expected 58 for CA)")
    print(f"  Output rows: {n_tracts:,}  (expected ~9,129)")
    print(f"  Sample:\n{out.head(3).to_string(index=False)}")

    out.to_csv(out_path, index=False)
    print(f"  Saved → {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("04_crosswalk.py — Building geographic crosswalk tables")
    print("=" * 60)

    build_zip_tract()
    build_prec_tract("g22", PREC_2022_URL)
    build_prec_tract("p18", PREC_2018_URL)
    build_county_tract()

    print("\n" + "=" * 60)
    print("All crosswalks complete.")
    print(f"Outputs in: {PROCESSED}")
    for f in sorted(PROCESSED.glob("crosswalk_*.csv")):
        rows = sum(1 for _ in open(f)) - 1
        print(f"  {f.name}: {rows:,} rows")
    print("=" * 60)


if __name__ == "__main__":
    main()
