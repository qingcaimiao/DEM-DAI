# `results/` — map of the aggregated outputs

All files here are **aggregated estimates only**; no participant-level records are included.

## Entry point for every number in the manuscript

`_ms_numbers.csv` — 3 columns, no header: `key,value,source_file`.
860 rows. Every number quoted in the manuscript and in the tables is read from this file by
`p17_ms_numbers.py` (writer) and `p18_verify_ms_numbers.py` (verifier). The `source_file` column
tells you which upstream file a value came from, so any figure can be traced in one step:

```
grep '^pool_M2_hr,' results/_ms_numbers.csv      # -> value, _pool.csv
```

## Main tables and model outputs

| File | Content |
|---|---|
| `Table1.csv`, `Table1_pooled.csv` | baseline characteristics by cohort and pooled |
| `Table2B.csv`, `_pool_2b.csv` | categorical gradient (1 / 2 / 3 syndromes vs 0) |
| `Table3A–3C.csv`, `_pool_3a/3b/3c.csv` | component-specific, mutually adjusted, and sensitivity models |
| `_m1234.csv` | models M1–M4, cohort by cohort |
| `_pool.csv` | DerSimonian–Laird pooled estimates (primary) |
| `_lag_win*.csv`, `_lag_cum*.csv`, `_lagspec*.csv` | time-lag ladder |
| `_tv*.csv` | interval-based time-varying models (incl. cluster-robust comparison) |
| `_traj*.csv` | trajectory / rate-of-change models |
| `_fg*.csv`, `_cif_*.csv` | Fine–Gray competing risks and cumulative incidence |
| `_med_*.csv` | mediation under three frameworks and four-way decomposition |
| `_alt_outcomes*.csv`, `_equiv.csv` | alternative outcome definitions, robustness window |
| `_sub.csv`, `_int.csv`, `_int_fdr.csv` | subgroups, interaction, BH-adjusted p |
| `_evalue.csv`, `_kappa.csv`, `_flow.csv`, `_miss_*.csv` | E-value, agreement, flow, missingness |
| `fig/Fig1–4.png` | figures exactly as embedded in the submitted manuscript (400 dpi) |

## Audit logs

`_verify_numbers.txt`, `_verify_docx.txt`, `_audit_tables_notes.txt`, `_tables_check.txt`,
`_derived_check.txt`, `_codepoint_scan.txt`, `_forbidden_scan.txt` — machine output of the checks
run against the manuscript before submission. All report zero unresolved items.
