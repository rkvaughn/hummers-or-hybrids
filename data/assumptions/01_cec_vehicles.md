# Data Assumptions: CEC / CA DMV Vehicle Registration

**Source:** California Energy Commission / CA Open Data Portal
**File:** `data/raw/cec_zev/annual/vehicles_{year}.csv` (2018–2024)
**Script:** `scripts/01_acquire_cec.py`

---

## A1 — Annual snapshot treated as stock, not flow

**Assumption:** Each file is a December 31 end-of-year snapshot of registered vehicles. We treat this as the vehicle *stock* in a given ZIP code at year-end.

**Implication:** We do not observe vehicle purchases directly — only cumulative registration counts. A vehicle registered in 2019 still appears in 2024. The dependent variable in panel regressions is the total *stock* of EVs per ZIP/year, not new registrations.

**Writeup note:** "Vehicle counts represent the registered stock as of December 31 of each year, not new sales. A vehicle purchased in an earlier year remains in the count as long as it stays registered in California. This means our estimates capture cumulative adoption patterns, not marginal purchase decisions within the year."

---

## A2 — Privacy suppression creates a floor of noise

**Assumption:** The CEC suppresses make-level counts below 10 per ZIP/year/fuel/make combination, recording them as `OTHER/UNK`. We retain these rows as-is in the raw data and drop them from make-specific analyses (e.g., Tesla counts).

**Implication:** Small ZIPs with few EVs have make-level composition masked. This disproportionately affects rural or low-adoption ZIPs in early years (2018–2020) and small/new non-Tesla brands throughout the panel. Tesla, as the dominant brand, is less affected.

**Potential bias:** If high-ideology rural areas disproportionately have suppressed make counts, our ideology-EV correlation at the ZIP level may be attenuated in early years.

**Writeup note:** "The CEC suppresses vehicle make counts below 10 per ZIP/year/fuel type combination, recording them as 'Other/Unknown.' These suppressed records are excluded from make-specific regressions. Because suppression is more common in ZIPs with low EV adoption, this may introduce attenuation bias in early panel years and disproportionately affects smaller non-Tesla EV brands."

---

## A3 — Fuel type recoding

**Assumption:** Raw fuel type strings are recoded to standard codes:

| Raw string | Code | Included as ZEV |
|---|---|---|
| Battery Electric | BEV | Yes |
| Plug-in Hybrid | PHEV | Yes |
| Hydrogen Fuel Cell | FCEV | Yes |
| Gasoline | GAS | No (light truck proxy only) |
| Diesel and Diesel Hybrid | DIESEL | No |
| Hybrid Gasoline | HEV | No (not plug-in) |
| Flex-Fuel | FLEX | No |
| Natural Gas | CNG | No |

**Implication:** PHEVs are included as ZEVs. PHEVs can run on gasoline and may be purchased for different reasons than BEVs (e.g., range anxiety, tax credit eligibility). Robustness checks exclude PHEVs and analyze BEV-only.

**Writeup note:** "We classify Battery Electric (BEV), Plug-in Hybrid (PHEV), and Hydrogen Fuel Cell (FCEV) vehicles as zero-emission vehicles following CEC conventions. Because plug-in hybrids can operate primarily on gasoline and may be adopted for different reasons than pure EVs, we report BEV-only results as a robustness check."

---

## A4 — Tesla classification by make name only

**Assumption:** Vehicles are flagged as Tesla if `make == "TESLA"`. This captures all Tesla models (Model 3, Y, S, X, Cybertruck) without distinguishing between them.

**Implication:** We cannot separate the affordable/mass-market Teslas (Model 3, Y) from the premium models (S, X) or the politically charged Cybertruck without model-level data. Model-level CEC data exists in the Excel file — flag for future disaggregation.

**Writeup note:** "All Tesla-branded vehicles are grouped together regardless of model. We cannot distinguish mass-market Teslas (Model 3, Model Y) from premium models (S, X) or the Cybertruck in the primary ZIP-level analysis, though the CEC Excel file contains model-level data that could support future disaggregation."

---

## A5 — Light truck classification by make name

**Assumption:** The "modern Hummer" proxy (light trucks) is classified by make name membership in a fixed list: Ford, RAM, Chevrolet, GMC, Toyota, Nissan, Honda, Jeep, Dodge. All fuel types for these makes under the light-duty classification are included.

**Implication:** This is a crude proxy. Ford also sells the F-150 Lightning (BEV) and Maverick Hybrid; Toyota sells the Tacoma. We cannot distinguish truck models from sedans/SUVs within these makes at the ZIP/fuel level without model-level data.

**Writeup note:** "Light trucks are approximated by vehicles from common truck manufacturers (Ford, RAM, Chevrolet, GMC, Toyota, Nissan, Honda, Jeep, Dodge) under the light-duty classification. This includes all models from these manufacturers, not just pickup trucks. A more precise measure using model-level data from the CEC Excel file is a robustness check."

---

## A6 — ZIP code geography, not Census tract

**Assumption:** CEC data is reported at the ZIP code level. Census tracts are our target geography for the panel analysis. We crosswalk ZIP → Census tract using HUD ZIP-ZCTA-Tract relationship files (see `data/assumptions/04_crosswalk.md`).

**Implication:** ZCTAs do not align perfectly with ZIP codes or Census tract boundaries. The crosswalk introduces measurement error, particularly in areas where a single ZIP spans multiple tracts with heterogeneous characteristics.

**Writeup note:** See crosswalk assumptions file.
