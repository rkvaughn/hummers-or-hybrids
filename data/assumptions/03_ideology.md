# Data Assumptions: Ideology and Climate Belief Measures

**Sources:**
- Yale Climate Opinion Maps (YCOM): `data/raw/ycom/ycom_ca_counties.csv`
- Voter Registration: `data/raw/voter_registration/votreg_ca_raw.csv`
- Ballot Measures: `data/raw/ballot_measures/ballots_g22_raw.csv`, `ballots_p18_raw.csv`

**Script:** `scripts/03_acquire_ideology.py`

---

## YCOM Assumptions

### A1 — County-level beliefs assigned uniformly to all tracts

**Assumption:** YCOM provides estimates at the county level (58 CA counties). We assign each county's belief values to all Census tracts within that county.

**Implication:** This imposes zero within-county variation in climate beliefs. All cross-sectional identification from YCOM comes from between-county differences. Within-county variation in the ideology composite index comes entirely from voter registration and ballot measure sources.

**Bias direction:** If high-belief individuals cluster in urban cores (which they likely do), assigning the county average to all tracts understates beliefs in urban tracts and overstates them in suburban/rural tracts within the same county. This would attenuate our ideology coefficient toward zero — estimates are likely conservative.

**Writeup note:** "Yale Climate Opinion Maps (YCOM) estimates are available at the county level, estimated via multilevel regression and poststratification (MrP) from nationally representative surveys. We assign each county's climate belief values to all Census tracts within that county, imposing uniform beliefs within counties. All within-county variation in our composite ideology index derives from tract-level voter registration and ballot measure data. The county-level YCOM assignment likely attenuates ideology coefficients, so our estimates should be interpreted as conservative lower bounds."

---

### A2 — 2020 vintage applied to 2018–2024 panel

**Assumption:** The GitHub-hosted YCOM 5.0 data represents 2020 estimates (based on surveys pooled through Spring 2020). We apply this single vintage to all years of our 2018–2024 vehicle panel, treating climate beliefs as time-invariant.

**Implication:** Climate beliefs do shift over time (Yale's own research shows modest increases in the "happening" measure over the 2010s), but year-to-year changes are small relative to between-county variation. Treating beliefs as fixed is standard in cross-sectional analysis of this type.

**Note:** YCOM offers updated estimates through 2024 via their web tool (requires registration at climatecommunication.yale.edu). If a newer vintage is obtained and placed in `data/raw/ycom/`, re-running `03_acquire_ideology.py` will automatically use it.

**Writeup note:** "YCOM estimates are from the 2020 vintage (YCOM 5.0), based on surveys pooled through Spring 2020, and are treated as time-invariant across the 2018–2024 analysis period. While climate belief levels have increased modestly over this period, between-county variation dominates the time series trend."

---

### A3 — YCOM variables selected

**Assumption:** Five YCOM variables are retained: `happening`, `human`, `worried`, `regulate`, `supportRPS`. These are expressed as percentages (0–100).

| Variable | Question paraphrase |
|---|---|
| `happening` | % who think global warming is happening |
| `human` | % who think it is mostly human-caused |
| `worried` | % who are worried about global warming |
| `regulate` | % who support regulating CO2 as a pollutant |
| `supportRPS` | % who support requiring utilities to use renewables |

**Excluded:** Variables related to drilling (offshore, ANWR), carbon tax, and media consumption are excluded as less relevant to the climate *belief* construct (vs. political/policy preferences).

**Writeup note:** "We use five YCOM variables that most directly capture climate change beliefs and attitudes: whether global warming is happening, whether it is human-caused, degree of worry, and support for two major policy responses. These are entered into the PCA alongside tract-level behavioral measures."

---

## Voter Registration Assumptions

### A4 — Party registration as a revealed-preference proxy

**Assumption:** Democratic minus Republican party registration share is used as a proxy for climate ideology at the precinct level, with the assumption that party registration correlates with climate beliefs at the community level.

**Implication:** Party registration is an imperfect measure of climate beliefs specifically. Many Democrats do not prioritize climate; some Republicans do. The correlation between party registration and YCOM climate belief measures at the county level provides a validation check (to be computed in `06_ideology_index.py`).

**Writeup note:** "Party registration share — specifically the Democratic minus Republican margin — is used as a revealed-preference proxy for community climate ideology. While party affiliation does not map one-to-one onto climate beliefs, the two are highly correlated at the community level in California. We validate this by comparing registration-based measures to YCOM survey beliefs at the county level."

---

### A5 — 2022 registration applied as time-invariant

**Assumption:** We use the 2022 General Election voter registration file as our primary registration snapshot. This is applied as a time-invariant control (one registration share per precinct/tract), consistent with the single-cross-section ACS approach.

**Implication:** Tracts that experienced significant partisan sorting between 2018 and 2024 will have mismeasured ideology in early or late panel years. Tract fixed effects in panel models partially absorb this, but time-varying registration is a robustness check.

**Writeup note:** "Voter registration shares are drawn from the November 2022 General Election voter file and treated as time-invariant across the analysis period."

---

## Ballot Measure Assumptions

### A6 — Prop 30 (2022) as the primary climate ideology signal

**Assumption:** Proposition 30 (November 2022) — which would have funded EV charging infrastructure and wildfire prevention through a tax on incomes over $2 million — is used as the primary ballot measure component of the ideology index. The YES vote share at the precinct level is computed as `PR_30_Y / (PR_30_Y + PR_30_N)`.

**Implication:** Prop 30 was specifically about EVs and climate, making it the most directly relevant ballot measure available. However, its funding mechanism (millionaire's tax) means opposition may reflect anti-tax preferences rather than climate skepticism — the measure conflates climate support with income redistribution preferences. This is partially addressed by the Prop 7 (daylight saving, placebo) robustness check.

**Writeup note:** "Proposition 30 (2022) — which proposed funding EV infrastructure and wildfire response via a tax on incomes over $2 million — provides our most direct ballot-based measure of climate policy support. We compute the YES vote share at the precinct level. A limitation is that opposition may partly reflect anti-tax sentiment rather than climate skepticism; our placebo test using Proposition 7 (daylight saving time, unrelated to climate) helps assess whether results are driven by general liberal voting rather than climate-specific beliefs."

---

### A7 — Prop 68 (2018) as secondary measure

**Assumption:** Proposition 68 (June 2018 Primary) — a $4 billion parks, water, and climate bond — is included as a secondary ideology measure. YES vote share computed as `PR_68_Y / (PR_68_Y + PR_68_N)`.

**Implication:** Bond measures have lower salience than general election initiatives and the 2018 Primary had lower turnout than the 2022 General. Vote shares may be noisier. Additionally, the 2018 Primary electorate skews more liberal than the general electorate, which may inflate the absolute YES shares while preserving relative cross-precinct variation.

**Writeup note:** "Proposition 68 (2018 Primary), a $4 billion parks and climate bond, is included as a secondary ballot measure. Primary election measures are subject to lower turnout and a more ideologically extreme electorate; we treat this measure as a supplementary component of the composite index rather than a primary indicator."

---

### A8 — Precinct-level vote shares require crosswalk to Census tracts

**Assumption:** All ballot measure data is reported at the election precinct level. Precincts do not align with Census tract boundaries. We crosswalk precinct → Census tract using population-weighted area interpolation.

**Implication:** See `data/assumptions/04_crosswalk.md` for full crosswalk assumptions.
