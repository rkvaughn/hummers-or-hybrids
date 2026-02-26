# CLAUDE.md — Hummers or Hybrids Replication & Extension

## Project Overview

This project replicates and extends Kahn (2007), "Do greens drive Hummers or hybrids? Environmental ideology as a determinant of consumer choice," *Journal of Environmental Economics and Management*, 53(2), 129–145.

The original paper used California Green Party registration (2000) as an ideology proxy to show that environmentalists consume less gasoline, use more transit, buy more Priuses, and avoid Hummers. It used OLS and negative binomial regression on Census tract/zip-code data from the 2001 NHTS, 2000 Census, and 2005 RL Polk vehicle registrations (LA County only).

**Our goal:** Reframe the ideology construct around *beliefs about climate change* rather than party affiliation, replicate the core findings with modern data, and extend the analysis to the EV era — with a central focus on whether the Tesla brand has decoupled from climate ideology following Elon Musk's political pivot and his role in the Trump administration beginning in 2025.

**Target audience:** Substack and personal website (ryankvaughn.com). Writing should be clear and accessible — explain methods in plain language, lead with findings, use strong visuals. Avoid academic jargon without definition.

---

## Research Questions

1. **Replication:** Do California communities with stronger climate change beliefs still exhibit lower-carbon transportation behavior (less gas, more transit, fewer trucks) today?
2. **EV Extension:** Does climate change ideology predict EV ownership? Does it predict *Tesla* ownership differently from *non-Tesla EV* ownership?
3. **The Elon Effect:** Has the correlation between climate ideology and Tesla ownership shifted over time — particularly following Elon Musk's Twitter acquisition (Oct 2022) and his prominent role in the Trump administration (2025)? Does the same shift appear for other EV brands (placebo test)?
4. **Status Signaling:** Has the "green status signal" migrated away from Tesla toward other EV brands among high-ideology communities?

---

## Ideology Construct

**Reframe from original:** Kahn used Green Party registration as a crude proxy for "environmentalism." We reframe the underlying construct as **climate change beliefs** — the degree to which a community accepts the scientific consensus on climate change and supports climate action.

### Primary Measures (composite index)

1. **Yale Climate Opinion Maps (YCOM)** — Yale Program on Climate Change Communication estimates of climate beliefs at the county level via multilevel regression and poststratification (MrP). Key variables: "% who think climate change is happening," "% who are worried," "% who support climate policies." Available at county level; crosswalk to tract using county FIPS.
   - Source: https://climatecommunication.yale.edu/visualizations-data/ycom-us/

2. **Party registration share** — Democratic minus Republican registration share at the Census tract level (California Secretary of State voter file). Not a direct measure of climate beliefs, but a useful structural predictor; include separately from YCOM and in the composite.

3. **Environmental ballot measure vote share** — California Secretary of State Statement of Vote, precinct level, aggregated to Census tract via population-weighted area interpolation.
   - **Primary:** Prop 30 (2022) — EV charging/wildfire funding. Most directly climate-relevant.
   - **Secondary:** Prop 20 (2020), Prop 68 (2018) — additional environmental measures for index construction.
   - **Placebo/control:** Prop 7 (2018) — daylight saving time (unrelated to climate, tests for general liberal voting vs. climate-specific beliefs).

### Composite Climate Ideology Index
Construct via principal component analysis (PCA) across: YCOM belief measures, Dem−Rep registration share, and environmental ballot measure vote shares. Retain first principal component as the index. Validate by correlating with Congressional LCV scores for California districts.

### Appendix Robustness Checks (deferred)
- **Time-varying demographic controls:** The main analysis uses 2023 ACS controls (2020 tract definitions) as a single cross-section applied to the full 2018–2024 vehicle panel. A cleaner but more complex alternative is to use 2019 ACS controls (2015–2019 5-year) for early panel years and 2023 ACS for later years. This requires re-tabulating 2019 ACS data to 2020 tract boundaries using the NHGIS tract-to-tract crosswalk (https://www.nhgis.org/geographic-crosswalks), which involves population-weighted interpolation across the ~1,072 tracts that changed between 2010 and 2020 definitions. Implement and report in the appendix.

### Ideology Robustness Checks (three tiers)
1. **County level, YCOM only** — run all main models aggregated to county, using YCOM measures directly. Maximizes measurement quality of the ideology variable; sacrifices geographic granularity. Tests whether findings hold when ideology is cleanly measured but spatial variation is coarse.
2. **Tract level, no YCOM** — run all main models at Census tract level using only voter registration share and ballot measure vote shares. Maximizes geographic granularity; ideology construct is narrower (behavioral/revealed preference only, no survey beliefs). Tests whether findings hold without the county-level YCOM assumption.
3. **Prop 30 vote share alone** — single-measure alternative at tract level. Most directly climate-relevant ballot measure; simplest possible specification.
4. **Party registration share alone** — most structurally comparable to Kahn's original Green Party proxy.

---

## Data Sources

### Vehicle Data
- **California Energy Commission (CEC) ZEV Population Data** — publicly available, zip-code level counts of registered ZEVs by make/model, annually 2010–present
  - Source: https://www.energy.ca.gov/zevstats
  - Key vehicle groups:
    - Tesla (Model 3, Y, S, X; Cybertruck separately when available)
    - Non-Tesla BEVs (Chevy Bolt, Nissan Leaf, Hyundai Ioniq, Rivian, etc.)
    - PHEVs (Plug-in hybrids — separate category)
    - Light trucks / ICE SUVs (modern "Hummer" proxy — F-150, RAM 1500, Silverado)
  - Geography: zip code; crosswalk to Census tract
- **California DMV** — total vehicle registrations by zip/tract for denominator

### Commuting / Transportation
- **ACS 5-Year Estimates (2019–2023)** — Census tract commute mode share (transit, drive alone, walk, WFH)
- **NHTS 2017** — California household gasoline consumption (if California subsample is adequate)

### Demographics / Controls
- **ACS 2019–2023 (5-Year)** — income (median HH), education (% BA+), race/ethnicity, population density, housing tenure
- **EV charger density** — AFDC/DOE Alternative Fuels Station Locator API, aggregated to tract (controls for charging access as a confound)
- **Work-from-home rate** — ACS 2021–2023 (post-COVID control; reduces commute-driven consumption)
- **Median home value** — ACS (proxy for wealth beyond income, relevant for EV affordability)

---

## Methodology

### Step 1 — Construct Ideology Index
- Download and clean YCOM county-level data; crosswalk to Census tract (assign county value to all tracts within county — note limitation)
- Download CA voter registration data; compute Dem−Rep share at tract level
- Download SoS Statement of Vote; build precinct→tract crosswalk (population-weighted area interpolation using TIGER shapefiles)
- Run PCA across ideology measures; retain PC1 as the composite Climate Ideology Index
- Validate: regress index on Congressional district LCV scores

### Step 2 — Replicate Kahn's Core Specification (Cross-Section)
Reproduce the spirit of Kahn's analysis using the most recent data cross-section:
- OLS: transit commute share ~ ideology index + controls (Census tract level)
- OLS: gasoline consumption ~ ideology index + controls (NHTS, zip level)
- Negative Binomial: EV count ~ ideology index + controls (zip/tract level)
- Comparison: are signs and magnitudes directionally consistent with Kahn?

### Step 3 — EV Panel Analysis
Build a tract × year panel using CEC annual snapshots (2015–2024):
- Dependent variables: log(Tesla count), log(non-Tesla EV count), log(light truck count), Tesla share of total EVs
- Fixed effects: tract FE, year FE
- Ideology interacted with year dummies → **event study plot**
- Key hypothesis: ideology × year coefficient for Tesla declines post-2022/2025; ideology × year coefficient for non-Tesla EVs does not

### Step 4 — The Elon Effect (Event Study)
Define events:
- **Event 1:** Elon Musk acquires Twitter (Oct 2022) — first major public political signal
- **Event 2:** Elon Musk joins Trump transition / DOGE role announced (Nov 2024–Jan 2025)

For each event, estimate:
```
EV_count_it = α_i + γ_t + Σ_τ β_τ (Ideology_i × 1[t=τ]) + X_it·δ + ε_it
```
Plot β_τ coefficients over time with 95% CIs (event study plot). Parallel trends assumption for pre-event periods is the key diagnostic.

Non-Tesla EVs serve as the placebo/control series — if the "Elon Effect" is real, their ideology coefficient should be flat or rising while Tesla's falls.

### Step 5 — Ideology Robustness Checks
Run all main specifications (cross-section replication + EV panel + event study) three additional times:

| Specification | Geography | Ideology Measure | Purpose |
|---|---|---|---|
| Main | Census tract | PCA composite (YCOM + reg + ballot) | Primary results |
| R1 | County | YCOM only | Clean measurement, coarse geography |
| R2 | Census tract | Voter reg + ballot measures only (no YCOM) | Fine geography, no county-level assumption |
| R3 | Census tract | Prop 30 share only | Simplest, most direct climate signal |

Present R1 and R2 side-by-side with the main specification in a single robustness table. Consistent signs and magnitudes across all three tiers strengthen causal interpretation; divergence informs discussion of measurement vs. spatial granularity tradeoffs.

### Step 6 — Spatial Robustness
- Moran's I on residuals from Step 2/3 models
- Spatial Lag Model (SAR) or Spatial Durbin Model (SDM) if spatial autocorrelation is significant
- Spatial weights: queen contiguity among Census tracts

---

## Assumptions, Caveats, and Identification

### What This Study Can and Cannot Claim

**Ecological inference limitation (same as Kahn):** The unit of analysis is the Census tract/zip code, not the individual household. We observe that tracts with stronger climate beliefs have more EVs — we cannot directly observe which households within a tract are buying EVs. This is the same limitation Kahn acknowledged; results should be interpreted as community-level correlations.

**YCOM crosswalk limitation:** YCOM data is at the county level. Assigning county values to all tracts within a county assumes uniform belief distribution within counties — this is clearly an approximation. Two robustness checks address this directly: (1) run all models at the county level using YCOM directly, removing the crosswalk assumption entirely; (2) run all models at the tract level using only voter registration and ballot measure shares, removing YCOM from the index. Convergent results across all three specifications strengthen confidence in the findings.

**Tiebout sorting vs. peer effects:** Communities sort by ideology (Tiebout); we cannot cleanly separate pre-existing sorting from social norm effects. The panel analysis helps here — if ideology's effect *changes* over time, that is harder to explain by sorting alone.

**Reverse causality:** EV ownership may reinforce climate beliefs rather than the reverse. Cross-sectional analysis cannot resolve this. The event study partially addresses this by exploiting exogenous shifts in the Tesla brand signal.

**California generalizability:** Results are specific to California — a state with strong EV infrastructure, high EV incentives, and a relatively liberal electorate. Discussion section must address whether and how findings might generalize nationally, and what identification challenges would exist for a national study (variation in charging infrastructure, incentive policies, climate attitudes, and vehicle market structure all differ substantially).

**"Elon Effect" identification:** Musk's political shift coincides with other macroeconomic and market factors (rising interest rates, EV market maturation, increased competition). We cannot perfectly isolate the brand-political signal from these trends. Non-Tesla EV trends serve as a within-time control, but are imperfect given Tesla's different price point and market position.

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

## Project Status (updated 2026-02-25)

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

**Open items / known gaps:**
1. `data/raw/afdc/` is empty — EV charger density was never acquired; omitted from all models as a control
2. Time-varying ACS controls (2019 vintage for early panel years) deferred; noted in Technical Appendix
3. GitHub repo link placeholder remains in `paper/draft.md` — fill before publishing
4. 2025 CEC data not yet available; would provide a stronger Elon Effect test (DOGE/Trump events only appear at tail of 2024 panel)

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
