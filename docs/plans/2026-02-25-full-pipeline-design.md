# Design: Full Analysis Pipeline + Substack Post

**Date:** 2026-02-25
**Project:** Hummers or Hybrids — Replication & Extension of Kahn (2007)
**Scope:** Scripts 05–11 (analysis pipeline) + paper/draft.md (Substack post)

---

## Overview

Scripts 01–04 (data acquisition and crosswalks) are complete. This design covers the remaining
7 analysis scripts and the final Substack post. All scripts follow existing conventions:
read from `data/raw/` or `data/processed/`, write outputs to `data/processed/` or `output/`.

Order of execution: 05 → 06 → 07 → 08 → 09 → 10 → 11 → paper

---

## Script 05 — build_panel.py

**Purpose:** Merge all raw inputs into a single tract × year panel dataset.

**Inputs:**
- `data/raw/cec_zev/cec_panel_zev.csv` — ZEV counts by ZIP/year/make
- `data/raw/cec_zev/cec_panel_light.csv` — light-duty counts by ZIP/year/make
- `data/raw/acs/acs_tracts_ca_clean.csv` — ACS demographics by tract
- `data/processed/crosswalk_zip_tract.csv` — ZCTA → tract weights
- `data/processed/crosswalk_county_tract.csv` — county FIPS → tract lookup
- `data/processed/crosswalk_prec_tract_g22.csv` — 2022 precinct → tract weights
- `data/processed/crosswalk_prec_tract_p18.csv` — 2018 precinct → tract weights
- `data/raw/ycom/ycom_ca_counties.csv` — YCOM county beliefs
- `data/raw/voter_registration/votreg_ca_raw.csv` — precinct-level party registration
- `data/raw/ballot_measures/ballots_g22_raw.csv` — 2022 precinct SOV (Prop 30)
- `data/raw/ballot_measures/ballots_p18_raw.csv` — 2018 precinct SOV (Prop 68)

**Vehicle variables (crosswalked from ZIP to tract, aggregated by year):**
- `tesla_bev` — Tesla BEV stock
- `nontesla_bev` — non-Tesla BEV stock
- `total_bev` — all BEVs
- `total_phev` — PHEVs
- `light_truck_count` — light-duty ICE truck proxy
- `total_light` — all light-duty vehicles (denominator)

**Ideology variables (time-invariant, assigned via crosswalks):**
- `ycom_happening`, `ycom_worried`, `ycom_regulate`, `ycom_human`, `ycom_supportRPS`
- `dem_minus_rep` — Democratic minus Republican registration share (2022)
- `prop30_yes_share` — Prop 30 YES fraction (2022 precincts → tract)
- `prop68_yes_share` — Prop 68 YES fraction (2018 precincts → tract)

**ACS controls (2023 vintage, time-invariant):**
- `median_hh_income`, `pct_ba_plus`, `pct_white`, `pct_black`, `pct_asian`, `pct_hispanic`
- `pop_density`, `pct_transit`, `pct_drove_alone`, `pct_wfh`, `median_home_value`

**Output:**
- `data/processed/panel_tract_year.csv` — ~9,100 tracts × 7 years = ~63,700 rows
- Print merge diagnostics (tract match rates, vehicle count totals by year)

---

## Script 06 — ideology_index.py

**Purpose:** Construct composite Climate Ideology Index via PCA, validate against LCV scores.

**PCA inputs (all standardized before PCA):**
- 5 YCOM variables: `ycom_happening`, `ycom_worried`, `ycom_regulate`, `ycom_human`, `ycom_supportRPS`
- `dem_minus_rep`
- `prop30_yes_share`
- `prop68_yes_share`

**PCA output:** PC1 retained as `climate_ideology_index` (expected ~60–70% variance explained).

**Validation:** Aggregate index to Congressional district level; regress on LCV scores scraped
from the LCV website (https://scorecard.lcv.org/). Simple OLS; print R² and scatter plot.

**Outputs:**
- `data/processed/ideology_index.csv` — tract-level index + all component scores
- `output/tables/pca_loadings.csv` — variable loadings on PC1
- `output/figures/pca_scree.png` — scree plot
- `output/figures/ideology_map.png` — choropleth of index across CA tracts

---

## Script 07 — replication.py

**Purpose:** Cross-sectional replication of Kahn (2007) spirit using 2023 data.

**Three specifications (2023 cross-section):**

1. OLS: `pct_transit ~ ideology + log(median_hh_income) + pct_ba_plus + pop_density + pct_white + pct_wfh`
2. OLS: `pct_drove_alone ~ ideology + same controls`
3. Negative Binomial: `total_bev ~ ideology + same controls + log(total_light) as exposure`

**Controls are the same across all three.** Standard errors: heteroskedasticity-robust (HC3).

**Outputs:**
- `output/tables/replication_ols_transit.csv/.html`
- `output/tables/replication_ols_drivealone.csv/.html`
- `output/tables/replication_negbin_bev.csv/.html`
- `output/figures/replication_scatter.png` — ideology vs. transit share + EV share scatter

**Note on comparability:** Kahn used LA County only and Green Party registration. We use all
of California and a PCA composite. Results should be directionally consistent, not numerically
comparable. Writeup acknowledges this.

---

## Script 08 — ev_panel.py

**Purpose:** Two-way fixed effects panel regressions — ideology predicting EV adoption over time.

**Specification:**
```
Y_it = α_i + γ_t + Σ_τ β_τ(ideology_i × 1[year=τ]) + X_i·δ + ε_it
```

**Four dependent variables:**
1. `log(tesla_bev + 1)`
2. `log(nontesla_bev + 1)`
3. `log(light_truck_count + 1)`
4. `tesla_share` — Tesla / (Tesla + nonTesla BEV)

**Estimator:** `linearmodels.PanelOLS` with tract + year FE, standard errors clustered at tract.
Also run pooled OLS (no FE) for comparison.

**Outputs:**
- `output/tables/ev_panel_twfe.csv/.html` — main TWFE results
- `output/tables/ev_panel_pooled.csv/.html` — pooled OLS
- `output/figures/ev_panel_coefs.png` — coefficient plot across all 4 DVs

---

## Script 09 — event_study.py

**Purpose:** The centerpiece. Visualize whether ideology's relationship with Tesla adoption
changed after Musk's political pivot.

**Specification:**
```
log(EV_count + 1)_it = α_i + γ_t + Σ_τ β_τ(ideology_i × 1[year=τ]) + X_i·δ + ε_it
```

Run separately for Tesla BEVs and non-Tesla BEVs. 2018 = omitted base year (β normalized to 0).

**Event markers:**
- **2022** — Musk acquires Twitter (Oct 2022)
- **2024** — DOGE role / Trump administration (Nov 2024–Jan 2025; 2024 CEC snapshot is last year)

**Identification:** Pre-2022 parallel trends between Tesla and non-Tesla = validity check.
Post-2022 divergence = the Elon Effect. Non-Tesla EVs serve as placebo/control series.

**Outputs:**
- `output/figures/event_study_tesla_vs_nontesla.png` — hero figure: Tesla (red) vs. non-Tesla (blue)
  with β_τ ± 95% CI, vertical dashed lines at events
- `output/tables/event_study_coefs.csv` — coefficient table
- `output/figures/event_study_truck.png` — light trucks (placebo; should be flat or declining)

---

## Script 10 — robustness.py

**Purpose:** Re-run main specifications with three alternative ideology measures.

| Spec | Geography | Ideology Measure |
|---|---|---|
| Main | Census tract | PCA composite (YCOM + reg + ballot) |
| R1 | County | YCOM only |
| R2 | Census tract | Voter reg + ballot only (no YCOM) |
| R3 | Census tract | Prop 30 share only |

**What gets re-run:** Cross-section OLS (transit + drive-alone), NB BEV count, TWFE EV panel.

**R1 note:** Requires aggregating vehicle counts to county level from the tract panel
(~58 counties × 7 years = 406 rows). Handled internally — no new raw data needed.

**Outputs:**
- `output/tables/robustness_main.csv/.html` — 4-column table (Main, R1, R2, R3) per regression
- Single combined HTML with all robustness tables

---

## Script 11 — spatial.py

**Purpose:** Test for spatial autocorrelation in residuals; correct if significant.

**Step 1 — Moran's I:**
- Build queen contiguity weights from 2020 TIGER tract shapefiles (already in `data/raw/shapefiles/`)
- Run Moran's I on residuals from 3 cross-section models
- If all p-values > 0.05: report and stop
- If significant: proceed to Step 2

**Step 2 — Spatial Lag Model (SAR):**
- Estimate SAR via `pysal/spreg`
- If LM-test favors SDM, run SDM instead
- Report spatial autoregressive coefficient (ρ) alongside OLS

**Implementation:** Use `libpysal` sparse weights to handle ~9,100 tract matrix efficiently.

**Outputs:**
- `output/tables/spatial_morans.csv` — Moran's I and p-values
- `output/tables/spatial_sar.csv/.html` — SAR/SDM results if warranted
- `output/figures/spatial_weights_map.png` — queen contiguity structure
- `output/figures/residual_map.png` — OLS residual choropleth

---

## Paper — paper/draft.md

**Format:** Substack-ready Markdown. Written after all scripts run with real results.

**Structure:**
1. **Hook** — "Did Tesla buyers stop being environmentalists?" Frame around brand identity shift.
2. **Section 1 — The original question** — Brief Kahn (2007) summary. Quick replication result.
   Charts: ideology vs. EV share scatter, transit/commute comparison.
3. **Section 2 — The EV era** — Climate ideology predicts EV adoption 2018–2024. Coefficient plot.
4. **Section 3 — The Elon Effect** — Hero section. Event study figure. Plain-language interpretation
   of magnitude. Pre-trend validation explained accessibly.
5. **Section 4 — Status signal migration** — Tesla share of total BEVs by ideology tier over time.
6. **Section 5 — Caveats** — Short. Ecological inference, YCOM limitation, California-only.
7. **Appendix/footnotes** — Data sources, methodology, robustness references.

All figures referenced by path from `output/figures/`. Written for ryankvaughn.com/Substack.

---

## Dependencies Between Scripts

```
01_acquire_cec.py
02_acquire_acs.py      ──┐
03_acquire_ideology.py ──┤
04_crosswalk.py        ──┴──> 05_build_panel.py ──> 06_ideology_index.py
                                                          │
                                               ┌──────────┴──────────┐
                                               ▼                     ▼
                                         07_replication.py     08_ev_panel.py
                                               │                     │
                                               └──────────┬──────────┘
                                                          ▼
                                                  09_event_study.py
                                                          │
                                                  10_robustness.py
                                                          │
                                                  11_spatial.py
                                                          │
                                                   paper/draft.md
```

---

## Key Technical Choices

- **Python** throughout; no R
- `linearmodels.PanelOLS` for TWFE (not `statsmodels`, which lacks panel FE)
- `statsmodels` for OLS, NB, spatial diagnostics
- `pysal/spreg` for SAR/SDM
- `geopandas` for spatial operations (already used in script 04)
- `scikit-learn` PCA for ideology index
- `matplotlib/seaborn` for all figures, saved at 300 dpi
- Clustered standard errors (tract-level) throughout panel models
- HC3 robust SEs for cross-section models
- All regression tables saved as both `.csv` and `.html`
