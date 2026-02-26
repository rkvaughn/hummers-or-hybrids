#!/usr/bin/env python3
"""
09_event_study.py
Event study: Has climate ideology's relationship with Tesla adoption changed
following Elon Musk's political pivot?

Specification (within-tract demeaned to absorb tract FE):
  dm(log_EV_it) = Σ_τ β_τ * dm(ideology_i × 1[year=τ]) + X_it·δ + C(year) + ε_it

ACS controls (X_it): log_median_hh_income, pct_ba_plus, pop_density, pct_white, pct_wfh
These controls are time-invariant (2023 ACS vintage applied to all years). Within-tract
demeaning of a time-invariant variable produces a column of zeros, so they do not
contribute to the within estimator — but are included for specification consistency
with script 08.

Run separately for:
  - Tesla BEVs (main series)
  - Non-Tesla BEVs (control series — should not diverge)
  - Light trucks (placebo — should be flat or declining)

2018 = base year; β_2018 = 0 by construction (omitted).

Event markers:
  2022 — Musk acquires Twitter (Oct 2022)
  2024 — DOGE role / Trump administration (Nov 2024–Jan 2025)

Outputs:
  output/figures/event_study_tesla_vs_nontesla.png   (hero figure)
  output/tables/event_study_coefs.csv
  output/figures/event_study_truck_placebo.png
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
EVENTS = {
    2022: "Musk acquires Twitter\n(Oct 2022)",
    2024: "DOGE / Trump admin\n(Nov 2024)",
}

CONTROLS = ["log_median_hh_income", "pct_ba_plus", "pop_density", "pct_white", "pct_wfh"]


def load_panel() -> pd.DataFrame:
    panel = pd.read_csv(PROCESSED / "panel_tract_year.csv", dtype={"tract_geoid_20": str})
    index = pd.read_csv(PROCESSED / "ideology_index.csv", dtype={"tract_geoid_20": str})

    df = panel.merge(index[["tract_geoid_20", "climate_ideology_index"]],
                     on="tract_geoid_20", how="left")
    df = df.dropna(subset=["climate_ideology_index"])

    df["log_tesla_bev"]    = np.log1p(df["tesla_bev"])
    df["log_nontesla_bev"] = np.log1p(df["nontesla_bev"])
    df["log_light_truck"]  = np.log1p(df["light_truck_count"])

    print(f"  Panel: {len(df):,} rows, {df['tract_geoid_20'].nunique():,} tracts, "
          f"years {sorted(df['data_year'].unique())}")
    return df


def run_event_study(df: pd.DataFrame, dv_col: str, series_label: str) -> pd.DataFrame:
    """
    Estimate ideology × year interaction coefficients using within-tract demeaning.

    Within-tract demeaning (the Frisch-Waugh-Lovell / within estimator) absorbs
    tract fixed effects without creating ~9,100 dummy variables. Standard errors
    are clustered at the tract level.

    Returns DataFrame: year, coef, se, ci_lo, ci_hi, series
    """
    print(f"\n  Event study: {series_label}...")

    years = sorted(df["data_year"].unique())
    non_base = [y for y in years if y != BASE_YEAR]

    sub = df[["tract_geoid_20", "data_year", dv_col, "climate_ideology_index"] + CONTROLS].dropna().copy()

    # Panel balance check — within-tract demeaning is unbiased only for balanced panels
    year_counts = sub.groupby("tract_geoid_20")["data_year"].count()
    n_years = sub["data_year"].nunique()
    n_unbalanced = (year_counts != n_years).sum()
    if n_unbalanced > 0:
        pct = 100 * n_unbalanced / len(year_counts)
        print(f"    WARNING: {n_unbalanced:,} tracts ({pct:.1f}%) have fewer than {n_years} observations (unbalanced)")
        print(f"    Restricting to balanced panel (tracts with all {n_years} years)...")
        balanced_tracts = year_counts[year_counts == n_years].index
        sub = sub[sub["tract_geoid_20"].isin(balanced_tracts)].copy()
        print(f"    Balanced panel: {len(sub):,} obs, {sub['tract_geoid_20'].nunique():,} tracts")
    else:
        print(f"    Panel is balanced ({n_years} years per tract).")

    # Create ideology × year interaction dummies
    for yr in non_base:
        sub[f"ideo_x_{yr}"] = sub["climate_ideology_index"] * (sub["data_year"] == yr).astype(float)

    inter_cols = [f"ideo_x_{yr}" for yr in non_base]
    all_cols   = [dv_col, "climate_ideology_index"] + inter_cols + CONTROLS

    # Within-tract demean all variables
    # Note: CONTROLS are time-invariant (2023 ACS vintage); after demeaning they will be
    # all zeros (or near-zero floating-point noise). They contribute nothing to the within
    # estimator but are included for specification consistency with script 08.
    tract_means = sub.groupby("tract_geoid_20")[all_cols].transform("mean")
    sub_dm = sub.copy()
    for col in all_cols:
        sub_dm[f"dm_{col}"] = sub[col] - tract_means[col]

    # Verify time-invariant controls demean to (near) zero
    ctrl_max_var = max(sub_dm[f"dm_{c}"].var() for c in CONTROLS)
    print(f"    NOTE: ACS controls are time-invariant; max within-tract variance after "
          f"demeaning = {ctrl_max_var:.2e} (expected ~0). Included for spec consistency with 08.")

    dm_inter_str = " + ".join(f"dm_ideo_x_{yr}" for yr in non_base)
    dm_ctrl_str  = " + ".join(f"dm_{c}" for c in CONTROLS)
    formula = f"dm_{dv_col} ~ {dm_inter_str} + {dm_ctrl_str} + C(data_year) - 1"

    print(f"    N obs = {len(sub_dm):,}, N tracts = {sub_dm['tract_geoid_20'].nunique():,}")
    print(f"    Fitting within-estimator (demeaned)...")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = smf.ols(formula, data=sub_dm).fit(
            cov_type="cluster",
            cov_kwds={"groups": sub_dm["tract_geoid_20"]}
        )

    # Collect coefficients
    rows = []
    for yr in years:
        if yr == BASE_YEAR:
            rows.append({"year": yr, "coef": 0.0, "se": 0.0,
                         "ci_lo": 0.0, "ci_hi": 0.0})
        else:
            pname = f"dm_ideo_x_{yr}"
            if pname not in res.params:
                print(f"    WARNING: {pname} not found in results")
                continue
            c  = res.params[pname]
            se = res.bse[pname]
            rows.append({
                "year": yr, "coef": c, "se": se,
                "ci_lo": c - 1.96 * se,
                "ci_hi": c + 1.96 * se,
            })

    result_df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    result_df["series"] = series_label
    result_df["dv"]     = dv_col

    coef_str = "  ".join(
        f"{r.year}: {r.coef:+.3f}" for _, r in result_df.iterrows()
    )
    print(f"    Coefficients: {coef_str}")
    return result_df


def plot_event_study(series_list: list[tuple], filename: str, title: str, caption: str):
    """
    Plot multiple event study series on one chart.

    series_list: list of (df_coefs, color, linestyle, marker, label)
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    for df_c, color, ls, marker, label in series_list:
        years = df_c["year"].values
        coefs = df_c["coef"].values
        ci_lo = df_c["ci_lo"].values
        ci_hi = df_c["ci_hi"].values

        ax.plot(years, coefs, color=color, linestyle=ls,
                marker=marker, linewidth=2, markersize=7, label=label, zorder=3)
        ax.fill_between(years, ci_lo, ci_hi, color=color, alpha=0.12)

    # Baseline
    ax.axhline(0, color="black", lw=0.8, linestyle="--", alpha=0.5)

    # Event markers — use get_xaxis_transform() so x is in data coordinates (pinned to
    # event year) and y is in axes fraction (0–1), keeping labels in bounds regardless
    # of data scale. Do NOT use ax.get_ylim() here as limits may not be finalized yet.
    for event_yr, event_label in EVENTS.items():
        ax.axvline(event_yr, color="#6b7280", lw=1.2, linestyle=":", alpha=0.8, zorder=1)
        ax.text(event_yr + 0.06, 0.88, event_label,
                transform=ax.get_xaxis_transform(),  # x in data coords, y in axes coords (0-1)
                fontsize=8, color="#374151", ha="left", va="top",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7))

    all_years = series_list[0][0]["year"].values
    ax.set_xticks(all_years)
    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel("Ideology × Year Coefficient\n(relative to 2018 baseline)", fontsize=10)
    ax.set_title(title, fontsize=12, pad=10)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", alpha=0.25)

    fig.text(0.5, -0.03, caption, ha="center", fontsize=8,
             style="italic", wrap=True, color="#4b5563")

    plt.tight_layout()
    fig.savefig(FIGURES / filename, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Figure → output/figures/{filename}")


def main():
    print("=== 09_event_study.py ===\n")

    for path in [PROCESSED / "panel_tract_year.csv", PROCESSED / "ideology_index.csv"]:
        if not path.exists():
            print(f"ERROR: {path} not found — run scripts 05 and 06 first")
            return

    df = load_panel()

    tesla    = run_event_study(df.copy(), "log_tesla_bev",    "Tesla BEV")
    nontesla = run_event_study(df.copy(), "log_nontesla_bev", "Non-Tesla BEV")
    truck    = run_event_study(df.copy(), "log_light_truck",  "Light Truck (Placebo)")

    # Save all coefficients
    all_coefs = pd.concat([tesla, nontesla, truck], ignore_index=True)
    all_coefs.to_csv(TABLES / "event_study_coefs.csv", index=False)
    print(f"\n  Coefficients → output/tables/event_study_coefs.csv")

    # Hero figure: Tesla vs. Non-Tesla
    plot_event_study(
        series_list=[
            (tesla,    "#dc2626", "-",  "o", "Tesla BEV"),
            (nontesla, "#1e40af", "-",  "s", "Non-Tesla BEV"),
        ],
        filename="event_study_tesla_vs_nontesla.png",
        title="The Elon Effect: Climate Ideology and EV Adoption Over Time\n"
              "California Census Tracts, 2018–2024",
        caption=(
            "Within-tract demeaned OLS with year FE. Tract-clustered SEs. 95% CI shaded. "
            "2018 = base year (β = 0). "
            "Vertical lines: Twitter acquisition (Oct 2022), DOGE/Trump admin (Nov 2024)."
        ),
    )

    # Placebo: trucks vs. non-Tesla
    plot_event_study(
        series_list=[
            (truck,    "#16a34a", "--", "^", "Light Truck (Placebo)"),
            (nontesla, "#1e40af", "-",  "s", "Non-Tesla BEV"),
        ],
        filename="event_study_truck_placebo.png",
        title="Placebo Check: Light Trucks vs. Non-Tesla EVs\n"
              "California Census Tracts, 2018–2024",
        caption=(
            "Light truck ideology coefficient should be negative or flat if the ideology-EV "
            "correlation is specific to green-signaling vehicles."
        ),
    )

    print("\nDone. Next: run 10_robustness.py")


if __name__ == "__main__":
    main()
