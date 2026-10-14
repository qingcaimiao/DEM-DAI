# -*- coding: utf-8 -*-
"""p07b_repool.py —— 只重算中介合并表（从已落盘的逐队列估计 _med_cs.csv / _gf.csv，
不重跑 bootstrap）。修正「合并比值口径」公式：1 − βdirect/βtotal。"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
M = pd.read_csv(os.path.join(OUT, '_med_cs.csv'))
M['variant'] = M.get('variant', pd.Series(index=M.index, dtype=object)).fillna('cross-sectional')
GF = pd.read_csv(os.path.join(OUT, '_gf.csv')) if os.path.exists(os.path.join(OUT, '_gf.csv')) else None

pool = []
for tag in ['cross-sectional', 'temporal']:
    sub = M[(M['flag'] == 'ok') & (M['variant'] == tag)]
    if len(sub) < 2:
        continue
    pt = L.dl_meta(np.log(sub['tot_hr']), sub['tot_se'])
    pd_ = L.dl_meta(np.log(sub['dir_hr']), sub['dir_se'])
    pi = L.dl_meta(np.log(sub['ind_hr']), sub['ind_se'])
    pp = L.dl_meta_raw(sub['prop'], sub['prop_se'])
    for nm, x in [('total HR', pt), ('direct HR', pd_), ('indirect HR', pi)]:
        pool.append(dict(framework=tag, estimand=nm, k=x['k'], value=x['hr'], lo=x['lo'],
                         hi=x['hi'], I2=x['I2']))
    if pp:
        pool.append(dict(framework=tag, estimand='mediated %', k=pp['k'], value=100 * pp['est'],
                         lo=100 * pp['lo'], hi=100 * pp['hi'], I2=pp['I2']))
    # 合并比值口径：1 − pooled βdirect / pooled βtotal
    pool.append(dict(framework=tag, estimand='ratio of pooled (indirect/total)', k=pt['k'],
                     value=100 * (1 - pd_['loghr'] / pt['loghr']), lo=np.nan, hi=np.nan, I2=np.nan))
if GF is not None and len(GF) >= 2:
    se = GF['PM'].std(ddof=1) / np.sqrt(len(GF)) if len(GF) > 1 else np.nan
    pool.append(dict(framework='counterfactual', estimand='mediated %', k=len(GF),
                     value=100 * GF['PM'].mean(), lo=100 * (GF['PM'].mean() - 1.96 * se),
                     hi=100 * (GF['PM'].mean() + 1.96 * se), I2=np.nan))
P = pd.DataFrame(pool)
P.to_csv(os.path.join(OUT, '_med_pool.csv'), index=False, encoding='utf-8-sig')
print(P.round(3).to_string(index=False))
