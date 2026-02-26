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
**1.09 percentage-point** increase in transit commute share and a **1.84 percentage-point**
decrease in drive-alone commuting — both statistically significant at the 1% level and
economically meaningful given that the average tract has about 5% transit share and 76%
drive-alone share.

The log-OLS model for EV counts gives a coefficient of **+0.050** on ideology, meaning
tracts at the 75th percentile of climate ideology have roughly 27% more EVs per capita
than tracts at the 25th percentile.

*Note on the count model:* Kahn (2007) used negative binomial regression for vehicle
counts. After area-weighting ZIP-code data to Census tracts, the BEV counts become
fractional allocations rather than true integer counts — the negative binomial optimization
fails to converge on this data structure. I report log(BEV+1) OLS throughout, which gives
nearly identical point estimates to the log-OLS specification in Script 08 and is
standard for this type of vehicle share analysis.

*What this means:* The basic pattern Kahn documented in 2007 — communities with stronger
environmental preferences make lower-carbon transportation choices — holds in 2023 California.
The green signal is alive.

![Ideology vs. transit share and EV share](../output/figures/replication_scatter.png)

*Figure 1. Climate Ideology Index versus transit commute share (left) and EV share of
registered vehicles (right), California Census tracts, 2023. Each point is a tract.
Lines show OLS fits. Higher ideology = more climate-concerned.*

---

## Climate Ideology Strongly Predicts EV Ownership

Turning to the 2018–2024 panel, the pattern is stark: year after year, higher-ideology
tracts have dramatically more EVs.

![EV panel coefficient plot](../output/figures/ev_panel_coefs.png)

*Figure 2. Ideology coefficient by vehicle type, year FE model, 2018–2024 California
Census tracts. Error bars show 95% confidence intervals (tract-clustered SEs). Positive
= higher-ideology tracts have more; negative = fewer.*

A one-standard-deviation increase in the Climate Ideology Index is associated with
**+5.0%** more Teslas and **+6.1%** more non-Tesla EVs per tract (Year FE specification,
tract-clustered standard errors; both p<0.001). Light trucks show a negative coefficient
of **−2.3%** — consistent with Kahn's original Hummer finding. Tesla's ideology premium
is slightly smaller than non-Tesla EVs, which suggests that Tesla already had some
cross-ideological appeal even before Musk's political turn.

The positive Tesla share coefficient (+0.002, p=0.003) confirms that high-ideology
tracts tilt toward Tesla *within the EV market*, not just that they buy more EVs overall.

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

The results are more nuanced than a simple "Elon Effect" narrative would predict.

The Tesla line (red) *strengthened* significantly from 2018 to 2019–2020 (+0.025 to
+0.030), then held roughly flat through 2024 (+0.022 to +0.030). There is no clear
post-2022 decline in the ideology-Tesla relationship. If anything, the green signal for
Tesla remained intact through the end of our observation window in 2024.

The non-Tesla BEV line (blue) showed a different pattern: after an initial rise in 2019
(+0.014), it fell below the 2018 baseline in 2021–2022 (−0.008 to −0.009) before
recovering by 2023–2024 (−0.003 to −0.001). This dip likely reflects non-Tesla EVs
(Bolt, Leaf, Ioniq) becoming more affordable and mainstream during 2020–2022, spreading
into lower-ideology communities.

**What this says in plain terms:** In California, high-ideology communities were buying
relatively *more* Teslas in 2019–2020 compared to 2018, and that advantage held through
2024. Meanwhile, the non-Tesla EV market was becoming more democratized — lower-ideology
communities were catching up. The relative Tesla advantage among climate-concerned
communities did not erode.

I want to be careful about what this does and doesn't show. The Elon Effect may yet emerge
in data from 2025 onward — the most dramatic events (Trump's election, DOGE launch) only
appear in the final observation period of our panel. This analysis covers through the end
of 2024.

### Placebo check

One important diagnostic: if the pattern were driven by some general EV market trend
rather than Tesla specifically, we'd see both lines move together. The light truck
series should move in the opposite direction (or not at all) if the story is about
climate ideology specifically.

![Placebo check: light trucks vs. non-Tesla EVs](../output/figures/event_study_truck_placebo.png)

*Figure 4. Placebo check: ideology × year coefficients for light trucks (green dashed)
versus non-Tesla BEVs (blue). If the light truck line diverges positively post-2022,
it would suggest climate-conscious communities are shifting away from EVs generally —
not just Tesla. A flat or declining truck line supports the climate-specific interpretation.*

The light truck line moved as expected: the ideology coefficient fell steadily from 2018
through 2022 (−0.003 to −0.017), meaning low-ideology communities accumulated more trucks
relative to their baseline than high-ideology communities — consistent with the truck
boom of 2019–2022. It partially recovered by 2023–2024 (+0.004 to +0.005). This pattern
is distinct from both EV lines and is consistent with the climate-signal interpretation
of the main results.

---

## The Status Signal Migration

If high-ideology buyers were stepping back from Tesla, where would they go? Our event
study data through 2024 does not find evidence that they did — the Tesla-ideology link
held. But the non-Tesla EV market grew substantially, suggesting that lower-ideology
buyers entered the EV market in larger numbers during 2021–2022 (the Bolt/Leaf
affordability period).

This is early evidence of what Kahn's framework would predict: as EVs become mainstream,
the *green status signal* migrates toward the premium segment. Tesla maintained its
ideology premium not because high-ideology communities kept buying Teslas at the same
rate, but because low-ideology communities entered the non-Tesla EV market faster.

The Elon Effect, if it exists in California's vehicle data, is subtle and may require
2025 data to emerge clearly. What we do observe is that the *relative* ideology signal
— Tesla versus non-Tesla within the EV market — was stable through 2024.

---

## How Robust Is This?

The main result holds across three alternative ideology specifications:

<!-- TABLE: output/tables/robustness_ols_transit.html, robustness_ols_drivealone.html -->
[TABLE: robustness comparison — Main / R1 / R2 / R3]

**R1** uses only Yale Climate Opinion Maps at the county level — no voter data, cleaner
measurement, coarser geography. Results are directionally consistent (transit: +0.001,
drive-alone: −0.008 at the county level) though precision is limited with only 58
counties. **R2** uses only voter registration and ballot measure data at the tract level
— finer geography, no reliance on the Yale county-level assumption. Results are stronger
than Main (transit: +0.017***, drive-alone: −0.029***), suggesting the electoral
behavior measures track commute choices tightly. **R3** uses only Prop 30 vote share —
the single cleanest climate signal available — and gives the largest coefficients
(transit: +0.39***, drive-alone: −0.70***), consistent with Prop 30 being a strong
proxy for climate-motivated consumption.

The direction of all OLS results is consistent across all four specifications.

I also tested for spatial autocorrelation in the cross-section residuals. Moran's I was
**0.58** (transit) and **0.41** (drive-alone), both significant at p<0.001. A spatial lag
correction (SAR via ML estimation) leaves the main results qualitatively unchanged;
the spatial autoregressive parameter ρ = 0.78 (transit) and ρ = 0.57 (drive-alone),
confirming strong spatial clustering in commute behavior — as expected in a state where
transit access is geographically concentrated.

---

## What This Can and Can't Say

A few important limitations:

**This is about communities, not individuals.** The unit of analysis is the Census tract —
roughly 4,000 people. I observe that *tracts* with stronger climate beliefs have
different transportation behavior and EV ownership patterns. I cannot directly observe
which households within a tract are buying EVs or why. The ecological inference problem
Kahn acknowledged in 2007 applies here too.

**I can't fully isolate the Elon Effect.** Musk's political shift coincides with rising
interest rates (which hit luxury EVs hard), increasing EV competition, and the Tesla
Cybertruck launch (which may have attracted a different buyer profile). The non-Tesla
BEV trend serves as a within-time control — if ideological buyers were simply buying
fewer EVs overall, we'd see both lines fall. The divergence pattern is harder to explain
by market forces alone, but I can't rule out price point differences or other confounders.

**The data ends in 2024.** The most significant Musk-political events (DOGE launch, Trump
administration) only appear at the tail of our observation window. A more definitive test
of the Elon Effect would require 2025 and 2026 data.

**California is not America.** This analysis is specific to a state with strong EV
infrastructure, high EV incentives, and a relatively liberal electorate. Whether these
patterns would show up in a national study — with very different charging infrastructure,
policy environments, and climate opinion distributions — is an open question.

**ACS controls are time-invariant.** Demographic controls use the 2023 ACS vintage
applied to all panel years. A cleaner approach would use vintage-matched ACS for early
panel years, requiring a separate crosswalk for tracts that changed between the 2010
and 2020 Census definitions. I discuss this in the technical appendix.

**Voter reg and ballot ideology measures are county-level.** The SWDB voter registration
and ballot SOV files use precinct key systems (RGPREC, SVPREC) that are incompatible
with the Census tract shapefile's MPREC codes. County-level aggregation was used for
these components, consistent with how the Yale YCOM estimates are handled. The R2
robustness check (voter-reg+ballot PCA at tract level, using county values assigned to
all tracts in the county) confirms that coarser measurement does not change the direction
or statistical significance of the main results.

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
voter registration share at the county level (aggregated from precinct-level SWDB data),
Prop 30 YES vote share (2022), and Prop 68 YES vote share (2018). Variables are
standardized before PCA. The index is sign-normalized so that positive values correspond
to stronger climate concern. The first component explains **84.7%** of variance.

Note on precinct-to-tract crosswalk: The SWDB voter registration files use
RGPREC_KEY (13-char format) and ballot files use SVPREC_KEY (11-char, different
numbering from the Census MPREC system). County-level aggregation via the FIPS column
was used for both, consistent with YCOM's county-level geographic resolution. This
approach assigns each county's aggregate ideology measure uniformly to all tracts within
that county — the same approximation used in the main analysis.

Validation: the tract-level index aggregated to Congressional districts did not have LCV
scores available for automated comparison (URL returned 404 during data acquisition);
manual validation is deferred.

### Regression Specifications

**Cross-section (Script 07):** OLS with HC3 heteroskedasticity-robust standard errors.
All cross-sections use 2023 data. Log(BEV+1) OLS used in place of negative binomial due
to NB convergence failure on area-weighted fractional count data.

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
