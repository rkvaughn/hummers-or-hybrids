#!/usr/bin/env python3
"""
09b_event_study_fd.py
First-difference event study — addresses the stock vs. flow critique.

The CEC data is a December 31 STOCK snapshot (total registered vehicles, not new sales).
First-differencing log(EV+1) converts year-over-year changes in stock into a proxy for
net new registrations (new purchases minus retirements/out-of-state transfers).

Specification (first-differenced, year FE absorbed via within-tract demeaning):
  Δlog(EV)_it = Σ_τ β_τ * dm(ideology_i × 1[year=τ]) + dm(year_FE) + ε_it

where Δlog(EV)_it = log(EV+1)_it − log(EV+1)_{i,t−1}

Base year: 2019 (first year with a valid first difference; 2018 dropped).
Standard errors: tract-clustered (primary) and county-clustered (robustness).
County FIPS = first 5 characters of tract_geoid_20.

Outputs:
  output/figures/event_study_fd_tesla_vs_nontesla.png
  output/figures/event_study_fd_truck_placebo.png
  output/tables/event_study_fd_coefs.csv
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

BASE_YEAR = 2019
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

    df = df.sort_values(["tract_geoid_20", "data_year"]).copy()

    # Compute log levels first
    for raw_col, log_col in [
        ("tesla_bev",         "log_tesla_bev"),
        ("nontesla_bev",      "log_nontesla_bev"),
        ("light_truck_count", "log_light_truck"),
    ]:
        df[log_col] = np.log1p(df[raw_col])

    # First differences (within tract, year-over-year)
    for log_col, fd_col in [
        ("log_tesla_bev",    "dlog_tesla_bev"),
        ("log_nontesla_bev", "dlog_nontesla_bev"),
        ("log_light_truck",  "dlog_light_truck"),
    ]:
        df[fd_col] = df.groupby("tract_geoid_20")[log_col].diff()

    # Drop 2018 rows (no prior year to diff against) and any NaN FD rows
    df = df[df["data_year"] >= 2019].dropna(
        subset=["dlog_tesla_bev", "dlog_nontesla_bev", "dlog_light_truck"]
    ).copy()

    print(f"  Panel: {len(df):,} rows, {df['tract_geoid_20'].nunique():,} tracts, "
          f"years {sorted(df['data_year'].unique())}")
    return df


def run_event_study(df: pd.DataFrame, dv_col: str, series_label: str) -> pd.DataFrame:
    """
    Estimate ideology × year interaction coefficients using within-tract demeaning
    on a first-differenced dependent variable.

    The first-differenced DV removes the persistent stock level; what remains is the
    year-over-year change in log(EV+1), a proxy for net new registrations.

    Within-tract demeaning (Frisch-Waugh-Lovell) absorbs tract fixed effects on the
    already-differenced data, providing a second layer of detrending.

    Standard errors:
      - Primary: tract-clustered
      - Robustness: county-clustered (county FIPS = first 5 chars of tract_geoid_20)

    Returns DataFrame: year, coef, se, ci_lo, ci_hi, se_county, ci_lo_county,
                       ci_hi_county, series, dv
    """
    print(f"\n  Event study (FD): {series_label}...")

    years = sorted(df["data_year"].unique())
    non_base = [y for y in years if y != BASE_YEAR]

    sub = df[["tract_geoid_20", "data_year", dv_col, "climate_ideology_index"] + CONTROLS].dropna().copy()

    # Panel balance check
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
    tract_means = sub.groupby("tract_geoid_20")[all_cols].transform("mean")
    sub_dm = sub.copy()
    for col in all_cols:
        sub_dm[f"dm_{col}"] = sub[col] - tract_means[col]

    ctrl_max_var = max(sub_dm[f"dm_{c}"].var() for c in CONTROLS)
    print(f"    NOTE: ACS controls are time-invariant; max within-tract variance after "
          f"demeaning = {ctrl_max_var:.2e} (expected ~0). Included for spec consistency with 08.")

    dm_inter_str = " + ".join(f"dm_ideo_x_{yr}" for yr in non_base)
    dm_ctrl_str  = " + ".join(f"dm_{c}" for c in CONTROLS)
    formula = f"dm_{dv_col} ~ {dm_inter_str} + {dm_ctrl_str} + C(data_year) - 1"

    print(f"    N obs = {len(sub_dm):,}, N tracts = {sub_dm['tract_geoid_20'].nunique():,}")
    print(f"    Fitting within-estimator on first-differenced DV (tract-clustered SEs)...")

    # Tract-clustered SEs (primary)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = smf.ols(formula, data=sub_dm).fit(
            cov_type="cluster",
            cov_kwds={"groups": sub_dm["tract_geoid_20"]}
        )

    # County-clustered SEs (robustness)
    county_groups = sub_dm["tract_geoid_20"].str[:5]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res_county = smf.ols(formula, data=sub_dm).fit(
            cov_type="cluster",
            cov_kwds={"groups": county_groups}
        )

    # Collect coefficients
    rows = []
    for yr in years:
        if yr == BASE_YEAR:
            rows.append({
                "year": yr,
                "coef": 0.0, "se": 0.0, "ci_lo": 0.0, "ci_hi": 0.0,
                "se_county": 0.0, "ci_lo_county": 0.0, "ci_hi_county": 0.0,
            })
        else:
            pname = f"dm_ideo_x_{yr}"
            if pname not in res.params:
                print(f"    WARNING: {pname} not found in results")
                continue
            c  = res.params[pname]
            se = res.bse[pname]
            se_co = res_county.bse[pname]
            rows.append({
                "year": yr,
                "coef": c,
                "se": se,
                "ci_lo": c - 1.96 * se,
                "ci_hi": c + 1.96 * se,
                "se_county": se_co,
                "ci_lo_county": c - 1.96 * se_co,
                "ci_hi_county": c + 1.96 * se_co,
            })

    result_df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    result_df["series"] = series_label
    result_df["dv"]     = dv_col

    coef_str = "  ".join(
        f"{r.year}: {r.coef:+.3f}" for _, r in result_df.iterrows()
    )
    print(f"    Coefficients: {coef_str}")
    return result_df


def plot_event_study(series_list: list, filename: str, title: str, caption: str):
    """
    Plot multiple first-differenced event study series on one chart.

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

    # Event markers
    for event_yr, event_label in EVENTS.items():
        ax.axvline(event_yr, color="#6b7280", lw=1.2, linestyle=":", alpha=0.8, zorder=1)
        ax.text(event_yr + 0.06, 0.88, event_label,
                transform=ax.get_xaxis_transform(),
                fontsize=8, color="#374151", ha="left", va="top",
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7))

    all_years = series_list[0][0]["year"].values
    ax.set_xticks(all_years)
    ax.set_xlabel("Year", fontsize=11)
    ax.set_ylabel("Ideology × Year Coefficient\n(relative to 2019 baseline, first-differenced)", fontsize=10)
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
    print("=== 09b_event_study_fd.py (First-Differenced) ===\n")

    for path in [PROCESSED / "panel_tract_year.csv", PROCESSED / "ideology_index.csv"]:
        if not path.exists():
            print(f"ERROR: {path} not found — run scripts 05 and 06 first")
            return

    df = load_panel()

    tesla    = run_event_study(df.copy(), "dlog_tesla_bev",    "Tesla BEV")
    nontesla = run_event_study(df.copy(), "dlog_nontesla_bev", "Non-Tesla BEV")
    truck    = run_event_study(df.copy(), "dlog_light_truck",  "Light Truck (Placebo)")

    # Save all coefficients
    all_coefs = pd.concat([tesla, nontesla, truck], ignore_index=True)
    out_cols = ["year", "coef", "se", "ci_lo", "ci_hi",
                "se_county", "ci_lo_county", "ci_hi_county", "series", "dv"]
    all_coefs[out_cols].to_csv(TABLES / "event_study_fd_coefs.csv", index=False)
    print(f"\n  Coefficients → output/tables/event_study_fd_coefs.csv")

    # Hero figure: Tesla vs. Non-Tesla (first-differenced)
    plot_event_study(
        series_list=[
            (tesla,    "#dc2626", "-",  "o", "Tesla BEV"),
            (nontesla, "#1e40af", "-",  "s", "Non-Tesla BEV"),
        ],
        filename="event_study_fd_tesla_vs_nontesla.png",
        title="The Elon Effect: Climate Ideology and EV Adoption Over Time\n"
              "First-Differenced Outcome — California Census Tracts, 2019–2024",
        caption=(
            "First-differenced within-tract OLS with year FE. Tract-clustered SEs. 95% CI shaded. "
            "2019 = base year (β = 0). DV: Δlog(EV+1), year-over-year change in stock "
            "(proxy for net new registrations). "
            "Vertical lines: Twitter acquisition (Oct 2022), DOGE/Trump admin (Nov 2024)."
        ),
    )

    # Placebo: trucks vs. non-Tesla (first-differenced)
    plot_event_study(
        series_list=[
            (truck,    "#16a34a", "--", "^", "Light Truck (Placebo)"),
            (nontesla, "#1e40af", "-",  "s", "Non-Tesla BEV"),
        ],
        filename="event_study_fd_truck_placebo.png",
        title="Placebo Check: Light Trucks vs. Non-Tesla EVs\n"
              "First-Differenced Outcome — California Census Tracts, 2019–2024",
        caption=(
            "First-differenced within-tract OLS with year FE. Tract-clustered SEs. 95% CI shaded. "
            "Light truck ideology coefficient should be negative or flat if the ideology-EV "
            "correlation is specific to green-signaling vehicles."
        ),
    )

    # End-of-script comparison: stock vs. FD for Tesla BEV
    stock_path = TABLES / "event_study_coefs.csv"
    if stock_path.exists():
        print("\n=== Stock vs. FD comparison: Tesla BEV ===")
        stock_all = pd.read_csv(stock_path)
        stock_tesla = stock_all[stock_all["series"] == "Tesla BEV"][["year", "coef"]].rename(
            columns={"coef": "Stock_coef"}
        )
        fd_tesla = tesla[["year", "coef"]].rename(columns={"coef": "FD_coef"})
        comparison = stock_tesla.merge(fd_tesla, on="year", how="outer").sort_values("year")
        comparison["Difference"] = comparison["FD_coef"] - comparison["Stock_coef"]
        header = f"{'Year':<6}  {'Stock_coef':>10}  {'FD_coef':>8}  {'Difference':>10}"
        print(header)
        print("-" * len(header))
        for _, row in comparison.iterrows():
            yr = int(row["year"]) if not pd.isna(row["year"]) else "?"
            sc = f"{row['Stock_coef']:+.4f}" if not pd.isna(row["Stock_coef"]) else "  n/a  "
            fc = f"{row['FD_coef']:+.4f}"    if not pd.isna(row["FD_coef"])    else "  n/a  "
            dc = f"{row['Difference']:+.4f}" if not pd.isna(row["Difference"]) else "  n/a  "
            print(f"{yr:<6}  {sc:>10}  {fc:>8}  {dc:>10}")
    else:
        print("\nNOTE: output/tables/event_study_coefs.csv not found — skipping stock vs. FD comparison.")

    print("\nDone. Outputs:")
    print("  output/figures/event_study_fd_tesla_vs_nontesla.png")
    print("  output/figures/event_study_fd_truck_placebo.png")
    print("  output/tables/event_study_fd_coefs.csv")


if __name__ == "__main__":
    main()
