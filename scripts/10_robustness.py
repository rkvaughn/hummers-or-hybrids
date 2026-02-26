#!/usr/bin/env python3
"""
10_robustness.py
Robustness checks: re-run three core cross-section models (OLS transit, OLS drive-alone,
Negative Binomial BEV) with four ideology specifications side-by-side.

Ideology specifications
-----------------------
Main : tract level, climate_ideology_index (PCA composite from 06_ideology_index.py)
R1   : county level, PCA of YCOM columns only (ycom_happening, ycom_worried,
       ycom_regulate, ycom_human, ycom_supportRPS)
R2   : tract level, PCA of voter-reg + ballot variables only
       (dem_minus_rep, prop30_yes_share, prop68_yes_share)
R3   : tract level, prop30_yes_share alone (single most direct climate signal)

Sign normalization for all PCA-derived indices: if the loading on dem_minus_rep (or
ycom_happening for R1) is negative, flip the sign of PC1 so that higher = more
climate-concerned.

Models (2023 cross-section)
---------------------------
1. OLS  : pct_transit    ~ ideology + controls  (HC3 robust SEs)
2. OLS  : pct_drove_alone ~ ideology + controls  (HC3 robust SEs)
3. Neg Binomial : total_bev (int) ~ ideology + controls, offset=log(total_light)

Controls: log_median_hh_income, pct_ba_plus, pop_density, pct_white, pct_wfh

Inputs
------
  data/processed/panel_tract_year.csv
  data/processed/ideology_index.csv

Outputs
-------
  output/tables/robustness_ols_transit.{csv,html}
  output/tables/robustness_ols_drivealone.{csv,html}
  output/tables/robustness_negbin_bev.{csv,html}

Each table has 4 rows (Main, R1, R2, R3) with columns:
  Specification | Ideology_Col | Coef | SE | p-value | Stars | N

Methodology note
----------------
R1 aggregates all tract-level variables to county (vehicle counts summed; controls
population-weighted). This tests whether the main finding holds when ideology is
measured cleanly (YCOM survey estimates) but at coarser geographic resolution.
R2 and R3 stay at tract level but remove the county-level YCOM assumption entirely,
relying only on revealed-preference measures (voter registration, ballot vote shares).
Convergent results across all four specifications strengthen causal interpretation.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import patsy
import statsmodels.discrete.discrete_model as discrete_models
import statsmodels.formula.api as smf
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
TABLES.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
CONTROL_COLS = [
    "log_median_hh_income",
    "pct_ba_plus",
    "pop_density",
    "pct_white",
    "pct_wfh",
]
CONTROLS_STR = " + ".join(CONTROL_COLS)

YCOM_COLS = [
    "ycom_happening",
    "ycom_worried",
    "ycom_regulate",
    "ycom_human",
    "ycom_supportRPS",
]

R2_COLS = ["dem_minus_rep", "prop30_yes_share", "prop68_yes_share"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_stars(pval: float) -> str:
    if pval < 0.01:
        return "***"
    if pval < 0.05:
        return "**"
    if pval < 0.1:
        return "*"
    return ""


def _pca_pc1(df: pd.DataFrame, cols: list, sign_anchor_col: str) -> np.ndarray:
    """
    Fit PCA on standardized cols; return PC1 scores sign-normalized so that
    higher values correlate positively with sign_anchor_col.

    Parameters
    ----------
    df : DataFrame with cols present (no NaNs expected in subset)
    cols : list of column names to include in PCA
    sign_anchor_col : column name used for sign orientation; if PC1 loading
                      on this column is negative, flip sign of PC1.

    Returns
    -------
    numpy array of PC1 scores, length == len(df)
    """
    scaler = StandardScaler()
    X = scaler.fit_transform(df[cols].values)
    pca = PCA(n_components=1)
    scores = pca.fit_transform(X).ravel()

    anchor_idx = cols.index(sign_anchor_col)
    loading = pca.components_[0, anchor_idx]
    if loading < 0:
        scores = -scores

    var_explained = pca.explained_variance_ratio_[0] * 100
    print(f"      PC1 variance explained: {var_explained:.1f}%")
    return scores


# ── Data loading ──────────────────────────────────────────────────────────────

def load_data() -> tuple:
    """
    Load 2023 cross-section panel merged with ideology index.

    Returns
    -------
    (tract_df, panel_full) where:
      tract_df  : tract-level 2023 cross-section with all ideology columns
      panel_full: full panel (used for county aggregation in R1)
    """
    panel_path = PROCESSED / "panel_tract_year.csv"
    index_path = PROCESSED / "ideology_index.csv"

    for p in [panel_path, index_path]:
        if not p.exists():
            raise FileNotFoundError(
                f"{p} not found. Run scripts 05 and 06 first."
            )

    panel = pd.read_csv(panel_path, dtype={"tract_geoid_20": str})
    index = pd.read_csv(index_path, dtype={"tract_geoid_20": str})

    cs = panel[panel["data_year"] == 2023].copy()

    # Merge Main ideology index
    cs = cs.merge(
        index[["tract_geoid_20", "climate_ideology_index"]],
        on="tract_geoid_20", how="left"
    )

    # Also pull raw ideology columns from panel (needed for R2 and R3)
    raw_ideo_cols = [c for c in R2_COLS + YCOM_COLS if c in panel.columns]
    if raw_ideo_cols:
        ideo_raw = (
            panel[panel["data_year"] == 2023][["tract_geoid_20"] + raw_ideo_cols]
            .drop_duplicates("tract_geoid_20")
        )
        cs = cs.merge(ideo_raw, on="tract_geoid_20", how="left")

    n_before = len(cs)
    required_base = CONTROL_COLS + [
        "pct_transit", "pct_drove_alone", "total_bev", "total_light",
        "climate_ideology_index"
    ]
    cs = cs.dropna(subset=required_base)
    cs = cs[cs["total_light"] > 0].copy()
    cs["total_bev_int"] = cs["total_bev"].round().astype(int)
    cs["log_total_light"] = np.log(cs["total_light"].clip(lower=1))

    print(f"  Tract cross-section: {n_before} → {len(cs):,} tracts after dropping missing")
    return cs, panel


# ── Ideology index construction ───────────────────────────────────────────────

def build_r1_county(panel: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate 2023 cross-section to county level; build YCOM-only PCA index.

    County FIPS = first 5 characters of tract_geoid_20.
    Vehicle counts are summed; controls are population-weighted means where
    population (pop_density * area) is not available, so we fall back to
    simple mean. pop_density itself is averaged (not summed) as it is a
    per-area rate.

    Returns county-level DataFrame with county_fips and r1_ideology columns
    plus all needed model variables.
    """
    cs = panel[panel["data_year"] == 2023].copy()

    # YCOM columns must be present for R1
    available_ycom = [c for c in YCOM_COLS if c in cs.columns]
    if not available_ycom:
        print("    WARNING: No YCOM columns found in panel — R1 will be skipped")
        return pd.DataFrame()

    cs["county_fips"] = cs["tract_geoid_20"].str[:5]

    # Columns to sum (counts) vs mean (rates/shares/densities)
    sum_cols = ["total_bev", "total_light", "total_phev"]
    # Rates and YCOM shares: use simple mean (within-county tracts assumed uniform for YCOM)
    mean_cols = (
        CONTROL_COLS
        + ["pct_transit", "pct_drove_alone"]
        + available_ycom
        + [c for c in R2_COLS if c in cs.columns]
    )

    # Keep only cols that exist
    sum_cols = [c for c in sum_cols if c in cs.columns]
    mean_cols = [c for c in mean_cols if c in cs.columns]

    agg_dict = {c: "sum" for c in sum_cols}
    agg_dict.update({c: "mean" for c in mean_cols})

    county = (
        cs.groupby("county_fips")
        .agg(agg_dict)
        .reset_index()
    )

    county = county[county["total_light"] > 0].copy()
    county = county.dropna(subset=available_ycom + CONTROL_COLS
                           + ["pct_transit", "pct_drove_alone"])
    county["total_bev_int"] = county["total_bev"].round().astype(int)
    county["log_total_light"] = np.log(county["total_light"].clip(lower=1))

    # Build YCOM-only PCA index
    print(f"      R1 YCOM PCA on {len(available_ycom)} columns, {len(county)} counties")
    county["r1_ideology"] = _pca_pc1(county, available_ycom, available_ycom[0])

    print(f"  R1 county aggregation: {len(county):,} counties")
    return county


def build_r2_index(cs: pd.DataFrame) -> pd.DataFrame:
    """
    Build R2 index: PCA on dem_minus_rep, prop30_yes_share, prop68_yes_share.

    Returns copy of cs with r2_ideology added; rows missing R2 cols are dropped.
    """
    available_r2 = [c for c in R2_COLS if c in cs.columns]
    if not available_r2:
        print("    WARNING: No R2 columns found — R2 will be skipped")
        return pd.DataFrame()

    sub = cs.dropna(subset=available_r2).copy()
    if len(sub) < 50:
        print(f"    WARNING: Only {len(sub)} tracts with complete R2 data — skipping R2")
        return pd.DataFrame()

    print(f"      R2 PCA on {len(available_r2)} columns, {len(sub)} tracts")
    sub["r2_ideology"] = _pca_pc1(sub, available_r2, available_r2[0])
    return sub


# ── Model runners ─────────────────────────────────────────────────────────────

def run_ols(df: pd.DataFrame, dv_col: str, ideology_col: str,
            spec_name: str) -> dict | None:
    """
    Run OLS with HC3 robust SEs. Returns summary dict or None on failure.
    """
    formula = f"{dv_col} ~ {ideology_col} + {CONTROLS_STR}"
    try:
        result = smf.ols(formula, data=df).fit(cov_type="HC3")
        coef = result.params[ideology_col]
        se = result.bse[ideology_col]
        pval = result.pvalues[ideology_col]
        n = int(result.nobs)
        r2 = result.rsquared
        print(f"    {spec_name}: coef={coef:.4f}, SE={se:.4f}, p={pval:.3f}, "
              f"R²={r2:.3f}, N={n:,}")
        return {
            "Specification": spec_name,
            "Ideology_Col": ideology_col,
            "Coef": round(coef, 4),
            "SE": round(se, 4),
            "p-value": round(pval, 3),
            "Stars": _format_stars(pval),
            "R2": round(r2, 3),
            "N": n,
        }
    except Exception as exc:
        print(f"    {spec_name}: OLS FAILED — {exc}")
        return None


def run_negbin(df: pd.DataFrame, ideology_col: str,
               spec_name: str) -> dict | None:
    """
    Run Negative Binomial on total_bev_int with log_total_light offset.
    Uses array-based statsmodels API (offset() is not a patsy builtin).

    Returns summary dict or None on failure.
    """
    formula = f"total_bev_int ~ {ideology_col} + {CONTROLS_STR}"
    try:
        y_nb, X_nb = patsy.dmatrices(formula, data=df, return_type="dataframe")
    except Exception as exc:
        print(f"    {spec_name}: patsy dmatrices FAILED — {exc}")
        return None

    nb_model = discrete_models.NegativeBinomial(
        y_nb, X_nb,
        offset=df.loc[y_nb.index, "log_total_light"].values
    )
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            warnings.filterwarnings("ignore", category=RuntimeWarning)
            result = nb_model.fit(disp=False, maxiter=200)
    except Exception as exc:
        print(f"    {spec_name}: NB fit FAILED — {exc}")
        return None

    if not result.mle_retvals.get("converged", True):
        print(f"    WARNING: NB did not converge for {spec_name}")

    coef = result.params[ideology_col]
    se = result.bse[ideology_col]
    pval = result.pvalues[ideology_col]
    irr = np.exp(coef)
    n = int(result.nobs)
    print(f"    {spec_name}: coef(log-rate)={coef:.4f}, IRR={irr:.4f}, "
          f"SE={se:.4f}, p={pval:.3f}, N={n:,}")
    return {
        "Specification": spec_name,
        "Ideology_Col": ideology_col,
        "Coef": round(coef, 4),
        "IRR": round(irr, 4),
        "SE": round(se, 4),
        "p-value": round(pval, 3),
        "Stars": _format_stars(pval),
        "N": n,
    }


# ── Output ────────────────────────────────────────────────────────────────────

def _rows_to_df(rows: list, model_type: str) -> pd.DataFrame:
    """Convert list of result dicts to a clean summary DataFrame."""
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # Add significance indicator to Coef column
    df["Coef_stars"] = df.apply(
        lambda r: f"{r['Coef']:.4f}{r['Stars']}", axis=1
    )
    df["SE_fmt"] = df["SE"].apply(lambda x: f"({x:.4f})")
    df["p_fmt"] = df["p-value"].apply(lambda x: f"{x:.3f}")

    if model_type == "ols":
        out_cols = ["Specification", "Ideology_Col", "Coef_stars", "SE_fmt",
                    "p_fmt", "R2", "N"]
        rename = {
            "Coef_stars": "Coef", "SE_fmt": "SE", "p_fmt": "p-value",
        }
    else:
        df["IRR_fmt"] = df["IRR"].apply(lambda x: f"{x:.4f}")
        out_cols = ["Specification", "Ideology_Col", "Coef_stars", "SE_fmt",
                    "p_fmt", "IRR_fmt", "N"]
        rename = {
            "Coef_stars": "Coef (log-rate)", "SE_fmt": "SE",
            "p_fmt": "p-value", "IRR_fmt": "IRR",
        }
    return df[out_cols].rename(columns=rename)


def _save_robustness_table(rows: list, model_type: str, model_label: str,
                           fname: str, dv_note: str = ""):
    """Save robustness comparison table as CSV and HTML."""
    if not rows:
        print(f"  No results for {fname} — skipping save")
        return

    valid_rows = [r for r in rows if r is not None]
    if not valid_rows:
        print(f"  All specifications failed for {fname} — skipping save")
        return

    df_out = _rows_to_df(valid_rows, model_type)
    csv_path = TABLES / f"{fname}.csv"
    html_path = TABLES / f"{fname}.html"

    df_out.to_csv(csv_path, index=False)

    se_note = "HC3 robust SEs" if model_type == "ols" else "MLE SEs; IRR = exp(coef)"
    stars_note = "*p<0.1, **p<0.05, ***p<0.01"
    footer = (
        f"<p>{stars_note} ({se_note}). {dv_note}<br>"
        f"R1=county/YCOM-only PCA; R2=tract/voter-reg+ballot PCA; "
        f"R3=tract/Prop 30 share alone.</p>"
    )
    html = (
        f"<h3>{model_label}</h3>"
        + df_out.to_html(index=False)
        + footer
    )
    with open(html_path, "w") as fh:
        fh.write(html)

    print(f"  Saved → output/tables/{fname}.{{csv,html}}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== 10_robustness.py ===\n")
    print("  Loading data...")
    tract_cs, panel_full = load_data()

    # ── Build R1 county-level data ─────────────────────────────────────────
    print("\n  [R1] Building county-level YCOM-PCA index...")
    county_r1 = build_r1_county(panel_full)
    r1_available = not county_r1.empty

    # ── Build R2 tract-level PCA index ─────────────────────────────────────
    print("\n  [R2] Building tract-level voter-reg+ballot PCA index...")
    tract_r2 = build_r2_index(tract_cs)
    r2_available = not tract_r2.empty

    # ── R3: prop30_yes_share directly ──────────────────────────────────────
    r3_col = "prop30_yes_share"
    r3_available = r3_col in tract_cs.columns and not tract_cs[r3_col].isna().all()
    if r3_available:
        tract_r3 = tract_cs.dropna(subset=[r3_col]).copy()
        print(f"\n  [R3] prop30_yes_share available for {len(tract_r3):,} tracts")
    else:
        tract_r3 = pd.DataFrame()
        print(f"\n  [R3] WARNING: {r3_col} not found or all NaN — R3 will be skipped")

    # ── Loop over the 3 models ─────────────────────────────────────────────
    for model_name, dv_col, dv_label, model_type in [
        ("ols_transit",    "pct_transit",     "OLS: Transit Share",    "ols"),
        ("ols_drivealone", "pct_drove_alone",  "OLS: Drive-Alone Share", "ols"),
        ("negbin_bev",     "total_bev_int",   "NB: BEV Count",         "negbin"),
    ]:
        print(f"\n{'─'*60}")
        print(f"  Model: {dv_label} (ideology robustness comparison)")
        print(f"{'─'*60}")

        rows = []

        # Main ── tract level, composite PCA
        print("  [Main] tract / composite PCA index")
        runner = run_ols if model_type == "ols" else run_negbin
        if model_type == "ols":
            row = run_ols(tract_cs, dv_col, "climate_ideology_index", "Main")
        else:
            row = run_negbin(tract_cs, "climate_ideology_index", "Main")
        rows.append(row)

        # R1 ── county level, YCOM-only PCA
        print("  [R1] county / YCOM-only PCA")
        if r1_available:
            if model_type == "ols":
                row = run_ols(county_r1, dv_col, "r1_ideology", "R1 (county/YCOM)")
            else:
                row = run_negbin(county_r1, "r1_ideology", "R1 (county/YCOM)")
        else:
            print("    Skipped (no county R1 data)")
            row = None
        rows.append(row)

        # R2 ── tract level, voter-reg+ballot PCA
        print("  [R2] tract / voter-reg+ballot PCA")
        if r2_available:
            if model_type == "ols":
                row = run_ols(tract_r2, dv_col, "r2_ideology", "R2 (tract/no YCOM)")
            else:
                row = run_negbin(tract_r2, "r2_ideology", "R2 (tract/no YCOM)")
        else:
            print("    Skipped (no R2 data)")
            row = None
        rows.append(row)

        # R3 ── tract level, Prop 30 alone
        print(f"  [R3] tract / {r3_col} alone")
        if r3_available:
            if model_type == "ols":
                row = run_ols(tract_r3, dv_col, r3_col, "R3 (Prop 30 share)")
            else:
                row = run_negbin(tract_r3, r3_col, "R3 (Prop 30 share)")
        else:
            print("    Skipped (no R3 data)")
            row = None
        rows.append(row)

        # Choose DV note
        if model_type == "ols" and dv_col == "pct_transit":
            dv_note = "Kahn (2007) analog: positive ideology coefficient expected."
        elif model_type == "ols" and dv_col == "pct_drove_alone":
            dv_note = "Kahn (2007) analog: negative ideology coefficient expected."
        else:
            dv_note = (
                "Offset = log(total_light). Positive IRR > 1 expected. "
                "R1 uses county aggregates; Main/R2/R3 use Census tracts."
            )

        fname = f"robustness_{model_name}"
        full_label = (
            f"Robustness: {dv_label} ~ Ideology (2023 CA, 4 specifications)"
        )
        _save_robustness_table(rows, model_type, full_label, fname, dv_note)

    print("\n=== 10_robustness.py complete ===")
    print("Outputs:")
    for name in ["robustness_ols_transit", "robustness_ols_drivealone",
                 "robustness_negbin_bev"]:
        print(f"  output/tables/{name}.{{csv,html}}")
    print("\nNext: run 11_spatial.py")


if __name__ == "__main__":
    main()
