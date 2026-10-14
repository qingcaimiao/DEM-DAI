# -*- coding: utf-8 -*-
"""j8_build_repo.py —— 构建可推送 GitHub 的代码仓库脚手架

输出：D:/桌面/AIzuopin/痴呆/代码仓库_DEM-DAI/
  code/     分析脚本（不含任何参与者级数据）
  results/  聚合结果（CSV / TXT / JSON / LOG / 图）
  README.md LICENSE CITATION.cff requirements.txt .gitignore
原则：**只含代码与聚合结果**；*.parquet（参与者级派生数据）与 docx 一律不入库。
"""
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

WORK = os.path.dirname(os.path.abspath(__file__))
D = r'D:/桌面/AIzuopin/痴呆'
REPO = os.path.join(D, '代码仓库_DEM-DAI')
CODE_SRC = os.path.join(WORK, 'dem_pipeline')
OUT_SRC = os.path.join(CODE_SRC, 'out')

CODE = os.path.join(REPO, 'code')
RES = os.path.join(REPO, 'results')
FIG = os.path.join(RES, 'fig')
for p in (REPO, CODE, RES, FIG):
    os.makedirs(p, exist_ok=True)

# ---- code/ ：所有分析脚本
n_code = 0
for f in sorted(os.listdir(CODE_SRC)):
    if f.endswith('.py'):
        shutil.copy(os.path.join(CODE_SRC, f), os.path.join(CODE, f))
        n_code += 1
for f in ('revise_ms.py', 'revise_apply.py'):
    shutil.copy(os.path.join(WORK, f), os.path.join(CODE, f))
    n_code += 1
for f in sorted(os.listdir(WORK)):
    if f.startswith('j') and f.endswith('.py') and f[1].isdigit():
        shutil.copy(os.path.join(WORK, f), os.path.join(CODE, f))
        n_code += 1

# ---- results/ ：聚合结果（排除 parquet 参与者级数据）
n_res = 0
for f in sorted(os.listdir(OUT_SRC)):
    p = os.path.join(OUT_SRC, f)
    if os.path.isfile(p) and f.split('.')[-1] in ('csv', 'txt', 'json', 'log', 'md'):
        shutil.copy(p, os.path.join(RES, f))
        n_res += 1
for f in sorted(os.listdir(os.path.join(OUT_SRC, 'fig'))):
    if f.endswith('.png'):
        shutil.copy(os.path.join(OUT_SRC, 'fig', f), os.path.join(FIG, f))

n_parq = len([f for f in os.listdir(OUT_SRC) if f.endswith('.parquet')])
print('code/ = %d 个脚本 ; results/ = %d 个文件 + %d 张图 ; 已排除 %d 个 parquet'
      % (n_code, n_res, len(os.listdir(FIG)), n_parq))
assert not any(f.endswith('.parquet') for f in os.listdir(RES)), '误将参与者级数据入库'

README = '''# DEM-DAI — Cumulative burden of three geriatric syndromes and incident dementia

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
'''

LICENSE = '''MIT License

Copyright (c) 2026 Qingcai Miao, Jianhong Cen, Lu Chen, Runzhi Lu, Renjie Zhang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

CITATION = '''cff-version: 1.2.0
message: "If you use this code, please cite both the manuscript and this archived release."
title: "DEM-DAI: analysis code for cumulative burden of three geriatric syndromes and incident dementia"
abstract: >-
  Analysis code for a six-cohort harmonized study of a minimal three-component geriatric syndrome
  accumulation index (disability, multimorbidity, depression) and incident dementia, including
  time-lagged, time-varying, trajectory, competing-risk, mediation and E-value analyses.
authors:
  - family-names: Miao
    given-names: Qingcai
    orcid: "https://orcid.org/0009-0006-1479-6726"
  - family-names: Cen
    given-names: Jianhong
  - family-names: Chen
    given-names: Lu
  - family-names: Lu
    given-names: Runzhi
  - family-names: Zhang
    given-names: Renjie
    orcid: "https://orcid.org/0009-0009-4026-2068"
license: MIT
version: 1.0.0
date-released: "2026-10-14"
'''

REQ = '''pandas==2.3.3
numpy==2.5.3
scipy==1.18.1
lifelines==0.30.3
statsmodels==0.15.0
matplotlib==3.11.2
pyarrow==26.0.0
Pillow==12.3.0
fpdf2==2.8.9
python-docx==1.2.0
'''

GITIGNORE = '''# participant-level derived data (not redistributable)
*.parquet
# local outputs / OS
__pycache__/
*.pyc
.ipynb_checkpoints/
.DS_Store
Thumbs.db
*.tmp
'''

for name, txt in [('README.md', README), ('LICENSE', LICENSE), ('CITATION.cff', CITATION),
                  ('requirements.txt', REQ), ('.gitignore', GITIGNORE)]:
    open(os.path.join(REPO, name), 'w', encoding='utf-8', newline='\n').write(txt)
print('写出 REPO:', REPO)
