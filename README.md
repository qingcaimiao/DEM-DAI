# DEM-DAI — Cumulative burden of three geriatric syndromes and incident dementia

Analysis code and aggregated results for the manuscript:

> **Cumulative burden of three geriatric syndromes and incident dementia across six harmonized
> ageing cohorts: a time-lagged analysis of 71,867 participants**

The exposure is a minimal, unweighted three-component index (DAI, range 0–3) — the **disability,
multimorbidity and depression accumulation index**. The outcome is algorithmically ascertained
incident dementia. Six population-based cohorts harmonized through the Gateway to Global Aging Data
are pooled by DerSimonian–Laird random-effects meta-analysis, with time-lagged, time-varying,
trajectory, competing-risk, mediation and E-value analyses.

## Version

| Tag | Date | Changes |
|---|---|---|
| **`v1.1.0`** | 2026-10-27 | Figures regenerated and now byte-identical to those embedded in the submitted manuscript; all analysis scripts synchronised with the version that produced the reported results; construct name corrected to *disability, multimorbidity and depression accumulation index*; manuscript-assembly paths parameterised through environment variables; development artefacts removed |
| `v1.0.0` | 2026-10-14 | First archive |

See `CHANGELOG.md` for details. Version `1.0.0` remains available and citable.

## Data availability

**No participant-level data are distributed with this repository.** The harmonized cohort data are
available to registered researchers from the *Gateway to Global Aging Data* (https://g2aging.org)
and from each cohort's own repository:

| Cohort | Region | File expected by `dem_lib.py` |
|---|---|---|
| CHARLS | China | `Charls/charls.csv` |
| ELSA | England | `Elsa/elsa.csv` |
| HRS | USA | `HRS/hrs.csv` |
| KLoSA | Korea | `KLOSA/klosa.csv` |
| MHAS | Mexico | `mhas/mhas.csv` |
| SHARE | Europe | `SHARE/share.csv` |
| LASI | India | `LASI/lasi.csv` (single wave; not in the primary analysis) |

Point the analysis at your local copy either by setting the `DEM_ROOT` environment variable or by
editing `ROOT` in `code/dem_lib.py` (line 12). File and identifier names are as expected by
`dem_lib.FILES` / `dem_lib.ID`; if your extracts use different names, adjust those two dictionaries.

## Scope of reproducibility

This archive is published for **transparency and verification**, and we state plainly what can and
cannot be reproduced from it.

| Step | Reproducible here? | Requirements |
|---|---|---|
| Analysis chain `p2` → `p17` | **Yes** | cohort data under `DEM_ROOT`; `pip install -r requirements.txt` |
| Table construction `p22` | **Yes** | a populated `code/out/`, or `DEM_OUT=../results` to reuse the published aggregates |
| Audit / verification `p18`, `p24`–`p38` | **Yes** | a manuscript `.docx`; point `DEM_DOCX` at it |
| Manuscript assembly `revise_apply` → `p23` → `p21` | **Partly** | needs the *pre-revision* manuscript `.docx`, which is **not distributed** (it contains the authors' working draft). All paths are parameterised (`DEM_SRC_DOCX`, `DEM_DST_DOCX`, `DEM_FIGDIR`), so the chain runs as soon as such a file is supplied. |
| Final Word/PDF rendering and journal-specific layout | **No** | performed in Microsoft Word; pagination and table fitting are not scriptable |

Two points worth stressing:

1. **No number is ever typed by hand.** Every statistic in the manuscript is read from
   `results/_ms_numbers.csv`, which is itself written by `p17_ms_numbers.py` from the upstream CSVs.
   `p18_verify_ms_numbers.py` re-extracts every number from the manuscript text and fails if any of
   them cannot be traced back to that file.
2. The assembly chain affects **typesetting only**. It inserts table objects, replaces figure files
   and applies text rules; it does not compute or alter any estimate.

## Reproducing the analysis

```bash
pip install -r requirements.txt
export DEM_ROOT=/path/to/cohort/data      # Windows: set DEM_ROOT=D:/shujuku/
cd code
python p2_build_cog.py      # cognitive harmonization
python p3_build_dai.py      # exposure construction (DAI, 0-3)
python p4_surv_cox.py       # primary Cox models (M1-M4)
python p5_tables.py         # cohort-level tables
python p6_lag_hetero.py     # time-lag ladder / heterogeneity
python p7_mediation.py      # mediation (three frameworks)
python p8_competing.py      # competing risks (Fine-Gray)
python p9_subgroup.py       # subgroups / interaction
python p10_mice.py          # multiple imputation
python p11_assemble.py      # assemble cohort-level inputs
python p12_outcomes.py      # alternative outcome definitions
python p13_timevar.py       # interval-based time-varying models
python p14_cindex.py        # discrimination / paired bootstrap
python p15_missing.py       # missingness
python p16_audit.py         # cohort-level audit
python p17_ms_numbers.py    # single source of truth for every number in the manuscript
```

Outputs are written to `code/out/`. To reuse the published aggregates instead of recomputing them,
`export DEM_OUT=/path/to/this/repo/results` before running the downstream scripts.

## Manuscript assembly

```bash
export DEM_SRC_DOCX=/path/to/pre-revision-manuscript.docx   # not distributed
export DEM_DST_DOCX=/path/to/output_v4.docx
python revise_apply.py      # text rules (revise_ms.py); unpacks the source on first run
python p22_tables.py        # build table objects -> out/_tables.json
python p23_insert_tables.py # insert tables into the .docx
python p21_replace_figs.py  # replace Fig. 1-4 (must run after p23)
```

## Verification

| Script | Check |
|---|---|
| `p18_verify_ms_numbers.py` | every body-text number reproduces from `_ms_numbers.csv` |
| `p24_verify_docx.py` | document structure |
| `p26_audit_docx_numbers.py` | table cells and table notes, token by token |
| `p28_derived_check.py` | derived statements ("X %", "X-fold", ranges) |
| `p32_codepoint_scan.py` | non-standard Unicode code points |
| `p36_forbidden_typos.py` | forbidden strings / leftover placeholders |
| `p38_external_claim_scan.py` | source-file counts for referee claims |
| `j39_layout_audit.py` | virtual typesetting: longest unbreakable token vs column width |
| `j40_colfit.py` | table column-width fitting against the actual page geometry |
| `j47_refs_verify.py`, `j47b_refs_titlecheck.py` | reference verification against Crossref / Europe PMC |

## Environment

Python 3.13. `requirements.txt` pins the exact package versions used for the published results.
The scripts were developed and run on Windows; they contain no platform-specific code.

## Licence

Code: MIT (see `LICENSE`). Aggregated results in `results/`: CC BY 4.0.

## Citation

If you use this code, please cite the manuscript and the archived release (see `CITATION.cff`).
