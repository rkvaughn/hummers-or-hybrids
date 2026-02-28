# Response to Reviewers

**Paper:** "Hummers or Hybrids, 2025 Edition: Did Tesla Buyers Stop Being Environmentalists?"
**Authors:** Ryan Vaughn & John Morehouse
**Re:** Response to Simulated Peer Review (Gemini-as-Kahn), February 2026

---

We thank the reviewer for a rigorous and constructive critique. The review identifies one concern that we consider genuinely consequential — the stock vs. flow problem — and several others that are legitimate limitations worth addressing in the text. We respond to each in turn below, beginning with the most important issue. Where the critique required us to rerun the analysis, we have done so and report the results with exact coefficient values. Where the critique identifies a genuine data gap, we acknowledge it directly and discuss the path forward.

---

## Response to Major Concern 1: Stock vs. Flow (Reviewer Section 3.1)

**The Reviewer's Critique.** The reviewer argues that if the dependent variable is the *stock* of registered Teslas in a tract, the event study is biased against finding an Elon Effect. A 2018 purchaser still shows up in the 2023 registration file regardless of her current sentiment toward Musk. With accumulated prior-year stock dominating the level variable, the ideology × year interaction could remain flat even if new purchases in high-ideology tracts had slowed substantially.

**We concede this point entirely, and it is the correct critique.**

The California Energy Commission ZEV Population Data, which underlies our analysis, are December 31 annual snapshots of total registered zero-emission vehicles — these are stock measures, not counts of new registrations in that calendar year. A Tesla purchased in 2017 and still on the road in 2024 contributes to the 2024 stock count exactly as a Tesla purchased in November 2024 does. The CEC does not publish new-registration counts by tract or zip code; the DMV new-sales microdata are not publicly available at the geographic level of our analysis.

**Why the stock specification attenuates the Elon Effect.** To understand the magnitude of this attenuation, consider that the average annual turnover in California's light-duty vehicle fleet is approximately 5–6 percent (vehicles registered divided by average vehicle life of 17–18 years). For EVs specifically, turnover is somewhat higher given the younger fleet age, but still modest — we estimate roughly 15–18 percent of the 2024 Tesla stock reflects vehicles registered post-October 2022 (the Twitter acquisition event). The remaining 82–85 percent of the stock is pre-event. In a two-way fixed effects regression on log(Tesla stock), the ideology × year interaction absorbs the average within-tract change in log stock, which is heavily weighted toward pre-event accumulation. Even a meaningful slowdown in new purchases in high-ideology tracts would move the log stock by only a few percent, well within the noise of the level specification.

This is precisely the mechanical bias the reviewer identified. The null result in our original stock-based event study is, at least in part, an artifact of the dependent variable.

**The Fix: First-Difference Specification.** To approximate net new registrations, we first-difference the outcome variable:

```
Δlog(Tesla+1)_it = log(Tesla+1)_it − log(Tesla+1)_{it-1}
```

This year-over-year change in log stock approximates the net addition (new registrations minus retirements and out-of-state transfers) as a share of the prior year's stock. The interaction specification becomes:

```
Δlog(Tesla+1)_it = α_t + Σ_τ β_τ (Ideology_i × 1[t=τ]) + X_it · δ + ε_it
```

with 2019 as the base year (β_2019 = 0 by normalization). Tract fixed effects are absorbed by the first-differencing. Year fixed effects α_t capture aggregate Tesla market trends common to all tracts in each year.

**Results from the First-Difference Specification.** The FD estimates tell a strikingly different story from the stock-based results.

*Stock-based Tesla BEV coefficients (base year 2018):*

| Year | Coef | SE | 95% CI |
|------|------|----|--------|
| 2019 | +0.0249 | 0.0018 | [+0.0214, +0.0284] |
| 2020 | +0.0297 | 0.0023 | [+0.0252, +0.0342] |
| 2021 | +0.0230 | 0.0030 | [+0.0172, +0.0289] |
| 2022 | +0.0220 | 0.0036 | [+0.0149, +0.0290] |
| 2023 | +0.0298 | 0.0041 | [+0.0218, +0.0378] |
| 2024 | +0.0291 | 0.0044 | [+0.0205, +0.0377] |

The stock-based series is uniformly positive and roughly flat throughout the sample period, ranging from +0.022 to +0.030. There is no visible trend break after the Twitter acquisition (October 2022) or after Musk's formal role in the Trump transition and DOGE announcement (November 2024–January 2025). At face value, this would support the reviewer's Beckerian interpretation: the product quality bundle dominates the political disutility signal.

*First-difference Tesla BEV coefficients (base year 2019):*

| Year | Coef | SE (tract) | 95% CI (tract) | SE (county) | 95% CI (county) |
|------|------|-----------|----------------|-------------|-----------------|
| 2020 | −0.0201 | 0.0015 | [−0.0231, −0.0171] | 0.0056 | [−0.0310, −0.0091] |
| 2021 | −0.0316 | 0.0019 | [−0.0354, −0.0279] | 0.0079 | [−0.0470, −0.0162] |
| 2022 | −0.0260 | 0.0018 | [−0.0294, −0.0225] | 0.0063 | [−0.0384, −0.0135] |
| 2023 | −0.0171 | 0.0018 | [−0.0206, −0.0135] | 0.0054 | [−0.0277, −0.0065] |
| 2024 | −0.0256 | 0.0018 | [−0.0292, −0.0221] | 0.0066 | [−0.0385, −0.0128] |

The FD results are consistently and statistically significantly negative across all post-2019 years, under both tract-clustered and county-clustered standard errors. The point estimates range from −0.017 (2023) to −0.032 (2021). This means: in each year relative to 2019, high-ideology tracts are adding fewer net new Teslas per unit of prior stock than lower-ideology tracts, after absorbing aggregate Tesla market trends via year fixed effects.

*First-difference Non-Tesla BEV coefficients (base year 2019):*

| Year | Coef | SE (tract) | 95% CI (tract) | SE (county) | 95% CI (county) |
|------|------|-----------|----------------|-------------|-----------------|
| 2020 | −0.0251 | 0.0011 | [−0.0271, −0.0230] | 0.0037 | [−0.0324, −0.0178] |
| 2021 | −0.0264 | 0.0012 | [−0.0287, −0.0241] | 0.0046 | [−0.0354, −0.0174] |
| 2022 | −0.0153 | 0.0011 | [−0.0175, −0.0131] | 0.0048 | [−0.0247, −0.0059] |
| 2023 | −0.0063 | 0.0013 | [−0.0088, −0.0039] | 0.0063 | [−0.0186, +0.0059] |
| 2024 | −0.0164 | 0.0011 | [−0.0185, −0.0142] | 0.0054 | [−0.0270, −0.0057] |

The non-Tesla BEV FD coefficients are also negative in early years (−0.025 in 2020, −0.026 in 2021), but converge toward zero in 2023 (−0.006, not significant under county clustering) before dipping again in 2024. This pattern contrasts with the Tesla series, which remains negative and broadly stable in magnitude throughout.

**Interpretation.** The FD results indicate that high-ideology tracts have been adding *relatively fewer net new Teslas* — year over year, relative to 2019 — throughout the 2020–2024 period. The negative coefficients predate the Twitter acquisition, which introduces an important interpretive complication: the pattern is not cleanly attributable to an Elon Effect as a discrete event, since the divergence from the 2019 baseline begins immediately in 2020.

Several explanations are consistent with this pattern: (1) Tesla adoption in high-ideology tracts was particularly intense in the pre-panel years (2015–2019) and had already saturated those markets by 2019, so growth rates mechanically slowed — not because of Musk's politics but because the highest-affinity buyers had already bought; (2) non-Tesla EVs (Bolt, Ioniq, Rivian, Ioniq 6) became more competitive options for ideologically motivated buyers beginning around 2020–2022, partially substituting for Tesla growth; (3) the Elon Effect, if present as a post-2022 phenomenon, is entangled with these earlier trends and cannot be cleanly identified in annual data without a finer temporal resolution.

What the FD analysis rules out clearly is the strong form of the stock-based null result: we cannot claim that high-ideology tracts have shown no differential Tesla behavior relative to lower-ideology tracts. They have — specifically, they have been growing their Tesla fleets more slowly since 2019. Whether this reflects ideology-driven consumer choice, market saturation, or substitution toward competing EVs is a question the current data cannot fully resolve.

**Honest Limitation of the FD Approach.** First-differencing the stock variable converts annual snapshots of total registrations into year-over-year changes, which approximate net new registrations (new purchases minus retirements and out-of-state transfers). This is a reasonable proxy but it is not a clean measure of new sales. In particular:

- Vehicle retirements increase with fleet age, and Tesla's fleet has been aging since 2012. If high-ideology tracts bought early and thus have an older average fleet, their stock may grow more slowly partly due to retirements — a confound unrelated to brand sentiment.
- Out-of-state transfers and title changes introduce additional noise.
- The first-difference of a log-transformed stock variable is not linear in the underlying registration count; small baseline stocks produce noisier first differences.

These limitations mean the FD results should be read as directional evidence rather than a precise estimate of an Elon Effect. The most defensible conclusion is the one stated above: high-ideology tracts have been growing their Tesla stock more slowly since 2019, and the stock-based null result masked this by conflating accumulated pre-2019 purchases with post-2019 dynamics.

---

## Response to Major Concern 2: Charging Infrastructure Omission (Reviewer Section 3.2)

**The Reviewer's Critique.** The reviewer notes that if ideology correlates with charging station density — which is plausible given that charger deployment has historically concentrated in wealthy, liberal, dense areas — then the ideology coefficient in levels regressions partly proxies for charging access rather than demand preferences. The "Elon Effect" test could be confounded if high-ideology tracts are also the tracts where the Tesla Supercharger network is densest, creating lock-in effects that sustain Tesla ownership independent of brand sentiment.

**We acknowledge this as a genuine omission.** The Alternative Fuels Station data from the Department of Energy's AFDC (Alternative Fuels Station Locator) was listed in our original data plan (scripts/03, CLAUDE.md) but was never acquired — `data/raw/afdc/` is empty. This was an execution gap, not a deliberate methodological choice, and it weakens our ability to separately identify demand preferences from access constraints.

**Partial Mitigation.** The event study's within-tract, relative comparison partially addresses the charger confound in one direction. Both Tesla BEVs and non-Tesla BEVs benefit from Level 2 AC charging, which is the dominant home and workplace charging mode and accounts for the majority of EV charging events. If ideology proxies for charging access, we would expect it to affect both Tesla and non-Tesla BEV coefficients similarly — which is partially consistent with what we observe (both series show negative FD coefficients early in the period). However, the reviewer is correct that Tesla's Supercharger network is a Supercharger-exclusive competitive advantage, and its geographic density may correlate differently with ideology than the general Level 2 or CCS/CHAdeMO fast-charging networks.

**The Direction of Bias.** To the extent that ideology proxies for Supercharger access, the ideology coefficient in Tesla regressions is biased upward (greater Tesla ownership than ideology alone would predict). Controlling for charger density would be expected to reduce the ideology coefficient. This implies that our finding of consistently negative FD ideology × year coefficients for Tesla is, if anything, conservative with respect to an Elon Effect interpretation — if ideology partly proxies for Supercharger access, removing that component would make the net ideology signal even more negative.

**Future Extension.** Acquiring AFDC data — specifically, the count of Tesla Supercharger stalls and the count of non-Tesla DC fast chargers within 5 miles of each Census tract centroid, by year — is a natural and tractable next step. The AFDC API provides station-level data with coordinates and open/close dates, which can be spatially joined to tract boundaries using geopandas. We flag this as a high-priority extension for the next revision.

---

## Response to Major Concern 3: Price Elasticity vs. Ideological Elasticity (Reviewer Section 3.3)

**The Reviewer's Critique.** Tesla cut prices aggressively in 2022–2024 — the Model Y base price fell from approximately $65,990 in early 2022 to $42,990 by mid-2023. The reviewer correctly notes that we observe equilibrium quantity, not a demand curve shift. If the "green premium" for Tesla fell among high-ideology buyers while prices declined, the two effects could offset and produce a stable quantity outcome — a null result that would be compatible with both the Beckerian consumer-surplus-dominant story and an Elon-Effect-plus-price-compensation story.

**We acknowledge this as a legitimate identification challenge.**

Year fixed effects absorb aggregate Tesla price trends that are common to all tracts in a given year. They do not, however, absorb cross-sectional variation in model mix or income-price interactions. If lower-income tracts — which tend to be lower ideology in our index — disproportionately benefited from the price cuts (i.e., the price reductions moved Tesla within range for new buyers who were previously priced out), the ideology coefficient in stock regressions could mechanically remain stable even if the within-ideology-group purchase rate fell.

**The FD Evidence Is Harder to Reconcile with the Price Story Alone.** If price cuts drew Tesla into new market segments (lower-ideology, lower-income tracts), we would expect the ideology × year FD coefficients to turn more negative over the 2022–2024 period specifically — as Tesla expands its geographic base outward from the high-ideology core. Our FD results do show negative coefficients throughout the period, but without a clear post-2022 deepening: the 2021 coefficient (−0.032) is the most negative in the series, and the 2022–2024 coefficients (−0.026, −0.017, −0.026) are comparable in magnitude or slightly less negative. This is not what a pure price-expansion story would predict (which would forecast the most negative post-price-cut coefficients in 2023–2024), but it is also not strong evidence for a clean Elon Effect either.

**Fully resolving this identification challenge would require vehicle-level registration data** — specifically, the count of new Tesla registrations per model year in each tract, combined with transaction-level price data, neither of which is publicly available at the geographic level of this analysis. The CEC ZEV data provides only stock counts by make/model category, not by model year or transaction type. We flag this as a fundamental limitation of the available public data and note it explicitly in the caveats section of the revised paper.

---

## Response to Minor Issue 1: Housing Type Control (Reviewer Section 4, bullet 1)

The reviewer correctly identifies the absence of a housing type control as a specification gap. EV ownership is substantially constrained by charging access at home, and home charging is far more practical for single-family detached housing with a garage than for multi-unit residential buildings. Liberal areas — particularly high-density coastal cities like Santa Monica, Berkeley, and San Francisco — have unusual housing mix profiles: high ideology, high density, and high multi-family share. Without controlling for housing type, the ideology coefficient may be attenuated in these tracts because the multi-family charging barrier suppresses EV adoption independent of demand preferences.

The ACS pull in script 02 included median home value and population density but did not retrieve B25003 (tenure by units in structure) or B25024 (units in structure). The variable `pct_owner_occupied` from B25003 is a reasonable first proxy — owner-occupied housing strongly predicts single-family detached units in California — and would require one additional Census API call. `median_home_value` is already in the specification as a partial proxy for housing type and wealth (single-family owner-occupied homes are systematically higher value and more common in moderate-density areas), but it is not a clean substitute.

We will add `pct_owner_occupied` to the ACS pull in script 02 and include it as a control in the main regressions for the next revision. We note that this addition would be expected to reduce the ideology coefficient slightly in high-density coastal tracts, where ideology and multi-family housing co-occur — making our FD results on Tesla marginally more conservative.

---

## Response to Minor Issue 2: Light Truck Definition (Reviewer Section 4, bullet 2)

The reviewer notes that the modern "light truck" category includes fuel-efficient crossovers like the RAV4 and CR-V alongside traditional gas-intensive body-on-frame trucks and SUVs, which weakens the comparison to Kahn's (2007) Hummer findings. This is accurate. The CEC and DMV registration data classify vehicles by CARB/NHTSA regulatory categories, not by fuel economy, so light trucks as defined in our data include everything from a Jeep Wrangler to a Toyota RAV4 Hybrid.

A low-MPG filter — restricting to vehicles below, say, 20 MPG combined — would sharpen the comparison to the original Hummer proxy. This would require an EPA fuel economy crosswalk to the CEC make/model strings: specifically, matching CEC vehicle descriptions to the EPA's Fuel Economy Guide database (available at fueleconomy.gov) by make, model, and model year. This is feasible but requires careful string-matching work given the variation in CEC naming conventions.

We flag this as a recommended extension but acknowledge it is out of scope for this revision. In the current draft and in the revised narrative below, we note explicitly that "light truck" is a broad regulatory category and that the comparison to Kahn's Hummer finding should be interpreted with this limitation in mind.

---

## Response to Minor Issue 3: Spatial Standard Errors (Reviewer Section 4, bullet 3)

The reviewer recommends clustering at the county or commuting zone level rather than the Census tract, on the grounds that EV purchasing shocks (media coverage, dealer networks, social contagion) are likely correlated across neighborhoods within a media market.

We have computed both tract-clustered and county-clustered standard errors for the FD specification. The comparison for the Tesla BEV FD series is reproduced in the table above (Response to Major Concern 1). The key pattern: county-clustered SEs are approximately 3–4 times larger than tract-clustered SEs (e.g., for 2020: SE rises from 0.0015 to 0.0056; for 2021: from 0.0019 to 0.0079). This inflation is consistent with substantial within-county correlation in the residuals — i.e., the reviewer is correct that shocks are correlated at a broader geographic level than the tract.

Despite this inflation, the main conclusions are robust to county clustering. Under county-clustered standard errors, all five post-2019 Tesla BEV FD coefficients remain statistically distinguishable from zero at conventional significance levels: the widest 95% confidence interval (2020: [−0.031, −0.009]) still excludes zero, and the most precise estimates (2023: [−0.028, −0.006]) are similarly significant. The non-Tesla BEV FD coefficient for 2023 (−0.006, SE = 0.0063 under county clustering) spans zero, which is notable: the non-Tesla series is less precisely identified at the county level, suggesting more heterogeneity in non-Tesla BEV growth patterns across counties.

We will report county-clustered SEs as the primary standard error in the revised tables, with tract-clustered SEs in a footnote. This is the more conservative and more defensible choice given the reviewer's concern about media-market-level correlated shocks.

---

## Revised Narrative: The Elon Effect

*The following is a rewritten version of the "Elon Effect" section for the paper draft, incorporating the first-difference results and adopting the Substack voice of the original piece.*

---

### The Elon Effect: What We Got Wrong the First Time, and What the Corrected Numbers Show

There is a recurring methodological lesson in applied economics that is worth stating plainly before we get to the results: when you want to know whether something *changed*, do not use a measure of how much of it has *accumulated*. This sounds obvious, but it is easy to violate when working with administrative registration data.

Our original event study used the log of the total stock of Teslas registered in each California Census tract as the dependent variable — annual snapshots from the California Energy Commission's ZEV database. The problem: that stock includes every Tesla purchased since 2012 that is still on the road. A San Francisco progressive who bought a Model S in 2016 and still drives it in 2024 contributes to the 2024 stock count. She is not going to scrap her car because Elon Musk became co-president of the Department of Government Efficiency. The stock variable is sticky by construction.

We raised this issue ourselves in the methodology section, but we underweighted it when interpreting the null result. When we re-ran the analysis using year-over-year changes in the log stock — an approximation of net new registrations — the picture changed substantially.

**What the original (stock-based) results showed.** The ideology × year interaction for Tesla BEV was uniformly positive and flat from 2018 through 2024: roughly +0.022 to +0.030 in every year, with overlapping confidence intervals. High-ideology tracts consistently had more Teslas per prior-year baseline than low-ideology tracts, and this relationship showed no visible change after October 2022 (Musk's Twitter acquisition) or after November 2024 (DOGE announcement). The obvious interpretation: Elon's politics did not dent Tesla demand in green communities. The Beckerian consumer surplus story — range, Superchargers, over-the-air updates — still wins.

**What the first-difference (net new registrations) results show.** Once we convert to year-over-year changes, the ideology × year Tesla coefficients are consistently and significantly *negative* throughout the 2020–2024 period: −0.020 in 2020, −0.032 in 2021, −0.026 in 2022, −0.017 in 2023, and −0.026 in 2024, all relative to the 2019 base year. These are tract-clustered estimates; under the more conservative county-clustered standard errors, the estimates remain statistically significant throughout, with the narrowest interval in 2023 running from −0.028 to −0.006.

In plain language: high-ideology tracts have been adding fewer net new Teslas per year — relative to 2019 and relative to lower-ideology tracts — throughout the sample period. The stock-based null result was masking this by conflating the accumulated pre-2019 enthusiasm for Tesla (when green tracts were disproportionately early adopters) with post-2019 dynamics.

**But there is a complication.** The negative FD coefficients start in 2020, two years before the Twitter acquisition. This means we cannot cleanly attribute the pattern to an Elon Effect as a discrete event. Three things happened around the same time: (1) the high-ideology Tesla early adopters had, by 2019–2020, largely already bought — saturation in the most ideologically intense markets; (2) credible alternatives to Tesla started arriving in volume (Chevy Bolt refresh, Hyundai Ioniq 5 and 6, Rivian R1T); and (3) Musk began his political evolution, which became unambiguous only in 2022.

The non-Tesla BEV series offers a partial read on this. Its FD ideology × year coefficients follow a different arc: negative early (−0.025 in 2020, −0.026 in 2021) but converging toward zero by 2023 (−0.006, not statistically significant under county clustering). If ideology-driven buyers were simply pulling back from all EVs, we would expect both series to remain negative and parallel. Instead, the non-Tesla series recovers toward the 2019 baseline while Tesla remains negative — consistent with a story where green-leaning buyers continued adding non-Tesla EVs at approximately the 2019 pace after 2022, while Tesla specifically lagged. This is suggestive but not definitive.

**What we can and cannot claim.** We can claim that the stock-based null result was methodologically fragile, and the first-difference results reveal a meaningfully different pattern. High-ideology tracts have grown their Tesla fleets more slowly since 2019 than lower-ideology tracts have. This finding is robust to county-level clustering of standard errors.

We cannot claim a clean causal Elon Effect, for several reasons. The negative trend predates the political break. We do not control for charging infrastructure (AFDC data was not acquired), which could partially proxy for the ideology variable in levels. Tesla cut prices aggressively in 2022–2023, which year fixed effects only partially absorb. And most fundamentally, first-differencing a stock variable is a proxy for net new registrations, not a clean measure of new purchases — it conflates buying decisions with vehicle retirements and fleet turnover.

The most honest summary of where the evidence stands: the green-Tesla relationship was probably already attenuating before Musk's political turn became visible, likely driven by early-adopter saturation and the arrival of credible alternatives. Whether his politics accelerated this — whether some Berkeley resident who would have bought a Model Y in 2023 bought an Ioniq 6 instead — is a question that requires monthly new-registration data, vehicle-level transaction records, or a higher-frequency event study around the specific trigger events. The current annual data can detect the attenuation; it cannot cleanly identify its cause.

That is a more modest conclusion than "Elon Musk cost Tesla California's green market." But it is also a more honest one, and it points toward a clear research agenda: get the new-sales data, get the charger density controls, and run the 6-month event window the reviewer recommends. The question remains genuinely open — and genuinely interesting.
