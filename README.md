# Hummers or Hybrids? Climate Ideology and EV Adoption in California

A replication and extension of Kahn (2007), *"Do greens drive Hummers or hybrids? Environmental ideology as a determinant of consumer choice,"* JEEM 53(2).

**Research questions:**
1. Do California communities with stronger climate change beliefs still exhibit lower-carbon transportation behavior today?
2. Does climate ideology predict EV ownership — and does it predict *Tesla* ownership differently from *non-Tesla EV* ownership?
3. Has the correlation between climate ideology and Tesla ownership shifted following Elon Musk's political pivot and his role in the Trump administration?

See [`CLAUDE.md`](CLAUDE.md) for full project overview, methodology, and data sources.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Data Acquisition

Run scripts in order. Each script downloads raw data to `data/raw/` and writes cleaned outputs to `data/processed/`.

```bash
python scripts/01_acquire_cec.py       # CEC ZEV population data (2010–2024)
python scripts/02_acquire_acs.py       # ACS 5-year tract-level demographics
python scripts/03_acquire_ideology.py  # YCOM, voter registration, ballot measures
python scripts/04_crosswalk.py         # Geographic crosswalk tables
python scripts/05_build_panel.py       # Merge into tract×year panel
```

## Geographic Crosswalks (Script 04)

Script 04 builds four crosswalk tables:

| Output | Mapping | Method |
|--------|---------|--------|
| `crosswalk_zip_tract.csv` | ZCTA → 2020 Census tract | Area-proportional weights |
| `crosswalk_prec_tract_g22.csv` | 2022 precinct → 2020 Census tract | GeoPandas spatial overlay |
| `crosswalk_prec_tract_p18.csv` | 2018 precinct → 2020 Census tract | GeoPandas spatial overlay |
| `crosswalk_county_tract.csv` | County FIPS → 2020 Census tract | GEOID prefix lookup |

All crosswalks target **2020 Census tract definitions** to align with the 2023 ACS.

## Data Sources

- **CEC ZEV Population Data**: https://www.energy.ca.gov/zevstats
- **ACS 5-Year Estimates**: US Census Bureau API
- **Yale Climate Opinion Maps (YCOM)**: https://climatecommunication.yale.edu/visualizations-data/ycom-us/
- **CA Voter Registration**: CA Secretary of State
- **CA Statement of Vote**: CA Secretary of State
- **Precinct Shapefiles**: UC Berkeley Statewide Database
- **TIGER/Line Tracts**: US Census Bureau

## Project Structure

```
scripts/          Analysis pipeline (numbered, self-contained)
data/
  raw/            Downloaded source data (gitignored)
  processed/      Cleaned outputs (gitignored)
  assumptions/    Methodology documentation
paper/            Substack/website draft
notebooks/        Exploratory analysis
output/           Figures and tables (gitignored)
```
