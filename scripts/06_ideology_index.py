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
  output/figures/ideology_lcv_validation.png  — LCV validation scatter (if LCV scrape succeeds)
"""

import io
import warnings
import zipfile
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
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

    # Use 2023 cross-section — ideology is time-invariant, any year gives same values
    available_vars = [v for v in IDEOLOGY_VARS if v in panel.columns]
    missing_vars = [v for v in IDEOLOGY_VARS if v not in panel.columns]
    if missing_vars:
        print(f"    WARNING: ideology vars not found in panel: {missing_vars}")
    if not available_vars:
        raise ValueError("No ideology variables found in panel — check 05_build_panel.py output")

    cs = (
        panel[panel["data_year"] == 2023][["tract_geoid_20"] + available_vars]
        .drop_duplicates("tract_geoid_20")
        .copy()
    )

    n_before = len(cs)
    cs = cs.dropna(subset=available_vars)
    n_after = len(cs)
    print(f"    Dropped {n_before - n_after} tracts with missing ideology data "
          f"({(n_before - n_after) / n_before * 100:.1f}%)")
    print(f"    PCA input: {n_after:,} tracts × {len(available_vars)} variables")

    scaler = StandardScaler()
    X = scaler.fit_transform(cs[available_vars])

    pca = PCA(n_components=len(available_vars))
    scores = pca.fit_transform(X)
    pc1 = scores[:, 0]

    # Normalize sign: higher PC1 = more climate-concerned
    # Check using dem_minus_rep (should be positively correlated with index)
    if "dem_minus_rep" in available_vars:
        dem_idx = available_vars.index("dem_minus_rep")
        if pca.components_[0, dem_idx] < 0:
            pc1 = -pc1
            pca.components_[0] = -pca.components_[0]
            print("    NOTE: Flipped PC1 sign so higher = more climate-concerned")

    cs["climate_ideology_index"] = pc1

    explained = pca.explained_variance_ratio_
    print(f"    PC1 variance explained: {explained[0]*100:.1f}%")
    print(f"    PC1+PC2 cumulative:     {sum(explained[:2])*100:.1f}%")

    # Save loadings
    loadings = pd.DataFrame({
        "variable": available_vars,
        "loading_pc1": pca.components_[0],
        "loading_pc2": pca.components_[1] if len(available_vars) > 1 else np.nan,
        "variance_explained_pc1": explained[0],
    })
    loadings.to_csv(TABLES / "pca_loadings.csv", index=False)
    print(f"\n    PCA loadings (PC1):")
    for _, row in loadings.iterrows():
        print(f"      {row['variable']:25s} {row['loading_pc1']:+.3f}")

    # Scree plot
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(range(1, len(explained) + 1), explained * 100, color="#2563eb", alpha=0.8)
    ax.plot(range(1, len(explained) + 1), np.cumsum(explained) * 100,
            color="red", marker="o", linewidth=1.5, markersize=5, label="Cumulative %")
    ax.axhline(100 / len(available_vars), color="gray", linestyle="--", alpha=0.6,
               label=f"Random chance ({100/len(available_vars):.0f}%)")
    ax.set_xlabel("Principal Component")
    ax.set_ylabel("Variance Explained (%)")
    ax.set_title("PCA Scree Plot — Climate Ideology Variables")
    ax.legend(fontsize=9)
    plt.tight_layout()
    fig.savefig(FIGURES / "pca_scree.png", dpi=300)
    plt.close()
    print(f"    Scree plot → output/figures/pca_scree.png")

    # Return tract-level index
    contrib_cols = []
    for i, var in enumerate(available_vars):
        col = f"pc1_contrib_{var}"
        cs[col] = X[:, i] * pca.components_[0, i]
        contrib_cols.append(col)

    return cs[["tract_geoid_20", "climate_ideology_index"] + contrib_cols].copy()


# ── LCV Validation ────────────────────────────────────────────────────────────

LCV_URL = "https://scorecard.lcv.org/members/2023"


def fetch_lcv_scores() -> pd.DataFrame:
    """Scrape LCV annual scores for CA Congressional members (118th Congress, 2023)."""
    print("\n  Fetching LCV scores from scorecard.lcv.org...")
    try:
        resp = requests.get(LCV_URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        # Try to find a table with member data
        tables = soup.find_all("table")
        if not tables:
            # Try looking for structured rows
            print("    No <table> tags found — trying row-based parsing")
            rows = soup.select("tr")
        else:
            rows = tables[0].find_all("tr")

        if not rows:
            print("    WARNING: No table rows found — LCV page structure may have changed")
            return pd.DataFrame()

        parsed = []
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if cells:
                parsed.append(cells)

        if len(parsed) < 2:
            print("    WARNING: Parsed fewer than 2 rows from LCV page")
            return pd.DataFrame()

        # Build DataFrame from parsed rows — normalize column count
        max_cols = max(len(r) for r in parsed)
        padded = [r + [""] * (max_cols - len(r)) for r in parsed]
        df = pd.DataFrame(padded[1:], columns=padded[0])

        # Detect state column
        state_col = next(
            (c for c in df.columns if "state" in str(c).lower()),
            None
        )
        if state_col is None:
            # Try to detect by content — look for column containing "CA" values
            for col in df.columns:
                if (df[col].str.upper().str.strip() == "CA").sum() > 5:
                    state_col = col
                    break

        if state_col is None:
            print(f"    WARNING: Cannot identify state column. Columns: {list(df.columns[:8])}")
            return pd.DataFrame()

        ca_df = df[df[state_col].str.upper().str.strip() == "CA"].copy()
        print(f"    Found {len(ca_df)} CA members")

        # Detect score column
        score_col = next(
            (c for c in df.columns if "score" in str(c).lower()
             or "lifetime" in str(c).lower() or "2023" in str(c)),
            None
        )
        # Detect district column
        dist_col = next(
            (c for c in df.columns if "district" in str(c).lower()
             or "dist" in str(c).lower()),
            None
        )

        result_rows = []
        for _, row in ca_df.iterrows():
            dist_num = None
            score = None
            if dist_col:
                import re as _re
                dist_num = pd.to_numeric(
                    _re.sub(r"^CA-0*", "", str(row[dist_col]).strip()) or "0",
                    errors="coerce"
                )
            if score_col:
                score = pd.to_numeric(
                    str(row[score_col]).replace("%", "").strip(),
                    errors="coerce"
                )
            result_rows.append({"district_num": dist_num, "lcv_score": score})

        result = pd.DataFrame(result_rows).dropna()
        print(f"    Parsed {len(result)} CA members with district + score")

        result.to_csv(TABLES / "lcv_scores_ca.csv", index=False)
        return result

    except requests.RequestException as e:
        print(f"    WARNING: LCV request failed: {e}")
        print("    Skipping LCV validation. To validate manually:")
        print("    1. Download scores from https://scorecard.lcv.org/")
        print(f"    2. Save as {TABLES}/lcv_scores_ca.csv with columns: district_num, lcv_score")
        return pd.DataFrame()
    except Exception as e:
        print(f"    WARNING: LCV parsing failed: {e}")
        return pd.DataFrame()


def build_cd_tract_crosswalk() -> pd.DataFrame:
    """Download 118th Congress CA district shapefile; assign each tract centroid to a district."""
    CD_URL = "https://www2.census.gov/geo/tiger/TIGER2023/CD/tl_2023_06_cd118.zip"
    TRACT_SHP = RAW / "shapefiles" / "tl_2020_06_tract"

    cd_dir = RAW / "shapefiles" / "tl_2023_06_cd118"
    if not cd_dir.exists() or not any(cd_dir.glob("*.shp")):
        cd_dir.mkdir(parents=True, exist_ok=True)
        print("    Downloading 118th Congress CA district shapefile...")
        resp = requests.get(CD_URL, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            zf.extractall(cd_dir)
        print(f"    Extracted to {cd_dir}")

    shp_files = list(cd_dir.glob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"No .shp found in {cd_dir}")

    cd = gpd.read_file(shp_files[0]).to_crs("EPSG:3310")

    tract_shp_files = list(TRACT_SHP.glob("*.shp")) if TRACT_SHP.exists() else []
    if not tract_shp_files:
        raise FileNotFoundError(f"Tract shapefile not found at {TRACT_SHP} — run script 04 first")

    tracts = gpd.read_file(tract_shp_files[0]).to_crs("EPSG:3310")
    geoid_col = next(c for c in tracts.columns if c.upper() == "GEOID")

    # Assign each tract centroid to a Congressional district
    tracts = tracts[[geoid_col, "geometry"]].copy()
    tracts["centroid_geom"] = tracts.geometry.centroid
    tracts_pt = tracts.set_geometry("centroid_geom").drop(columns=["geometry"])

    # Find district column in CD shapefile
    cd_num_col = next(
        (c for c in cd.columns if "CD" in c.upper() and "FP" in c.upper()),
        cd.columns[0]
    )
    joined = gpd.sjoin(tracts_pt, cd[[cd_num_col, "geometry"]], how="left", predicate="within")

    result = pd.DataFrame({
        "tract_geoid_20": joined[geoid_col].values,
        "district_num": pd.to_numeric(joined[cd_num_col], errors="coerce"),
    }).dropna(subset=["district_num"])
    result["district_num"] = result["district_num"].astype(int)
    print(f"    CD→tract crosswalk: {len(result):,} tracts assigned to {result['district_num'].nunique()} districts")
    return result


def validate_against_lcv(index_df: pd.DataFrame):
    """Aggregate ideology index to Congressional district; regress on LCV scores."""
    print("\n  Validating ideology index against LCV scores...")

    lcv = fetch_lcv_scores()
    if lcv.empty:
        print("    Skipping LCV validation (no data available)")
        return

    cd_tract_path = PROCESSED / "crosswalk_cd_tract.csv"
    if not cd_tract_path.exists():
        print("    Building CD→tract crosswalk...")
        try:
            cd_tract = build_cd_tract_crosswalk()
            cd_tract.to_csv(cd_tract_path, index=False)
        except Exception as e:
            print(f"    WARNING: CD crosswalk failed: {e}")
            print("    Skipping LCV validation")
            return

    cd_tract = pd.read_csv(cd_tract_path, dtype={"tract_geoid_20": str})
    merged = index_df[["tract_geoid_20", "climate_ideology_index"]].merge(
        cd_tract, on="tract_geoid_20", how="inner"
    )
    if merged.empty:
        print("    WARNING: CD-tract merge produced no matches — skipping LCV validation")
        return

    district_avg = (
        merged.groupby("district_num")["climate_ideology_index"]
        .mean()
        .reset_index()
        .rename(columns={"climate_ideology_index": "mean_ideology"})
    )
    val = district_avg.merge(lcv, on="district_num", how="inner")

    if len(val) < 5:
        print(f"    WARNING: Only {len(val)} districts matched LCV data — skipping regression")
        return

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = smf.ols("lcv_score ~ mean_ideology", data=val).fit()

    print(f"    LCV validation: N={len(val)} districts, R²={result.rsquared:.3f}, "
          f"ideology coef={result.params['mean_ideology']:.2f} "
          f"(p={result.pvalues['mean_ideology']:.3f})")

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(val["mean_ideology"], val["lcv_score"], alpha=0.7, color="#2563eb", s=50)
    xr = np.linspace(val["mean_ideology"].min(), val["mean_ideology"].max(), 100)
    yr = result.params["Intercept"] + result.params["mean_ideology"] * xr
    ax.plot(xr, yr, color="red", lw=1.5, label=f"R²={result.rsquared:.2f}")
    ax.set_xlabel("Mean Climate Ideology Index (district average)")
    ax.set_ylabel("LCV Score (2023)")
    ax.set_title("Ideology Index Validation\nCA Congressional Districts vs LCV Scores")
    ax.legend()
    plt.tight_layout()
    fig.savefig(FIGURES / "ideology_lcv_validation.png", dpi=300)
    plt.close()
    print("    Validation scatter → output/figures/ideology_lcv_validation.png")


# ── Choropleth map ────────────────────────────────────────────────────────────

def make_ideology_map(index_df: pd.DataFrame):
    """Choropleth of climate_ideology_index across CA Census tracts."""
    print("\n  Building ideology choropleth map...")
    tract_shp = RAW / "shapefiles" / "tl_2020_06_tract"
    shp_files = list(tract_shp.glob("*.shp")) if tract_shp.exists() else []
    if not shp_files:
        print("    WARNING: tract shapefile not found — skipping map (run script 04 first)")
        return

    tracts = gpd.read_file(shp_files[0])
    geoid_col = next(c for c in tracts.columns if c.upper() == "GEOID")
    tracts = tracts.rename(columns={geoid_col: "tract_geoid_20"})
    tracts = tracts.merge(
        index_df[["tract_geoid_20", "climate_ideology_index"]],
        on="tract_geoid_20", how="left"
    )

    fig, ax = plt.subplots(1, 1, figsize=(8, 10))
    tracts.plot(
        column="climate_ideology_index",
        cmap="RdBu",
        linewidth=0,
        ax=ax,
        legend=True,
        missing_kwds={"color": "lightgrey", "label": "No data"},
        legend_kwds={"label": "Climate Ideology Index (PC1)", "shrink": 0.6},
    )
    ax.set_axis_off()
    ax.set_title("Climate Ideology Index\nCalifornia Census Tracts (2020 boundaries)", fontsize=12)
    plt.tight_layout()
    fig.savefig(FIGURES / "ideology_map.png", dpi=300)
    plt.close()
    print("    Map → output/figures/ideology_map.png")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=== 06_ideology_index.py ===\n")

    panel_path = PROCESSED / "panel_tract_year.csv"
    if not panel_path.exists():
        print(f"ERROR: {panel_path} not found — run 05_build_panel.py first")
        return

    panel = pd.read_csv(panel_path, dtype={"tract_geoid_20": str})
    print(f"  Panel loaded: {len(panel):,} rows, {panel['tract_geoid_20'].nunique():,} tracts")

    index_df = build_ideology_index(panel)

    out_path = PROCESSED / "ideology_index.csv"
    index_df.to_csv(out_path, index=False)
    print(f"\n  Ideology index saved → {out_path}")
    print(f"  Tracts with index: {len(index_df):,}")
    print(f"  Index range: [{index_df['climate_ideology_index'].min():.2f}, "
          f"{index_df['climate_ideology_index'].max():.2f}]")

    validate_against_lcv(index_df)
    make_ideology_map(index_df)

    print("\nDone. Next: run 07_replication.py")


if __name__ == "__main__":
    main()
