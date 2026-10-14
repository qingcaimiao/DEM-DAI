# -*- coding: utf-8 -*-
"""p15_missing.py —— 缺失数据矩阵（Table S4a/S4b 的数据源）
S4a：逐变量逐队列缺失率（基线波、分析样本）
S4b：有/无协变量缺失者的基线特征对比（年龄、失能率、痴呆事件率）
输出：out/_miss_a.csv、out/_miss_b.csv
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
VARS = ['dai3', 'disab', 'multi', 'dep', 'age', 'male', 'edu', 'partnered',
        'smoke3', 'drink_now', 'bmi', 'urban', 'grip', 'act']

rows = []
for co in CO:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    rec = dict(cohort=co, n=len(d))
    for v in VARS:
        rec[v] = round(100 * d[v].isna().mean(), 2) if v in d.columns else np.nan
    rows.append(rec)
A = pd.DataFrame(rows)
A.to_csv(os.path.join(OUT, '_miss_a.csv'), index=False, encoding='utf-8-sig')
print('Table S4a 基线缺失率（%）:')
print(A.to_string(index=False))

# S4b：协变量完整 vs 缺失
COV = ['age', 'male', 'edu', 'partnered', 'smoke3', 'drink_now', 'bmi']
comp = []
for co in CO:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    miss = d[COV].isna().any(axis=1)
    comp.append(dict(cohort=co,
                     n_missing=int(miss.sum()), n_complete=int((~miss).sum()),
                     age_missing=round(d.loc[miss, 'age'].mean(), 2),
                     age_complete=round(d.loc[~miss, 'age'].mean(), 2),
                     disab_missing=round(100 * d.loc[miss, 'disab'].mean(), 1),
                     disab_complete=round(100 * d.loc[~miss, 'disab'].mean(), 1),
                     ev_missing=round(100 * d.loc[miss, 'E'].mean(), 1),
                     ev_complete=round(100 * d.loc[~miss, 'E'].mean(), 1)))
B = pd.DataFrame(comp)
B.to_csv(os.path.join(OUT, '_miss_b.csv'), index=False, encoding='utf-8-sig')
print('\nTable S4b 缺失者 vs 完整者:')
print(B.to_string(index=False))
tot = pd.DataFrame([dict(
    n_missing=int(B['n_missing'].sum()), n_complete=int(B['n_complete'].sum()),
    age_missing=round(np.average(B['age_missing'], weights=B['n_missing']), 2),
    age_complete=round(np.average(B['age_complete'], weights=B['n_complete']), 2),
    disab_missing=round(np.average(B['disab_missing'], weights=B['n_missing']), 1),
    disab_complete=round(np.average(B['disab_complete'], weights=B['n_complete']), 1),
    ev_missing=round(np.average(B['ev_missing'], weights=B['n_missing']), 1),
    ev_complete=round(np.average(B['ev_complete'], weights=B['n_complete']), 1))])
print('\n合计（加权）:')
print(tot.to_string(index=False))
tot.to_csv(os.path.join(OUT, '_miss_b_tot.csv'), index=False, encoding='utf-8-sig')
print('\nDONE')
