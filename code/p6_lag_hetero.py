# -*- coding: utf-8 -*-
"""p6_lag_hetero.py —— 时距分析 / 异质性 / 留一法 / E-value（Table 4C 的数据源）
① 累积法：排除随访前 L 年（L=0,2,4,6,8,10,12），逐队列重估 M2 → DL 合并 → 趋势检验
② 期段法：以各库实际评估年切期段，逐期段估 HR，按名义中点并入 2 年箱后合并
③ 留一法、区域亚组、队列层面元回归、E-value
输出：out/_lag_cum.csv、_lag_win.csv、_loo.csv、_region.csv、_metareg.csv、_evalue.csv
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
NAME = {'CHARLS': 'CHARLS', 'ELSA': 'ELSA', 'HRS': 'HRS', 'KLoSA': 'KLoSA',
        'MHAS': 'MHAS', 'SHARE': 'SHARE'}
REGION = {'CHARLS': 'East Asia', 'KLoSA': 'East Asia', 'ELSA': 'Europe', 'SHARE': 'Europe',
          'HRS': 'North America', 'MHAS': 'North America'}

surv = {co: pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co)) for co in CO}


def dcols(df, drop=()):
    return L.design_frame(df, drop=drop)


def fitM2(df, expo, dur='T', ev='E', drop=(), robust=True):
    """M2 模型；robust=True 时用四级稳健拟合（防 MHAS 类数值垃圾）。"""
    X = dcols(df, drop)
    d = pd.concat([df[[dur, ev, expo]], X], axis=1).dropna()
    if len(d) < 100 or d[ev].sum() < 20:
        return None
    cols = [expo] + list(X.columns)

    def one(pen, dd=d, cc=cols):
        r = L.cox(dd, dur, ev, cc, penalizer=pen, return_frame=True)
        return None if r is None else (float(r[5].loc[expo, 'coef']), float(r[5].loc[expo, 'se(coef)']),
                                       float(r[5].loc[expo, 'p']), len(dd), int(dd[ev].sum()))
    if not robust:
        v = one(1e-4)
        return None if v is None else dict(coef=v[0], se=v[1], p=v[2], n=v[3], ev=v[4])
    v1, v2 = one(1e-4), one(1e-2)
    if v1 and v2 and abs(v1[0] - v2[0]) <= 0.10 and abs(v1[0]) < 3 and v1[1] < 2:
        return dict(coef=v1[0], se=v1[1], p=v1[2], n=v1[3], ev=v1[4])
    # 去 age2 兜底
    X2 = X.drop(columns=[c for c in ['age2'] if c in X.columns])
    d2 = pd.concat([df[[dur, ev, expo]], X2], axis=1).dropna()
    v = one(1e-4, d2, [expo] + list(X2.columns))
    if v is None:
        return None
    return dict(coef=v[0], se=v[1], p=v[2], n=v[3], ev=v[4])


# ---------------------------------------------------------------- ① 累积法
rows = []
for co in CO:
    d = surv[co]
    for Lag in [0, 2, 4, 6, 8, 10, 12]:
        dd = d[d['T'] > Lag].copy()
        if Lag > 0:
            dd['T2'] = dd['T'] - Lag
        else:
            dd['T2'] = dd['T']
        r = fitM2(dd, 'dai3', dur='T2')
        if r and r['n'] >= 300 and r['ev'] >= 30:
            rows.append(dict(cohort=NAME[co], Lag=Lag, hr=np.exp(r['coef']), se=r['se'],
                             coef=r['coef'], n=r['n'], ev=r['ev']))
CUM = pd.DataFrame(rows)
CUM.to_csv(os.path.join(OUT, '_lag_cum.csv'), index=False, encoding='utf-8-sig')
poolC = []
for Lag, s in CUM.groupby('Lag'):
    p = L.dl_meta(s['coef'], s['se'], Lag)
    if p:
        poolC.append(dict(Lag=Lag, k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'], I2=p['I2'], Qp=p['Qp'],
                          coef=p['loghr'], se=p['se'], events=int(s['ev'].sum())))
PC = pd.DataFrame(poolC)
PC.to_csv(os.path.join(OUT, '_lag_cum_pool.csv'), index=False, encoding='utf-8-sig')

# 趋势检验（WLS: logHR ~ Lag）
def trend(df, xcol, ycol='coef', wcol='se'):
    d = df[[xcol, ycol, wcol]].dropna()
    w = 1.0 / d[wcol] ** 2
    A = np.vstack([np.ones(len(d)), d[xcol].values]).T
    W = np.diag(w.values)
    beta = np.linalg.solve(A.T @ W @ A, A.T @ W @ d[ycol].values)
    resid = d[ycol].values - A @ beta
    s2 = (w.values * resid ** 2).sum() / max(len(d) - 2, 1)
    cov = s2 * np.linalg.inv(A.T @ W @ A)
    se = np.sqrt(np.diag(cov))
    from scipy import stats as st
    tt = beta[1] / se[1]
    pp = 2 * (1 - st.t.cdf(abs(tt), len(d) - 2))
    return dict(slope=beta[1], se=se[1], p=pp)

TR_CUM = trend(PC, 'Lag')
print('① 累积法合并:\n', PC.to_string(index=False))
print('  趋势检验:', TR_CUM)

# ---------------------------------------------------------------- ② 期段法
win = []
for co in CO:
    d = surv[co]
    yb = L.WAVE_YEAR[co][L.BASE_WAVE[co]]
    ys = [L.WAVE_YEAR[co][w] - yb for w in L.WAVES[co] if w in L.WAVE_YEAR[co]]
    ys = sorted(set(ys))
    segs = [(a, b) for a, b in zip(ys, ys[1:])]
    for a, b in segs:
        dd = d[d['T'] > a].copy()
        if len(dd) < 200:
            continue
        dd['dur'] = np.minimum(dd['T'], b) - a
        dd['evt'] = ((dd['E'] == 1) & (dd['T'] <= b)).astype(int)
        dd = dd[dd['dur'] > 0]
        if dd['evt'].sum() < 15:
            continue
        r = fitM2(dd, 'dai3', dur='dur', ev='evt')
        if r:
            win.append(dict(cohort=NAME[co], seg='%d-%d' % (a, b), mid=(a + b) / 2.0,
                            hr=np.exp(r['coef']), se=r['se'], coef=r['coef'], n=r['n'], ev=r['ev']))
W = pd.DataFrame(win)
W.to_csv(os.path.join(OUT, '_lag_win.csv'), index=False, encoding='utf-8-sig')
W['bin'] = (W['mid'] // 2 * 2).astype(int)
poolW = []
for b, s in W.groupby('bin'):
    p = L.dl_meta(s['coef'], s['se'], b)
    if p:
        poolW.append(dict(bin_from=b, bin_to=b + 2, k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'],
                          I2=p['I2'], coef=p['loghr'], se=p['se'],
                          cohorts=','.join(sorted(s['cohort']))))
PW = pd.DataFrame(poolW)
PW.to_csv(os.path.join(OUT, '_lag_win_pool.csv'), index=False, encoding='utf-8-sig')
# 期段趋势：名义中点
_wm = []
for mid, s in W.groupby('mid'):
    p = L.dl_meta(s['coef'], s['se'])
    if p:
        _wm.append(dict(mid=mid, coef=p['loghr'], se=p['se']))
Wm = pd.DataFrame(_wm)
TR_WIN = trend(Wm, 'mid')
print('\n② 期段法合并:\n', PW.to_string(index=False))
print('  趋势检验(名义中点):', TR_WIN)

# ---------------------------------------------------------------- ③ 留一法 / 区域 / 元回归
m2 = pd.read_csv(os.path.join(OUT, '_m1234.csv'))
m2 = m2[m2['model'] == 'M2'].copy()
m2['coef'] = np.log(m2['hr'])
loo = []
for co in CO:
    s = m2[m2['cohort'] != co]
    p = L.dl_meta(s['coef'], s['se'], 'drop ' + co)
    if p:
        loo.append(dict(dropped=co, k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'], I2=p['I2'], p=p['p']))
pd.DataFrame(loo).to_csv(os.path.join(OUT, '_loo.csv'), index=False, encoding='utf-8-sig')
print('\n③ 留一法:\n', pd.DataFrame(loo).to_string(index=False))

reg = []
for g, s in m2.groupby(m2['cohort'].map(REGION)):
    p = L.dl_meta(s['coef'], s['se'], g)
    if p:
        reg.append(dict(region=g, cohorts=','.join(sorted(s['cohort'])), k=p['k'], hr=p['hr'],
                        lo=p['lo'], hi=p['hi'], I2=p['I2']))
pd.DataFrame(reg).to_csv(os.path.join(OUT, '_region.csv'), index=False, encoding='utf-8-sig')
print('\n③ 区域:\n', pd.DataFrame(reg).to_string(index=False))

# 队列层面元回归
feat = pd.read_csv(os.path.join(OUT, '_surv_flow.csv'))
feat['cohort'] = feat['cohort']
mer = m2.merge(feat[['cohort', 'N', 'events', 'person_years', 'median_fu', 'max_fu', 'dai_mean']], on='cohort')
mr = []
for f in ['baseline_year', 'median_fu', 'max_fu', 'dai_mean']:
    if f == 'baseline_year':
        by = {co: L.WAVE_YEAR[co][L.BASE_WAVE[co]] for co in CO}
        mer[f] = mer['cohort'].map(by)
    if mer[f].nunique() < 2:
        continue
    d = mer[[f, 'coef', 'se']].dropna()
    w = 1.0 / d['se'] ** 2
    A = np.vstack([np.ones(len(d)), d[f].values]).T
    Wm_ = np.diag(w.values)
    beta = np.linalg.solve(A.T @ Wm_ @ A, A.T @ Wm_ @ d['coef'].values)
    resid = d['coef'].values - A @ beta
    s2 = (w.values * resid ** 2).sum() / max(len(d) - 2, 1)
    se = np.sqrt(np.diag(s2 * np.linalg.inv(A.T @ Wm_ @ A)))
    from scipy import stats as st
    pp = 2 * (1 - st.t.cdf(abs(beta[1] / se[1]), len(d) - 2))
    mr.append(dict(feature=f, slope=beta[1], se=se[1], p=pp, k=len(d)))
MR = pd.DataFrame(mr)
MR.to_csv(os.path.join(OUT, '_metareg.csv'), index=False, encoding='utf-8-sig')
print('\n③ 元回归:\n', MR.to_string(index=False))

# ---------------------------------------------------------------- ④ E-value
def evalue(rr):
    if not np.isfinite(rr) or rr <= 1:
        return 1.0
    return rr + np.sqrt(rr * (rr - 1))

ev = []
for _, r in pd.read_csv(os.path.join(OUT, '_pool.csv')).iterrows():
    ev.append(dict(estimand=r['label'], hr=r['hr'], lo=r['lo'], hi=r['hi'],
                   E_point=round(evalue(r['hr']), 2),
                   E_CI=round(evalue(r['lo']) if r['lo'] > 1 else 1.0, 2)))
for _, r in PC.iterrows():
    ev.append(dict(estimand='cumulative Lag>=%d' % r['Lag'], hr=r['hr'], lo=r['lo'], hi=r['hi'],
                   E_point=round(evalue(r['hr']), 2), E_CI=round(evalue(r['lo']) if r['lo'] > 1 else 1.0, 2)))
EV = pd.DataFrame(ev)
EV.to_csv(os.path.join(OUT, '_evalue.csv'), index=False, encoding='utf-8-sig')
print('\n④ E-value:\n', EV.to_string(index=False))
print('\nDONE')
