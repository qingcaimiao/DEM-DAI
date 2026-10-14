# DEM-DAI — Cumulative burden of three geriatric syndromes and incident dementia

Analysis code for the manuscript:

> **Cumulative burden of three geriatric syndromes and incident dementia across six harmonized
> ageing cohorts: a time-lagged analysis of 71,867 participants**

The exposure is a minimal, unweighted three-component index (DAI, range 0–3) of **disability,
multimorbidity and depression**; the outcome is algorithmically ascertained incident dementia.
Six population-based cohorts harmonized through the Gateway to Global Aging Data are pooled by
DerSimonian–Laird random-effects meta-analysis, with time-lagged, time-varying, trajectory,
competing-risk, mediation and E-value analyses.

## Data availability

**No participant-level data are distributed with this repository.** The harmonized cohort data are
available to registered researchers from the *Gateway to Global Aging Data*
(https://g2aging.org) and from each cohort's own repository:

| Cohort | Region |
|---|---|
| CHARLS | China |
| ELSA | England |
| HRS | USA |
| KLoSA | Korea |
| MHAS | Mexico |
| SHARE | Europe |

Place the cohort files in a directory and point `ROOT` in `code/dem_lib.py` (line 12) at it.
Only `results/` (aggregated estimates, tables and figures) is included here.

## Reproducing the analysis

```bash
pip install -r requirements.txt
# 1) edit ROOT in code/dem_lib.py to your local data directory
cd code
python p2_build_cog.py      # cognitive harmonization
python p3_build_dai.py      # exposure construction
python p4_surv_cox.py       # primary Cox models (M1-M4)
python p5_tables.py         # cohort-level tables
python p6_lag_hetero.py     # lag / heterogeneity
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

Manuscript assembly (numbers are read from `results/_ms_numbers.csv`, never hard-coded):

```bash
python revise_apply.py      # text revision (rules in revise_ms.py)
cd dem_pipeline
python p22_tables.py        # build table objects
python p23_insert_tables.py # insert tables into the .docx
python p21_replace_figs.py  # replace Fig. 1-4 (must run after p23)
```

Journal-formatted variants and submission artefacts:

| Script | Purpose |
|---|---|
| `j1_make_jcm.py` | BMC-style manuscript -> JCM (MDPI) style |
| `j3_supp.py` | supplementary material terminology/numbering |
| `j5_coverletter.py` | cover letter (Markdown + PDF) |
| `j6_graphical_abstract.py` | graphical abstract |
| `p20_figures.py` | redraw Fig. 1-4 (`DEM_FIGDPI`, `DEM_FIGDIR` env vars) |

## Verification

Every reported number traces to `results/_ms_numbers.csv`. Audit scripts (set `DEM_DOCX` to point
at the manuscript being checked):

| Script | Check |
|---|---|
| `p18_verify_ms_numbers.py` | body-text numbers reproduce from the number table |
| `p24_verify_docx.py` | document structure |
| `p26_audit_docx_numbers.py` | table cells and table notes, token by token |
| `p28_derived_check.py` | derived statements ("X %", "X-fold", ranges) |
| `p32_codepoint_scan.py` | non-standard Unicode code points |
| `p36_forbidden_typos.py` | forbidden strings / leftover placeholders |
| `p38_external_claim_scan.py` | source-file counts for referee claims |

> Note: some scripts in this repository still contain absolute paths from the authors' working
> environment. Only `ROOT` (raw data) and `OUT` need to be set for the analysis chain to run;
> the manuscript-assembly scripts additionally embed the manuscript file name, which can be
> overridden with the `DEM_DOCX` environment variable.

## Environment

Python 3.13; see `requirements.txt` for the exact package versions used for the published results.

## License

Code released under the MIT License (see `LICENSE`). Aggregated results in `results/` are released
under CC BY 4.0.

## Citation

If you use this code, please cite the manuscript and the archived release (see `CITATION.cff`).
