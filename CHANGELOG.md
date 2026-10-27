# Changelog

## v1.1.0 — 2026-10-27

Housekeeping release: brings the archive in line with the manuscript as submitted, without
changing any analysis, estimate or conclusion.

### Figures
- `results/fig/Fig1–4.png` regenerated with the final layout. They are now **byte-identical**
  (md5) to the images embedded in the submitted manuscript.
- In `Fig. 1`, the step label reads `Cognitive assessment available` (previously
  `Baseline cognitive assessment available`); panel font sizes were increased for legibility.

### Code
- All analysis scripts synchronised with the versions that produced the reported results.
- `p23_insert_tables.py`, `p21_replace_figs.py`, `revise_ms.py`, `revise_apply.py`: the hard-coded
  absolute paths of the authors' working environment were replaced by
  `DEM_OUT` / `DEM_SRC_DOCX` / `DEM_DST_DOCX` / `DEM_FIGDIR` with relative defaults.
- `revise_apply.py` now unpacks the source `.docx` on first run instead of requiring a
  pre-extracted directory.
- `dem_lib.py`: `ROOT` can be set through `DEM_ROOT`.
- Added: `j39_layout_audit.py`, `j40_colfit.py`, `j41_pdf_layout_check.py`, `j42_package_verify.py`,
  `j44_make_bmc.py`, `j47_refs_verify.py`, `j47b_refs_titlecheck.py`, `j50_make_medicine.py`.

### Metadata
- Construct name corrected throughout: *disability, multimorbidity and depression accumulation
  index* (previously *geriatric syndrome accumulation index*, which did not match the acronym DAI).

### Housekeeping
- Removed development snapshots `_alt_outcomes_BEFORE.csv`, `_alt_pool_BEFORE.csv`,
  `_m1234_BEFORE.csv`, `_ms_numbers_PREV.csv`, `_ms_numbers_PRE_T4D.csv`, `p7_smoke.log`.
- Added `results/README.md` (map of the output files) and this changelog.
- `.gitattributes` retained (line endings forced to LF; PNG/ZIP/DOCX declared binary).
- `.gitattributes` retained (line endings forced to LF; PNG/ZIP/DOCX declared binary).

### Not included, deliberately
- Scripts that contain third-party e-mail addresses (suggested-reviewer handling) are **not**
  published.
- No participant-level data, no `.docx` and no `.parquet` files are distributed.

## v1.0.0 — 2026-10-14

First archive released with the initial submission.
