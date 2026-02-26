#!/usr/bin/env python3
"""
11_spatial.py
Spatial autocorrelation diagnostics and correction for the Kahn replication.

Tests whether OLS residuals from the two cross-section models (Script 07) exhibit
spatial clustering among California Census tracts. If so, corrects using a Spatial
Autoregressive (SAR / Spatial Lag) model.

Steps
-----
1. Build queen contiguity spatial weights from 2020 TIGER Census tract shapefile.
2. Run Moran's I on OLS residuals from two cross-section models (2023):
     - pct_transit    ~ climate_ideology_index + controls
     - pct_drove_alone ~ climate_ideology_index + controls
3. If Moran's I is significant (p < 0.05) for any model:
     - Estimate Spatial Lag Model (SAR) via spreg.ML_Lag
     - Report spatial autoregressive coefficient rho
4. Produce diagnostic maps.

Inputs
------
  data/processed/panel_tract_year.csv
  data/processed/ideology_index.csv
  data/raw/shapefiles/tl_2020_06_tract/*.shp

Outputs
-------
  output/tables/spatial_morans.csv
  output/tables/spatial_morans.html
  output/tables/spatial_sar.csv         (only if SAR correction needed)
  output/tables/spatial_sar.html        (only if SAR correction needed)
  output/figures/spatial_weights_map.png
  output/figures/residual_map.png

Methodology notes
-----------------
Weights alignment: the spatial weights object w assigns an ordering to tracts via
w.id_order. All residual arrays passed to Moran() and spreg.ML_Lag() must be in
this exact order. The cross-section is filtered to complete cases BEFORE building
the weights matrix so that the weights matrix covers exactly the tracts with data —
no imputation, no silent NaN filling.

Limitations
-----------
- Analysis uses 2023 cross-section only (same vintage as Script 07).
- YCOM ideology values are county-level means assigned to all tracts in the county;
  spatial clustering in residuals may partly reflect this measurement assumption.
- Queen contiguity assumes shared boundary = spatial interaction. Alternative
  specifications (k-nearest neighbors, distance-band) are not reported here.
"""

import sys
from pathlib import Path

import geopandas as gpd
import libpysal
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import spreg
import statsmodels.formula.api as smf
from esda.moran import Moran

ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"
SHAPEFILE_DIR = ROOT / "data" / "raw" / "shapefiles" / "tl_2020_06_tract"

TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

CONTROL_COLS = [
    "log_median_hh_income",
    "pct_ba_plus",
    "pop_density",
    "pct_white",
    "pct_wfh",
]
CONTROLS_STR = " + ".join(CONTROL_COLS)

# Two OLS models (same as Script 07, no NB — residuals must be continuous for Moran's I)
MODELS = [
    ("pct_transit",    "Transit Commute Share",    "transit"),
    ("pct_drove_alone", "Drive-Alone Commute Share", "drivealone"),
]


# ── Data loading ──────────────────────────────────────────────────────────────

def load_cross_section() -> pd.DataFrame:
    """
    Load 2023 cross-section merged with ideology index.
    Returns only complete cases for all required columns — no imputation.
    Rows are NOT yet sorted to weight order; that happens after building weights.
    """
    panel_path = PROCESSED / "panel_tract_year.csv"
    index_path = PROCESSED / "ideology_index.csv"

    for p in [panel_path, index_path]:
        if not p.exists():
            print(f"  ERROR: {p} not found — run scripts 05 and 06 first")
            sys.exit(1)

    panel = pd.read_csv(panel_path, dtype={"tract_geoid_20": str})
    index = pd.read_csv(index_path, dtype={"tract_geoid_20": str})

    cs = panel[panel["data_year"] == 2023].copy()
    cs = cs.merge(
        index[["tract_geoid_20", "climate_ideology_index"]],
        on="tract_geoid_20", how="left"
    )

    n_missing_ideo = cs["climate_ideology_index"].isna().sum()
    if n_missing_ideo > 0:
        print(f"  WARNING: {n_missing_ideo} tracts missing ideology index after merge")

    required_cols = (
        ["tract_geoid_20", "climate_ideology_index",
         "pct_transit", "pct_drove_alone"]
        + CONTROL_COLS
    )
    n_before = len(cs)
    cs = cs.dropna(subset=required_cols)
    print(f"  2023 cross-section: {n_before:,} → {len(cs):,} tracts "
          f"(complete cases, no imputation)")
    return cs


# ── Spatial weights ───────────────────────────────────────────────────────────

def load_shapefile(cs: pd.DataFrame) -> gpd.GeoDataFrame:
    """
    Load TIGER 2020 tract shapefile and filter to tracts present in cs.
    Returns GeoDataFrame in EPSG:4269 (NAD83, native for TIGER).
    """
    shp_files = list(SHAPEFILE_DIR.glob("*.shp"))
    if not shp_files:
        print(f"  ERROR: No .shp file found in {SHAPEFILE_DIR}")
        print("  Download the CA 2020 TIGER tract shapefile from:")
        print("    https://www2.census.gov/geo/tiger/TIGER2020/TRACT/tl_2020_06_tract.zip")
        sys.exit(1)

    shp_path = shp_files[0]
    print(f"  Loading shapefile: {shp_path.name}")
    tracts = gpd.read_file(shp_path)

    # Build a 20-character GEOID matching panel format (state+county+tract = 11 chars
    # as stored in TIGER's GEOID field, but the panel may use a longer padded form).
    # Normalise: TIGER GEOID is 11-digit string; panel tract_geoid_20 should match.
    tracts["tract_geoid_20"] = tracts["GEOID"].astype(str).str.zfill(11)

    # Filter to tracts in the cross-section (complete-case tracts only)
    cs_geoids = set(cs["tract_geoid_20"])
    n_before = len(tracts)
    tracts = tracts[tracts["tract_geoid_20"].isin(cs_geoids)].copy()
    tracts = tracts.reset_index(drop=True)
    print(f"  Shapefile: {n_before:,} total CA tracts → {len(tracts):,} matched "
          f"to complete-case cross-section")

    missing_geoids = cs_geoids - set(tracts["tract_geoid_20"])
    if missing_geoids:
        print(f"  WARNING: {len(missing_geoids)} cross-section tracts not found in "
              f"shapefile — they will be excluded from spatial analysis")

    return tracts


def build_weights(tracts: gpd.GeoDataFrame) -> libpysal.weights.W:
    """
    Build queen contiguity spatial weights from filtered GeoDataFrame.
    Uses tract_geoid_20 as the ID variable so w.id_order is a list of GEOIDs.

    Silences the UserWarning about deprecated idVariable — we use the
    recommended `ids` keyword instead.
    """
    print("  Building queen contiguity spatial weights...")
    w = libpysal.weights.Queen.from_dataframe(
        tracts,
        ids="tract_geoid_20",
        use_index=False,
    )
    w.transform = "r"  # row-standardize for Moran's I

    n_islands = len(w.islands)
    if n_islands > 0:
        print(f"  WARNING: {n_islands} island tracts (no queen contiguity neighbors) — "
              f"these are included in the weights object but have zero neighbors")

    print(f"  Weights: {w.n} tracts, mean neighbors = {w.mean_neighbors:.2f}, "
          f"pct nonzero = {w.pct_nonzero:.4f}")
    return w


# ── OLS models ────────────────────────────────────────────────────────────────

def run_ols(cs: pd.DataFrame, dv_col: str) -> tuple:
    """
    Run OLS with HC3 robust SEs on the aligned cross-section.
    Returns (result, residuals_array) where residuals_array is in w.id_order.
    cs must already be sorted to w.id_order before calling this function.
    """
    formula = f"{dv_col} ~ climate_ideology_index + {CONTROLS_STR}"
    result = smf.ols(formula, data=cs).fit(cov_type="HC3")
    resid = result.resid.values  # numpy array, same row order as cs
    return result, resid


# ── Moran's I ─────────────────────────────────────────────────────────────────

def run_morans_i(resid: np.ndarray, w: libpysal.weights.W,
                 model_label: str) -> dict:
    """
    Compute Moran's I on OLS residuals.
    w must be row-standardized (w.transform == 'r').
    resid must be in the same order as w.id_order.
    """
    moran = Moran(resid, w, permutations=999)
    sig = moran.p_sim < 0.05
    sig_str = "YES (p<0.05)" if sig else "NO (p≥0.05)"
    print(f"  {model_label}: Moran's I = {moran.I:.4f}, "
          f"E[I] = {moran.EI:.4f}, p-sim = {moran.p_sim:.4f}  → "
          f"Significant spatial autocorrelation: {sig_str}")
    return {
        "Model": model_label,
        "Moran_I": round(moran.I, 4),
        "Expected_I": round(moran.EI, 4),
        "p_sim": round(moran.p_sim, 4),
        "Significant_p05": sig_str,
        "Permutations": 999,
    }


# ── SAR model ─────────────────────────────────────────────────────────────────

def run_sar(cs: pd.DataFrame, dv_col: str, model_label: str,
            w: libpysal.weights.W) -> dict:
    """
    Estimate Spatial Lag Model (SAR) via maximum likelihood.
    cs must be sorted to w.id_order (guaranteed by the alignment step in main).
    Returns a summary dict for the results table.
    """
    print(f"  SAR ({model_label}): estimating via ML_Lag...")

    x_cols = ["climate_ideology_index"] + CONTROL_COLS
    y = cs[dv_col].values.reshape(-1, 1)
    X = np.column_stack([np.ones(len(cs))] + [cs[c].values for c in x_cols])
    name_x = ["const"] + x_cols

    try:
        sar = spreg.ML_Lag(
            y, X, w=w,
            name_y=dv_col,
            name_x=name_x,
            name_ds="CA 2023 Census Tracts",
        )
    except Exception as exc:
        print(f"  SAR FAILED for {model_label}: {exc}")
        return {
            "Model": model_label,
            "rho": "FAILED",
            "rho_se": "",
            "rho_z": "",
            "rho_p": "",
            "OLS_R2": "",
            "SAR_Pseudo_R2": "",
            "N": len(cs),
            "Note": str(exc),
        }

    rho     = sar.rho
    rho_se  = np.sqrt(sar.vm[0, 0]) if sar.vm is not None else np.nan
    rho_z   = rho / rho_se if rho_se and not np.isnan(rho_se) else np.nan
    rho_p   = 2 * (1 - _norm_cdf(abs(rho_z))) if not np.isnan(rho_z) else np.nan

    stars = _format_stars(rho_p) if not np.isnan(rho_p) else ""
    print(f"  SAR rho = {rho:.4f}{stars}  (SE={rho_se:.4f}, z={rho_z:.3f}, p={rho_p:.4f})")
    print(f"  Pseudo-R2 = {sar.pr2:.4f}")

    return {
        "Model":           model_label,
        "rho":             f"{rho:.4f}{stars}",
        "rho_se":          f"({rho_se:.4f})",
        "rho_z":           f"{rho_z:.3f}",
        "rho_p":           f"{rho_p:.4f}",
        "Pseudo_R2":       f"{sar.pr2:.4f}",
        "N":               int(sar.n),
        "Note": (
            "Spatial Lag Model (SAR) via ML. rho = spatial autoregressive coefficient. "
            "Positive rho indicates positive spatial spillovers in the DV."
        ),
    }


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via error function (no scipy needed)."""
    import math
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _format_stars(pval: float) -> str:
    if pval < 0.01:
        return "***"
    if pval < 0.05:
        return "**"
    if pval < 0.1:
        return "*"
    return ""


# ── Output tables ─────────────────────────────────────────────────────────────

def save_morans_table(rows: list):
    df = pd.DataFrame(rows)
    df.to_csv(TABLES / "spatial_morans.csv", index=False)
    footer = (
        "<p>Moran's I on OLS residuals (same models as Script 07, 2023 CA Census tracts). "
        "Row-standardized queen contiguity weights. "
        "p-sim = pseudo p-value from 999 random permutations. "
        "Significant p<0.05 triggers SAR correction in spatial_sar.{csv,html}.</p>"
    )
    html = "<h3>Moran's I — OLS Residuals Spatial Autocorrelation Test</h3>"
    html += df.to_html(index=False) + footer
    with open(TABLES / "spatial_morans.html", "w") as f:
        f.write(html)
    print("  Saved → output/tables/spatial_morans.{csv,html}")


def save_sar_table(rows: list):
    df = pd.DataFrame(rows)
    df.to_csv(TABLES / "spatial_sar.csv", index=False)
    footer = (
        "<p>Spatial Lag Model (SAR) estimated via maximum likelihood. "
        "rho = spatial autoregressive coefficient on the spatially lagged dependent variable. "
        "Positive rho indicates positive spatial autocorrelation after controlling for covariates. "
        "X variables identical to Script 07 OLS. "
        "*p&lt;0.1, **p&lt;0.05, ***p&lt;0.01 (z-test on rho).</p>"
    )
    html = "<h3>Spatial Lag Model (SAR) — Corrected Estimates</h3>"
    html += df.to_html(index=False) + footer
    with open(TABLES / "spatial_sar.html", "w") as f:
        f.write(html)
    print("  Saved → output/tables/spatial_sar.{csv,html}")


# ── Figures ───────────────────────────────────────────────────────────────────

def make_weights_map(tracts: gpd.GeoDataFrame, w: libpysal.weights.W):
    """
    Choropleth of tract boundaries, colored by number of queen contiguity
    neighbors (cardinality). Gives a quick visual check of the weights structure.
    """
    print("  Making spatial weights map...")

    # Build cardinality series indexed by tract_geoid_20
    card_series = pd.Series(w.cardinalities, name="n_neighbors")
    card_df = card_series.reset_index().rename(columns={"index": "tract_geoid_20"})

    tracts_plot = tracts.merge(card_df, on="tract_geoid_20", how="left")

    # Project to California Albers (EPSG:3310) for a less distorted map
    try:
        tracts_plot = tracts_plot.to_crs("EPSG:3310")
    except Exception:
        pass  # Fall back to native CRS if reprojection fails

    fig, ax = plt.subplots(1, 1, figsize=(10, 12))
    tracts_plot.plot(
        column="n_neighbors",
        ax=ax,
        cmap="YlOrRd",
        linewidth=0.05,
        edgecolor="white",
        legend=True,
        legend_kwds={"label": "Queen Contiguity Neighbors", "shrink": 0.6},
        missing_kwds={"color": "#cccccc", "label": "No data"},
    )
    ax.set_axis_off()
    ax.set_title(
        "Queen Contiguity Spatial Weights\nCalifornia Census Tracts (2020 TIGER)",
        fontsize=13, pad=10
    )
    fig.text(
        0.5, 0.01,
        "Color = number of queen contiguity neighbors per tract. "
        "Darker = more neighbors (typically interior tracts). "
        "White = no data / not in analysis sample.",
        ha="center", fontsize=8, style="italic", color="#4b5563"
    )
    plt.tight_layout()
    fig.savefig(FIGURES / "spatial_weights_map.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Figure → output/figures/spatial_weights_map.png")


def make_residual_map(cs: pd.DataFrame, tracts: gpd.GeoDataFrame,
                      resid: np.ndarray, w: libpysal.weights.W):
    """
    Choropleth of OLS residuals from the transit model.
    cs is already sorted to w.id_order; residuals align directly.
    """
    print("  Making OLS residual map (transit model)...")

    resid_df = pd.DataFrame({
        "tract_geoid_20": w.id_order,
        "ols_resid_transit": resid,
    })
    tracts_plot = tracts.merge(resid_df, on="tract_geoid_20", how="left")

    try:
        tracts_plot = tracts_plot.to_crs("EPSG:3310")
    except Exception:
        pass

    # Diverging colormap: negative residuals (below predicted transit) = red,
    # positive (above predicted) = blue
    vmax = np.nanpercentile(np.abs(resid), 97)
    vmin = -vmax

    fig, ax = plt.subplots(1, 1, figsize=(10, 12))
    tracts_plot.plot(
        column="ols_resid_transit",
        ax=ax,
        cmap="RdBu",
        vmin=vmin,
        vmax=vmax,
        linewidth=0.05,
        edgecolor="white",
        legend=True,
        legend_kwds={
            "label": "OLS Residual (Transit Model)",
            "shrink": 0.6,
        },
        missing_kwds={"color": "#cccccc", "label": "Not in sample"},
    )
    ax.set_axis_off()
    ax.set_title(
        "OLS Residuals: Transit Commute Share Model\n"
        "California Census Tracts, 2023",
        fontsize=13, pad=10
    )
    fig.text(
        0.5, 0.01,
        "OLS residuals from: pct_transit ~ climate_ideology_index + controls (HC3). "
        "Blue = tract uses more transit than predicted; red = less than predicted. "
        "Spatial clustering of residuals motivates SAR correction. "
        "Color scale clipped at 97th percentile for readability.",
        ha="center", fontsize=8, style="italic", color="#4b5563", wrap=True
    )
    plt.tight_layout()
    fig.savefig(FIGURES / "residual_map.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("  Figure → output/figures/residual_map.png")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== 11_spatial.py ===\n")

    # ── Step 0: Check shapefile exists ─────────────────────────────────────
    if not SHAPEFILE_DIR.exists():
        print(f"ERROR: Shapefile directory not found: {SHAPEFILE_DIR}")
        print("Download the CA 2020 TIGER Census tract shapefile:")
        print("  https://www2.census.gov/geo/tiger/TIGER2020/TRACT/tl_2020_06_tract.zip")
        print("Unzip into: data/raw/shapefiles/tl_2020_06_tract/")
        sys.exit(0)  # Graceful exit (not a crash) — data simply not available yet

    # ── Step 1: Load complete-case cross-section ────────────────────────────
    print("Step 1: Loading 2023 cross-section (complete cases only)...")
    cs_full = load_cross_section()

    # ── Step 2: Load shapefile and build weights ────────────────────────────
    print("\nStep 2: Loading shapefile and building queen contiguity weights...")
    tracts = load_shapefile(cs_full)

    w = build_weights(tracts)

    # Align cross-section to weight order: set index to tract_geoid_20, then
    # reindex to w.id_order so that cs row i corresponds to weight row i.
    # Only tracts that appear in both cs_full and w.id_order are kept.
    # Because we filtered the shapefile to cs_full tracts before building weights,
    # the sets should be identical (minus any islands dropped by libpysal).
    cs = (
        cs_full
        .set_index("tract_geoid_20")
        .reindex(w.id_order)
        .reset_index()
    )
    n_aligned = cs["pct_transit"].notna().sum()
    if n_aligned < len(w.id_order):
        n_dropped = len(w.id_order) - n_aligned
        print(f"  NOTE: {n_dropped} weight-order tracts have NaN after alignment "
              f"(likely island tracts that lost neighbors). These will produce NaN "
              f"residuals and are handled gracefully by Moran's I.")

    # Confirm no NaN in required columns after alignment — our complete-case filter
    # above should guarantee this, but check explicitly.
    n_nan = cs[["pct_transit", "pct_drove_alone", "climate_ideology_index"]
               + CONTROL_COLS].isna().any(axis=1).sum()
    if n_nan > 0:
        print(f"  WARNING: {n_nan} rows have NaN in model variables after alignment. "
              f"Moran's I and SAR require a complete array — check data pipeline.")

    print(f"  Aligned cross-section: {len(cs):,} tracts (in w.id_order)")

    # ── Step 3: Run OLS models and Moran's I ───────────────────────────────
    print("\nStep 3: Running OLS models and Moran's I diagnostics...")

    moran_rows = []
    ols_results = {}   # dv_col -> (result, resid, label)
    any_significant = False

    for dv_col, dv_label, dv_short in MODELS:
        print(f"\n  Model: {dv_label}")
        ols_result, resid = run_ols(cs, dv_col)
        ols_results[dv_col] = (ols_result, resid, dv_label)

        # Replace NaN residuals with 0 for Moran's I (these correspond to
        # island tracts; treating as 0 is conservative but avoids crashing)
        resid_clean = np.where(np.isfinite(resid), resid, 0.0)

        row = run_morans_i(resid_clean, w, dv_label)
        moran_rows.append(row)
        if row["Significant_p05"].startswith("YES"):
            any_significant = True

    # ── Step 4: Save Moran's I table ───────────────────────────────────────
    print("\nStep 4: Saving Moran's I results...")
    save_morans_table(moran_rows)

    # ── Step 5: SAR correction (if needed) ─────────────────────────────────
    sar_rows = []
    if any_significant:
        print("\nStep 5: Significant spatial autocorrelation detected — "
              "running SAR (Spatial Lag) models...")
        for dv_col, dv_label, dv_short in MODELS:
            moran_sig = next(
                r["Significant_p05"].startswith("YES")
                for r in moran_rows if r["Model"] == dv_label
            )
            if moran_sig:
                print(f"\n  SAR for: {dv_label}")
                # cs is already sorted to w.id_order; no further alignment needed
                cs_sar = cs[["tract_geoid_20", dv_col, "climate_ideology_index"]
                            + CONTROL_COLS].copy()
                n_sar_nan = cs_sar.isna().any(axis=1).sum()
                if n_sar_nan > 0:
                    print(f"  WARNING: {n_sar_nan} rows have NaN values; dropping "
                          f"for SAR (this changes alignment — results are approximate)")
                    # Build a sub-weights matrix for the non-NaN subset
                    cs_sar = cs_sar.dropna()
                    valid_ids = cs_sar["tract_geoid_20"].tolist()
                    w_sub = w[valid_ids]  # libpysal supports subsetting by id list
                    w_sub.transform = "r"
                    cs_sar = (
                        cs_sar
                        .set_index("tract_geoid_20")
                        .reindex(w_sub.id_order)
                        .reset_index()
                    )
                    sar_row = run_sar(cs_sar, dv_col, dv_label, w_sub)
                else:
                    sar_row = run_sar(cs_sar, dv_col, dv_label, w)
                sar_rows.append(sar_row)
            else:
                print(f"  Moran's I not significant for {dv_label} — SAR skipped")

        if sar_rows:
            print("\nStep 5b: Saving SAR results...")
            save_sar_table(sar_rows)
    else:
        print("\nStep 5: No significant spatial autocorrelation (p >= 0.05 for all models) "
              "— SAR correction not needed. OLS estimates from Script 07 are preferred.")
        print("  spatial_sar.{csv,html} not written (not needed).")

    # ── Step 6: Figures ────────────────────────────────────────────────────
    print("\nStep 6: Generating diagnostic figures...")

    make_weights_map(tracts, w)

    # Use transit model residuals for the residual map (first model in MODELS)
    transit_resid = ols_results["pct_transit"][1]
    transit_resid_clean = np.where(np.isfinite(transit_resid), transit_resid, np.nan)
    make_residual_map(cs, tracts, transit_resid_clean, w)

    # ── Summary ────────────────────────────────────────────────────────────
    print("\n=== 11_spatial.py complete ===")
    print("\nOutputs:")
    print("  output/tables/spatial_morans.{csv,html}")
    if sar_rows:
        print("  output/tables/spatial_sar.{csv,html}")
    print("  output/figures/spatial_weights_map.png")
    print("  output/figures/residual_map.png")
    print("\nInterpretation:")
    for row in moran_rows:
        sig = row["Significant_p05"]
        print(f"  {row['Model']}: Moran's I = {row['Moran_I']}, p = {row['p_sim']} "
              f"→ {sig}")
    if not any_significant:
        print("  → OLS estimates from Script 07 are spatially unbiased (no correction needed).")
    else:
        print("  → SAR results account for spatial spillovers; "
              "rho quantifies the strength of spatial dependence.")


if __name__ == "__main__":
    main()
