#!/usr/bin/env python3
"""
07_replication.py
Cross-sectional replication of Kahn (2007).

Uses 2023 data cross-section. Three specifications:
  1. OLS: pct_transit ~ ideology + controls (HC3 robust SEs)
  2. OLS: pct_drove_alone ~ ideology + controls (HC3 robust SEs)
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

import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import patsy
import statsmodels.discrete.discrete_model as discrete_models
import statsmodels.formula.api as smf

ROOT = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"
TABLES.mkdir(parents=True, exist_ok=True)
FIGURES.mkdir(parents=True, exist_ok=True)

CONTROLS = (
    "log_median_hh_income + pct_ba_plus + pop_density + pct_white + pct_wfh"
)
CONTROL_COLS = ["log_median_hh_income", "pct_ba_plus", "pop_density", "pct_white", "pct_wfh"]


def load_cross_section() -> pd.DataFrame:
    """Load 2023 cross-section merged with ideology index."""
    panel = pd.read_csv(PROCESSED / "panel_tract_year.csv", dtype={"tract_geoid_20": str})
    index = pd.read_csv(PROCESSED / "ideology_index.csv", dtype={"tract_geoid_20": str})

    cs = panel[panel["data_year"] == 2023].copy()
    cs = cs.merge(index[["tract_geoid_20", "climate_ideology_index"]],
                  on="tract_geoid_20", how="left")

    n_missing = cs["climate_ideology_index"].isna().sum()
    if n_missing > 0:
        print(f"  WARNING: {n_missing} tracts missing ideology index after merge")

    required = (["climate_ideology_index", "pct_transit", "pct_drove_alone",
                 "total_bev", "total_light"] + CONTROL_COLS)
    n_before = len(cs)
    cs = cs.dropna(subset=required)
    cs = cs[cs["total_light"] > 0]
    print(f"  2023 cross-section: {n_before} → {len(cs):,} tracts after dropping missing")
    return cs


def _format_stars(pval: float) -> str:
    if pval < 0.01:
        return "***"
    if pval < 0.05:
        return "**"
    if pval < 0.1:
        return "*"
    return ""


def _result_to_df(result, model_type: str = "ols") -> pd.DataFrame:
    """Convert statsmodels result to a tidy DataFrame for saving."""
    pval_col = "P>|t|" if model_type == "ols" else "P>|z|"
    rows = []
    for var in result.params.index:
        stars = _format_stars(result.pvalues[var])
        ci = result.conf_int()
        rows.append({
            "Variable": var,
            "Coef": f"{result.params[var]:.4f}{stars}",
            "SE": f"({result.bse[var]:.4f})",
            "p-value": f"{result.pvalues[var]:.3f}",
            "CI_lo": f"{ci.loc[var, 0]:.4f}",
            "CI_hi": f"{ci.loc[var, 1]:.4f}",
        })
    return pd.DataFrame(rows)


def _save_table(df_table: pd.DataFrame, result, title: str, fname: str,
                notes: str = "", se_note: str = "HC3 robust SEs"):
    """Save regression table as CSV and HTML."""
    df_table.to_csv(TABLES / f"{fname}.csv", index=False)
    n = int(result.nobs)
    r2_str = f" | R²={result.rsquared:.3f}" if hasattr(result, "rsquared") else ""
    ll_str = f" | Log-L={result.llf:.1f}" if hasattr(result, "llf") else ""
    footer = (f"<p>N={n:,}{r2_str}{ll_str}<br>"
              f"*p&lt;0.1, **p&lt;0.05, ***p&lt;0.01 ({se_note}). {notes}</p>")
    html = f"<h3>{title}</h3>" + df_table.to_html(index=False) + footer
    with open(TABLES / f"{fname}.html", "w") as f:
        f.write(html)
    print(f"  Saved → output/tables/{fname}.{{csv,html}}")


def run_ols_transit(cs: pd.DataFrame):
    print("\n  OLS: Transit commute share...")
    formula = f"pct_transit ~ climate_ideology_index + {CONTROLS}"
    result = smf.ols(formula, data=cs).fit(cov_type="HC3")
    coef = result.params["climate_ideology_index"]
    pval = result.pvalues["climate_ideology_index"]
    print(f"    ideology coef = {coef:.4f} (p={pval:.3f}), R²={result.rsquared:.3f}")
    df_table = _result_to_df(result, "ols")
    _save_table(df_table, result,
                "OLS: Transit Commute Share ~ Climate Ideology (2023 CA Tracts)",
                "replication_ols_transit",
                "Kahn (2007) analog: positive coefficient expected.")
    return result


def run_ols_drivealone(cs: pd.DataFrame):
    print("\n  OLS: Drive-alone commute share...")
    formula = f"pct_drove_alone ~ climate_ideology_index + {CONTROLS}"
    result = smf.ols(formula, data=cs).fit(cov_type="HC3")
    coef = result.params["climate_ideology_index"]
    pval = result.pvalues["climate_ideology_index"]
    print(f"    ideology coef = {coef:.4f} (p={pval:.3f}), R²={result.rsquared:.3f}")
    df_table = _result_to_df(result, "ols")
    _save_table(df_table, result,
                "OLS: Drive-Alone Commute Share ~ Climate Ideology (2023 CA Tracts)",
                "replication_ols_drivealone",
                "Kahn (2007) analog: negative coefficient expected.")
    return result


def run_negbin_bev(cs: pd.DataFrame):
    print("\n  Negative Binomial: BEV count...")
    cs = cs.copy()
    cs["total_bev_int"] = cs["total_bev"].round().astype(int)
    cs["log_total_light"] = np.log(cs["total_light"].clip(lower=1))

    # offset() is not a patsy builtin; use the array-based API with offset= argument
    y_nb, X_nb = patsy.dmatrices(
        f"total_bev_int ~ climate_ideology_index + {CONTROLS}",
        data=cs, return_type="dataframe"
    )
    nb_model = discrete_models.NegativeBinomial(
        y_nb, X_nb,
        offset=cs.loc[y_nb.index, "log_total_light"].values
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = nb_model.fit(disp=False, maxiter=200)
    if not result.mle_retvals.get("converged", True):
        print("    WARNING: NegativeBinomial did not converge")

    coef = result.params["climate_ideology_index"]
    irr = np.exp(coef)
    pval = result.pvalues["climate_ideology_index"]
    print(f"    ideology coef (log-rate) = {coef:.4f}, IRR = {irr:.4f} (p={pval:.3f})")

    rows = []
    for var in result.params.index:
        stars = _format_stars(result.pvalues[var])
        rows.append({
            "Variable": var,
            "Coef (log-rate)": f"{result.params[var]:.4f}{stars}",
            "IRR": f"{np.exp(result.params[var]):.4f}",
            "SE": f"({result.bse[var]:.4f})",
            "p-value": f"{result.pvalues[var]:.3f}",
        })
    df_table = pd.DataFrame(rows)
    _save_table(df_table, result,
                "Negative Binomial: BEV Count ~ Climate Ideology (2023 CA Tracts)",
                "replication_negbin_bev",
                notes="IRR = incidence rate ratio (exp of log-rate coefficient). "
                      "Positive IRR > 1 expected.",
                se_note="MLE standard errors; IRR = exp(coef)")
    return result


def make_scatter(cs: pd.DataFrame):
    print("\n  Making replication scatter plots...")
    cs_scatter = cs.copy()
    # Second panel: ideology vs EV share (total_bev / total_light)
    cs_scatter["ev_share"] = cs_scatter["total_bev"] / cs_scatter["total_light"]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for ax, (ycol, ylabel, expected_dir) in zip(axes, [
        ("pct_transit", "Transit Commute Share", "(+)"),
        ("ev_share", "EV Share (BEV / Total Light Vehicles)", "(+)"),
    ]):
        x = cs_scatter["climate_ideology_index"].values
        y = cs_scatter[ycol].values
        mask = np.isfinite(x) & np.isfinite(y)
        ax.scatter(x[mask], y[mask], alpha=0.12, s=6, color="#1e40af", rasterized=True)
        m, b = np.polyfit(x[mask], y[mask], 1)
        xr = np.linspace(x[mask].min(), x[mask].max(), 200)
        ax.plot(xr, m * xr + b, color="#dc2626", lw=1.5, label=f"slope={m:.4f} {expected_dir}")
        ax.set_xlabel("Climate Ideology Index (PC1)", fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(f"{ylabel} vs. Climate Ideology", fontsize=10)
        ax.legend(fontsize=9)
        ax.grid(alpha=0.2)

    fig.suptitle("Replication of Kahn (2007) — California Census Tracts, 2023", fontsize=11)
    plt.tight_layout()
    fig.savefig(FIGURES / "replication_scatter.png", dpi=300)
    plt.close()
    print("  Scatter → output/figures/replication_scatter.png")


def main():
    print("=== 07_replication.py ===\n")

    for path in [PROCESSED / "panel_tract_year.csv", PROCESSED / "ideology_index.csv"]:
        if not path.exists():
            print(f"ERROR: {path} not found — run scripts 05 and 06 first")
            return

    cs = load_cross_section()
    run_ols_transit(cs)
    run_ols_drivealone(cs)
    run_negbin_bev(cs)
    make_scatter(cs)

    print("\nDone. Next: run 08_ev_panel.py")


if __name__ == "__main__":
    main()
