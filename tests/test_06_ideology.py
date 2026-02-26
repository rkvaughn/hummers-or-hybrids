"""Validation checks for ideology_index.csv output."""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX = ROOT / "data" / "processed" / "ideology_index.csv"
LOADINGS = ROOT / "output" / "tables" / "pca_loadings.csv"


def test_index_exists():
    assert INDEX.exists(), "ideology_index.csv not found — run 06_ideology_index.py first"


def test_index_columns():
    df = pd.read_csv(INDEX, nrows=1)
    assert "tract_geoid_20" in df.columns
    assert "climate_ideology_index" in df.columns


def test_index_shape():
    df = pd.read_csv(INDEX)
    assert len(df) > 8_000, f"Too few tracts: {len(df)}"
    assert df["tract_geoid_20"].nunique() == len(df), "Duplicate tracts in ideology index"


def test_index_standardized():
    df = pd.read_csv(INDEX)
    idx = df["climate_ideology_index"].dropna()
    assert abs(idx.mean()) < 0.1, f"Index mean not near 0: {idx.mean():.3f}"
    assert 0.8 < idx.std() < 1.2, f"Index std not near 1: {idx.std():.3f}"


def test_loadings_exist():
    assert LOADINGS.exists(), "pca_loadings.csv not found"


def test_loadings_columns():
    df = pd.read_csv(LOADINGS)
    assert "loading_pc1" in df.columns, "loading_pc1 column missing from PCA loadings"
    assert "variable" in df.columns, "variable column missing from PCA loadings"


if __name__ == "__main__":
    import pytest, sys
    sys.exit(pytest.main([__file__, "-v"]))
