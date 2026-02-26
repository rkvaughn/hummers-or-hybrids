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
import numpy as np

ROOT = Path(__file__).parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(exist_ok=True)


def weighted_sum_to_tract(df_unit: pd.DataFrame, unit_col: str,
                           value_cols: list, xwalk: pd.DataFrame,
                           xwalk_unit_col: str) -> pd.DataFrame:
    """
    Crosswalk unit-level data to Census tracts via weighted allocation.
    Distributes value_cols across overlapping tracts using weight column.
    Returns DataFrame with columns [tract_geoid_20] + value_cols aggregated by tract.
    """
    n_units_before = df_unit[unit_col].nunique()
    merged = df_unit.merge(
        xwalk[[xwalk_unit_col, "tract_geoid_20", "weight"]],
        left_on=unit_col, right_on=xwalk_unit_col, how="left"
    )
    unmatched = merged[merged["weight"].isna()][unit_col].nunique()
    if unmatched > 0:
        pct = unmatched / n_units_before * 100
        print(f"    WARNING: {unmatched}/{n_units_before} ({pct:.1f}%) {unit_col} values "
              f"had no crosswalk match and will be excluded")
    merged = merged[merged["weight"].notna()]
    for col in value_cols:
        merged[col] = merged[col] * merged["weight"]
    return (
        merged.groupby("tract_geoid_20")[value_cols]
        .sum()
        .reset_index()
    )


def build_vehicle_panel() -> pd.DataFrame:
    print("  [1] Building vehicle panel from CEC ZEV data...")
    zev = pd.read_csv(RAW / "cec_zev" / "cec_panel_zev.csv", dtype={"zip_code": str})
    light = pd.read_csv(RAW / "cec_zev" / "cec_panel_light.csv", dtype={"zip_code": str})
    xwalk = pd.read_csv(PROCESSED / "crosswalk_zip_tract.csv",
                        dtype={"zcta5": str, "tract_geoid_20": str})

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


def build_ycom_tract() -> pd.DataFrame:
    print("  [2] Assigning YCOM county beliefs to tracts...")
    ycom = pd.read_csv(RAW / "ycom" / "ycom_ca_counties.csv", dtype={"county_fips": str})
    xwalk = pd.read_csv(PROCESSED / "crosswalk_county_tract.csv",
                        dtype={"county_fips": str, "tract_geoid_20": str})

    ycom_cols = [c for c in ycom.columns if c not in ("county_fips", "county_name")]
    ycom = ycom[["county_fips"] + ycom_cols].copy()
    ycom["county_fips"] = ycom["county_fips"].str.zfill(5)

    tract_ycom = xwalk.merge(ycom, on="county_fips", how="left")
    rename = {c: f"ycom_{c}" for c in ycom_cols}
    ycom_null_rate = tract_ycom[list(rename.keys())].isnull().mean().mean() * 100
    if ycom_null_rate > 1:
        print(f"    WARNING: YCOM null rate after county merge: {ycom_null_rate:.1f}% — check county_fips format")
    else:
        print(f"    YCOM null rate: {ycom_null_rate:.1f}% (expected 0)")
    tract_ycom = tract_ycom.rename(columns=rename)[["tract_geoid_20"] + list(rename.values())]
    print(f"    YCOM tract table: {len(tract_ycom):,} rows")
    return tract_ycom


def build_votreg_tract() -> pd.DataFrame:
    """
    Aggregate voter registration to county level, then assign county value
    to all tracts in the county (same approach as YCOM).

    Note: SWDB registration precincts use RGPREC_KEY (13-char) which does not
    match the MPREC shapefile PREC_KEY (11-char) used by the precinct→tract
    crosswalk. County-level aggregation via the FIPS column is used instead.
    """
    print("  [3] Crosswalking voter registration to tracts (county-level)...")
    votreg_path = RAW / "voter_registration" / "votreg_ca_raw.csv"
    if not votreg_path.exists():
        print("    WARNING: votreg_ca_raw.csv not found — skipping voter reg")
        return pd.DataFrame(columns=["tract_geoid_20", "dem_minus_rep"])

    xwalk = pd.read_csv(PROCESSED / "crosswalk_county_tract.csv",
                        dtype={"county_fips": str, "tract_geoid_20": str})
    votreg = pd.read_csv(votreg_path, dtype=str, low_memory=False)
    votreg.columns = [c.upper().strip() for c in votreg.columns]
    # Deduplicate column names — stacking g22+g20 files can produce duplicates
    votreg = votreg.loc[:, ~votreg.columns.duplicated(keep="first")]

    # Filter to g22 registration snapshot
    if "ELECTION" in votreg.columns:
        g22 = votreg[votreg["ELECTION"].str.lower() == "g22"].copy()
        if len(g22) > 0:
            votreg = g22
            print(f"    Using g22 election data: {len(votreg):,} precincts")

    if "FIPS" not in votreg.columns:
        print(f"    WARNING: FIPS column not found. Available: {list(votreg.columns[:15])}")
        return pd.DataFrame(columns=["tract_geoid_20", "dem_minus_rep"])

    dem_col = next((c for c in votreg.columns if c in ("DEM", "DEM_REG", "DEM_1")), None)
    rep_col = next((c for c in votreg.columns if c in ("REP", "REP_REG", "REP_1")), None)
    if dem_col is None or rep_col is None:
        print(f"    WARNING: DEM/REP columns not found. Available: {list(votreg.columns[:20])}")
        return pd.DataFrame(columns=["tract_geoid_20", "dem_minus_rep"])

    votreg["county_fips"] = votreg["FIPS"].astype(str).str.zfill(5)
    votreg[dem_col] = pd.to_numeric(votreg[dem_col], errors="coerce").fillna(0)
    votreg[rep_col] = pd.to_numeric(votreg[rep_col], errors="coerce").fillna(0)

    # Aggregate to county
    county_reg = votreg.groupby("county_fips")[[dem_col, rep_col]].sum().reset_index()
    county_reg["total_reg"] = county_reg[dem_col] + county_reg[rep_col]
    county_reg["dem_minus_rep"] = (
        (county_reg[dem_col] - county_reg[rep_col])
        / county_reg["total_reg"].replace(0, np.nan)
    )
    print(f"    County voter reg: {len(county_reg)} counties aggregated")

    # Assign county value to all tracts in that county
    result = xwalk.merge(county_reg[["county_fips", "dem_minus_rep"]],
                         on="county_fips", how="left")
    null_pct = result["dem_minus_rep"].isna().mean() * 100
    if null_pct > 1:
        print(f"    WARNING: dem_minus_rep null rate: {null_pct:.1f}%")
    else:
        print(f"    dem_minus_rep null rate: {null_pct:.1f}% (expected 0)")
    result = result[["tract_geoid_20", "dem_minus_rep"]]
    print(f"    Voter reg tract table: {len(result):,} rows")
    return result


def _extract_prop_share(df: pd.DataFrame, yes_col: str, no_col: str) -> pd.Series:
    yes = pd.to_numeric(df[yes_col], errors="coerce").fillna(0)
    no = pd.to_numeric(df[no_col], errors="coerce").fillna(0)
    total = yes + no
    return (yes / total.replace(0, pd.NA)).fillna(0)


def build_ballot_tract() -> pd.DataFrame:
    """
    Aggregate ballot measure votes to county level, then assign county value
    to all tracts in the county (same approach as YCOM).

    Note: SWDB ballot data uses SVPREC_KEY (voting precinct, 11-char) which does
    not match the MPREC shapefile PREC_KEY (11-char, different numbering) used
    by the precinct→tract crosswalk. County-level aggregation via the FIPS
    column is used instead.
    """
    print("  [4] Crosswalking ballot measures to tracts (county-level)...")

    xwalk = pd.read_csv(PROCESSED / "crosswalk_county_tract.csv",
                        dtype={"county_fips": str, "tract_geoid_20": str})

    ballot_configs = [
        ("ballots_g22_raw.csv", "prop30_yes_share", "PR_30_Y", "PR_30_N"),
        ("ballots_p18_raw.csv", "prop68_yes_share", "PR_68_Y", "PR_68_N"),
    ]

    county_results = {}
    for fname, out_col, yes_col, no_col in ballot_configs:
        bpath = RAW / "ballot_measures" / fname
        if not bpath.exists():
            print(f"    WARNING: {fname} not found — skipping {out_col}")
            continue

        df = pd.read_csv(bpath, dtype=str, low_memory=False)
        df.columns = [c.upper().strip() for c in df.columns]

        actual_yes = next((c for c in df.columns if c == yes_col), None)
        actual_no = next((c for c in df.columns if c == no_col), None)
        if actual_yes is None or actual_no is None:
            prop_cols = [c for c in df.columns if c.startswith("PR_")]
            print(f"    WARNING: {yes_col}/{no_col} not found. Prop cols: {prop_cols[:20]}")
            continue

        if "FIPS" not in df.columns:
            print(f"    WARNING: FIPS column not found in {fname}")
            continue

        df["county_fips"] = df["FIPS"].astype(str).str.zfill(5)
        df[actual_yes] = pd.to_numeric(df[actual_yes], errors="coerce").fillna(0)
        df[actual_no] = pd.to_numeric(df[actual_no], errors="coerce").fillna(0)

        # Aggregate to county
        county = df.groupby("county_fips")[[actual_yes, actual_no]].sum().reset_index()
        county["_total"] = county[actual_yes] + county[actual_no]
        county[out_col] = county[actual_yes] / county["_total"].replace(0, np.nan)
        print(f"    {out_col}: {len(county)} counties aggregated "
              f"(mean share: {county[out_col].mean():.3f})")
        county_results[out_col] = county[["county_fips", out_col]]

    if not county_results:
        return pd.DataFrame(columns=["tract_geoid_20", "prop30_yes_share", "prop68_yes_share"])

    # Merge all county-level ballot results together
    county_df = list(county_results.values())[0]
    for other in list(county_results.values())[1:]:
        county_df = county_df.merge(other, on="county_fips", how="outer")

    # Assign county values to all tracts in that county
    result = xwalk.merge(county_df, on="county_fips", how="left")
    for col in county_results:
        null_pct = result[col].isna().mean() * 100
        if null_pct > 1:
            print(f"    WARNING: {col} null rate: {null_pct:.1f}%")
        else:
            print(f"    {col} null rate: {null_pct:.1f}% (expected 0)")
    result = result[["tract_geoid_20"] + list(county_results.keys())]
    print(f"    Ballot tract table: {len(result):,} rows")
    return result


def build_acs_tract() -> pd.DataFrame:
    print("  [5] Loading ACS demographics...")
    acs = pd.read_csv(RAW / "acs" / "acs_tracts_ca_clean.csv", dtype={"geoid": str})

    acs["pct_ba_plus"] = acs["pop_ba_degree"] / acs["pop_25plus"].replace(0, np.nan)
    acs["pct_white"] = acs["pop_nh_white"] / acs["pop_race_total"].replace(0, np.nan)
    acs["pct_black"] = acs["pop_nh_black"] / acs["pop_race_total"].replace(0, np.nan)
    acs["pct_asian"] = acs["pop_nh_asian"] / acs["pop_race_total"].replace(0, np.nan)
    acs["pct_hispanic"] = acs["pop_hispanic"] / acs["pop_race_total"].replace(0, np.nan)
    acs["pct_transit"] = acs["workers_transit"] / acs["workers_total"].replace(0, np.nan)
    acs["pct_drove_alone"] = acs["workers_drove_alone"] / acs["workers_total"].replace(0, np.nan)
    acs["pct_wfh"] = acs["workers_wfh"] / acs["workers_total"].replace(0, np.nan)
    acs["log_median_hh_income"] = acs["median_hh_income"].apply(
        lambda x: np.nan if pd.isna(x) or x <= 0 else np.log(x)
    )
    # Population density: use total_pop as proxy (land area not in API response)
    # A rough density can be computed if shapefile area is available; placeholder here
    acs["pop_density"] = acs["total_pop"]  # will be refined if land area available

    keep = [
        "geoid", "total_pop", "median_hh_income", "log_median_hh_income",
        "median_home_value", "pop_density", "pct_ba_plus", "pct_white", "pct_black",
        "pct_asian", "pct_hispanic", "pct_transit", "pct_drove_alone", "pct_wfh",
    ]
    acs = acs[[c for c in keep if c in acs.columns]].rename(columns={"geoid": "tract_geoid_20"})
    print(f"    ACS tract table: {len(acs):,} tracts")
    return acs


def main():
    print("=== 05_build_panel.py ===\n")

    veh = build_vehicle_panel()
    ycom = build_ycom_tract()
    votreg = build_votreg_tract()
    ballot = build_ballot_tract()
    acs = build_acs_tract()

    panel = veh.copy()
    panel["tract_geoid_20"] = panel["tract_geoid_20"].astype(str)

    for label, df in [("YCOM", ycom), ("voter reg", votreg),
                      ("ballot", ballot), ("ACS", acs)]:
        df["tract_geoid_20"] = df["tract_geoid_20"].astype(str)
        n_before = panel["tract_geoid_20"].nunique()
        panel = panel.merge(df, on="tract_geoid_20", how="left")
        n_after = panel["tract_geoid_20"].nunique()
        print(f"  After {label} join: {len(panel):,} rows, tract coverage {n_after}/{n_before}")

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
