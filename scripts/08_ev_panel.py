#!/usr/bin/env python3
"""
08_ev_panel.py
Panel regressions: ideology predicting EV adoption, 2018–2024.

Since climate_ideology_index is time-invariant, we cannot use tract fixed effects
(they would absorb ideology). Instead we use:
  (a) Year FE with tract-clustered standard errors
  (b) Pooled OLS with HC3 standard errors

Four dependent variables:
  1. log(tesla_bev + 1)
  2. log(nontesla_bev + 1)
  3. log(light_truck_count + 1)
  4. tesla_share = tesla_bev / (tesla_bev + nontesla_bev)

Inputs:
  data/processed/panel_tract_year.csv
  data/processed/ideology_index.csv

Outputs:
  output/tables/ev_panel_yearfe.{csv,html}
  output/tables/ev_panel_pooled.{csv,html}
  output/figures/ev_panel_coefs.png
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

CONTROL_COLS = [
    "log_median_hh_income", "pct_ba_plus", "pop_density", "pct_white", "pct_wfh"
]
CONTROLS_STR = " + ".join(CONTROL_COLS)

DVS = [
    ("log_tesla_bev",    "log(Tesla BEV + 1)"),
    ("log_nontesla_bev", "log(Non-Tesla BEV + 1)"),
    ("log_light_truck",  "log(Light Truck + 1)"),
    ("tesla_share",      "Tesla Share of BEVs"),
]


def load_panel() -> pd.DataFrame:
    panel = pd.read_csv(PROCESSED / "panel_tract_year.csv", dtype={"tract_geoid_20": str})
    index = pd.read_csv(PROCESSED / "ideology_index.csv", dtype={"tract_geoid_20": str})

    df = panel.merge(index[["tract_geoid_20", "climate_ideology_index"]],
                     on="tract_geoid_20", how="left")

    # Derived DVs
    df["log_tesla_bev"]    = np.log1p(df["tesla_bev"])
    df["log_nontesla_bev"] = np.log1p(df["nontesla_bev"])
    df["log_light_truck"]  = np.log1p(df["light_truck_count"])
    total_ev = df["tesla_bev"] + df["nontesla_bev"]
    df["tesla_share"] = df["tesla_bev"] / total_ev.replace(0, np.nan)

    n_before = len(df)
    df = df.dropna(subset=["climate_ideology_index"])
    print(f"  Panel: {n_before:,} → {len(df):,} rows after dropping missing ideology")
    print(f"  Tracts: {df['tract_geoid_20'].nunique():,}, Years: {sorted(df['data_year'].unique())}")
    return df


def run_year_fe(df: pd.DataFrame) -> dict:
    """Year FE with tract-clustered SEs. Ideology identified by cross-sectional variation."""
    print("\n  === Year FE (clustered SEs) ===")
    results = {}
    for dv_col, dv_label in DVS:
        formula = (f"{dv_col} ~ climate_ideology_index + {CONTROLS_STR} "
                   f"+ C(data_year)")
        sub = df.dropna(subset=[dv_col] + CONTROL_COLS + ["climate_ideology_index"]).copy()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = smf.ols(formula, data=sub).fit(
                cov_type="cluster",
                cov_kwds={"groups": sub["tract_geoid_20"]}
            )
        coef = res.params["climate_ideology_index"]
        se   = res.bse["climate_ideology_index"]
        pval = res.pvalues["climate_ideology_index"]
        stars = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.1 else ""
        print(f"    {dv_label:30s}: coef={coef:+.4f}{stars}  SE={se:.4f}  p={pval:.3f}  "
              f"N={int(res.nobs):,}")
        results[dv_col] = (dv_label, res)
    return results


def run_pooled(df: pd.DataFrame) -> dict:
    """Pooled OLS with HC3 SEs — easier to interpret baseline."""
    print("\n  === Pooled OLS (HC3) ===")
    results = {}
    for dv_col, dv_label in DVS:
        formula = f"{dv_col} ~ climate_ideology_index + {CONTROLS_STR}"
        sub = df.dropna(subset=[dv_col] + CONTROL_COLS + ["climate_ideology_index"])
        res = smf.ols(formula, data=sub).fit(cov_type="HC3")
        coef = res.params["climate_ideology_index"]
        pval = res.pvalues["climate_ideology_index"]
        stars = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.1 else ""
        print(f"    {dv_label:30s}: coef={coef:+.4f}{stars}  p={pval:.3f}  "
              f"R²={res.rsquared:.3f}  N={int(res.nobs):,}")
        results[dv_col] = (dv_label, res)
    return results


def _make_summary_df(results: dict) -> pd.DataFrame:
    rows = []
    for dv_col, (dv_label, res) in results.items():
        coef = res.params["climate_ideology_index"]
        se   = res.bse["climate_ideology_index"]
        pval = res.pvalues["climate_ideology_index"]
        stars = "***" if pval < 0.01 else "**" if pval < 0.05 else "*" if pval < 0.1 else ""
        row = {
            "Dependent Variable": dv_label,
            "Ideology Coef":      f"{coef:+.4f}{stars}",
            "SE":                 f"({se:.4f})",
            "p-value":            f"{pval:.3f}",
            "N":                  int(res.nobs),
        }
        if hasattr(res, "rsquared"):
            row["R²"] = f"{res.rsquared:.3f}"
        rows.append(row)
    return pd.DataFrame(rows)


def save_tables(yearfe: dict, pooled: dict):
    for results, fname, title in [
        (yearfe, "ev_panel_yearfe",
         "EV Panel — Year FE with Tract-Clustered SEs (2018–2024 CA Tracts)"),
        (pooled, "ev_panel_pooled",
         "EV Panel — Pooled OLS with HC3 SEs (2018–2024 CA Tracts)"),
    ]:
        df_tbl = _make_summary_df(results)
        df_tbl.to_csv(TABLES / f"{fname}.csv", index=False)
        footer = ("<p>*p&lt;0.1, **p&lt;0.05, ***p&lt;0.01.<br>"
                  "Ideology = Climate Ideology Index (PC1 of YCOM + voter reg + ballot measures).<br>"
                  "Controls: log(median HH income), % BA+, population density, % white, % WFH.</p>")
        html = f"<h3>{title}</h3>" + df_tbl.to_html(index=False) + footer
        with open(TABLES / f"{fname}.html", "w") as f:
            f.write(html)
        print(f"  Saved → output/tables/{fname}.{{csv,html}}")


def make_coef_plot(yearfe: dict, pooled: dict):
    """Coefficient plot: ideology effect across 4 DVs, Year FE vs Pooled OLS."""
    fig, ax = plt.subplots(figsize=(9, 5))
    dvs   = list(yearfe.keys())
    labels = [yearfe[d][0] for d in dvs]
    y = np.arange(len(dvs))

    styles = [
        (yearfe,  "#1e40af", "o", "Year FE (clustered SE)"),
        (pooled,  "#dc2626", "s", "Pooled OLS (HC3)"),
    ]
    offsets = [-0.15, 0.15]

    for (res_dict, color, marker, label), offset in zip(styles, offsets):
        coefs = [res_dict[d][1].params["climate_ideology_index"] for d in dvs]
        ses   = [res_dict[d][1].bse["climate_ideology_index"]    for d in dvs]
        ypos  = y + offset
        ax.errorbar(coefs, ypos,
                    xerr=[1.96 * s for s in ses],
                    fmt=marker, color=color, capsize=4,
                    label=label, markersize=7, linewidth=1.5)

    ax.axvline(0, color="black", lw=0.8, linestyle="--", alpha=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.set_xlabel("Climate Ideology Index Coefficient", fontsize=10)
    ax.set_title("Effect of Climate Ideology on Vehicle Adoption\n"
                 "California Census Tracts, 2018–2024", fontsize=11)
    ax.legend(fontsize=9)
    ax.grid(axis="x", alpha=0.25)
    plt.tight_layout()
    fig.savefig(FIGURES / "ev_panel_coefs.png", dpi=300)
    plt.close()
    print("  Coefficient plot → output/figures/ev_panel_coefs.png")


def main():
    print("=== 08_ev_panel.py ===\n")

    for path in [PROCESSED / "panel_tract_year.csv", PROCESSED / "ideology_index.csv"]:
        if not path.exists():
            print(f"ERROR: {path} not found — run scripts 05 and 06 first")
            return

    df = load_panel()
    yearfe = run_year_fe(df)
    pooled = run_pooled(df)
    save_tables(yearfe, pooled)
    make_coef_plot(yearfe, pooled)

    print("\nDone. Next: run 09_event_study.py")


if __name__ == "__main__":
    main()
