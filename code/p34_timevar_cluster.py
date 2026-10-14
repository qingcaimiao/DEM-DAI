# -*- coding: utf-8 -*-
"""p34_timevar_cluster.py —— 时变（counting-process）模型的聚类稳健标准误

审稿意见：区间数据中同一受试者贡献多个区间，区间之间不独立，
必须用聚类稳健方差，否则 CI 偏窄、P 值不可信。

用与 p13 完全相同的区间组装逻辑；对三个变体分别给出
① 常规标准误 ② 按 pid 聚类的稳健标准误。稳健方差由 statsmodels 的
PHReg.fit(groups=) 计算（lifelines 的 cluster_col 在数十万行上过慢）。

输出：out/_tv_cluster.csv、out/_tv_cluster_cmp.csv
"""
import os
import time
import numpy as np
import pandas as pd
import dem_lib as L

OUT, CO = L.OUT, L.COHORTS


def fit_sm(dd, dur, ev, expo, cols, entry=None, groups=None, pen=1e-4):
    """statsmodels PHReg；groups 给定时返回聚类稳健标准误。

    ties='efron' 必须显式指定：statsmodels 默认 Breslow，而本流程其余部分
    （lifelines）用 Efron。区间数据在每一波存在大量并列事件时间，两种近似
    给出的系数差异可达 0.05–0.10，足以让新旧结果对不上。
    """
    from statsmodels.duration.hazard_regression import PHReg
    y = dd[dur].to_numpy(float)
    X = dd[cols].to_numpy(float)
    st = dd[ev].to_numpy(int)
    en = dd[entry].to_numpy(float) if entry else None
    try:
        m = PHReg(y, X, status=st, entry=en, ties='efron')
        if groups is not None:
            r = m.fit(groups=dd[groups].to_numpy())
        else:
            r = m.fit(disp=0)
    except Exception:
        return None
    i = cols.index(expo)
    coef = float(r.params[i])
    se = float(r.bse[i])
    if not np.isfinite(coef) or not np.isfinite(se) or se <= 0 or abs(coef) > 3 or se > 2:
        return None
    return dict(coef=coef, se=se, hr=float(np.exp(coef)), n=len(dd), ev=int(dd[ev].sum()))


def pooled(rows, label=''):
    if not rows:
        return None
    s = pd.DataFrame(rows)
    q = L.dl_meta(s['coef'], s['se'], label)
    if q:
        q['n'] = int(s['n'].sum())
        q['ev'] = int(s['ev'].sum())
    return q


def show(m, q):
    if not q:
        print('  %-16s 不可合并' % m)
        return
    print('  %-16s k=%d  HR=%.3f (%.3f-%.3f)  I2=%5.1f%%  区间=%d 事件=%d'
          % (m, q['k'], q['hr'], q['lo'], q['hi'], q['I2'], q['n'], q['ev']))


# ---------------------------------------------------------------- 区间组装（同 p13）
print('组装区间数据 ...', flush=True)
panel = {}
for co in CO:
    dai = pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % co))
    cog = pd.read_parquet(os.path.join(OUT, '_cog2_%s.parquet' % co))
    for x in (dai, cog):
        x['pid'] = x['pid'].astype(str)
    p = dai.merge(cog[['pid', 'wave', 'dem_alg_edu']], on=['pid', 'wave'], how='inner')
    p['year'] = p['wave'].map(L.WAVE_YEAR[co])
    p = p[p['dai3'].notna() & p['dem_alg_edu'].notna()].sort_values(['pid', 'year'])
    panel[co] = p
print('  完成', flush=True)

rows, cmp = [], []
for co in CO:
    t0 = time.time()
    p = panel[co].copy()
    base = L.BASE_WAVE[co]
    ybase = L.WAVE_YEAR[co][base]
    g = p.groupby('pid')
    p['prev_dem'] = g['dem_alg_edu'].shift(1)
    p['dai3_prev'] = g['dai3'].shift(1)
    p['dai3_prev2'] = g['dai3'].shift(2)
    p['year_prev'] = g['year'].shift(1)
    p['dai3_cum'] = p.groupby('pid')['dai3'].transform(lambda s: s.expanding().mean())
    p['dai3_cum_prev'] = p.groupby('pid')['dai3_cum'].shift(1)
    p['E'] = ((p['dem_alg_edu'] == 1) & (p['prev_dem'] != 1)).astype(int)
    p = p[(p['wave'] != base) & p['prev_dem'].notna()]
    for tag, expo in [('time-varying (1 wave)', 'dai3_prev'),
                      ('lagged (2 waves)', 'dai3_prev2'),
                      ('cumulative mean', 'dai3_cum_prev')]:
        sub = p[p[expo].notna()].copy()
        sub['exit'] = sub['year'] - ybase
        sub['en'] = sub['year_prev'] - ybase
        sub = sub[sub['exit'] > sub['en']]
        if len(sub) < 200 or sub['E'].sum() < 20:
            continue
        X = L.design_frame(sub, extra=[expo])
        dd = pd.concat([sub[['exit', 'E', 'pid', 'en']], X], axis=1).dropna()
        cols = list(X.columns)
        r0 = fit_sm(dd, 'exit', 'E', expo, cols, entry='en')
        r1 = fit_sm(dd, 'exit', 'E', expo, cols, entry='en', groups='pid')
        if r0:
            rows.append(dict(cohort=co, variant=tag, se_type='plain', **r0))
        if r1:
            rows.append(dict(cohort=co, variant=tag, se_type='cluster', **r1))
        if r0 and r1:
            cmp.append(dict(cohort=co, variant=tag, hr=r1['hr'],
                            se_plain=r0['se'], se_cluster=r1['se'],
                            ratio=r1['se'] / r0['se'],
                            n_clusters=int(dd['pid'].nunique()), n_rows=len(dd),
                            ev=int(dd['E'].sum())))
    print('  %s done (%.1fs)' % (co, time.time() - t0), flush=True)

R = pd.DataFrame(rows)
R.to_csv(os.path.join(OUT, '_tv_cluster.csv'), index=False, encoding='utf-8-sig')
C = pd.DataFrame(cmp)
C.to_csv(os.path.join(OUT, '_tv_cluster_cmp.csv'), index=False, encoding='utf-8-sig')

print()
print('=== 时变模型：常规 vs 聚类稳健 ===')
for v in ['time-varying (1 wave)', 'lagged (2 waves)', 'cumulative mean']:
    print('--', v)
    for st in ['plain', 'cluster']:
        s = R[(R['variant'] == v) & (R['se_type'] == st)]
        show(st, pooled(s.to_dict('records'), v + '/' + st))
    c = C[C['variant'] == v]
    if len(c):
        print('     逐队列 SE 比: %s'
              % '; '.join('%s %.2f' % (r['cohort'], r['ratio']) for _, r in c.iterrows()))
        print('     中位 SE 比 %.3f；个体 %d，区间 %d，事件 %d'
              % (float(c['ratio'].median()), int(c['n_clusters'].sum()),
                 int(c['n_rows'].sum()), int(c['ev'].sum())))
print()
print('DONE p34')
