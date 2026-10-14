# -*- coding: utf-8 -*-
"""p13_timevar.py —— 时变暴露（counting-process）、暴露轨迹、水平 vs 变化
① 区间设计：每人每个相邻评估波区间一行，暴露取自区间起点波，结局在区间终点波评估
   a) 时变（间隔 1 波） b) 滞后（间隔 2 波） c) 直至区间起点的累积平均
② 暴露轨迹：基线→第二波的二分类负担变化（持续低 0→0 / 缓解 1→0 / 新发 0→1 / 持续 1→1）
③ 水平 vs 变化：基线水平、随访水平、变化量（单入）与两个水平（同入）
输出：out/_tv.csv、_tv_pool.csv、_traj.csv、_traj_pool.csv、_traj_rate.csv、_level.csv
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS


def dcols(df, drop=()):
    return L.design_frame(df, drop=drop)


def fitX(df, expo, entry=None):
    X = dcols(df)
    need = [expo] + list(X.columns) + ['exit', 'E'] + ([entry] if entry else [])
    d = df.copy()
    d['exit'] = d['exit'].astype(float)
    d = pd.concat([d[['exit', 'E', expo] + ([entry] if entry else [])], X], axis=1).dropna()
    if len(d) < 200 or d['E'].sum() < 20:
        return None
    cols = [expo] + list(X.columns)
    if entry is not None:
        cols = cols + [entry]

    def one(c, pen):
        r = L.cox(d, 'exit', 'E', c, penalizer=pen, return_frame=True)
        if r is None or expo not in r[5].index:
            return None
        s = r[5]
        return float(s.loc[expo, 'coef']), float(s.loc[expo, 'se(coef)'])
    v1, v2 = one(cols, 1e-4), one(cols, 1e-2)
    if v1 and v2 and abs(v1[0] - v2[0]) <= 0.10 and abs(v1[0]) < 3 and v1[1] < 2:
        v = v1
    else:
        c2 = [x for x in cols if x != 'age2']
        v = one(c2, 1e-4)
        if v is None:
            return None
    return dict(coef=v[0], se=v[1], hr=np.exp(v[0]), n=len(d), ev=int(d['E'].sum()))


# ---------------------------------------------------------------- 组装逐波长表
panel = {}
for co in CO:
    dai = pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % co))
    cog = pd.read_parquet(os.path.join(OUT, '_cog2_%s.parquet' % co))
    for x in (dai, cog):
        x['pid'] = x['pid'].astype(str)
    p = dai.merge(cog[['pid', 'wave', 'dem_alg_edu']], on=['pid', 'wave'], how='inner')
    p['year'] = p['wave'].map(L.WAVE_YEAR[co])
    p = p[p['dai3'].notna() & p['dem_alg_edu'].notna()]
    p = p.sort_values(['pid', 'year'])
    panel[co] = p

rows = []
for co in CO:
    p = panel[co]
    base = L.BASE_WAVE[co]
    idg = p.groupby('pid')
    # 入选：基线未痴呆、有 ≥2 个评估波
    ok = idg['dem_alg_edu'].transform(lambda s: (s == 1).cumsum().shift(1).fillna(0) == 0)
    p = p[ok.fillna(False) | p['dem_alg_edu'].notna()]
    p = p.sort_values(['pid', 'year'])
    g = p.groupby('pid')
    p['prev_dem'] = g['dem_alg_edu'].shift(1)
    p['prev2_dem'] = g['dem_alg_edu'].shift(2)
    p['dai3_prev'] = g['dai3'].shift(1)
    p['dai3_prev2'] = g['dai3'].shift(2)
    p['year_prev'] = g['year'].shift(1)
    p['year_prev2'] = g['year'].shift(2)
    p['dai3_cum'] = g['dai3'].transform(lambda s: s.expanding().mean())
    p['dai3_cum_prev'] = g['dai3_cum'].shift(1)
    p['first_wave'] = g['wave'].transform('min')
    # 结局：本波首次达到（前一波未达）
    p['E'] = ((p['dem_alg_edu'] == 1) & (p['prev_dem'] != 1)).astype(int)
    # 排除基线波本身
    p = p[p['wave'] != base]
    p = p[p['prev_dem'].notna()]
    # a) 时变：暴露 = 前一波 dai3；区间 [year_prev, year]
    a = p[p['dai3_prev'].notna()].copy()
    a['exit'] = a['year'] - L.WAVE_YEAR[co][base]
    a['en'] = a['year_prev'] - L.WAVE_YEAR[co][base]
    ra = fitX(a, 'dai3_prev', entry='en')
    if ra:
        ra.update(cohort=co, variant='time-varying (1 wave)')
    # b) 滞后：暴露 = 前两波 dai3；要求 year>year_prev2
    b = p[p['dai3_prev2'].notna()].copy()
    b['exit'] = b['year'] - L.WAVE_YEAR[co][base]
    b['en'] = b['year_prev'] - L.WAVE_YEAR[co][base]
    rb = fitX(b, 'dai3_prev2', entry='en')
    if rb:
        rb.update(cohort=co, variant='lagged (2 waves)')
    # c) 累积平均（至区间起点）
    c = p[p['dai3_cum_prev'].notna()].copy()
    c['exit'] = c['year'] - L.WAVE_YEAR[co][base]
    c['en'] = c['year_prev'] - L.WAVE_YEAR[co][base]
    rc = fitX(c, 'dai3_cum_prev', entry='en')
    if rc:
        rc.update(cohort=co, variant='cumulative mean')
    for r in (ra, rb, rc):
        if r:
            rows.append(r)
TV = pd.DataFrame(rows)
TV.to_csv(os.path.join(OUT, '_tv.csv'), index=False, encoding='utf-8-sig')
tp = []
for v, s in TV.groupby('variant'):
    q = L.dl_meta(s['coef'], s['se'], v)
    if q:
        tp.append(dict(variant=v, k=q['k'], hr=q['hr'], lo=q['lo'], hi=q['hi'], I2=q['I2'],
                       intervals=int(s['n'].sum())))
TP = pd.DataFrame(tp)
TP.to_csv(os.path.join(OUT, '_tv_pool.csv'), index=False, encoding='utf-8-sig')
print('① 时变暴露（区间设计，合并）:')
print(TP.to_string(index=False))

# ---------------------------------------------------------------- ② 轨迹
rows, dist, rate = [], [], []
for co in CO:
    p = panel[co]
    base = L.BASE_WAVE[co]
    ws = [w for w in L.WAVES[co] if w in p['wave'].unique()]
    if len(ws) < 2:
        continue
    w0, w1 = ws[0], ws[1]
    b = p[p['wave'] == w0][['pid', 'dai3', 'dem_alg_edu', 'year']].rename(
        columns={'dai3': 'd0', 'year': 'y0', 'dem_alg_edu': 'dem0'})
    f = p[p['wave'] == w1][['pid', 'dai3', 'dem_alg_edu', 'year']].rename(
        columns={'dai3': 'd1', 'year': 'y1', 'dem_alg_edu': 'dem1'})
    m = b.merge(f, on='pid')
    m = m[(m['dem0'] != 1) & (m['dem1'] != 1)]
    m['grp'] = np.where(m['d0'] > 0, 'P', 'L') + np.where(m['d1'] > 0, 'P', 'L')
    m['traj'] = m['grp'].map({'LL': 'persistently low', 'PL': 'remitted',
                               'LP': 'incident', 'PP': 'persistently affected'})
    # 结局：w1 之后的首次痴呆
    after = p[p['year'] > w1 and False] if False else p[p['wave'].isin([w for w in L.WAVES[co] if w > w1])]
    ev = after[after['dem_alg_edu'] == 1].groupby('pid')['year'].min()
    last = after.groupby('pid')['year'].max()
    m = m.merge(pd.DataFrame({'yr_event': ev, 'yr_last': last}), left_on='pid', right_index=True, how='left')
    m = m[m['yr_last'].notna()].copy()
    m['E'] = m['yr_event'].notna().astype(int)
    m['exit'] = np.where(m['E'] == 1, m['yr_event'] - m['y1'], m['yr_last'] - m['y1']).astype(float)
    m = m[m['exit'] > 0]
    cvm = p[['pid', 'male', 'edu', 'partnered', 'smoke3', 'drink_now', 'bmi', 'age']].drop_duplicates('pid')
    m = m.merge(cvm, on='pid', how='inner')
    for t in ['persistently low', 'remitted', 'incident', 'persistently affected']:
        s = m[m['traj'] == t]
        if len(s) < 100:
            continue
        dist.append(dict(cohort=co, traj=t, n=len(s), ev=int(s['E'].sum()),
                         density=1000 * s['E'].sum() / max(s['exit'].sum(), 1)))
        if t == 'persistently low':
            continue
        s2 = pd.concat([m[m['traj'] == 'persistently low'], s])
        s2 = s2.copy(); s2['_x'] = (s2['traj'] == t).astype(float)
        r = fitX(s2.rename(columns={'_x': 'expo'}), 'expo')
        if r:
            rows.append(dict(cohort=co, traj=t, **r))
TR = pd.DataFrame(rows)
TR.to_csv(os.path.join(OUT, '_traj.csv'), index=False, encoding='utf-8-sig')
tp2 = []
for t, s in TR.groupby('traj'):
    q = L.dl_meta(s['coef'], s['se'], t)
    if q:
        tp2.append(dict(traj=t, k=q['k'], hr=q['hr'], lo=q['lo'], hi=q['hi'], I2=q['I2']))
TP2 = pd.DataFrame(tp2)
TP2.to_csv(os.path.join(OUT, '_traj_pool.csv'), index=False, encoding='utf-8-sig')
D = pd.DataFrame(dist)
D.to_csv(os.path.join(OUT, '_traj_dist.csv'), index=False, encoding='utf-8-sig')
print('\n② 轨迹发病密度（逐队列）:')
print(D.pivot_table(index='cohort', columns='traj', values='density').round(1).to_string())
print('\n   轨迹 HR（合并）:')
print(TP2.to_string(index=False))

# ---------------------------------------------------------------- ③ 水平 vs 变化
# 简化：用「持续低 + 其余」的全样本，比较基线水平、随访水平、变化量
rows2 = []
for co in CO:
    p = panel[co]
    ws = sorted(p['wave'].unique())
    if len(ws) < 2:
        continue
    w0, w1 = ws[0], ws[1]
    b = p[p['wave'] == w0][['pid', 'dai3']].rename(columns={'dai3': 'd0'})
    f = p[p['wave'] == w1][['pid', 'dai3']].rename(columns={'dai3': 'd1'})
    m = b.merge(f, on='pid')
    after = p[p['wave'].isin([w for w in L.WAVES[co] if w > w1])]
    ev = after[after['dem_alg_edu'] == 1].groupby('pid')['year'].min()
    last = after.groupby('pid')['year'].max()
    y1 = L.WAVE_YEAR[co][w1]
    m = m.merge(pd.DataFrame({'yr_event': ev, 'yr_last': last}), left_on='pid', right_index=True, how='left')
    m = m[m['yr_last'].notna()].copy()
    m['E'] = m['yr_event'].notna().astype(int)
    m['exit'] = np.where(m['E'] == 1, m['yr_event'] - y1, m['yr_last'] - y1).astype(float)
    m = m[m['exit'] > 0]
    m['dchg'] = m['d1'] - m['d0']
    cvm = p[['pid', 'male', 'edu', 'partnered', 'smoke3', 'drink_now', 'bmi', 'age']].drop_duplicates('pid')
    m = m.merge(cvm, on='pid', how='inner')
    for lab, cols in [('baseline level', ['d0']), ('follow-up level', ['d1']),
                      ('change', ['dchg']), ('baseline+follow-up', ['d0', 'd1'])]:
        X = dcols(m)
        d = pd.concat([m[['exit', 'E'] + cols], X], axis=1).dropna()
        if len(d) < 200 or d['E'].sum() < 20:
            continue
        cc = cols + list(X.columns)
        r = L.cox(d, 'exit', 'E', cc, penalizer=1e-4, return_frame=True)
        if r is None:
            continue
        s = r[5]
        for c in cols:
            if c in s.index:
                rows2.append(dict(cohort=co, model=lab, term=c,
                                  hr=float(s.loc[c, 'exp(coef)']), se=float(s.loc[c, 'se(coef)']),
                                  p=float(s.loc[c, 'p']), n=len(d), ev=int(d['E'].sum())))
LV = pd.DataFrame(rows2)
LV.to_csv(os.path.join(OUT, '_level.csv'), index=False, encoding='utf-8-sig')
print('\n③ 水平 vs 变化（合并）:')
for (mdl, tm), s in LV.groupby(['model', 'term']):
    q = L.dl_meta(np.log(s['hr']), s['se'], mdl + ':' + tm)
    if q:
        print('   %-22s %-9s k=%d %.3f (%.3f-%.3f) I2=%.1f%%'
              % (mdl, tm, q['k'], q['hr'], q['lo'], q['hi'], q['I2']))
print('\nDONE')
