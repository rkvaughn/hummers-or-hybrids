#!/usr/bin/env python3
"""
12_component_maps.py — Generate county choropleth maps for each ideology component.

Produces one PNG per ideology component in output/figures/:
    map_ycom_happening.png
    map_ycom_worried.png
    map_ycom_human.png
    map_ycom_regulate.png
    map_ycom_supportRPS.png
    map_dem_minus_rep.png
    map_prop30_yes_share.png
    map_prop68_yes_share.png

These maps are referenced in the appendix slides of paper/slides.tex.

Data sources (all pre-existing in data/raw/ or data/processed/):
    - data/processed/ideology_tract.parquet  (one row per tract, all ideology columns)
    - data/raw/shapefiles/tl_2020_06_tract/  (TIGER tract shapefile, dissolved to county)

Run after 05_build_panel.py and 06_ideology_index.py have been executed.
"""

from pathlib import Path

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
from matplotlib.colors import Normalize
from mpl_toolkits.axes_grid1 import make_axes_locatable

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.parent
PROC    = ROOT / "data" / "processed"
SHAPES  = ROOT / "data" / "raw" / "shapefiles"
OUTFIG  = ROOT / "output" / "figures"
OUTFIG.mkdir(parents=True, exist_ok=True)

CRS_CA = "EPSG:3310"   # CA Albers Equal Area — equal-area projection for maps

# ── Component metadata ─────────────────────────────────────────────────────────
# Each tuple: (column_name, title, subtitle, colormap, data_format)
COMPONENTS = [
    (
        "ycom_happening",
        "Climate Change Is Happening",
        "YCOM: % of county agreeing (2023 estimates)",
        "YlOrRd",
        "percent",
    ),
    (
        "ycom_worried",
        "Worried About Climate Change",
        "YCOM: % of county who are worried (2023 estimates)",
        "YlOrRd",
        "percent",
    ),
    (
        "ycom_human",
        "Climate Change Is Human-Caused",
        "YCOM: % attributing CC primarily to human activity (2023 estimates)",
        "YlOrRd",
        "percent",
    ),
    (
        "ycom_regulate",
        "Support Climate Regulation",
        "YCOM: % supporting CO\u2082 regulation (2023 estimates)",
        "YlOrRd",
        "percent",
    ),
    (
        "ycom_supportRPS",
        "Support Renewable Portfolio Standard",
        "YCOM: % supporting renewable energy mandates (2023 estimates)",
        "YlOrRd",
        "percent",
    ),
    (
        "dem_minus_rep",
        "Democrat \u2212 Republican Registration Share",
        "CA SoS voter registration (g22 vintage): (DEM \u2212 REP) / total registered",
        "RdBu",
        "fraction",
    ),
    (
        "prop30_yes_share",
        "Prop 30 YES Share (2022)",
        "EV charging / wildfire funding measure \u2014 YES / (YES + NO) per county",
        "YlOrRd",
        "fraction",
    ),
    (
        "prop68_yes_share",
        "Prop 68 YES Share (2018)",
        "Environmental bond measure \u2014 YES / (YES + NO) per county",
        "YlOrRd",
        "fraction",
    ),
]


# ── Load and prepare data ──────────────────────────────────────────────────────

def load_county_ideology() -> pd.DataFrame:
    """
    Load ideology_tract.parquet; drop duplicates to get one row per county.
    All ideology columns are county-level constants (assigned uniformly to tracts).
    Returns a DataFrame indexed by county_fips (first 5 chars of tract GEOID).
    """
    ideo_path = PROC / "ideology_tract.parquet"
    if not ideo_path.exists():
        raise FileNotFoundError(
            f"ideology_tract.parquet not found at {ideo_path}.\n"
            "Run scripts/06_ideology_index.py first."
        )

    df = pd.read_parquet(ideo_path)
    print(f"  Loaded ideology_tract.parquet: {len(df):,} tract rows")

    # Derive county_fips from tract GEOID (first 5 chars)
    geoid_col = next(
        (c for c in df.columns if c.lower() in ("geoid", "tract_geoid_20", "tract_geoid")),
        None,
    )
    if geoid_col is None:
        # Fall back: use index if it looks like a GEOID
        if str(df.index[0]).startswith("06") and len(str(df.index[0])) == 11:
            df = df.reset_index().rename(columns={"index": "geoid"})
            geoid_col = "geoid"
        else:
            raise KeyError(
                f"Cannot find GEOID column. Available columns: {list(df.columns)}"
            )

    df["county_fips"] = df[geoid_col].astype(str).str[:5]

    # Ideology is county-constant; drop duplicates to get one row per county
    cols = ["county_fips"] + [c for c, *_ in COMPONENTS if c in df.columns]
    available = [c for c in cols if c in df.columns]
    missing   = [c for c, *_ in COMPONENTS if c not in df.columns]
    if missing:
        print(f"  WARNING: ideology columns not found (may need re-run of 06): {missing}")

    county_df = df[available].drop_duplicates("county_fips").set_index("county_fips")
    print(f"  Unique counties in ideology data: {len(county_df)}")
    return county_df


def load_county_shapes() -> gpd.GeoDataFrame:
    """
    Load the CA 2020 Census tract shapefile; dissolve to county by GEOID[:5].
    Returns a GeoDataFrame with one row per county, indexed by county_fips.
    """
    tract_shp_dir = SHAPES / "tl_2020_06_tract"
    shp_files = list(tract_shp_dir.rglob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(
            f"No .shp found in {tract_shp_dir}. "
            "Run scripts/04_crosswalk.py first to download the shapefile."
        )

    tracts = gpd.read_file(shp_files[0])
    print(f"  Loaded tract shapefile: {len(tracts):,} tracts, CRS={tracts.crs}")

    geoid_col = next(
        (c for c in tracts.columns if c.upper() == "GEOID"), None
    )
    if geoid_col is None:
        raise KeyError(f"No GEOID column in tract shapefile. Columns: {list(tracts.columns)}")

    tracts["county_fips"] = tracts[geoid_col].astype(str).str[:5]
    tracts = tracts.to_crs(CRS_CA)

    counties = tracts.dissolve(by="county_fips", as_index=False)[["county_fips", "geometry"]]
    counties = counties.set_index("county_fips")
    print(f"  Dissolved to {len(counties)} counties")
    return counties


# ── Plotting ───────────────────────────────────────────────────────────────────

def make_map(
    gdf: gpd.GeoDataFrame,
    column: str,
    title: str,
    subtitle: str,
    cmap: str,
    data_format: str,
    out_path: Path,
) -> None:
    """
    Draw a county choropleth map for a single ideology component and save to disk.

    Parameters
    ----------
    gdf         : GeoDataFrame with geometry + ideology column, indexed by county_fips
    column      : column name to map
    title       : map title (bold)
    subtitle    : subtitle / source note
    cmap        : matplotlib colormap name
    data_format : 'percent' (0-100 scale) or 'fraction' (-1 to 1 or 0 to 1)
    out_path    : output PNG path
    """
    if column not in gdf.columns:
        print(f"  [skip] {column} not found in GeoDataFrame — cannot generate map.")
        return

    fig, ax = plt.subplots(1, 1, figsize=(9, 10))

    vmin = gdf[column].quantile(0.02)
    vmax = gdf[column].quantile(0.98)

    # For dem_minus_rep, center colormap at 0
    if data_format == "fraction" and column == "dem_minus_rep":
        extreme = max(abs(vmin), abs(vmax))
        vmin, vmax = -extreme, extreme

    norm = Normalize(vmin=vmin, vmax=vmax)
    sm   = mpl.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])

    gdf.plot(
        column=column,
        ax=ax,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        edgecolor="white",
        linewidth=0.3,
        missing_kwds={"color": "lightgrey", "label": "No data"},
    )

    # Colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="4%", pad=0.05)
    cb  = fig.colorbar(sm, cax=cax)
    cb.ax.tick_params(labelsize=8)

    if data_format == "percent":
        cb.ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.0f%%"))
    else:
        cb.ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))

    # Labels and styling
    ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
    ax.set_xlabel(subtitle, fontsize=8, color="gray")
    ax.set_axis_off()

    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved → {out_path.name}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("12_component_maps.py — Ideology component maps")
    print("=" * 60)

    print("\n[1] Loading county ideology data...")
    ideo = load_county_ideology()

    print("\n[2] Loading and dissolving county shapefiles...")
    counties = load_county_shapes()

    # Merge ideology onto county shapes
    gdf = counties.join(ideo, how="left")
    print(f"\n  Merged GDF: {len(gdf)} counties, columns: {list(ideo.columns)}")

    print("\n[3] Generating maps...")
    generated = 0
    for col, title, subtitle, cmap, fmt in COMPONENTS:
        out_path = OUTFIG / f"map_{col}.png"
        make_map(
            gdf=gdf,
            column=col,
            title=title,
            subtitle=subtitle,
            cmap=cmap,
            data_format=fmt,
            out_path=out_path,
        )
        generated += 1

    print(f"\n{'=' * 60}")
    print(f"Done. {generated} maps saved to {OUTFIG}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
