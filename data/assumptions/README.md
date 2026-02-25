# Data Assumptions Log

Each file documents assumptions made during data acquisition and pre-processing for one source. These notes are the basis for the Data & Methods section and appendix of the final writeup.

| File | Source | Key assumptions |
|---|---|---|
| `01_cec_vehicles.md` | CEC / CA DMV vehicle registration | Stock vs. flow, privacy suppression, fuel recoding, Tesla/truck classification, ZIP geography |
| `02_acs.md` | ACS 5-year estimates | Single cross-section of controls, sentinel values, density calculation, education coding |
| `03_ideology.md` | YCOM, voter registration, ballot measures | County-level YCOM assignment, 2020 vintage as time-invariant, Prop 30 conflation issue, precinct crosswalk |
| `04_crosswalk.md` | ZIP→tract, precinct→tract, county→tract | ZCTA proxy, population weighting, areal interpolation, rural measurement error bias |

## Conventions

- Each assumption is tagged **A1, A2, ...** within its file
- Each entry includes: the assumption stated plainly, its implication for estimates, the expected bias direction where known, and a **Writeup note** — a draft sentence or paragraph for the methods section
- TODOs flag decisions not yet finalized that require user input before analysis
