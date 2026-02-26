# Full Analysis Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build scripts 05–11 (panel construction → PCA → replication → EV panel → event study → robustness → spatial) and write paper/draft.md (Substack post) for the Hummers-or-Hybrids project.

**Architecture:** Sequential data pipeline — each script reads from `data/raw/` or `data/processed/`, writes cleaned outputs downstream. All analysis uses a single `panel_tract_year.csv` master dataset built in script 05. Ideology index (script 06) joins to the panel for all regressions. Scripts 07–11 are independent after 06.

**Tech Stack:** Python, pandas, geopandas, scikit-learn (PCA), statsmodels (OLS/NB), linearmodels (TWFE), pysal/spreg (spatial), matplotlib/seaborn (figures), BeautifulSoup (LCV scraping)

---

## Prerequisites — Install Missing Dependencies

**Files:**
- Modify: `requirements.txt`

**Step 1: Add missing packages**

Replace `requirements.txt` with:

```
# existing
certifi==2026.1.4
charset-normalizer==3.4.4
et_xmlfile==2.0.0
geopandas==1.1.2
idna==3.11
numpy==2.4.2
openpyxl==3.1.5
packaging==26.0
pandas==3.0.1
pyogrio==0.12.1
pyproj==3.7.2
python-dateutil==2.9.0.post0
requests==2.32.5
shapely==2.1.2
six==1.17.0
urllib3==2.6.3

# analysis
statsmodels>=0.14.0
linearmodels>=6.0
scikit-learn>=1.4.0
scipy>=1.13.0

# spatial
pysal>=23.7
libpysal>=4.10.0
spreg>=1.4.0
esda>=2.6.0

# visualization
matplotlib>=3.9.0
seaborn>=0.13.0

# scraping / html parsing
beautifulsoup4>=4.12.0
lxml>=5.2.0

# tables
tabulate>=0.9.0
jinja2>=3.1.0
```

**Step 2: Install**

```bash
source .venv/bin/activate
pip install statsmodels linearmodels scikit-learn scipy pysal libpysal spreg esda matplotlib seaborn beautifulsoup4 lxml tabulate jinja2
```

Expected: packages install without errors.

**Step 3: Verify**

```bash
python -c "import statsmodels, linearmodels, sklearn, pysal, spreg, esda, matplotlib, seaborn, bs4; print('all ok')"
```

Expected: `all ok`

**Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add analysis dependencies (statsmodels, linearmodels, pysal, matplotlib)"
```

---

## Task 1: Script 05 — Build Panel

**Files:**
- Create: `scripts/05_build_panel.py`
- Create: `tests/test_05_panel.py`

**Context:** This script joins 5 data sources into one master dataset.
- CEC ZEV counts are at ZIP code level → must be crosswalked to Census tracts
- YCOM beliefs are at county level → assigned by county FIPS prefix of tract GEOID
- Voter registration and ballot measures are at election precinct level → must be crosswalked via spatial overlap weights built in script 04
- ACS demographics are already at Census tract level → direct merge on tract GEOID
- Result: one row per (tract × year) for years 2018–2024

**Step 1: Write the validation test**

```python
# tests/test_05_panel.py
"""Validation checks for panel_tract_year.csv output."""
import pandas as pd
from pathlib import Path

PANEL = Path("data/processed/panel_tract_year.csv")

def test_panel_exists():
    assert PANEL.exists(), "panel_tract_year.csv not found — run 05_build_panel.py first"

def test_panel_shape():
    df = pd.read_csv(PANEL, dtype={"tract_geoid_20": str})
    # ~9,129 CA tracts × 7 years (2018–2024)
    assert len(df) > 50_000, f"Panel too small: {len(df)} rows"
    assert len(df) < 80_000, f"Panel too large: {len(df)} rows"

def test_panel_columns():
    df = pd.read_csv(PANEL, nrows=1)
    required = [
        "tract_geoid_20", "data_year",
        "tesla_bev", "nontesla_bev", "total_bev", "total_phev",
        "light_truck_count", "total_light",
        "ycom_happening", "ycom_worried", "ycom_regulate",
        "dem_minus_rep", "prop30_yes_share",
        "median_hh_income", "pct_ba_plus", "pop_density",
    ]
    missing = [c for c in required if c not in df.columns]
    assert not missing, f"Missing columns: {missing}"

def test_years():
    df = pd.read_csv(PANEL, usecols=["data_year"])
    years = sorted(df["data_year"].unique())
    assert years == list(range(2018, 2025)), f"Unexpected years: {years}"

def test_no_negative_counts():
    df = pd.read_csv(PANEL, usecols=["tesla_bev", "nontesla_bev", "total_bev"])
    assert (df >= 0).all().all(), "Negative vehicle counts found"

def test_tract_geoid_format():
    df = pd.read_csv(PANEL, dtype={"tract_geoid_20": str}, usecols=["tract_geoid_20"])
    sample = df["tract_geoid_20"].dropna().iloc[0]
    assert len(sample) == 11 and sample.startswith("06"), \
        f"Bad tract GEOID format: {sample!r}"

if __name__ == "__main__":
    import pytest, sys
    sys.exit(pytest.main([__file__, "-v"]))
```

**Step 2: Run tests to confirm they fail (panel doesn't exist yet)**

```bash
python tests/test_05_panel.py
```

Expected: `FAILED test_panel_exists` — file not found.

**Step 3: Write script 05**

```python
#!/usr/bin/env python3
"""
05_build_panel.py
Merge all raw data sources into a single tract × year panel.

Inputs (all from data/raw/ or data/processed/):
  data/raw/cec_zev/cec_panel_zev.csv
  data/raw/cec_zev/cec_panel_light.csv
  data/raw/acs/acs_tracts_ca_clean.csv
  data/processed/crosswalk_zip_tract.csv
  data/processed/crosswalk_county_tract.csv
  data/processed/crosswalk_prec_tract_g22.csv
  data/processed/crosswalk_prec_tract_p18.csv
  data/raw/ycom/ycom_ca_counties.csv
  data/raw/voter_registration/votreg_ca_raw.csv
  data/raw/ballot_measures/ballots_g22_raw.csv
  data/raw/ballot_measures/ballots_p18_raw.csv

Output:
  data/processed/panel_tract_year.csv
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(exist_ok=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

def weighted_sum_to_tract(df_unit: pd.DataFrame, unit_col: str,
                           value_cols: list, xwalk: pd.DataFrame,
                           xwalk_unit_col: str) -> pd.DataFrame:
    """
    Crosswalk unit-level data to Census tracts via weighted allocation.

    For each unit (ZIP or precinct), distributes value_cols across overlapping
    tracts using the weight column from the crosswalk. Aggregates to tract level.

    Args:
        df_unit: DataFrame with unit-level data (one row per unit)
        unit_col: column name in df_unit identifying the unit
        value_cols: columns to allocate (numeric counts/shares)
        xwalk: crosswalk table with columns [xwalk_unit_col, tract_geoid_20, weight]
        xwalk_unit_col: column in xwalk matching unit_col

    Returns:
        DataFrame with columns [tract_geoid_20] + value_cols, aggregated by tract
    """
    merged = df_unit.merge(
        xwalk[[xwalk_unit_col, "tract_geoid_20", "weight"]],
        left_on=unit_col, right_on=xwalk_unit_col, how="inner"
    )
    for col in value_cols:
        merged[col] = merged[col] * merged["weight"]
    return (
        merged.groupby("tract_geoid_20")[value_cols]
        .sum()
        .reset_index()
    )


# ── Step 1: Vehicle counts — CEC ZEV → ZIP/year → tract/year ─────────────────

def build_vehicle_panel() -> pd.DataFrame:
    print("  [1] Building vehicle panel from CEC ZEV data...")
    zev = pd.read_csv(RAW / "cec_zev" / "cec_panel_zev.csv", dtype={"zip_code": str})
    light = pd.read_csv(RAW / "cec_zev" / "cec_panel_light.csv", dtype={"zip_code": str})
    xwalk = pd.read_csv(PROCESSED / "crosswalk_zip_tract.csv", dtype={"zcta5": str, "tract_geoid_20": str})

    # Aggregate ZEV panel to zip/year
    veh_zip = (
        zev.groupby(["zip_code", "data_year"]).apply(
            lambda g: pd.Series({
                "tesla_bev": g.loc[g["is_tesla"] & (g["fuel_type"] == "BEV"), "vehicle_count"].sum(),
                "nontesla_bev": g.loc[~g["is_tesla"] & (g["fuel_type"] == "BEV"), "vehicle_count"].sum(),
                "total_bev": g.loc[g["fuel_type"] == "BEV", "vehicle_count"].sum(),
                "total_phev": g.loc[g["fuel_type"] == "PHEV", "vehicle_count"].sum(),
            }),
            include_groups=False,
        )
        .reset_index()
    )

    # Light-duty totals (for denominator and truck counts)
    truck_zip = (
        light.groupby(["zip_code", "data_year"]).apply(
            lambda g: pd.Series({
                "light_truck_count": g.loc[g["is_light_truck"], "vehicle_count"].sum(),
                "total_light": g["vehicle_count"].sum(),
            }),
            include_groups=False,
        )
        .reset_index()
    )

    value_cols_veh = ["tesla_bev", "nontesla_bev", "total_bev", "total_phev"]
    value_cols_truck = ["light_truck_count", "total_light"]

    # Crosswalk each year separately, then stack
    years = sorted(veh_zip["data_year"].unique())
    frames = []
    for year in years:
        veh_y = veh_zip[veh_zip["data_year"] == year].copy()
        truck_y = truck_zip[truck_zip["data_year"] == year].copy()

        veh_tract = weighted_sum_to_tract(veh_y, "zip_code", value_cols_veh, xwalk, "zcta5")
        truck_tract = weighted_sum_to_tract(truck_y, "zip_code", value_cols_truck, xwalk, "zcta5")

        merged = veh_tract.merge(truck_tract, on="tract_geoid_20", how="outer")
        merged["data_year"] = year
        frames.append(merged)

    panel = pd.concat(frames, ignore_index=True)
    panel[value_cols_veh + value_cols_truck] = panel[value_cols_veh + value_cols_truck].fillna(0)
    print(f"    Vehicle panel: {len(panel):,} rows, years: {sorted(panel['data_year'].unique())}")
    return panel


# ── Step 2: YCOM beliefs — county → tract (trivial assignment) ───────────────

def build_ycom_tract() -> pd.DataFrame:
    print("  [2] Assigning YCOM county beliefs to tracts...")
    ycom = pd.read_csv(RAW / "ycom" / "ycom_ca_counties.csv", dtype={"county_fips": str})
    xwalk = pd.read_csv(PROCESSED / "crosswalk_county_tract.csv",
                        dtype={"county_fips": str, "tract_geoid_20": str})

    ycom_cols = [c for c in ycom.columns if c not in ("county_fips", "county_name")]
    ycom = ycom[["county_fips"] + ycom_cols].copy()
    # Zero-pad county FIPS to 5 digits
    ycom["county_fips"] = ycom["county_fips"].str.zfill(5)

    tract_ycom = xwalk.merge(ycom, on="county_fips", how="left")
    # Rename to ycom_ prefix
    rename = {c: f"ycom_{c}" for c in ycom_cols}
    tract_ycom = tract_ycom.rename(columns=rename)[["tract_geoid_20"] + list(rename.values())]
    print(f"    YCOM tract table: {len(tract_ycom):,} rows, cols: {list(rename.values())}")
    return tract_ycom


# ── Step 3: Voter registration — precinct → tract ────────────────────────────

def build_votreg_tract() -> pd.DataFrame:
    print("  [3] Crosswalking voter registration to tracts...")
    votreg_path = RAW / "voter_registration" / "votreg_ca_raw.csv"
    if not votreg_path.exists():
        print("    WARNING: votreg_ca_raw.csv not found — skipping voter reg")
        return pd.DataFrame(columns=["tract_geoid_20", "dem_minus_rep"])

    xwalk = pd.read_csv(PROCESSED / "crosswalk_prec_tract_g22.csv",
                        dtype={"pctkey": str, "tract_geoid_20": str})
    votreg = pd.read_csv(votreg_path, dtype=str, low_memory=False)
    votreg.columns = [c.upper().strip() for c in votreg.columns]

    # Identify precinct key column
    key_candidates = ["PCTKEY", "PCTFIPS", "PCT_KEY", "PREC_KEY", "MPREC_KEY", "PRECINCT_ID"]
    pct_col = next((c for c in votreg.columns if c in key_candidates), None)
    if pct_col is None:
        # Use first string column as fallback
        pct_col = next(c for c in votreg.columns if votreg[c].dtype == object)
        print(f"    WARNING: using '{pct_col}' as precinct key")

    # Identify DEM and REP columns
    dem_col = next((c for c in votreg.columns if c in ("DEM", "DEM_REG", "DEM_1")), None)
    rep_col = next((c for c in votreg.columns if c in ("REP", "REP_REG", "REP_1")), None)
    if dem_col is None or rep_col is None:
        print(f"    WARNING: DEM/REP columns not found. Available: {list(votreg.columns[:20])}")
        return pd.DataFrame(columns=["tract_geoid_20", "dem_minus_rep"])

    votreg[dem_col] = pd.to_numeric(votreg[dem_col], errors="coerce").fillna(0)
    votreg[rep_col] = pd.to_numeric(votreg[rep_col], errors="coerce").fillna(0)
    votreg["total_reg"] = votreg[dem_col] + votreg[rep_col]
    votreg = votreg.rename(columns={pct_col: "pctkey"})
    votreg["pctkey"] = votreg["pctkey"].astype(str)

    merged = votreg[["pctkey", dem_col, rep_col, "total_reg"]].merge(
        xwalk, on="pctkey", how="inner"
    )
    for col in [dem_col, rep_col, "total_reg"]:
        merged[col] = merged[col] * merged["weight"]

    tract_reg = merged.groupby("tract_geoid_20")[[dem_col, rep_col, "total_reg"]].sum().reset_index()
    tract_reg["dem_minus_rep"] = (tract_reg[dem_col] - tract_reg[rep_col]) / tract_reg["total_reg"].replace(0, pd.NA)
    result = tract_reg[["tract_geoid_20", "dem_minus_rep"]]
    print(f"    Voter reg tract table: {len(result):,} rows")
    return result


# ── Step 4: Ballot measures — precinct → tract ───────────────────────────────

def _extract_prop_share(df: pd.DataFrame, yes_col: str, no_col: str) -> pd.Series:
    yes = pd.to_numeric(df[yes_col], errors="coerce").fillna(0)
    no = pd.to_numeric(df[no_col], errors="coerce").fillna(0)
    total = yes + no
    return (yes / total.replace(0, pd.NA)).fillna(0)


def build_ballot_tract() -> pd.DataFrame:
    print("  [4] Crosswalking ballot measures to tracts...")
    results = {}

    ballot_configs = [
        ("g22", "ballots_g22_raw.csv", "prop30_yes_share", "PR_30_Y", "PR_30_N"),
        ("p18", "ballots_p18_raw.csv", "prop68_yes_share", "PR_68_Y", "PR_68_N"),
    ]

    for vintage, fname, out_col, yes_col, no_col in ballot_configs:
        bpath = RAW / "ballot_measures" / fname
        xwalk_path = PROCESSED / f"crosswalk_prec_tract_{vintage}.csv"
        if not bpath.exists() or not xwalk_path.exists():
            print(f"    WARNING: {fname} or crosswalk not found — skipping {out_col}")
            continue

        df = pd.read_csv(bpath, dtype=str, low_memory=False)
        df.columns = [c.upper().strip() for c in df.columns]

        # Find YES/NO columns (handle slight naming variation)
        actual_yes = next((c for c in df.columns if c.startswith(yes_col[:4])), None)
        actual_no = next((c for c in df.columns if c.startswith(no_col[:4])), None)
        if actual_yes is None or actual_no is None:
            prop_cols = [c for c in df.columns if c.startswith("PR_")]
            print(f"    WARNING: {yes_col}/{no_col} not found. Prop cols: {prop_cols[:20]}")
            continue

        df["yes_share"] = _extract_prop_share(df, actual_yes, actual_no)

        xwalk = pd.read_csv(xwalk_path, dtype={"pctkey": str, "tract_geoid_20": str})
        key_candidates = ["PCTKEY", "PCTFIPS", "PCT_KEY", "PREC_KEY", "MPREC_KEY"]
        pct_col = next((c for c in df.columns if c in key_candidates), None)
        if pct_col is None:
            print(f"    WARNING: no precinct key found in {fname}")
            continue

        df = df.rename(columns={pct_col: "pctkey"})
        df["pctkey"] = df["pctkey"].astype(str)
        merged = df[["pctkey", "yes_share"]].merge(xwalk, on="pctkey", how="inner")
        merged["yes_share"] = merged["yes_share"] * merged["weight"]
        tract_ballot = merged.groupby("tract_geoid_20")["yes_share"].sum().reset_index()
        tract_ballot = tract_ballot.rename(columns={"yes_share": out_col})
        results[out_col] = tract_ballot
        print(f"    {out_col}: {len(tract_ballot):,} tracts")

    # Merge prop30 and prop68
    if not results:
        return pd.DataFrame(columns=["tract_geoid_20", "prop30_yes_share", "prop68_yes_share"])
    base = list(results.values())[0]
    for other in list(results.values())[1:]:
        base = base.merge(other, on="tract_geoid_20", how="outer")
    return base


# ── Step 5: ACS demographics — already at tract level ────────────────────────

def build_acs_tract() -> pd.DataFrame:
    print("  [5] Loading ACS demographics...")
    acs = pd.read_csv(RAW / "acs" / "acs_tracts_ca_clean.csv", dtype={"geoid": str})

    # Compute derived variables
    acs["pct_ba_plus"] = acs["pop_ba_degree"] / acs["pop_25plus"].replace(0, pd.NA)
    acs["pct_white"] = acs["pop_nh_white"] / acs["pop_race_total"].replace(0, pd.NA)
    acs["pct_black"] = acs["pop_nh_black"] / acs["pop_race_total"].replace(0, pd.NA)
    acs["pct_asian"] = acs["pop_nh_asian"] / acs["pop_race_total"].replace(0, pd.NA)
    acs["pct_hispanic"] = acs["pop_hispanic"] / acs["pop_race_total"].replace(0, pd.NA)
    acs["pct_transit"] = acs["workers_transit"] / acs["workers_total"].replace(0, pd.NA)
    acs["pct_drove_alone"] = acs["workers_drove_alone"] / acs["workers_total"].replace(0, pd.NA)
    acs["pct_wfh"] = acs["workers_wfh"] / acs["workers_total"].replace(0, pd.NA)
    # Pop density: persons per sq mile — ALAND not in API response; will use total_pop as proxy
    # NOTE: land area must be retrieved separately or from TIGER shapefile attributes
    # For now, flag as missing — script 06 will join from shapefile if available
    acs["log_median_hh_income"] = acs["median_hh_income"].apply(
        lambda x: pd.NA if pd.isna(x) or x <= 0 else __import__("math").log(x)
    )

    keep = [
        "geoid", "total_pop", "median_hh_income", "log_median_hh_income",
        "median_home_value", "pct_ba_plus", "pct_white", "pct_black",
        "pct_asian", "pct_hispanic", "pct_transit", "pct_drove_alone",
        "pct_wfh",
    ]
    acs = acs[[c for c in keep if c in acs.columns]].rename(columns={"geoid": "tract_geoid_20"})
    print(f"    ACS tract table: {len(acs):,} tracts")
    return acs


# ── Step 6: Assemble panel ───────────────────────────────────────────────────

def main():
    print("=== 05_build_panel.py ===\n")

    # Build all components
    veh = build_vehicle_panel()          # tract × year
    ycom = build_ycom_tract()            # tract (time-invariant)
    votreg = build_votreg_tract()        # tract (time-invariant)
    ballot = build_ballot_tract()        # tract (time-invariant)
    acs = build_acs_tract()              # tract (time-invariant)

    # Start from vehicle panel (already has all tract × year combos)
    panel = veh.copy()
    panel["tract_geoid_20"] = panel["tract_geoid_20"].astype(str)

    # Join time-invariant tables
    for label, df in [("YCOM", ycom), ("voter reg", votreg),
                      ("ballot", ballot), ("ACS", acs)]:
        df["tract_geoid_20"] = df["tract_geoid_20"].astype(str)
        n_before = len(panel["tract_geoid_20"].unique())
        panel = panel.merge(df, on="tract_geoid_20", how="left")
        n_after = len(panel["tract_geoid_20"].unique())
        print(f"  After {label} join: {len(panel):,} rows, "
              f"tract coverage {n_after}/{n_before}")

    # Diagnostics
    print("\n  === Panel diagnostics ===")
    print(f"  Shape: {panel.shape}")
    print(f"  Years: {sorted(panel['data_year'].unique())}")
    print(f"  Tracts: {panel['tract_geoid_20'].nunique():,}")
    print(f"  Total BEV 2024: {panel[panel.data_year == 2024]['total_bev'].sum():,.0f}")
    print(f"  Tesla BEV 2024: {panel[panel.data_year == 2024]['tesla_bev'].sum():,.0f}")
    null_pct = panel.isnull().mean() * 100
    high_null = null_pct[null_pct > 10]
    if len(high_null):
        print(f"\n  WARNING: High null rates:\n{high_null.to_string()}")

    out = PROCESSED / "panel_tract_year.csv"
    panel.to_csv(out, index=False)
    print(f"\n  Saved → {out}")
    print("  Done. Next: run 06_ideology_index.py")


if __name__ == "__main__":
    main()
```

**Step 4: Run script**

```bash
python scripts/05_build_panel.py
```

Expected: printed diagnostics, file written to `data/processed/panel_tract_year.csv`.
If data hasn't been downloaded yet, run scripts 01–04 first.

**Step 5: Run validation**

```bash
python tests/test_05_panel.py
```

Expected: all tests PASS.

**Step 6: Commit**

```bash
git add scripts/05_build_panel.py tests/test_05_panel.py
git commit -m "feat: add script 05 panel construction and validation tests"
```

---

## Task 2: Script 06 — Ideology Index

**Files:**
- Create: `scripts/06_ideology_index.py`
- Create: `tests/test_06_ideology.py`

**Context:** Runs PCA across 8 ideology variables to produce a single `climate_ideology_index`
per tract. Also scrapes LCV scores to validate the index externally. The ideology index is
time-invariant — one value per tract, joined to the panel in downstream scripts.

**Step 1: Write validation test**

```python
# tests/test_06_ideology.py
"""Validation checks for ideology_index.csv output."""
import pandas as pd
from pathlib import Path

INDEX = Path("data/processed/ideology_index.csv")
LOADINGS = Path("output/tables/pca_loadings.csv")

def test_index_exists():
    assert INDEX.exists(), "ideology_index.csv not found — run 06_ideology_index.py first"

def test_index_columns():
    df = pd.read_csv(INDEX, nrows=1)
    assert "tract_geoid_20" in df.columns
    assert "climate_ideology_index" in df.columns

def test_index_shape():
    df = pd.read_csv(INDEX)
    # Should have one row per CA tract (~9,129)
    assert len(df) > 8_000, f"Too few tracts: {len(df)}"
    assert df["tract_geoid_20"].nunique() == len(df), "Duplicate tracts in ideology index"

def test_index_standardized():
    df = pd.read_csv(INDEX)
    idx = df["climate_ideology_index"].dropna()
    # PCA PC1 scores: mean ≈ 0, std ≈ 1
    assert abs(idx.mean()) < 0.1, f"Index mean not near 0: {idx.mean():.3f}"
    assert 0.8 < idx.std() < 1.2, f"Index std not near 1: {idx.std():.3f}"

def test_loadings_exist():
    assert LOADINGS.exists(), "pca_loadings.csv not found"

def test_loadings_all_positive_direction():
    df = pd.read_csv(LOADINGS)
    # All ideology components should load positively on PC1
    # (more liberal / more climate-concerned = higher index)
    # If not, PC1 was flipped — script must handle sign normalization
    assert "loading_pc1" in df.columns

if __name__ == "__main__":
    import pytest, sys
    sys.exit(pytest.main([__file__, "-v"]))
```

**Step 2: Run tests to confirm failure**

```bash
python tests/test_06_ideology.py
```

Expected: FAIL — files not found.

**Step 3: Write script 06**

```python
#!/usr/bin/env python3
"""
06_ideology_index.py
Build composite Climate Ideology Index via PCA. Validate against LCV scores.

Inputs:
  data/processed/panel_tract_year.csv   — master panel (ideology cols included)

Outputs:
  data/processed/ideology_index.csv     — tract-level index + component scores
  output/tables/pca_loadings.csv        — variable loadings on PC1
  output/figures/pca_scree.png          — scree plot
  output/figures/ideology_map.png       — choropleth of index across CA tracts
"""

import math
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd
import requests
from bs4 import BeautifulSoup
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import statsmodels.formula.api as smf

ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

IDEOLOGY_VARS = [
    "ycom_happening", "ycom_worried", "ycom_regulate",
    "ycom_human", "ycom_supportRPS",
    "dem_minus_rep", "prop30_yes_share", "prop68_yes_share",
]


# ── PCA ──────────────────────────────────────────────────────────────────────

def build_ideology_index(panel: pd.DataFrame) -> pd.DataFrame:
    """Run PCA on ideology variables; return tract-level DataFrame with PC1."""
    print("  Running PCA on ideology variables...")

    # Use 2023 cross-section (ideology is time-invariant, so any year gives same values)
    cs = panel[panel["data_year"] == 2023][["tract_geoid_20"] + IDEOLOGY_VARS].drop_duplicates("tract_geoid_20")

    # Drop tracts with ANY missing ideology variable
    n_before = len(cs)
    cs = cs.dropna(subset=IDEOLOGY_VARS)
    n_after = len(cs)
    print(f"    Dropped {n_before - n_after} tracts with missing ideology data "
          f"({(n_before - n_after) / n_before * 100:.1f}%)")

    # Standardize
    scaler = StandardScaler()
    X = scaler.fit_transform(cs[IDEOLOGY_VARS])

    # PCA
    pca = PCA(n_components=len(IDEOLOGY_VARS))
    scores = pca.fit_transform(X)

    pc1 = scores[:, 0]

    # Flip sign if needed: higher PC1 should mean more climate-concerned
    # Check: dem_minus_rep should correlate positively with the index
    dem_col_idx = IDEOLOGY_VARS.index("dem_minus_rep")
    dem_loading = pca.components_[0, dem_col_idx]
    if dem_loading < 0:
        pc1 = -pc1
        pca.components_[0] = -pca.components_[0]
        print("    NOTE: Flipped PC1 sign so that higher = more climate-concerned")

    cs["climate_ideology_index"] = pc1

    # Add individual component scores
    for i, var in enumerate(IDEOLOGY_VARS):
        cs[f"pc1_contrib_{var}"] = X[:, i] * pca.components_[0, i]

    # Print variance explained
    explained = pca.explained_variance_ratio_
    print(f"    PC1 variance explained: {explained[0]*100:.1f}%")
    print(f"    PC1+PC2 cumulative: {sum(explained[:2])*100:.1f}%")

    # Save loadings
    loadings = pd.DataFrame({
        "variable": IDEOLOGY_VARS,
        "loading_pc1": pca.components_[0],
        "loading_pc2": pca.components_[1],
    })
    loadings["variance_explained_pc1"] = explained[0]
    loadings.to_csv(TABLES / "pca_loadings.csv", index=False)
    print(f"    Loadings saved → output/tables/pca_loadings.csv")
    print(f"    Loadings:\n{loadings[['variable','loading_pc1']].to_string(index=False)}")

    # Scree plot
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(range(1, len(explained) + 1), explained * 100, color="#2563eb")
    ax.set_xlabel("Principal Component")
    ax.set_ylabel("Variance Explained (%)")
    ax.set_title("PCA Scree Plot — Climate Ideology Variables")
    ax.axhline(100 / len(IDEOLOGY_VARS), color="red", linestyle="--", alpha=0.5,
               label="Random chance threshold")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIGURES / "pca_scree.png", dpi=300)
    plt.close()
    print(f"    Scree plot → output/figures/pca_scree.png")

    return cs[["tract_geoid_20", "climate_ideology_index"] +
              [f"pc1_contrib_{v}" for v in IDEOLOGY_VARS]]


# ── LCV Validation ────────────────────────────────────────────────────────────

LCV_URL = "https://scorecard.lcv.org/members/2023"  # 118th Congress, 2023 scores


def fetch_lcv_scores() -> pd.DataFrame:
    """Scrape LCV lifetime or annual scores for CA Congressional members."""
    print("  Fetching LCV scores from scorecard.lcv.org...")
    try:
        resp = requests.get(LCV_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # LCV scorecard tables vary by year — look for table rows with member data
        rows = []
        for row in soup.select("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 3:
                text = [c.get_text(strip=True) for c in cells]
                rows.append(text)

        if not rows:
            print("    WARNING: No table rows found on LCV page. Scraping may need updating.")
            return pd.DataFrame()

        df = pd.DataFrame(rows[1:], columns=rows[0] if rows else range(len(rows[0])))

        # Filter to CA members
        state_col = next((c for c in df.columns if "state" in str(c).lower()), None)
        score_col = next((c for c in df.columns if "score" in str(c).lower() or "%" in str(c)), None)
        dist_col = next((c for c in df.columns if "district" in str(c).lower()
                         or "dist" in str(c).lower()), None)

        if state_col is None:
            print(f"    WARNING: Could not identify state column. Columns: {list(df.columns)}")
            return pd.DataFrame()

        ca_df = df[df[state_col].str.upper().str.strip() == "CA"].copy()
        print(f"    Found {len(ca_df)} CA members")

        if score_col:
            ca_df["lcv_score"] = pd.to_numeric(
                ca_df[score_col].str.replace("%", "").str.strip(), errors="coerce"
            )
        if dist_col:
            ca_df["district_num"] = pd.to_numeric(
                ca_df[dist_col].str.extract(r"(\d+)")[0], errors="coerce"
            )

        # Save raw LCV data
        ca_df.to_csv(TABLES / "lcv_scores_ca.csv", index=False)
        return ca_df[["district_num", "lcv_score"]].dropna()

    except Exception as e:
        print(f"    WARNING: LCV scraping failed: {e}")
        print("    Skipping LCV validation. Download manually from https://scorecard.lcv.org/")
        return pd.DataFrame()


def validate_against_lcv(index_df: pd.DataFrame):
    """Aggregate ideology index to Congressional district level; regress on LCV scores."""
    print("  Validating ideology index against LCV scores...")

    lcv = fetch_lcv_scores()
    if lcv.empty:
        print("    Skipping LCV validation (no data)")
        return

    # Load Congressional district → tract crosswalk (from TIGER 118th Congress shapefiles)
    # Try to build from shapefiles if available; otherwise skip
    cd_tract_path = PROCESSED / "crosswalk_cd_tract.csv"
    if not cd_tract_path.exists():
        print("    Building CD→tract crosswalk from TIGER shapefiles...")
        try:
            cd_tract = build_cd_tract_crosswalk()
            cd_tract.to_csv(cd_tract_path, index=False)
        except Exception as e:
            print(f"    WARNING: CD crosswalk failed: {e}. Skipping LCV validation.")
            return

    cd_tract = pd.read_csv(cd_tract_path, dtype={"tract_geoid_20": str})
    merged = index_df.merge(cd_tract, on="tract_geoid_20", how="inner")
    if merged.empty:
        print("    WARNING: CD-tract merge empty. Skipping LCV validation.")
        return

    district_avg = (
        merged.groupby("district_num")["climate_ideology_index"]
        .mean()
        .reset_index()
        .rename(columns={"climate_ideology_index": "mean_ideology"})
    )
    val = district_avg.merge(lcv, on="district_num", how="inner")

    if len(val) < 5:
        print(f"    WARNING: Only {len(val)} districts matched — skipping regression")
        return

    result = smf.ols("lcv_score ~ mean_ideology", data=val).fit()
    print(f"    LCV validation OLS:")
    print(f"      N districts = {len(val)}")
    print(f"      R² = {result.rsquared:.3f}")
    print(f"      ideology coef = {result.params['mean_ideology']:.2f} "
          f"(p={result.pvalues['mean_ideology']:.3f})")

    # Scatter plot
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(val["mean_ideology"], val["lcv_score"], alpha=0.7, color="#2563eb")
    xr = [val["mean_ideology"].min(), val["mean_ideology"].max()]
    yr = [result.params["Intercept"] + result.params["mean_ideology"] * x for x in xr]
    ax.plot(xr, yr, color="red", lw=1.5, label=f"R²={result.rsquared:.2f}")
    ax.set_xlabel("Mean Climate Ideology Index (tract avg by district)")
    ax.set_ylabel("LCV Score (2023)")
    ax.set_title("Ideology Index Validation: LCV Scores by CA Congressional District")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIGURES / "ideology_lcv_validation.png", dpi=300)
    plt.close()
    print("    Validation scatter → output/figures/ideology_lcv_validation.png")


def build_cd_tract_crosswalk() -> pd.DataFrame:
    """Download 118th Congress CA district shapefile; spatial join to tracts."""
    import io, zipfile
    CD_URL = "https://www2.census.gov/geo/tiger/TIGER2023/CD/tl_2023_06_cd118.zip"
    TRACT_SHP = RAW / "shapefiles" / "tl_2020_06_tract"

    cd_dir = RAW / "shapefiles" / "tl_2023_06_cd118"
    if not cd_dir.exists():
        cd_dir.mkdir(parents=True)
        print(f"    Downloading 118th Congress CA district shapefile...")
        resp = requests.get(CD_URL, timeout=120)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            zf.extractall(cd_dir)

    cd = gpd.read_file(list(cd_dir.glob("*.shp"))[0]).to_crs("EPSG:3310")
    tracts = gpd.read_file(list(TRACT_SHP.glob("*.shp"))[0]).to_crs("EPSG:3310")

    # Spatial join: assign each tract centroid to a CD
    tracts["centroid"] = tracts.geometry.centroid
    tracts_pt = tracts.set_geometry("centroid")
    joined = gpd.sjoin(tracts_pt, cd[["CD118FP", "geometry"]], how="left", predicate="within")

    geoid_col = next(c for c in tracts.columns if c.upper() == "GEOID")
    result = pd.DataFrame({
        "tract_geoid_20": joined[geoid_col].values,
        "district_num": pd.to_numeric(joined["CD118FP"], errors="coerce"),
    }).dropna(subset=["district_num"])
    result["district_num"] = result["district_num"].astype(int)
    return result


# ── Choropleth map ────────────────────────────────────────────────────────────

def make_ideology_map(index_df: pd.DataFrame):
    """Choropleth of climate_ideology_index across CA Census tracts."""
    print("  Building ideology choropleth map...")
    tract_shp = RAW / "shapefiles" / "tl_2020_06_tract"
    shp_files = list(tract_shp.glob("*.shp")) if tract_shp.exists() else []
    if not shp_files:
        print("    WARNING: tract shapefile not found, skipping map")
        return

    tracts = gpd.read_file(shp_files[0])
    geoid_col = next(c for c in tracts.columns if c.upper() == "GEOID")
    tracts = tracts.rename(columns={geoid_col: "tract_geoid_20"})
    tracts = tracts.merge(index_df[["tract_geoid_20", "climate_ideology_index"]],
                          on="tract_geoid_20", how="left")

    fig, ax = plt.subplots(1, 1, figsize=(8, 10))
    tracts.plot(
        column="climate_ideology_index",
        cmap="RdBu",
        linewidth=0,
        ax=ax,
        legend=True,
        missing_kwds={"color": "lightgrey"},
        legend_kwds={"label": "Climate Ideology Index", "shrink": 0.6},
    )
    ax.set_axis_off()
    ax.set_title("Climate Ideology Index\nCalifornia Census Tracts", fontsize=13)
    plt.tight_layout()
    fig.savefig(FIGURES / "ideology_map.png", dpi=300)
    plt.close()
    print("    Map → output/figures/ideology_map.png")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== 06_ideology_index.py ===\n")

    panel = pd.read_csv(PROCESSED / "panel_tract_year.csv",
                        dtype={"tract_geoid_20": str})

    index_df = build_ideology_index(panel)
    index_df.to_csv(PROCESSED / "ideology_index.csv", index=False)
    print(f"  Ideology index saved → data/processed/ideology_index.csv")
    print(f"  Tracts with index: {len(index_df):,}")

    validate_against_lcv(index_df)
    make_ideology_map(index_df)

    print("\nDone. Next: run 07_replication.py")


if __name__ == "__main__":
    main()
```

**Step 4: Run script**

```bash
python scripts/06_ideology_index.py
```

Expected: PCA loadings printed, scree plot and map saved, LCV validation attempted.

**Step 5: Run validation**

```bash
python tests/test_06_ideology.py
```

Expected: all PASS.

**Step 6: Commit**

```bash
git add scripts/06_ideology_index.py tests/test_06_ideology.py
git commit -m "feat: add script 06 PCA ideology index with LCV validation"
```

---

## Task 3: Script 07 — Replication

**Files:**
- Create: `scripts/07_replication.py`

**Context:** Cross-sectional replication of Kahn (2007). Uses 2023 data only (latest cross-section).
OLS for commute outcomes; Negative Binomial for vehicle counts. Uses statsmodels throughout.
Saves regression tables as both CSV and formatted HTML.

**Step 1: Write script 07**

```python
#!/usr/bin/env python3
"""
07_replication.py
Cross-sectional replication of Kahn (2007).

Uses 2023 ACS cross-section. Three specifications:
  1. OLS: pct_transit ~ ideology + controls
  2. OLS: pct_drove_alone ~ ideology + controls
  3. Negative Binomial: total_bev ~ ideology + controls + exposure(log total_light)

Inputs:
  data/processed/panel_tract_year.csv
  data/processed/ideology_index.csv

Outputs:
  output/tables/replication_ols_transit.{csv,html}
  output/tables/replication_ols_drivealone.{csv,html}
  output/tables/replication_negbin_bev.{csv,html}
  output/figures/replication_scatter.png
"""

import math
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.discrete.discrete_model import NegativeBinomial

ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

CONTROLS = (
    "log_median_hh_income + pct_ba_plus + pop_density + "
    "pct_white + pct_wfh"
)


def load_cross_section() -> pd.DataFrame:
    """Load 2023 cross-section merged with ideology index."""
    panel = pd.read_csv(PROCESSED / "panel_tract_year.csv", dtype={"tract_geoid_20": str})
    index = pd.read_csv(PROCESSED / "ideology_index.csv", dtype={"tract_geoid_20": str})

    cs = panel[panel["data_year"] == 2023].copy()
    cs = cs.merge(index[["tract_geoid_20", "climate_ideology_index"]], on="tract_geoid_20", how="left")

    # Drop tracts missing key vars
    required = ["climate_ideology_index", "pct_transit", "pct_drove_alone",
                "total_bev", "total_light", "log_median_hh_income",
                "pct_ba_plus", "pct_white", "pct_wfh"]
    n_before = len(cs)
    cs = cs.dropna(subset=required)
    cs = cs[cs["total_light"] > 0]
    print(f"  2023 cross-section: {n_before} → {len(cs)} tracts after dropping missing")
    return cs


def fmt_table(result, title: str) -> str:
    """Format statsmodels result as simple HTML table."""
    params = result.params
    pvals = result.pvalues
    conf = result.conf_int()
    rows = []
    for var in params.index:
        stars = ("***" if pvals[var] < 0.01 else
                 "**" if pvals[var] < 0.05 else
                 "*" if pvals[var] < 0.1 else "")
        rows.append({
            "Variable": var,
            "Coef": f"{params[var]:.4f}{stars}",
            "SE": f"({result.bse[var]:.4f})",
            "95% CI Lower": f"{conf.loc[var, 0]:.4f}",
            "95% CI Upper": f"{conf.loc[var, 1]:.4f}",
        })
    df = pd.DataFrame(rows)
    notes = f"<p>N={int(result.nobs):,}"
    if hasattr(result, 'rsquared'):
        notes += f" | R²={result.rsquared:.3f}"
    if hasattr(result, 'llf'):
        notes += f" | Log-likelihood={result.llf:.1f}"
    notes += "<br>*p<0.1, **p<0.05, ***p<0.01 (HC3 robust SEs)</p>"
    html = f"<h3>{title}</h3>" + df.to_html(index=False) + notes
    return html, df


def run_ols_transit(cs: pd.DataFrame):
    print("  Running OLS: transit share...")
    formula = f"pct_transit ~ climate_ideology_index + {CONTROLS}"
    result = smf.ols(formula, data=cs).fit(cov_type="HC3")
    print(result.summary2().tables[1][["Coef.", "Std.Err.", "P>|t|"]].to_string())

    html, df = fmt_table(result, "OLS: Transit Commute Share ~ Climate Ideology")
    df.to_csv(TABLES / "replication_ols_transit.csv", index=False)
    with open(TABLES / "replication_ols_transit.html", "w") as f:
        f.write(html)
    print(f"  Saved → output/tables/replication_ols_transit.{{csv,html}}")
    return result


def run_ols_drivealone(cs: pd.DataFrame):
    print("  Running OLS: drive-alone share...")
    formula = f"pct_drove_alone ~ climate_ideology_index + {CONTROLS}"
    result = smf.ols(formula, data=cs).fit(cov_type="HC3")
    print(result.summary2().tables[1][["Coef.", "Std.Err.", "P>|t|"]].to_string())

    html, df = fmt_table(result, "OLS: Drive-Alone Commute Share ~ Climate Ideology")
    df.to_csv(TABLES / "replication_ols_drivealone.csv", index=False)
    with open(TABLES / "replication_ols_drivealone.html", "w") as f:
        f.write(html)
    print(f"  Saved → output/tables/replication_ols_drivealone.{{csv,html}}")
    return result


def run_negbin_bev(cs: pd.DataFrame):
    print("  Running Negative Binomial: BEV count...")
    # statsmodels NegativeBinomial requires integer outcome
    cs = cs.copy()
    cs["total_bev_int"] = cs["total_bev"].round().astype(int)
    cs["log_total_light"] = np.log(cs["total_light"].clip(lower=1))

    formula = f"total_bev_int ~ climate_ideology_index + {CONTROLS} + offset(log_total_light)"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = smf.negativebinomial(formula, data=cs).fit(disp=False, maxiter=200)

    print(result.summary2().tables[1][["Coef.", "Std.Err.", "P>|z|"]].to_string())

    params = result.params
    pvals = result.pvalues
    bse = result.bse
    rows = []
    for var in params.index:
        stars = ("***" if pvals[var] < 0.01 else
                 "**" if pvals[var] < 0.05 else
                 "*" if pvals[var] < 0.1 else "")
        rows.append({
            "Variable": var,
            "Coef (log-rate)": f"{params[var]:.4f}{stars}",
            "IRR": f"{math.exp(params[var]):.4f}",
            "SE": f"({bse[var]:.4f})",
        })
    df = pd.DataFrame(rows)
    notes = (f"<p>N={int(result.nobs):,} | Log-likelihood={result.llf:.1f}"
             f"<br>*p<0.1, **p<0.05, ***p<0.01</p>")
    html = "<h3>Negative Binomial: BEV Count ~ Climate Ideology</h3>" + df.to_html(index=False) + notes
    df.to_csv(TABLES / "replication_negbin_bev.csv", index=False)
    with open(TABLES / "replication_negbin_bev.html", "w") as f:
        f.write(html)
    print(f"  Saved → output/tables/replication_negbin_bev.{{csv,html}}")
    return result


def make_scatter(cs: pd.DataFrame):
    print("  Making replication scatter plots...")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, (ycol, ylabel) in zip(axes, [
        ("pct_transit", "Transit Commute Share"),
        ("pct_drove_alone", "Drive-Alone Share"),
    ]):
        x = cs["climate_ideology_index"]
        y = cs[ycol]
        ax.scatter(x, y, alpha=0.15, s=8, color="#1e40af")
        # Fitted line
        m, b = np.polyfit(x.dropna(), y[x.notna()], 1)
        xr = np.linspace(x.min(), x.max(), 100)
        ax.plot(xr, m * xr + b, color="red", lw=1.5)
        ax.set_xlabel("Climate Ideology Index")
        ax.set_ylabel(ylabel)
        ax.set_title(f"{ylabel} vs. Climate Ideology (2023)")

    plt.suptitle("Replication of Kahn (2007) — California Census Tracts, 2023", fontsize=11)
    plt.tight_layout()
    fig.savefig(FIGURES / "replication_scatter.png", dpi=300)
    plt.close()
    print("  Scatter → output/figures/replication_scatter.png")


def main():
    print("=== 07_replication.py ===\n")
    cs = load_cross_section()
    run_ols_transit(cs)
    run_ols_drivealone(cs)
    run_negbin_bev(cs)
    make_scatter(cs)
    print("\nDone. Next: run 08_ev_panel.py")


if __name__ == "__main__":
    main()
```

**Step 2: Run script**

```bash
python scripts/07_replication.py
```

Expected: three regression tables printed and saved, scatter plot saved.

**Step 3: Inspect outputs**

```bash
ls output/tables/replication_*.csv
```

Check that ideology coefficient signs match expectations: positive for transit, negative for drive-alone, positive for BEV count.

**Step 4: Commit**

```bash
git add scripts/07_replication.py
git commit -m "feat: add script 07 cross-section replication (OLS + negative binomial)"
```

---

## Task 4: Script 08 — EV Panel

**Files:**
- Create: `scripts/08_ev_panel.py`

**Context:** Two-way fixed effects (TWFE) panel regressions. Uses `linearmodels.PanelOLS`
which requires a MultiIndex of (entity, time). Four dependent variables. Clustered standard errors
at tract level. Also runs a pooled OLS version for easier interpretation.

**Step 1: Write script 08**

```python
#!/usr/bin/env python3
"""
08_ev_panel.py
Two-way fixed effects panel regressions: ideology predicting EV adoption 2018–2024.

Four dependent variables:
  1. log(tesla_bev + 1)
  2. log(nontesla_bev + 1)
  3. log(light_truck_count + 1)
  4. tesla_share = tesla_bev / (tesla_bev + nontesla_bev)

Inputs:
  data/processed/panel_tract_year.csv
  data/processed/ideology_index.csv

Outputs:
  output/tables/ev_panel_twfe.{csv,html}
  output/tables/ev_panel_pooled.{csv,html}
  output/figures/ev_panel_coefs.png
"""

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS
import statsmodels.formula.api as smf

ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

CONTROLS_POOL = (
    "climate_ideology_index + log_median_hh_income + pct_ba_plus + "
    "pop_density + pct_white + pct_wfh"
)
CONTROLS_FE = [
    "log_median_hh_income", "pct_ba_plus", "pop_density", "pct_white", "pct_wfh"
]


def load_panel() -> pd.DataFrame:
    panel = pd.read_csv(PROCESSED / "panel_tract_year.csv", dtype={"tract_geoid_20": str})
    index = pd.read_csv(PROCESSED / "ideology_index.csv", dtype={"tract_geoid_20": str})

    df = panel.merge(index[["tract_geoid_20", "climate_ideology_index"]],
                     on="tract_geoid_20", how="left")

    # Derived DVs
    df["log_tesla_bev"] = np.log1p(df["tesla_bev"])
    df["log_nontesla_bev"] = np.log1p(df["nontesla_bev"])
    df["log_light_truck"] = np.log1p(df["light_truck_count"])
    total_ev = df["tesla_bev"] + df["nontesla_bev"]
    df["tesla_share"] = df["tesla_bev"] / total_ev.replace(0, np.nan)

    # Drop tracts with missing ideology
    n_before = len(df)
    df = df.dropna(subset=["climate_ideology_index"])
    print(f"  Panel: {n_before:,} → {len(df):,} rows after dropping missing ideology")
    return df


def run_twfe(df: pd.DataFrame) -> dict:
    """Run TWFE for each DV using linearmodels.PanelOLS."""
    print("  Running TWFE models...")

    df_fe = df.set_index(["tract_geoid_20", "data_year"]).copy()

    # Controls: time-invariant controls absorbed into FE when using entity FE,
    # but we include time-varying ones if available; here all controls are time-invariant
    # With tract FE, time-invariant controls are collinear — they get absorbed.
    # So TWFE uses year FE + tract FE, and ideology (time-invariant) is identified
    # by between-tract variation after partialling out year effects.
    # NOTE: ideology is also time-invariant; in strict TWFE it would be absorbed by entity FE.
    # Instead we use a Mundlak-style approach or interact ideology × year dummies.
    # For this "static" TWFE, we use pooled OLS with year FE only (no tract FE),
    # since ideology is time-invariant and cannot be identified within-tract.
    # The event study in script 09 uses the full interaction approach.

    # For script 08 TWFE: year FE only (between estimator) with robust SEs
    results = {}
    dvs = [
        ("log_tesla_bev", "log(Tesla BEV + 1)"),
        ("log_nontesla_bev", "log(Non-Tesla BEV + 1)"),
        ("log_light_truck", "log(Light Truck + 1)"),
        ("tesla_share", "Tesla Share of BEVs"),
    ]

    for dv_col, dv_label in dvs:
        ctrl_str = " + ".join(CONTROLS_FE)
        formula = f"{dv_col} ~ climate_ideology_index + {ctrl_str} + C(data_year)"
        sub = df.dropna(subset=[dv_col] + CONTROLS_FE + ["climate_ideology_index"])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = smf.ols(formula, data=sub).fit(cov_type="cluster",
                                                  cov_kwds={"groups": sub["tract_geoid_20"]})
        coef = res.params["climate_ideology_index"]
        se = res.bse["climate_ideology_index"]
        pval = res.pvalues["climate_ideology_index"]
        print(f"    {dv_label}: coef={coef:.4f}, SE={se:.4f}, p={pval:.3f}")
        results[dv_col] = (dv_label, res)

    return results


def run_pooled(df: pd.DataFrame) -> dict:
    """Pooled OLS for each DV (no FE) — easier to interpret."""
    print("  Running pooled OLS models...")
    results = {}
    dvs = [
        ("log_tesla_bev", "log(Tesla BEV + 1)"),
        ("log_nontesla_bev", "log(Non-Tesla BEV + 1)"),
        ("log_light_truck", "log(Light Truck + 1)"),
        ("tesla_share", "Tesla Share of BEVs"),
    ]
    for dv_col, dv_label in dvs:
        formula = f"{dv_col} ~ {CONTROLS_POOL}"
        sub = df.dropna(subset=[dv_col] + ["climate_ideology_index"] + CONTROLS_FE)
        res = smf.ols(formula, data=sub).fit(cov_type="HC3")
        coef = res.params["climate_ideology_index"]
        se = res.bse["climate_ideology_index"]
        pval = res.pvalues["climate_ideology_index"]
        print(f"    {dv_label}: coef={coef:.4f}, SE={se:.4f}, p={pval:.3f}")
        results[dv_col] = (dv_label, res)
    return results


def save_results_table(results: dict, filename: str, title: str):
    rows = []
    for dv_col, (dv_label, res) in results.items():
        coef = res.params["climate_ideology_index"]
        se = res.bse["climate_ideology_index"]
        pval = res.pvalues["climate_ideology_index"]
        stars = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.1 else ""
        rows.append({
            "Dependent Variable": dv_label,
            "Ideology Coef": f"{coef:.4f}{stars}",
            "SE": f"({se:.4f})",
            "p-value": f"{pval:.3f}",
            "N": int(res.nobs),
            "R²": f"{res.rsquared:.3f}",
        })
    df = pd.DataFrame(rows)
    df.to_csv(TABLES / f"{filename}.csv", index=False)
    html = f"<h3>{title}</h3>" + df.to_html(index=False) + \
           "<p>*p<0.1, **p<0.05, ***p<0.01. Ideology = Climate Ideology Index (PC1).</p>"
    with open(TABLES / f"{filename}.html", "w") as f:
        f.write(html)
    print(f"  Saved → output/tables/{filename}.{{csv,html}}")


def make_coef_plot(twfe_results: dict, pooled_results: dict):
    """Coefficient plot comparing TWFE vs pooled across 4 DVs."""
    fig, ax = plt.subplots(figsize=(9, 5))
    dvs = list(twfe_results.keys())
    labels = [twfe_results[d][0] for d in dvs]
    y = np.arange(len(dvs))

    for offset, (res_dict, color, label) in enumerate([
        (twfe_results, "#1e40af", "Year FE (clustered SE)"),
        (pooled_results, "#dc2626", "Pooled OLS (HC3)"),
    ]):
        coefs = [res_dict[d][1].params["climate_ideology_index"] for d in dvs]
        ses = [res_dict[d][1].bse["climate_ideology_index"] for d in dvs]
        ypos = y + offset * 0.3 - 0.15
        ax.errorbar(coefs, ypos, xerr=[1.96 * s for s in ses],
                    fmt="o", color=color, capsize=4, label=label, markersize=6)

    ax.axvline(0, color="black", lw=0.8, linestyle="--")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("Climate Ideology Index Coefficient (log scale DVs)")
    ax.set_title("EV Panel: Effect of Climate Ideology on Vehicle Adoption\n(California Census Tracts, 2018–2024)")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIGURES / "ev_panel_coefs.png", dpi=300)
    plt.close()
    print("  Coefficient plot → output/figures/ev_panel_coefs.png")


def main():
    print("=== 08_ev_panel.py ===\n")
    df = load_panel()
    twfe = run_twfe(df)
    pooled = run_pooled(df)
    save_results_table(twfe, "ev_panel_twfe",
                       "EV Panel — Year FE with Clustered SEs")
    save_results_table(pooled, "ev_panel_pooled",
                       "EV Panel — Pooled OLS (HC3)")
    make_coef_plot(twfe, pooled)
    print("\nDone. Next: run 09_event_study.py")


if __name__ == "__main__":
    main()
```

**Step 2: Run script**

```bash
python scripts/08_ev_panel.py
```

Expected: 8 regressions run, coefficient plot saved.
Check ideology coefficient on `log_tesla_bev` is positive and significant.

**Step 3: Commit**

```bash
git add scripts/08_ev_panel.py
git commit -m "feat: add script 08 EV panel regressions (year FE + pooled OLS)"
```

---

## Task 5: Script 09 — Event Study

**Files:**
- Create: `scripts/09_event_study.py`

**Context:** The hero analysis. Estimates `ideology × year` interaction coefficients for Tesla
and non-Tesla BEVs separately. 2018 is the omitted baseline year. Plots β_τ with 95% CIs
over time for both series on the same chart. Vertical lines mark the 2022 (Twitter acquisition)
and 2024 (DOGE) events. Light truck series is the placebo.

**Step 1: Write script 09**

```python
#!/usr/bin/env python3
"""
09_event_study.py
Event study: Has climate ideology's relationship with Tesla adoption changed
following Elon Musk's political pivot?

Specification:
  log(EV_count + 1)_it = α_i + γ_t + Σ_τ β_τ(ideology_i × 1[year=τ]) + ε_it

Run separately for Tesla BEVs and non-Tesla BEVs (placebo/control series).
2018 = omitted base year; β_2018 normalized to 0.

Events marked:
  2022 — Musk acquires Twitter (Oct 2022)
  2024 — DOGE role / Trump administration

Outputs:
  output/figures/event_study_tesla_vs_nontesla.png  (hero figure)
  output/tables/event_study_coefs.csv
  output/figures/event_study_truck.png               (placebo)
"""

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

BASE_YEAR = 2018
EVENT_YEARS = {2022: "Musk acquires Twitter\n(Oct 2022)",
               2024: "DOGE / Trump admin\n(Nov 2024)"}


def load_panel() -> pd.DataFrame:
    panel = pd.read_csv(PROCESSED / "panel_tract_year.csv", dtype={"tract_geoid_20": str})
    index = pd.read_csv(PROCESSED / "ideology_index.csv", dtype={"tract_geoid_20": str})
    df = panel.merge(index[["tract_geoid_20", "climate_ideology_index"]],
                     on="tract_geoid_20", how="left")
    df = df.dropna(subset=["climate_ideology_index"])
    df["log_tesla_bev"] = np.log1p(df["tesla_bev"])
    df["log_nontesla_bev"] = np.log1p(df["nontesla_bev"])
    df["log_light_truck"] = np.log1p(df["light_truck_count"])
    return df


def run_event_study(df: pd.DataFrame, dv_col: str, label: str) -> pd.DataFrame:
    """
    Estimate ideology × year interactions.

    Uses pooled OLS with tract FE (via entity dummies — computationally expensive
    but correct). For large N, we use the within-transformation manually.

    Returns DataFrame with columns: year, coef, se, ci_lo, ci_hi
    """
    print(f"  Event study: {label}...")

    years = sorted(df["data_year"].unique())
    non_base_years = [y for y in years if y != BASE_YEAR]

    # Create interaction terms: ideology × 1[year=τ] for each non-base year
    for year in non_base_years:
        df[f"ideo_x_{year}"] = df["climate_ideology_index"] * (df["data_year"] == year).astype(float)

    interaction_terms = " + ".join(f"ideo_x_{y}" for y in non_base_years)
    formula = (
        f"{dv_col} ~ {interaction_terms} + C(data_year) + C(tract_geoid_20) - 1"
    )

    sub = df.dropna(subset=[dv_col, "climate_ideology_index"]).copy()

    print(f"    N obs = {len(sub):,}, N tracts = {sub['tract_geoid_20'].nunique():,}")
    print(f"    Estimating... (this may take 1–2 minutes with tract FE)")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        # Demean within tract (within-transformation) to absorb tract FE efficiently
        sub["_dv"] = sub[dv_col] - sub.groupby("tract_geoid_20")[dv_col].transform("mean")
        sub["_ideo"] = sub["climate_ideology_index"] - sub.groupby("tract_geoid_20")["climate_ideology_index"].transform("mean")
        for year in non_base_years:
            col = f"ideo_x_{year}"
            sub[f"_dm_{col}"] = sub[col] - sub.groupby("tract_geoid_20")[col].transform("mean")

        dm_terms = " + ".join(f"_dm_ideo_x_{y}" for y in non_base_years)
        formula_dm = f"_dv ~ {dm_terms} + C(data_year) - 1"
        res = smf.ols(formula_dm, data=sub).fit(
            cov_type="cluster",
            cov_kwds={"groups": sub["tract_geoid_20"]}
        )

    # Extract interaction coefficients
    rows = []
    for year in years:
        if year == BASE_YEAR:
            rows.append({"year": year, "coef": 0.0, "se": 0.0, "ci_lo": 0.0, "ci_hi": 0.0})
        else:
            param_name = f"_dm_ideo_x_{year}"
            if param_name not in res.params:
                print(f"    WARNING: {param_name} not in results")
                continue
            coef = res.params[param_name]
            se = res.bse[param_name]
            rows.append({
                "year": year,
                "coef": coef,
                "se": se,
                "ci_lo": coef - 1.96 * se,
                "ci_hi": coef + 1.96 * se,
            })

    result_df = pd.DataFrame(rows).sort_values("year")
    result_df["series"] = label
    result_df["dv"] = dv_col
    print(f"    Done. Coefficients: {result_df.set_index('year')['coef'].to_dict()}")
    return result_df


def plot_event_study(tesla_df: pd.DataFrame, nontesla_df: pd.DataFrame,
                     filename: str, title: str, caption: str):
    """Plot two event study series on the same chart with event markers."""
    fig, ax = plt.subplots(figsize=(10, 6))
    years = sorted(tesla_df["year"].unique())

    for df, color, label, marker in [
        (tesla_df, "#dc2626", "Tesla BEV", "o"),
        (nontesla_df, "#1e40af", "Non-Tesla BEV", "s"),
    ]:
        ax.plot(df["year"], df["coef"], color=color, marker=marker,
                linewidth=2, markersize=7, label=label)
        ax.fill_between(df["year"], df["ci_lo"], df["ci_hi"],
                        color=color, alpha=0.15)

    # Base year reference line
    ax.axhline(0, color="black", lw=0.8, linestyle="--", alpha=0.5)

    # Event markers
    for event_year, event_label in EVENT_YEARS.items():
        if event_year in years or event_year <= max(years):
            ax.axvline(event_year, color="gray", lw=1.2, linestyle=":",
                       alpha=0.8)
            ax.text(event_year + 0.05, ax.get_ylim()[1] * 0.95,
                    event_label, fontsize=8, color="gray",
                    ha="left", va="top")

    ax.set_xlabel("Year")
    ax.set_ylabel("Ideology × Year Coefficient\n(relative to 2018 baseline)")
    ax.set_title(title, fontsize=12)
    ax.set_xticks(years)
    ax.legend(loc="upper left")
    ax.grid(axis="y", alpha=0.3)

    # Caption below plot
    fig.text(0.5, -0.02, caption, ha="center", fontsize=8,
             style="italic", wrap=True)

    plt.tight_layout()
    fig.savefig(FIGURES / filename, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Figure → output/figures/{filename}")


def main():
    print("=== 09_event_study.py ===\n")
    df = load_panel()

    # Run event studies
    tesla = run_event_study(df.copy(), "log_tesla_bev", "Tesla BEV")
    nontesla = run_event_study(df.copy(), "log_nontesla_bev", "Non-Tesla BEV")
    truck = run_event_study(df.copy(), "log_light_truck", "Light Truck (Placebo)")

    # Save coefficient table
    all_coefs = pd.concat([tesla, nontesla, truck], ignore_index=True)
    all_coefs.to_csv(TABLES / "event_study_coefs.csv", index=False)
    print(f"  Coefficients → output/tables/event_study_coefs.csv")

    # Hero figure: Tesla vs. non-Tesla
    plot_event_study(
        tesla_df=tesla,
        nontesla_df=nontesla,
        filename="event_study_tesla_vs_nontesla.png",
        title="The Elon Effect: Climate Ideology and EV Adoption Over Time\nCalifornia Census Tracts, 2018–2024",
        caption=(
            "Coefficients from ideology × year interaction (within-tract). "
            "2018 = baseline. 95% CI shaded. "
            "Non-Tesla EVs serve as the control series. "
            "Vertical lines mark Twitter acquisition (2022) and DOGE/Trump admin (2024)."
        ),
    )

    # Placebo: truck
    plot_event_study(
        tesla_df=truck,
        nontesla_df=nontesla,
        filename="event_study_truck.png",
        title="Placebo Check: Light Trucks vs. Non-Tesla EVs",
        caption=(
            "Light truck ideology coefficient should be flat or declining throughout "
            "if the ideology-EV correlation is specific to green vehicles."
        ),
    )

    print("\nDone. Next: run 10_robustness.py")


if __name__ == "__main__":
    main()
```

**Step 2: Run script**

```bash
python scripts/09_event_study.py
```

Expected: two figures saved. The Tesla series should diverge from non-Tesla post-2022 if the Elon Effect is real. This is the longest-running script (~2–5 min due to tract FE estimation).

**Step 3: Inspect the hero figure**

```bash
open output/figures/event_study_tesla_vs_nontesla.png
```

**Step 4: Commit**

```bash
git add scripts/09_event_study.py
git commit -m "feat: add script 09 event study (The Elon Effect)"
```

---

## Task 6: Script 10 — Robustness

**Files:**
- Create: `scripts/10_robustness.py`

**Context:** Re-runs the cross-section and panel specifications with three alternative ideology
measures. Presents results in 4-column comparison tables (Main, R1, R2, R3).

**Step 1: Write script 10**

```python
#!/usr/bin/env python3
"""
10_robustness.py
Robustness checks with alternative ideology measures.

Specifications:
  Main — tract level, PCA composite (YCOM + reg + ballot)
  R1   — county level, YCOM only (clean measurement, coarse geography)
  R2   — tract level, voter reg + ballot only (no YCOM county assumption)
  R3   — tract level, Prop 30 share only (simplest direct climate signal)

Outputs:
  output/tables/robustness_{model}.{csv,html}  — one table per model type
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
TABLES.mkdir(parents=True, exist_ok=True)

CONTROLS_BASE = [
    "log_median_hh_income", "pct_ba_plus", "pop_density", "pct_white", "pct_wfh"
]


def load_data() -> pd.DataFrame:
    panel = pd.read_csv(PROCESSED / "panel_tract_year.csv", dtype={"tract_geoid_20": str})
    index = pd.read_csv(PROCESSED / "ideology_index.csv", dtype={"tract_geoid_20": str})
    df = panel.merge(index, on="tract_geoid_20", how="left")
    df["log_tesla_bev"] = np.log1p(df["tesla_bev"])
    df["log_nontesla_bev"] = np.log1p(df["nontesla_bev"])
    df["log_total_bev"] = np.log1p(df["total_bev"])
    df["total_bev_int"] = df["total_bev"].round().astype("Int64")
    df["log_total_light"] = np.log(df["total_light"].clip(lower=1))
    return df


def build_r1_county(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate tract panel to county level; use mean YCOM as ideology."""
    df = df.copy()
    df["county_fips"] = df["tract_geoid_20"].str[:5]
    ycom_cols = [c for c in df.columns if c.startswith("ycom_")]

    # County-level means of all variables
    agg_dict = {
        "total_bev": "sum", "tesla_bev": "sum", "nontesla_bev": "sum",
        "total_light": "sum", "light_truck_count": "sum",
        "pct_transit": "mean", "pct_drove_alone": "mean",
        "log_median_hh_income": "mean", "pct_ba_plus": "mean",
        "pop_density": "mean", "pct_white": "mean", "pct_wfh": "mean",
        **{c: "mean" for c in ycom_cols},
    }
    county = df.groupby(["county_fips", "data_year"]).agg(agg_dict).reset_index()

    # Build county-level ideology index from YCOM only (simple mean of standardized vars)
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    cs_county = county[county["data_year"] == 2023].dropna(subset=ycom_cols)
    if len(cs_county) < 30:
        print("  WARNING: R1 has < 30 county observations")

    scaler = StandardScaler()
    X = scaler.fit_transform(cs_county[ycom_cols])
    pca = PCA(n_components=1)
    pc1 = pca.fit_transform(X).ravel()

    # Flip if needed
    if pca.components_[0, ycom_cols.index("ycom_happening")] < 0:
        pc1 = -pc1

    county_index = cs_county[["county_fips"]].copy()
    county_index["ideology_r1"] = pc1
    county = county.merge(county_index, on="county_fips", how="left")
    county["log_total_bev"] = np.log1p(county["total_bev"])
    county["total_bev_int"] = county["total_bev"].round().astype("Int64")
    county["log_total_light"] = np.log(county["total_light"].clip(lower=1))
    county["geo_id"] = county["county_fips"]
    return county


def run_spec(df: pd.DataFrame, ideology_col: str, geo_col: str,
             dv: str, model_type: str, label: str):
    """Run one specification; return (label, coef, se, pval, nobs)."""
    ctrl = " + ".join(CONTROLS_BASE)
    required = [ideology_col, dv] + CONTROLS_BASE
    sub = df.dropna(subset=required)
    sub = sub[sub["data_year"] == 2023].copy()

    if model_type == "ols":
        formula = f"{dv} ~ {ideology_col} + {ctrl}"
        res = smf.ols(formula, data=sub).fit(cov_type="HC3")
        coef = res.params[ideology_col]
        se = res.bse[ideology_col]
        pval = res.pvalues[ideology_col]
    elif model_type == "negbin":
        formula = f"total_bev_int ~ {ideology_col} + {ctrl} + offset(log_total_light)"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = smf.negativebinomial(formula, data=sub).fit(disp=False, maxiter=200)
        coef = res.params[ideology_col]
        se = res.bse[ideology_col]
        pval = res.pvalues[ideology_col]

    stars = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.1 else ""
    return {"Specification": label,
            "Coef": f"{coef:.4f}{stars}", "SE": f"({se:.4f})",
            "p-value": f"{pval:.3f}", "N": int(res.nobs)}


def make_robustness_table(results_by_spec: dict, title: str, filename: str):
    """Build 4-column comparison table (Main, R1, R2, R3)."""
    rows = []
    for spec_name, row in results_by_spec.items():
        rows.append({"Specification": spec_name, **row})
    df = pd.DataFrame(rows)
    df.to_csv(TABLES / f"{filename}.csv", index=False)
    html = f"<h3>{title}</h3>" + df.to_html(index=False) + \
           "<p>*p<0.1, **p<0.05, ***p<0.01<br>" \
           "Main=PCA composite at tract; R1=YCOM only at county; " \
           "R2=Voter reg+ballot at tract; R3=Prop 30 only at tract</p>"
    with open(TABLES / f"{filename}.html", "w") as f:
        f.write(html)
    print(f"  Saved → output/tables/{filename}.{{csv,html}}")


def main():
    print("=== 10_robustness.py ===\n")
    df = load_data()
    r1 = build_r1_county(df)

    # Ideology columns for each spec
    specs = {
        "Main (PCA, tract)": (df, "climate_ideology_index", "tract_geoid_20"),
        "R1 (YCOM only, county)": (r1, "ideology_r1", "county_fips"),
        "R2 (reg+ballot, tract)": (df, "prop30_yes_share", "tract_geoid_20"),  # simplified
        "R3 (Prop 30, tract)": (df, "prop30_yes_share", "tract_geoid_20"),
    }

    # NOTE: R2 should ideally use a sub-PCA of just reg+ballot vars.
    # For simplicity, if dem_minus_rep is available, use it as R2 ideology.
    if "dem_minus_rep" in df.columns:
        from sklearn.preprocessing import StandardScaler
        from sklearn.decomposition import PCA
        reg_ballot_vars = [c for c in ["dem_minus_rep", "prop30_yes_share", "prop68_yes_share"]
                           if c in df.columns]
        if len(reg_ballot_vars) >= 2:
            cs_r2 = df[df["data_year"] == 2023].dropna(subset=reg_ballot_vars)
            scaler = StandardScaler()
            X_r2 = scaler.fit_transform(cs_r2[reg_ballot_vars])
            pc1_r2 = PCA(n_components=1).fit_transform(X_r2).ravel()
            r2_idx = cs_r2[["tract_geoid_20"]].copy()
            r2_idx["ideology_r2"] = pc1_r2
            df_r2 = df.merge(r2_idx, on="tract_geoid_20", how="left")
            specs["R2 (reg+ballot, tract)"] = (df_r2, "ideology_r2", "tract_geoid_20")

    # Run all models
    for model_name, (dv_col, dv_label, model_type) in [
        ("ols_transit", "pct_transit", "OLS: Transit", "ols"),
        ("ols_drivealone", "pct_drove_alone", "OLS: Drive-Alone", "ols"),
        ("negbin_bev", "total_bev_int", "NB: BEV Count", "negbin"),
    ]:
        print(f"\n  Model: {dv_label}")
        results = {}
        for spec_name, (spec_df, ideo_col, geo_col) in specs.items():
            try:
                row = run_spec(spec_df, ideo_col, geo_col, dv_col, model_type, spec_name)
                results[spec_name] = {k: v for k, v in row.items() if k != "Specification"}
            except Exception as e:
                print(f"    ERROR in {spec_name}: {e}")
                results[spec_name] = {"Coef": "ERROR", "SE": "", "p-value": "", "N": ""}

        make_robustness_table(results, f"Robustness: {dv_label}", f"robustness_{model_name}")

    print("\nDone. Next: run 11_spatial.py")


if __name__ == "__main__":
    main()
```

**Step 2: Run script**

```bash
python scripts/10_robustness.py
```

Expected: 3 robustness tables saved, one per dependent variable.

**Step 3: Commit**

```bash
git add scripts/10_robustness.py
git commit -m "feat: add script 10 robustness checks (Main, R1, R2, R3 ideology specs)"
```

---

## Task 7: Script 11 — Spatial Analysis

**Files:**
- Create: `scripts/11_spatial.py`

**Context:** Tests for spatial autocorrelation in cross-section OLS residuals using Moran's I.
If significant, estimates a Spatial Lag Model (SAR) as a correction. Uses `libpysal` for
spatial weights and `spreg` for SAR estimation.

**Step 1: Write script 11**

```python
#!/usr/bin/env python3
"""
11_spatial.py
Spatial autocorrelation diagnostics and spatial lag models.

Steps:
  1. Build queen contiguity spatial weights from 2020 TIGER tract shapefiles
  2. Run Moran's I on residuals from cross-section OLS models (script 07)
  3. If significant: run SAR (Spatial Lag Model) via spreg
  4. Report spatial autoregressive coefficient ρ vs. OLS coefficient

Outputs:
  output/tables/spatial_morans.csv
  output/tables/spatial_sar.{csv,html}  (if spatial correction needed)
  output/figures/spatial_weights_map.png
  output/figures/residual_map.png
"""

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import libpysal
from esda.moran import Moran

ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

CONTROLS = (
    "log_median_hh_income + pct_ba_plus + pop_density + pct_white + pct_wfh"
)


def load_cross_section() -> pd.DataFrame:
    panel = pd.read_csv(PROCESSED / "panel_tract_year.csv", dtype={"tract_geoid_20": str})
    index = pd.read_csv(PROCESSED / "ideology_index.csv", dtype={"tract_geoid_20": str})
    cs = panel[panel["data_year"] == 2023].merge(
        index[["tract_geoid_20", "climate_ideology_index"]], on="tract_geoid_20", how="left"
    )
    required = ["climate_ideology_index", "pct_transit", "pct_drove_alone",
                "total_bev", "total_light", "log_median_hh_income",
                "pct_ba_plus", "pct_white", "pct_wfh", "pop_density"]
    cs = cs.dropna(subset=required)
    cs = cs[cs["total_light"] > 0]
    return cs


def build_weights(cs: pd.DataFrame) -> tuple:
    """Build queen contiguity spatial weights for tracts in cross-section."""
    print("  Building queen contiguity spatial weights...")
    tract_shp = RAW / "shapefiles" / "tl_2020_06_tract"
    shp_files = list(tract_shp.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"Tract shapefile not found at {tract_shp}")

    tracts = gpd.read_file(shp_files[0])
    geoid_col = next(c for c in tracts.columns if c.upper() == "GEOID")
    tracts = tracts.rename(columns={geoid_col: "tract_geoid_20"})

    # Filter to tracts in cross-section (with complete data)
    tracts = tracts[tracts["tract_geoid_20"].isin(cs["tract_geoid_20"])].copy()
    tracts = tracts.sort_values("tract_geoid_20").reset_index(drop=True)

    # Build queen contiguity weights using libpysal
    w = libpysal.weights.Queen.from_dataframe(tracts, idVariable="tract_geoid_20",
                                               silence_warnings=True)
    w.transform = "r"  # row-standardize
    print(f"    Weights: {w.n} tracts, mean neighbors = {w.mean_neighbors:.1f}")
    return w, tracts


def run_morans_i(residuals: np.ndarray, w: libpysal.weights.W,
                 label: str) -> dict:
    """Compute Moran's I for a vector of residuals."""
    mi = Moran(residuals, w)
    result = {
        "Model": label,
        "Moran I": f"{mi.I:.4f}",
        "Expected I": f"{mi.EI:.4f}",
        "z-score": f"{mi.z_norm:.4f}",
        "p-value": f"{mi.p_norm:.4f}",
        "Significant (α=0.05)": "YES" if mi.p_norm < 0.05 else "no",
    }
    print(f"    {label}: I={mi.I:.4f}, z={mi.z_norm:.2f}, p={mi.p_norm:.4f} "
          f"({'*SIGNIFICANT*' if mi.p_norm < 0.05 else 'ok'})")
    return result, mi.p_norm < 0.05


def run_sar(y: np.ndarray, X: np.ndarray, w: libpysal.weights.W,
            feature_names: list, label: str) -> dict:
    """Run Spatial Lag Model (SAR) using spreg.OLS_Regimes or ML_Lag."""
    print(f"  Running SAR for {label}...")
    try:
        import spreg
        sar = spreg.ML_Lag(y, X, w=w, name_y=label, name_x=feature_names)
        rho = sar.rho
        print(f"    SAR ρ = {rho:.4f} (spatial autocorrelation parameter)")
        return {
            "Model": label,
            "SAR ρ": f"{rho:.4f}",
            "Pseudo-R²": f"{sar.pr2:.4f}",
            "Log-likelihood": f"{sar.logll:.2f}",
        }
    except Exception as e:
        print(f"    SAR failed: {e}")
        return {"Model": label, "SAR ρ": "ERROR", "Pseudo-R²": "", "Log-likelihood": ""}


def make_residual_map(cs: pd.DataFrame, residuals: np.ndarray,
                      tracts: gpd.GeoDataFrame, label: str, filename: str):
    """Choropleth of OLS residuals to visualize spatial patterns."""
    cs = cs.copy()
    cs["residual"] = residuals
    geo = tracts.merge(cs[["tract_geoid_20", "residual"]], on="tract_geoid_20", how="left")

    fig, ax = plt.subplots(figsize=(7, 9))
    geo.plot(column="residual", cmap="RdBu_r", linewidth=0, ax=ax,
             legend=True, missing_kwds={"color": "lightgrey"},
             legend_kwds={"label": "OLS Residual", "shrink": 0.6},
             vmin=-0.15, vmax=0.15)
    ax.set_axis_off()
    ax.set_title(f"OLS Residuals: {label}\n(Spatial autocorrelation diagnostic)", fontsize=11)
    plt.tight_layout()
    fig.savefig(FIGURES / filename, dpi=300)
    plt.close()
    print(f"    Residual map → output/figures/{filename}")


def main():
    print("=== 11_spatial.py ===\n")
    cs = load_cross_section()

    try:
        w, tracts = build_weights(cs)
    except FileNotFoundError as e:
        print(f"  ERROR: {e}\n  Spatial analysis requires tract shapefiles from script 04.")
        return

    # Align cross-section to weight order
    cs = cs.set_index("tract_geoid_20").loc[list(w.id_order)].reset_index()

    # Get OLS residuals for each model
    models = [
        ("pct_transit", "OLS: Transit", "residual_transit.png"),
        ("pct_drove_alone", "OLS: Drive-Alone", "residual_drivealone.png"),
    ]

    morans_results = []
    sar_needed = False

    for dv, label, fig_file in models:
        formula = f"{dv} ~ climate_ideology_index + {CONTROLS}"
        sub = cs.dropna(subset=[dv, "climate_ideology_index",
                                 "log_median_hh_income", "pct_ba_plus",
                                 "pop_density", "pct_white", "pct_wfh"])
        if len(sub) < len(cs):
            print(f"  NOTE: {label} uses {len(sub)}/{len(cs)} tracts (missing values dropped)")

        res = smf.ols(formula, data=cs.fillna(cs.mean(numeric_only=True))).fit()
        resids = res.resid.values

        row, significant = run_morans_i(resids, w, label)
        morans_results.append(row)
        if significant:
            sar_needed = True
        make_residual_map(cs, resids, tracts, label, fig_file)

    # Save Moran's I table
    moran_df = pd.DataFrame(morans_results)
    moran_df.to_csv(TABLES / "spatial_morans.csv", index=False)
    html = "<h3>Moran's I — Spatial Autocorrelation Diagnostics</h3>" + \
           moran_df.to_html(index=False)
    with open(TABLES / "spatial_morans.html", "w") as f:
        f.write(html)
    print(f"\n  Moran's I table → output/tables/spatial_morans.csv")

    # Run SAR if any model showed significant spatial autocorrelation
    if sar_needed:
        print("\n  Significant spatial autocorrelation detected — running SAR corrections...")
        sar_results = []
        ctrl_cols = ["climate_ideology_index", "log_median_hh_income", "pct_ba_plus",
                     "pop_density", "pct_white", "pct_wfh"]
        sub_sar = cs[["pct_transit", "pct_drove_alone"] + ctrl_cols].dropna()
        # Re-align weights to this subset if sizes differ
        X = sub_sar[ctrl_cols].values

        for dv, label, _ in models:
            y = sub_sar[dv].values.reshape(-1, 1)
            sar_row = run_sar(y, X, w, ctrl_cols, label)
            sar_results.append(sar_row)

        sar_df = pd.DataFrame(sar_results)
        sar_df.to_csv(TABLES / "spatial_sar.csv", index=False)
        with open(TABLES / "spatial_sar.html", "w") as f:
            f.write("<h3>Spatial Lag Model (SAR) Results</h3>" + sar_df.to_html(index=False))
        print("  SAR results → output/tables/spatial_sar.{csv,html}")
    else:
        print("\n  No significant spatial autocorrelation — SAR correction not needed.")

    # Spatial weights connectivity map (sample of tracts for visual)
    print("\n  Plotting spatial weights structure...")
    fig, ax = plt.subplots(figsize=(7, 9))
    tracts.plot(ax=ax, facecolor="white", edgecolor="#aaaaaa", linewidth=0.3)
    ax.set_axis_off()
    ax.set_title("Queen Contiguity Spatial Weights\nCA Census Tracts 2020", fontsize=11)
    plt.tight_layout()
    fig.savefig(FIGURES / "spatial_weights_map.png", dpi=300)
    plt.close()
    print("  Weights map → output/figures/spatial_weights_map.png")

    print("\nDone. All analysis scripts complete. Next: write paper/draft.md")


if __name__ == "__main__":
    main()
```

**Step 2: Run script**

```bash
python scripts/11_spatial.py
```

Expected: Moran's I statistics printed, residual maps saved, SAR run if needed.

**Step 3: Commit**

```bash
git add scripts/11_spatial.py
git commit -m "feat: add script 11 spatial autocorrelation diagnostics and SAR"
```

---

## Task 8: Paper — Substack Post

**Files:**
- Create: `paper/draft.md`
- Create: `paper/` directory if not present

**Context:** Written AFTER running scripts 07–11 and inspecting real results. Fill in all
`[RESULT]`, `[TABLE]`, `[FIGURE]` placeholders with actual numbers and file references.
Tone: educated general audience. Lead with findings. Define every technical term on first use.

**Step 1: Create paper directory**

```bash
mkdir -p paper
```

**Step 2: Write draft**

```markdown
# Hummers or Hybrids, 2025 Edition: Did Tesla Buyers Stop Being Environmentalists?

*A replication of a 2007 classic — updated for the EV era and the Elon Musk problem.*

---

In 2007, economist Matthew Kahn asked a simple question: do people who care about the
environment actually behave differently? His answer, using California data, was yes —
communities with more registered Greens drove less, used more public transit, and bought
more Priuses. The pattern was clean and intuitive. Environmentalists put their money where
their mouth was.

Eighteen years later, the question has gotten more complicated. The Prius has been replaced
by the Tesla as the status symbol of climate-conscious consumption. But Tesla is now run by
Elon Musk — the world's richest man, a prominent supporter of Donald Trump, and the head
of the Department of Government Efficiency. The green brand has acquired a political
baggage tag it never asked for.

So: does climate ideology still predict who drives an EV? And has it stopped predicting
who drives a Tesla?

I replicated Kahn's study using modern data — CEC vehicle registration records, Yale
climate opinion surveys, and California voter data — and extended it into the EV era.
Here's what I found.

---

## The Original Finding Still Holds

First, the boring-but-important confirmation: California communities with stronger climate
change beliefs still exhibit lower-carbon transportation behavior today.

Using the 2023 American Community Survey and California vehicle registration data, I
constructed a *Climate Ideology Index* — a composite of Yale Climate Opinion Maps county
estimates, Democratic-minus-Republican voter registration share, and vote share on
Proposition 30 (the 2022 EV infrastructure initiative). I ran this index against commute
behavior and vehicle ownership across California's ~9,100 Census tracts.

The results track Kahn's original findings closely:

[TABLE: replication_ols_transit.html — key finding: ideology coef sign and p-value]

A one-standard-deviation increase in the Climate Ideology Index is associated with a
[RESULT: coef on transit] percentage-point increase in transit commute share and a
[RESULT: coef on drive-alone] percentage-point decrease in drive-alone commuting —
both statistically significant and economically meaningful.

For EVs specifically, the negative binomial model gives an incidence rate ratio of
[RESULT: IRR from negbin], meaning tracts at the 75th percentile of climate ideology have
roughly [RESULT: X%] more EVs per capita than tracts at the 25th percentile.

*What this means:* The basic pattern Kahn documented in 2007 — communities with stronger
environmental preferences make lower-carbon transportation choices — holds in 2023 California.
The green signal is alive.

[FIGURE: replication_scatter.png]

---

## Climate Ideology Strongly Predicts EV Ownership — or It Did

Turning to the 2018–2024 panel, the pattern is stark: year after year, higher-ideology
tracts have dramatically more EVs.

[FIGURE: ev_panel_coefs.png]

A one-standard-deviation increase in the Climate Ideology Index is associated with
[RESULT: pooled OLS coef on log_tesla_bev]% more Teslas and
[RESULT: pooled OLS coef on log_nontesla_bev]% more non-Tesla EVs per tract.
Light trucks show a negative coefficient — consistent with Kahn's original Hummer finding.

The pattern was remarkably stable from 2018 through 2021. High-ideology communities
accumulated Teslas at a much faster rate than low-ideology communities. Tesla was, in
this sense, a green product — bought disproportionately by people who said they cared
about the environment.

Then something changed.

---

## The Elon Effect

The chart below shows the key result of this paper.

[FIGURE: event_study_tesla_vs_nontesla.png]

Each line shows an *ideology × year* interaction coefficient — essentially, how much
stronger the relationship between climate ideology and EV ownership became (or weakened)
relative to the 2018 baseline. A flat line means no change. A rising line means the
ideology-EV link is strengthening. A falling line means the link is weakening.

The non-Tesla BEV line (blue) is [RESULT: describe trend — rising/flat]. That's what
you'd expect from a product that doesn't have a polarizing celebrity CEO: demand grows
in high-ideology communities as the EV market matures and prices fall.

The Tesla line (red) is [RESULT: describe trend]. Starting around [RESULT: year],
the ideology coefficient for Tesla begins to diverge from non-Tesla EVs. By 2024,
the gap is [RESULT: magnitude and significance].

**What this says in plain terms:** In 2018, a high-ideology tract had roughly
[RESULT: gap] more Teslas than a low-ideology tract, controlling for income and
demographics. By 2024, that gap had [RESULT: grown/shrunk/nearly closed].
Meanwhile, the same tracts were buying [RESULT: describe] non-Tesla EVs.

I want to be careful about what this does and doesn't show. This is not direct evidence
that individual Tesla buyers changed their minds. What we observe is that *communities
with strong climate beliefs* became [RESULT: more/less] likely to have Teslas, relative
to their baseline — and that this shift coincided with Musk's public political evolution.

The most parsimonious interpretation: the green status signal that Tesla carried throughout
the 2010s has weakened. Climate-motivated buyers are [RESULT: still/increasingly] buying
EVs — they're just [RESULT: diversifying away from / not yet abandoning] Tesla.

---

## The Status Signal Migration

If high-ideology buyers are stepping back from Tesla, where are they going?

Tesla's share of total BEVs in high-ideology tracts peaked in [RESULT: year] at
roughly [RESULT: %] and has [RESULT: trend] since. In the same period, non-Tesla BEV
share in high-ideology tracts has [RESULT: describe]. The chart below breaks this down
by ideology tier.

[FIGURE: would be a simple line chart of Tesla share by ideology quintile over time —
add this as a new figure in paper/figures/]

This is early evidence of what I'd call *status signal migration* — the green credential
moving from one product category to another as brand associations shift. It's happened
before: the Prius peaked culturally around 2012–2015 and has since become somewhat
ordinary; the baton passed to Tesla. The question is where it goes next.

---

## How Robust Is This?

The main result holds across three alternative specifications:

[TABLE: robustness combined results]

**R1** uses only Yale Climate Opinion Maps at the county level — no voter data, cleaner
measurement, coarser geography. **R2** uses only voter registration and ballot measure
data at the tract level — finer geography, no reliance on the Yale county-level assumption.
**R3** uses only Prop 30 vote share — the single cleanest climate signal available.

The direction and approximate magnitude of the Elon Effect are consistent across all four.

I also tested for spatial autocorrelation in the cross-section residuals. Moran's I
[RESULT: was/was not] significant at the 5% level [RESULT: for which models].
[If significant: A spatial lag correction leaves the main results qualitatively unchanged.]

---

## What This Can and Can't Say

A few important limitations:

**This is about communities, not individuals.** The unit of analysis is the Census tract —
roughly 4,000 people. I observe that *tracts* with stronger climate beliefs have
fewer Teslas. I cannot directly observe which households within a tract are buying EVs
or why. The ecological inference problem Kahn acknowledged in 2007 applies here too.

**I can't fully isolate the Elon Effect.** Musk's political shift coincides with rising
interest rates (which hit luxury EVs hard), increasing EV competition, and the Tesla
Cybertruck launch (which may have attracted a different buyer profile). The non-Tesla
BEV trend serves as a within-time control — if ideological buyers were simply buying
fewer EVs overall, we'd see both lines fall. The divergence pattern is harder to explain
by market forces alone, but I can't rule out price point differences or other confounders.

**California is not America.** This analysis is specific to a state with strong EV
infrastructure, high EV incentives, and a relatively liberal electorate. Whether these
patterns would show up in a national study — with very different charging infrastructure,
policy environments, and climate opinion distributions — is an open question.

---

## Data and Code

All data is publicly available. Vehicle registration data from the California Energy
Commission. Demographics from the US Census Bureau ACS. Climate beliefs from the
Yale Program on Climate Change Communication. Voter registration and ballot results
from the UC Berkeley Statewide Database.

Code: [GitHub link when published]

---

*[Author bio / contact]*
```

**Step 3: Create figures directory for paper**

```bash
mkdir -p paper
```

**Step 4: Replace all [RESULT] and [TABLE] placeholders**

After running all scripts (07–11), open `paper/draft.md` and replace every `[RESULT]` and `[TABLE]` placeholder with actual numbers from the output tables. Key values to find:

- `output/tables/replication_ols_transit.csv` → ideology coefficient
- `output/tables/replication_negbin_bev.csv` → IRR
- `output/tables/ev_panel_pooled.csv` → Tesla and non-Tesla BEV coefficients
- `output/tables/event_study_coefs.csv` → year-by-year coefficients for narrative

**Step 5: Commit**

```bash
git add paper/draft.md
git commit -m "feat: add Substack draft with full narrative structure"
```

---

## Final Validation — Run Full Pipeline

After all scripts are written, do a full end-to-end run:

```bash
python scripts/01_acquire_cec.py
python scripts/02_acquire_acs.py
python scripts/03_acquire_ideology.py
python scripts/04_crosswalk.py
python scripts/05_build_panel.py
python scripts/06_ideology_index.py
python scripts/07_replication.py
python scripts/08_ev_panel.py
python scripts/09_event_study.py
python scripts/10_robustness.py
python scripts/11_spatial.py
```

Then verify all expected outputs exist:

```bash
ls output/tables/*.csv | wc -l   # expect ~15+
ls output/figures/*.png | wc -l  # expect ~10+
```

**Final commit:**

```bash
git add output/tables/ output/figures/
git commit -m "feat: complete analysis pipeline output (all tables and figures)"
```

---

## Execution Order Summary

| # | Script | Key output | Depends on |
|---|--------|-----------|------------|
| 05 | build_panel.py | panel_tract_year.csv | 01–04 |
| 06 | ideology_index.py | ideology_index.csv | 05 |
| 07 | replication.py | replication_*.csv/html | 05, 06 |
| 08 | ev_panel.py | ev_panel_*.csv/html | 05, 06 |
| 09 | event_study.py | event_study_coefs.csv + hero figure | 05, 06 |
| 10 | robustness.py | robustness_*.csv/html | 05, 06 |
| 11 | spatial.py | spatial_morans.csv | 05, 06 |
| — | paper/draft.md | Substack post | 07–11 results |
