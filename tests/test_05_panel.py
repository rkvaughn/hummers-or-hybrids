"""Validation checks for panel_tract_year.csv output."""
import pandas as pd
from pathlib import Path

PANEL = Path("data/processed/panel_tract_year.csv")

def test_panel_exists():
    assert PANEL.exists(), "panel_tract_year.csv not found — run 05_build_panel.py first"

def test_panel_shape():
    df = pd.read_csv(PANEL, dtype={"tract_geoid_20": str})
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
