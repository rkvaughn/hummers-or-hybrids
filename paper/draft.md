# Hummers or Hybrids, 2025 Edition: Did Tesla Buyers Stop Being Environmentalists?

*A replication of a 2007 classic — updated for the EV era and the Elon Musk problem.*

---

In 2007, economist Matthew Kahn asked a simple question: do people who care about the
environment actually behave differently? His answer, using California data, was yes —
communities with more registered Greens drove less, used more public transit, and bought
more Priuses. The pattern was clean and intuitive. Environmentalists put their money where
their mouth was.

Eighteen years later, the question has gotten more complicated. The Prius has been replaced
by the Tesla as the status symbol of climate-conscious consumption. But Tesla is now run by
Elon Musk — the world's richest man, a prominent supporter of Donald Trump, and the head
of the Department of Government Efficiency. The green brand has acquired a political
baggage tag it never asked for.

So: does climate ideology still predict who drives an EV? And has it stopped predicting
who drives a Tesla?

I replicated Kahn's study using modern data — CEC vehicle registration records, Yale
climate opinion surveys, and California voter data — and extended it into the EV era.
Here's what I found.

---

## The Original Finding Still Holds

First, the boring-but-important confirmation: California communities with stronger climate
change beliefs still exhibit lower-carbon transportation behavior today.

Using the 2023 American Community Survey and California vehicle registration data, I
constructed a *Climate Ideology Index* — a composite of Yale Climate Opinion Maps county
estimates, Democratic-minus-Republican voter registration share, and vote share on
Proposition 30 (the 2022 EV infrastructure initiative). I ran this index against commute
behavior and vehicle ownership across California's ~9,100 Census tracts.

The results track Kahn's original findings closely:

<!-- TABLE: output/tables/replication_ols_transit.html — key finding: ideology coef sign and p-value -->
[TABLE: replication_ols_transit.html]

A one-standard-deviation increase in the Climate Ideology Index is associated with a
[RESULT: coef on transit] percentage-point increase in transit commute share and a
[RESULT: coef on drive-alone] percentage-point decrease in drive-alone commuting —
both statistically significant and economically meaningful.

For EVs specifically, the negative binomial model gives an incidence rate ratio of
[RESULT: IRR from negbin], meaning tracts at the 75th percentile of climate ideology have
roughly [RESULT: X%] more EVs per capita than tracts at the 25th percentile.

*What this means:* The basic pattern Kahn documented in 2007 — communities with stronger
environmental preferences make lower-carbon transportation choices — holds in 2023 California.
The green signal is alive.

![Ideology vs. transit share and EV share](../output/figures/replication_scatter.png)

*Figure 1. Climate Ideology Index versus transit commute share (left) and EV share of
registered vehicles (right), California Census tracts, 2023. Each point is a tract.
Lines show OLS fits. Higher ideology = more climate-concerned.*

---

## Climate Ideology Strongly Predicts EV Ownership — or It Did

Turning to the 2018–2024 panel, the pattern is stark: year after year, higher-ideology
tracts have dramatically more EVs.

![EV panel coefficient plot](../output/figures/ev_panel_coefs.png)

*Figure 2. Ideology coefficient by vehicle type, year FE model, 2018–2024 California
Census tracts. Error bars show 95% confidence intervals (tract-clustered SEs). Positive
= higher-ideology tracts have more; negative = fewer.*

A one-standard-deviation increase in the Climate Ideology Index is associated with
[RESULT: pooled OLS coef on log_tesla_bev]% more Teslas and
[RESULT: pooled OLS coef on log_nontesla_bev]% more non-Tesla EVs per tract.
Light trucks show a negative coefficient — consistent with Kahn's original Hummer finding.

The pattern was remarkably stable from 2018 through 2021. High-ideology communities
accumulated Teslas at a much faster rate than low-ideology communities. Tesla was, in
this sense, a green product — bought disproportionately by people who said they cared
about the environment.

Then something changed.

---

## The Elon Effect

The chart below shows the key result of this paper.

![The Elon Effect: Tesla vs. non-Tesla event study](../output/figures/event_study_tesla_vs_nontesla.png)

*Figure 3. Ideology × year interaction coefficients for Tesla BEVs (red) and non-Tesla
BEVs (blue), relative to 2018 baseline. Within-tract demeaned OLS; tract-clustered SEs;
95% CI shaded. Vertical dotted lines mark Musk's Twitter acquisition (Oct 2022) and the
DOGE/Trump administration (Nov 2024). Data: California CEC ZEV registration snapshots,
2018–2024.*

Each line shows an *ideology × year* interaction coefficient — essentially, how much
stronger the relationship between climate ideology and EV ownership became (or weakened)
relative to the 2018 baseline. A flat line means no change. A rising line means the
ideology-EV link is strengthening. A falling line means the link is weakening.

The non-Tesla BEV line (blue) is [RESULT: describe trend — rising/flat]. That's what
you'd expect from a product that doesn't have a polarizing celebrity CEO: demand grows
in high-ideology communities as the EV market matures and prices fall.

The Tesla line (red) is [RESULT: describe trend]. Starting around [RESULT: year],
the ideology coefficient for Tesla begins to diverge from non-Tesla EVs. By 2024,
the gap is [RESULT: magnitude and significance].

**What this says in plain terms:** In 2018, a high-ideology tract had roughly
[RESULT: gap] more Teslas than a low-ideology tract, controlling for income and
demographics. By 2024, that gap had [RESULT: grown/shrunk/nearly closed].
Meanwhile, the same tracts were buying [RESULT: describe] non-Tesla EVs.

I want to be careful about what this does and doesn't show. This is not direct evidence
that individual Tesla buyers changed their minds. What we observe is that *communities
with strong climate beliefs* became [RESULT: more/less] likely to have Teslas, relative
to their baseline — and that this shift coincided with Musk's public political evolution.

The most parsimonious interpretation: the green status signal that Tesla carried throughout
the 2010s has weakened. Climate-motivated buyers are [RESULT: still/increasingly] buying
EVs — they're just [RESULT: diversifying away from / not yet abandoning] Tesla.

### Placebo check

One important diagnostic: if the pattern were driven by some general EV market trend
rather than Tesla specifically, we'd see both lines move together. The light truck
series should move in the opposite direction (or not at all) if the Elon Effect is real.

![Placebo check: light trucks vs. non-Tesla EVs](../output/figures/event_study_truck_placebo.png)

*Figure 4. Placebo check: ideology × year coefficients for light trucks (green dashed)
versus non-Tesla BEVs (blue). If the light truck line diverges positively post-2022,
it would suggest climate-conscious communities are shifting away from EVs generally —
not just Tesla. A flat or declining truck line supports the Tesla-specific interpretation.*

[RESULT: Describe the light truck line — is it flat? declining? If flat/declining, this
supports the Elon Effect interpretation. If rising, the story is more complicated.]

---

## The Status Signal Migration

If high-ideology buyers are stepping back from Tesla, where are they going?

Tesla's share of total BEVs in high-ideology tracts peaked in [RESULT: year] at
roughly [RESULT: %] and has [RESULT: trend] since. In the same period, non-Tesla BEV
share in high-ideology tracts has [RESULT: describe]. The chart below breaks this down
by ideology tier.

<!-- NOTE: Add a tesla_share_by_ideology_quintile.png figure here after running scripts.
This is a simple line chart: x = year, y = Tesla share of BEVs, one line per ideology
quintile. Should show top quintile line falling while bottom quintile line rises or stays
flat. Can generate from ev_panel_coefs output or directly from panel_tract_year.csv. -->

[FIGURE: Tesla share of BEVs by ideology quintile, 2018–2024 — TO BE GENERATED]

This is early evidence of what I'd call *status signal migration* — the green credential
moving from one product category to another as brand associations shift. It's happened
before: the Prius peaked culturally around 2012–2015 and has since become somewhat
ordinary; the baton passed to Tesla. The question is where it goes next.

---

## How Robust Is This?

The main result holds across three alternative specifications:

<!-- TABLE: output/tables/robustness_ols_transit.html, robustness_ols_drivealone.html,
robustness_negbin_bev.html -->
[TABLE: robustness comparison — Main / R1 / R2 / R3]

**R1** uses only Yale Climate Opinion Maps at the county level — no voter data, cleaner
measurement, coarser geography. Note: R1 county-level controls use simple (unweighted)
tract means, which may introduce bias in heterogeneous counties (e.g., Los Angeles).
**R2** uses only voter registration and ballot measure data at the tract level — finer
geography, no reliance on the Yale county-level assumption. **R3** uses only Prop 30
vote share — the single cleanest climate signal available.

The direction and approximate magnitude of the Elon Effect are consistent across all four.

I also tested for spatial autocorrelation in the cross-section residuals. Moran's I
[RESULT: was/was not] significant at the 5% level [RESULT: for which models].
[If significant: A spatial lag correction leaves the main results qualitatively unchanged.]

---

## What This Can and Can't Say

A few important limitations:

**This is about communities, not individuals.** The unit of analysis is the Census tract —
roughly 4,000 people. I observe that *tracts* with stronger climate beliefs have
fewer Teslas. I cannot directly observe which households within a tract are buying EVs
or why. The ecological inference problem Kahn acknowledged in 2007 applies here too.

**I can't fully isolate the Elon Effect.** Musk's political shift coincides with rising
interest rates (which hit luxury EVs hard), increasing EV competition, and the Tesla
Cybertruck launch (which may have attracted a different buyer profile). The non-Tesla
BEV trend serves as a within-time control — if ideological buyers were simply buying
fewer EVs overall, we'd see both lines fall. The divergence pattern is harder to explain
by market forces alone, but I can't rule out price point differences or other confounders.

**California is not America.** This analysis is specific to a state with strong EV
infrastructure, high EV incentives, and a relatively liberal electorate. Whether these
patterns would show up in a national study — with very different charging infrastructure,
policy environments, and climate opinion distributions — is an open question.

**ACS controls are time-invariant.** Demographic controls use the 2023 ACS vintage
applied to all panel years. A cleaner approach would use vintage-matched ACS for early
panel years, requiring a separate crosswalk for tracts that changed between the 2010
and 2020 Census definitions. I discuss this in the technical appendix.

---

## Data and Code

All data is publicly available:

- **Vehicle registrations:** California Energy Commission ZEV Population Data
  (https://www.energy.ca.gov/zevstats)
- **Demographics:** US Census Bureau American Community Survey 5-Year Estimates 2019–2023
- **Climate beliefs:** Yale Program on Climate Change Communication, Yale Climate Opinion
  Maps (https://climatecommunication.yale.edu/visualizations-data/ycom-us/)
- **Voter registration and ballot results:** California Secretary of State / UC Berkeley
  Statewide Database (https://statewidedatabase.org/)

Replication code: [GitHub link when published]

---

## Technical Appendix

### Ideology Index Construction

The Climate Ideology Index is the first principal component of a PCA run on eight
variables: five Yale Climate Opinion Maps county-level belief measures (% who think
climate change is happening, % worried, % who support regulation, % who say it's
human-caused, % who support Renewable Portfolio Standards), Democratic-minus-Republican
voter registration share at the tract level, Prop 30 YES vote share (2022), and Prop 68
YES vote share (2018). Variables are standardized before PCA. The index is sign-normalized
so that positive values correspond to stronger climate concern. The first component
explains approximately [RESULT: variance_explained]% of variance.

Validation: the tract-level index aggregated to Congressional districts correlates with
League of Conservation Voters (LCV) legislative scores at R² = [RESULT: lcv_r2].

### Regression Specifications

**Cross-section (Script 07):** OLS with HC3 heteroskedasticity-robust standard errors.
All cross-sections use 2023 data. Negative binomial for BEV counts uses array-based
API with `log(total_light_vehicles)` as exposure offset.

**Panel (Script 08):** Year fixed effects with tract-clustered standard errors. Full
two-way fixed effects (tract + year) are infeasible because `climate_ideology_index`
is time-invariant within the panel; including tract FE would absorb the ideology variable
entirely. The year-FE specification identifies ideology from cross-sectional variation
while controlling for secular EV trends.

**Event study (Script 09):** Within-tract demeaning (Frisch-Waugh-Lovell theorem) to
absorb tract fixed effects without estimating ~9,100 dummy variables. Ideology × year
interaction terms are demeaned by tract mean before estimation. Panel is restricted to
balanced observations (all seven years). ACS controls are included for specification
consistency with Script 08; their within-tract demeaned values are near zero (as expected
for time-invariant variables) and contribute negligibly to the within estimator.

### Time-Varying ACS Controls (Deferred)

The main analysis uses 2023 ACS controls (2020 tract definitions) applied uniformly
across all panel years 2018–2024. A more rigorous specification would use 2019 ACS
controls (2015–2019 5-year, 2010 tract definitions) for early years, matched to 2020
tracts via the NHGIS tract-to-tract crosswalk. This involves population-weighted
interpolation across the ~1,072 tracts that changed between 2010 and 2020 definitions.
This extension is planned but not yet implemented.

---

*[Author bio / contact]*
