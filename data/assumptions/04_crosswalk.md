# Data Assumptions: Geographic Crosswalks

**Script:** `scripts/04_crosswalk.py` (to be built)
**Crosswalks required:**
1. ZIP code → Census tract (for CEC vehicle data)
2. Election precinct → Census tract (for voter registration and ballot measures)
3. County → Census tract (for YCOM — trivial assignment, no interpolation)

All crosswalks target **2020 Census tract definitions** to match the 2023 ACS vintage.

---

## Crosswalk 1: ZIP Code → Census Tract (CEC Vehicle Data)

### A1 — ZCTAs used as proxy for ZIP codes

**Assumption:** The Census Bureau does not define Census geographies for USPS ZIP codes (which are mail routes, not areas). Instead, we use ZIP Code Tabulation Areas (ZCTAs), which are Census-constructed approximate equivalents. Most 5-digit ZIP codes correspond to a ZCTA, but a minority do not (P.O. box-only ZIPs, unique-organization ZIPs).

**Source:** HUD USPS ZIP Code Crosswalk or Census ZCTA-to-tract relationship file.

**Implication:** ZIP codes in the CEC data that do not have a corresponding ZCTA are dropped. This primarily affects P.O. box-only ZIPs, which typically have few or zero vehicle registrations. Drop rate expected to be <1% of records by count.

**Writeup note:** "ZIP code vehicle registration data is crosswalked to Census tracts via ZIP Code Tabulation Areas (ZCTAs). ZIP codes without a corresponding ZCTA — primarily P.O. box-only designations — are excluded from the analysis."

---

### A2 — Many-to-many ZIP-tract relationship requires population weighting

**Assumption:** A single ZIP/ZCTA often overlaps multiple Census tracts, and a single Census tract may overlap multiple ZCTAs. We use population-weighted allocation: each ZIP's vehicle count is distributed across overlapping tracts in proportion to the share of the ZIP's population residing in each tract.

**Weight source:** HUD ZIP-Tract crosswalk allocation factors (column `RES_RATIO` — residential address ratio), or Census ZCTA-to-tract relationship file with population weights from 2020 Census block-level data.

**Implication:** This assumes vehicles are distributed within a ZIP in proportion to residential population. In practice, vehicles may be more concentrated in denser, higher-income sub-areas of a ZIP. Population weighting is standard but imperfect.

**Writeup note:** "Where ZIP code boundaries span multiple Census tracts, vehicle counts are allocated across tracts using residential address weights from the HUD ZIP-to-tract crosswalk. This assumes vehicles are distributed within ZIP codes in proportion to residential population density."

---

### A3 — Crosswalk vintage matched to 2020 tract definitions

**Assumption:** We use the 2020-vintage HUD crosswalk (released 2021–2024) to align with 2020 Census tract definitions used in the 2023 ACS. Using a 2010-vintage crosswalk would introduce boundary mismatch.

**Implication:** Some ZIPs changed boundaries between 2010 and 2020; using the contemporaneous crosswalk minimizes this error.

---

## Crosswalk 2: Election Precinct → Census Tract

### A4 — Population-weighted area interpolation

**Assumption:** Election precincts and Census tracts do not share boundaries. We use areal interpolation: for each precinct-tract overlap, the share of the precinct's area that falls within the tract (weighted by population from 2020 Census blocks) determines how much of the precinct's vote/registration count is attributed to that tract.

**Source:** TIGER/Line shapefiles for both 2022 election precincts (from CA Secretary of State / Statewide Database) and 2020 Census tracts. Spatial intersection computed in GeoPandas.

**Implication:** Precinct boundaries are often drawn to follow geographic features (roads, waterways) that also serve as Census tract boundaries, so misalignment is typically small. Larger errors occur in areas with irregular precinct shapes or large low-density precincts in rural counties.

**Writeup note:** "Election precinct vote shares and registration counts are mapped to Census tracts using population-weighted areal interpolation. For each precinct-tract intersection, the fraction of the precinct's 2020 Census population residing within the overlapping area determines the allocation weight. Precinct shapefiles are from the UC Berkeley Statewide Database; Census tract shapefiles are 2020 TIGER/Line boundaries."

---

### A5 — Precinct vintage: 2022 precincts used for both 2022 and 2018 ballot data

**Assumption:** Precinct boundaries change between elections. The Statewide Database provides election-specific precinct boundaries. We use 2022 precinct definitions for the 2022 SOV (Prop 30) and 2018 precinct definitions for the 2018 SOV (Prop 68), matching each election's data to its own precinct geography before crosswalking both to 2020 Census tracts.

**Implication:** This is the correct approach. Using mismatched precinct vintages would introduce boundary errors.

---

## Crosswalk 3: County → Census Tract (YCOM)

### A6 — Trivial many-to-one assignment

**Assumption:** Each Census tract is assigned the YCOM belief values of the county it belongs to. This is a deterministic lookup using the first 5 digits of the tract GEOID (state 2 + county 3 = county FIPS). No interpolation is needed.

**Implication:** As noted in `03_ideology.md` (A1), this imposes zero within-county variation in YCOM-derived ideology. Within-county variation in the composite index comes from voter registration and ballot measures only.

**Writeup note:** See `03_ideology.md` A1.

---

## General Crosswalk Caveats

### A7 — Crosswalk measurement error is non-random

All three crosswalks introduce measurement error. Importantly, this error is unlikely to be random:
- Dense urban areas: small, compact geographies → high concordance between ZIP/precinct/tract boundaries → low measurement error
- Sparse rural areas: large, irregular geographies spanning multiple units → high measurement error

Since high-ideology, high-EV-adoption areas tend to be denser (and thus have lower crosswalk error), this systematic pattern means rural areas are measured with more noise. If anything, this further attenuates ideology coefficients in rural areas — consistent with a conservative bias in our estimates.

**Writeup note:** "Geographic crosswalk measurement error is larger in rural areas where ZIP codes, election precincts, and Census tracts span larger and more irregular geographic units. Because high-ideology, high-EV-adoption communities tend to be urban and therefore better-measured, systematic crosswalk error likely attenuates our estimates modestly, particularly in rural subsamples."
