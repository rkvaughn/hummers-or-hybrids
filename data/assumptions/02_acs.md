# Data Assumptions: American Community Survey (ACS)

**Source:** U.S. Census Bureau ACS 5-Year Estimates
**File:** `data/raw/acs/acs_tracts_ca_2023.csv`
**Script:** `scripts/02_acquire_acs.py`
**Vintage:** 2023 (covering 2019–2023), 2020 Census tract definitions

---

## A1 — Single cross-section of controls applied to full 2018–2024 panel

**Assumption:** We use the 2023 ACS (2019–2023 5-year estimates) as the demographic control vector for all years of the vehicle panel (2018–2024). Demographics are treated as fixed across panel years.

**Why:** The 2019 ACS uses 2010 Census tract definitions (8,057 CA tracts); the 2023 ACS uses 2020 definitions (9,129 CA tracts). Directly merging the two vintages is not valid without a tract-to-tract crosswalk. Rather than introduce that additional source of measurement error in the primary analysis, we use a single cross-section.

**Potential bias:** If ZIP-level demographics changed meaningfully between 2018 and 2024 (e.g., gentrification, income shifts in high-EV-adoption areas), time-invariant controls introduce omitted variable bias. This is partially mitigated by tract fixed effects in the panel models, which absorb time-invariant differences between tracts. Time-varying controls using the NHGIS 2010→2020 tract crosswalk are deferred to the appendix robustness checks.

**Writeup note:** "Demographic controls are drawn from the 2023 ACS 5-year estimates (covering 2019–2023) and applied as a time-invariant vector across all panel years. The 2020 Census tract redefinition — which increased California's tract count from 8,057 to 9,129 — prevents direct combination of the 2019 and 2023 ACS vintages without a population-weighted crosswalk. In panel specifications, tract fixed effects absorb any time-invariant demographic confounders. An appendix robustness check using time-varying controls via the NHGIS crosswalk is reported in Appendix [X]."

---

## A2 — Five-year estimates treated as point-in-time

**Assumption:** The 2023 ACS 5-year estimate covers survey responses from 2019–2023. We treat it as representing the 2021–2022 midpoint, not 2023 specifically.

**Implication:** For outcomes measured in 2022–2024, controls are approximately contemporaneous. For 2018–2020 outcomes, controls are forward-looking by 2–4 years. This is standard practice in the literature (Kahn (2007) used 2000 Census controls for 2001–2005 data) but is worth noting.

**Writeup note:** "The ACS 5-year estimates represent an average over the 2019–2023 survey period. We treat these as approximately contemporaneous with the middle of our vehicle panel. For the earliest panel years (2018–2020), demographic controls are drawn from a slightly later period, consistent with standard practice in the literature."

---

## A3 — Sentinel value treatment

**Assumption:** The Census API returns `-666666666` as a sentinel value for suppressed or unavailable estimates (typically small populations or confidentiality suppression). These are converted to `NA` before any analysis.

**Implication:** Tracts with suppressed income, home value, or demographic estimates are excluded from regressions that include those controls. Suppression is concentrated in small/rural tracts and group quarters.

**Writeup note:** "Census API sentinel values (−666,666,666), which indicate suppressed estimates due to small cell sizes, are treated as missing. Tracts with missing values for any control variable are excluded from the corresponding regression. Suppression is most common in small rural tracts and Census-designated group quarters."

---

## A4 — Population density calculation

**Assumption:** Population density is calculated as `total_pop / (ALAND / 2,589,988)`, converting land area from square meters to square miles. Water area is excluded.

**Implication:** Tracts with large water bodies (coastal tracts, lake-adjacent tracts) have land area that accurately excludes water — this is appropriate. Tracts with ALAND = 0 (fully water tracts, rare) would produce division-by-zero errors and are excluded.

**Writeup note:** "Population density is calculated as total population divided by land area in square miles (excluding water area), using the ALAND field from the Census geographic reference file."

---

## A5 — Education proxy: bachelor's degree or higher among 25+

**Assumption:** Education is operationalized as the share of the population aged 25+ with a bachelor's degree or higher (`B15003_022E / B15003_001E`). This excludes graduate and professional degrees from the numerator.

**Note:** `B15003_022E` is bachelor's degree only. To include graduate/professional, we would also need `B15003_023E` (master's), `B15003_024E` (professional), `B15003_025E` (doctorate). This is a known undercount of the BA+ share.

**TODO (pre-analysis):** Confirm whether to use bachelor's only or full BA+ (bachelor's + advanced). Update script to add graduate degree codes and re-pull if using BA+.

**Writeup note:** "Educational attainment is measured as the share of adults 25 and older with at least a bachelor's degree, using ACS table B15003."
