# CLAUDE.md — Hummers or Hybrids Replication & Extension

## Project Overview

This project replicates and extends Kahn (2007), "Do greens drive Hummers or hybrids? Environmental ideology as a determinant of consumer choice," *Journal of Environmental Economics and Management*, 53(2), 129–145.

The original paper used California Green Party registration (2000) as an ideology proxy to show that environmentalists consume less gasoline, use more transit, buy more Priuses, and avoid Hummers. It used OLS and negative binomial regression on Census tract/zip-code data from the 2001 NHTS, 2000 Census, and 2005 RL Polk vehicle registrations (LA County only).

**Our goal:** Reframe the ideology construct around *beliefs about climate change* rather than party affiliation, replicate the core findings with modern data, and extend the analysis to the EV era — with a central focus on whether the Tesla brand has decoupled from climate ideology following Elon Musk's political pivot and his role in the Trump administration beginning in 2025.

**Target audience:** Substack and personal website (ryankvaughn.com). Writing should be clear and accessible — explain methods in plain language, lead with findings, use strong visuals. Avoid academic jargon without definition.

---

## Prompt Log

See [`PROMPT_LOG.md`](PROMPT_LOG.md) for a timestamped record of all user prompts and
Claude outputs for this project.

---

> **Skills for this project:**
> - `/hummers-methods` — Research questions, ideology construct, full methodology (Steps 1–6), assumptions and identification caveats
> - `/hummers-data` — Full data source specs (CEC, ACS, YCOM, voter reg, ballot measures, AFDC note)
> - `/hummers-backlog` — Open items, B1 slide fix history, B2 stock/flow issue and recommended fix

---

## Project Structure

```
hummers_or_hybrids_replication/
├── CLAUDE.md                        # This file
├── greens.pdf                       # Original Kahn (2007) paper
├── data/
│   ├── raw/                         # Raw downloads — never modified
│   │   ├── cec_zev/                 # CEC ZEV annual files
│   │   ├── acs/                     # ACS 5-year tables
│   │   ├── ycom/                    # Yale Climate Opinion Maps
│   │   ├── voter_registration/      # CA SoS voter reg data
│   │   ├── ballot_measures/         # CA SoS Statement of Vote
│   │   └── shapefiles/              # TIGER Census tract shapefiles
│   └── processed/                   # Cleaned, merged datasets
├── scripts/
│   ├── 01_acquire_cec.py            # Download/parse CEC ZEV data
│   ├── 02_acquire_acs.py            # Pull ACS via Census API
│   ├── 03_acquire_ideology.py       # YCOM, voter reg, ballot measures
│   ├── 04_crosswalk.py              # Precinct→tract & zip→tract crosswalks
│   ├── 05_build_panel.py            # Merge all data into tract×year panel
│   ├── 06_ideology_index.py         # PCA composite index, validation
│   ├── 07_replication.py            # Cross-section replication of Kahn
│   ├── 08_ev_panel.py               # EV panel regressions (main: tract + composite index)
│   ├── 09_event_study.py            # Elon Effect event study plot
│   ├── 10_robustness.py             # R1 (county/YCOM), R2 (tract/no YCOM), R3 (Prop 30 only)
│   └── 11_spatial.py               # Spatial autocorrelation & SDM
├── notebooks/
│   └── exploratory.ipynb            # EDA, maps, descriptive stats
├── output/
│   ├── tables/                      # Regression tables (CSV + formatted)
│   └── figures/                     # Maps, event study plots, charts
└── paper/
    └── draft.md                     # Substack/website draft
```

---

## Language & Tools

- **Python** — primary language
- **pandas, geopandas** — data wrangling and spatial joins
- **scikit-learn** — PCA for ideology index
- **statsmodels** — OLS, negative binomial, panel models
- **linearmodels** — two-way fixed effects panel models
- **pysal / libpysal** — spatial weights, Moran's I, spatial regression
- **matplotlib / seaborn** — figures and event study plots
- **Census API / censusdatadownloader** — ACS data acquisition
- **tabulate / great_tables** — formatted output tables

---

## Project Status (updated 2026-02-28)

**The full analysis pipeline is complete.** All scripts 01–11 have been written and run successfully. The paper draft (`paper/draft.md`) contains rendered results tables and references generated figures.

| Script | Output | Status |
|---|---|---|
| `01_acquire_cec.py` | `data/raw/cec_zev/cec_panel_zev.csv` | Complete |
| `02_acquire_acs.py` | `data/raw/acs/acs_tracts_ca_2023.csv` | Complete |
| `03_acquire_ideology.py` | YCOM, voter reg, ballot measure raw files | Complete |
| `04_crosswalk.py` | 4 crosswalk CSVs in `data/processed/` | Complete |
| `05_build_panel.py` | `data/processed/panel_tract_year.parquet` (tract × year, 2018–2024) | Complete |
| `06_ideology_index.py` | PCA composite index; PC1 = 84.7% variance; `data/processed/ideology_tract.parquet` | Complete |
| `07_replication.py` | OLS transit/drive-alone + log-OLS EV; replication tables in `output/tables/` | Complete |
| `08_ev_panel.py` | Year-FE panel: Tesla +5.0%, non-Tesla EV +6.1%, light truck −2.3% per SD ideology | Complete |
| `09_event_study.py` | Elon Effect event study; Tesla ideology link stable post-2022; non-Tesla democratized | Complete |
| `10_robustness.py` | R1/R2/R3 robustness tables; main results hold across all ideology specs | Complete |
| `11_spatial.py` | Moran's I = 0.58 (transit), 0.41 (drive-alone); SAR ρ = 0.78 / 0.57; results survive | Complete |
| `paper/draft.md` | Full Substack draft with rendered tables and figure references | Complete |
| `paper/draft_revised.md` | Author reply to peer review; FD event study discussion | Complete (John) |
| `paper/slides.tex` | Beamer deck rebuilt 2026-02-28; all major frame overflows fixed | Complete |

**Open items / known gaps:**
1. `data/raw/afdc/` is empty — EV charger density never acquired; omitted from all models
2. Time-varying ACS controls deferred; noted in Technical Appendix
3. GitHub repo link placeholder in `paper/draft.md` — fill before publishing
4. 2025 CEC data not yet available; would strengthen Elon Effect test
5. **B2 (open):** Stock vs. flow issue in event study — CEC data is stock, not flow; recommended fix is first-differenced outcome `Δlog(Tesla+1)`. Full analysis in `/hummers-backlog` skill.

---

## Data Integrity — No Fabricated Quantitative Values

**Full rule is in `~/Projects/CLAUDE.md`. This section adds project-specific enforcement.**

Claude must never generate, hardcode, or invent any quantitative value — including numbers, thresholds, arrays, vectors, matrices, ideology scores, vote shares, EV counts, or classification cutoffs — unless it is read from an existing project data file, derived from one by documented computation, a universally-known constant, or a value pre-specified in the research design and explicitly confirmed by the PI.

**Critical for this project:** Do not construct or impute ideology index values, climate belief scores, or political registration shares for any geographic unit before the underlying source files (YCOM, CA SoS voter registration, statement of vote CSVs, CEC ZEV data) have been downloaded and verified. Do not create placeholder panels or example regression outputs with invented coefficients.

Any threshold, PCA component weight, ideology index scaling decision, or event-study parameter not directly output by a script reading project data files requires the confirmation protocol in `~/Projects/CLAUDE.md`.

---

## Shared Utilities

The `scripts/02_acquire_acs.py` and `scripts/04_crosswalk.py` scripts in this
project were the **original source** for the following reusable utility modules,
now published at https://github.com/rkvaughn/python-geo-utils:

| Utility | Originated from |
|---------|----------------|
| `census_api.py` | `scripts/02_acquire_acs.py` — Census API batch fetcher pattern |
| `geo_crosswalk.py` | `scripts/04_crosswalk.py` — ZCTA→tract, county→tract, precinct→tract |
| `download_utils.py` | `scripts/04_crosswalk.py` — `download_zip` helper |

If you need to extend any crosswalk or Census API logic for future work on this
project, check the canonical utilities repo first. If the canonical version
doesn't cover the new case, update it there and note the change.

**Do not rewrite these patterns inline** — the utility modules exist precisely
to avoid diverging implementations across projects.

---

## Instructions for Claude

- Working directory: `~/Projects/hummers_or_hybrids_replication/`
- Raw data goes in `data/raw/` — never overwrite or modify after download; re-download if needed
- Scripts are numbered and self-contained; each reads from `data/raw/` or `data/processed/` and writes output to `data/processed/` or `output/`
- Prefer reproducible acquisition (API calls, direct URLs with `requests`/`wget`) over manual downloads; document all source URLs in comments at the top of each acquisition script
- Every regression: print a summary, save table to `output/tables/` as both CSV and a readable text/HTML format
- Every figure: save to `output/figures/` as PNG (300 dpi) and include a plain-language caption
- Before any merge: verify that geographic identifiers align (tract FIPS format, zip code format, vintage year of shapefiles matches data year)
- Flag methodology decisions that require user input before proceeding — do not silently make assumptions
- When writing the paper draft, write for a general educated audience (Substack). Define all technical terms on first use. Lead each section with the finding, not the method.
- All assumptions and identification limitations must be explicitly stated in the appropriate script comments and in the paper draft's caveats section
