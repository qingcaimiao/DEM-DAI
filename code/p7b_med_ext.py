# -*- coding: utf-8 -*-
"""p7b_med_ext.py —— 中介分析的扩展部分（补齐原稿中的 4 个敏感性设定 + 四向分解）

原稿 Results 报过而从未重建的量：
  (1) 两波洗脱（暴露@w0、中介@w1、结局自 w2 起）
  (2) 仅事件性抑郁（基线无抑郁者进入）
  (3) 含暴露×中介交互项
  (4) 以「多病单独」为暴露
  (5) 反事实四向分解：CDE / INT_ref / INT_med / PIE（加性风险尺度）

全部数字由脚本计算落盘，不允许手工写入。
输出：out/_med_sens.csv、out/_med_sens_pool.csv、out/_gf_cells.csv、out/_med_4way.csv
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
NB = int(os.environ.get('NB', 100))


# ---------------------------------------------------------------- 工具（与 p7 同源）
def dcols(df, drop=()):
    return L.design_frame(df, drop=drop)


def _ok(res, key):
    if not res or key not in res:
        return False
    b, se, _ = res[key]
    return np.isfinite(b) and np.isfinite(se) and abs(b) < 3 and 0 < se < 2


def best_fit(d0, dur, ev, cols, key='dm2'):
    """四级稳健拟合：pen 1e-4 → pen 1e-2 → 去 age2（均需 key 稳定）。"""
    def one(d, c, pen):
        r = L.cox(d, dur, ev, c, penalizer=pen, return_frame=True)
        if r is None:
            return None
        s = r[5]
        if key not in s.index:
            return None
        return {k: (float(s.loc[k, 'coef']), float(s.loc[k, 'se(coef)']), float(s.loc[k, 'p']))
                for k in c if k in s.index}
    for cc, pen in [(cols, 1e-4), (cols, 1e-2), ([c for c in cols if c != 'age2'], 1e-4)]:
        r = one(d0, cc, pen)
        if _ok(r, key):
            return r, cc
    return None, None


def prep(co):
    surv = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    dai = pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % co))
    dai['pid'] = dai['pid'].astype(str)
    surv['pid'] = surv['pid'].astype(str)
    b = L.BASE_WAVE[co]
    da = dai[dai['wave'] == b][['pid', 'disab', 'multi', 'dep']].set_index('pid')
    s = surv.set_index('pid').join(da, how='inner', rsuffix='_b')
    s = s[s['disab'].notna() & s['multi'].notna() & s['dep'].notna()].copy()
    s['dm2'] = (s['disab'] + s['multi']).astype(float)
    s['Xbin'] = (s['dm2'] > 0).astype(float)
    return s.reset_index(), dai, b


def prop_of(d, dur, ev, expo, med, boot):
    """总效应 vs 调中介的直接效应 → 中介比例。返回 dict 或 None。"""
    Xc = dcols(d)
    dd = pd.concat([d[[dur, ev, expo, med]], Xc], axis=1).dropna()
    if len(dd) < 300 or dd[ev].sum() < 40:
        return None
    base = list(Xc.columns)
    _, usecols = best_fit(dd, dur, ev, [expo, med] + base, key=expo)
    if usecols is None:
        return None
    use = [c for c in usecols if c != med]
    tr, _ = best_fit(dd, dur, ev, use, key=expo)
    dr, _ = best_fit(dd, dur, ev, usecols, key=expo)
    if not (tr and dr):
        return None
    bt, bd = tr[expo][0], dr[expo][0]
    if abs(bt) < 0.03:
        return dict(flag='unstable', n=len(dd), ev=int(dd[ev].sum()))
    prop = (bt - bd) / bt

    def one(x):
        t, _ = best_fit(x, dur, ev, use, key=expo)
        c, _ = best_fit(x, dur, ev, usecols, key=expo)
        if not (t and c):
            return np.nan
        a, b2 = t[expo][0], c[expo][0]
        return np.nan if abs(a) < 1e-6 else (a - b2) / a
    rng = np.random.default_rng(11)
    bs = np.array([one(dd.iloc[rng.integers(0, len(dd), len(dd))]) for _ in range(boot)])
    bs = bs[np.isfinite(bs)]
    return dict(flag='ok', n=len(dd), ev=int(dd[ev].sum()),
                tot_hr=float(np.exp(bt)), dir_hr=float(np.exp(bd)),
                prop=float(prop), prop_se=float(bs.std(ddof=1)) if len(bs) > 20 else np.nan,
                boot_ok=int(len(bs)))


def prop_interaction(d, dur, ev, expo, med, boot):
    """含 expo×med 交互项：直接效应取 med=0 处的 expo 系数。"""
    Xc = dcols(d)
    dd = pd.concat([d[[dur, ev, expo, med]], Xc], axis=1).dropna()
    if len(dd) < 300 or dd[ev].sum() < 40:
        return None
    dd = dd.copy()
    dd['_IX'] = dd[expo].astype(float) * dd[med].astype(float)
    dd['_IX'] = dd['_IX'] - dd['_IX'].mean()
    base = list(Xc.columns)
    cols_i = [expo, med, '_IX'] + base
    cols_t = [expo] + base
    ri, ci = best_fit(dd, dur, ev, cols_i, key=expo)
    rt, _ = best_fit(dd, dur, ev, cols_t, key=expo)
    if not (ri and rt):
        return None
    bt, bd = rt[expo][0], ri[expo][0]
    if abs(bt) < 0.03:
        return dict(flag='unstable', n=len(dd), ev=int(dd[ev].sum()))
    prop = (bt - bd) / bt

    def one(x):
        a, _ = best_fit(x, dur, ev, cols_t, key=expo)
        b, _ = best_fit(x, dur, ev, cols_i, key=expo)
        if not (a and b):
            return np.nan
        p, q = a[expo][0], b[expo][0]
        return np.nan if abs(p) < 1e-6 else (p - q) / p
    rng = np.random.default_rng(13)
    bs = np.array([one(dd.iloc[rng.integers(0, len(dd), len(dd))]) for _ in range(boot)])
    bs = bs[np.isfinite(bs)]
    return dict(flag='ok', n=len(dd), ev=int(dd[ev].sum()),
                tot_hr=float(np.exp(bt)), dir_hr=float(np.exp(bd)),
                prop=float(prop), prop_se=float(bs.std(ddof=1)) if len(bs) > 20 else np.nan,
                boot_ok=int(len(bs)))


# ---------------------------------------------------------------- 主循环
sens, cells = [], []
for co in CO:
    print('=' * 70)
    print('#', co)
    s, dai, b = prep(co)
    ws = [w for w in L.WAVES[co] if w > b]
    if not ws:
        continue
    w1 = ws[0]
    nxt = dai[dai['wave'] == w1][['pid', 'dep']].rename(columns={'dep': 'dep1'}).set_index('pid')
    t1 = L.WAVE_YEAR[co][w1] - L.WAVE_YEAR[co][b]
    st = s.set_index('pid').join(nxt, how='inner')
    st = st[st['T'] > t1].copy()
    st['T1'] = st['T'] - t1

    # (1) 一波洗脱（=p7 的时序法，此处作基线参照）
    r = prop_of(st, 'T1', 'E', 'dm2', 'dep1', NB)
    if r and r.get('flag') == 'ok':
        sens.append(dict(cohort=co, spec='one-wave lag', **r))
        print('  (1) one-wave lag  : prop=%.3f n=%d' % (r['prop'], r['n']))

    # (2) 两波洗脱：结局自 w2 起
    if len(ws) >= 2:
        w2 = ws[1]
        t2 = L.WAVE_YEAR[co][w2] - L.WAVE_YEAR[co][b]
        s2 = st[st['T1'] > (t2 - t1)].copy()
        s2['T2'] = s2['T1'] - (t2 - t1)
        r = prop_of(s2, 'T2', 'E', 'dm2', 'dep1', NB)
        if r and r.get('flag') == 'ok':
            sens.append(dict(cohort=co, spec='two-wave washout', **r))
            print('  (2) two-wave      : prop=%.3f n=%d' % (r['prop'], r['n']))

    # (3) 仅事件性抑郁：基线无抑郁
    inc = st[st['dep'] == 0].copy()
    r = prop_of(inc, 'T1', 'E', 'dm2', 'dep1', NB)
    if r and r.get('flag') == 'ok':
        sens.append(dict(cohort=co, spec='incident depression', **r))
        print('  (3) incident dep  : prop=%.3f n=%d' % (r['prop'], r['n']))

    # (4) 含交互项（截面）
    r = prop_interaction(s, 'T', 'E', 'dm2', 'dep', NB)
    if r and r.get('flag') == 'ok':
        sens.append(dict(cohort=co, spec='with interaction', **r))
        print('  (4) interaction   : prop=%.3f n=%d' % (r['prop'], r['n']))

    # (5) 以多病单独为暴露
    r = prop_of(s, 'T', 'E', 'multi', 'dep', NB)
    if r and r.get('flag') == 'ok':
        sens.append(dict(cohort=co, spec='multimorbidity only', **r))
        print('  (5) multi only    : prop=%.3f n=%d' % (r['prop'], r['n']))

    # (6) g-formula 细胞风险 + 中介概率 → 四向分解
    try:
        from lifelines import CoxPHFitter
        import statsmodels.api as sm
        Xc = dcols(s)
        d = pd.concat([s[['T', 'E', 'Xbin', 'dep']], Xc], axis=1).dropna()
        cph = CoxPHFitter(penalizer=1e-4)
        cph.fit(d[['T', 'E', 'Xbin', 'dep'] + list(Xc.columns)], duration_col='T', event_col='E')
        Xl = pd.concat([d[['Xbin']], d[list(Xc.columns)]], axis=1)
        Xl = Xl.loc[:, Xl.nunique() > 1]
        lg = sm.Logit(d['dep'].astype(float), Xl).fit(disp=0)

        def risk(xv, mv):
            z = Xl.copy(); z['Xbin'] = xv; z['dep'] = mv
            S = cph.predict_survival_function(z, times=[5.0])
            return 1 - S.iloc[0].values
        z0 = Xl.copy(); z0['Xbin'] = 0.0
        z1 = Xl.copy(); z1['Xbin'] = 1.0
        pM0 = np.asarray(lg.predict(z0)).ravel()
        pM1 = np.asarray(lg.predict(z1)).ravel()
        R00, R01, R10, R11 = risk(0., 0.), risk(0., 1.), risk(1., 0.), risk(1., 1.)
        Y00c = float(np.mean(R00)); Y01c = float(np.mean(R01))
        Y10c = float(np.mean(R10)); Y11c = float(np.mean(R11))
        pm0 = float(np.mean(pM0)); pm1 = float(np.mean(pM1))
        TE = (pm1 * Y11c + (1 - pm1) * Y10c) - (pm0 * Y01c + (1 - pm0) * Y00c)
        CDE = Y10c - Y00c
        I = Y11c - Y10c - Y01c + Y00c
        INT_ref = pm0 * I
        INT_med = (pm1 - pm0) * I
        PIE = (pm1 - pm0) * (Y01c - Y00c)
        NIE = PIE + INT_med
        cells.append(dict(cohort=co, n=len(d), ev=int(d['E'].sum()),
                          Y00=Y00c, Y01=Y01c, Y10=Y10c, Y11=Y11c, pM0=pm0, pM1=pm1,
                          TE=TE, CDE=CDE, INT_ref=INT_ref, INT_med=INT_med, PIE=PIE, NIE=NIE,
                          prop_PIE=(PIE / TE if abs(TE) > 1e-9 else np.nan),
                          prop_NIE=(NIE / TE if abs(TE) > 1e-9 else np.nan)))
        print('  (6) 4-way: TE=%.4f CDE=%.4f INTref=%.4f INTmed=%.4f PIE=%.4f  PIE/NIE=%.2f'
              % (TE, CDE, INT_ref, INT_med, PIE, PIE / NIE if abs(NIE) > 1e-9 else np.nan))
    except Exception as e:
        print('  (6) 四向分解失败:', type(e).__name__, e)

S = pd.DataFrame(sens)
S.to_csv(os.path.join(OUT, '_med_sens.csv'), index=False, encoding='utf-8-sig')
pd.DataFrame(cells).to_csv(os.path.join(OUT, '_gf_cells.csv'), index=False, encoding='utf-8-sig')

print('\n' + '=' * 70)
print('# 敏感性设定合并（原始尺度 DL）')
pool = []
for spec, g in S.groupby('spec'):
    p = L.dl_meta_raw(g['prop'], g['prop_se'], spec)
    if not p:
        continue
    print('  %-22s k=%d %.1f%% (%.1f-%.1f) I2=%.1f%%'
          % (spec, p['k'], 100 * p['est'], 100 * p['lo'], 100 * p['hi'], p['I2']))
    pool.append(dict(spec=spec, k=p['k'], pct=100 * p['est'], lo=100 * p['lo'],
                     hi=100 * p['hi'], I2=p['I2']))
pd.DataFrame(pool).to_csv(os.path.join(OUT, '_med_sens_pool.csv'), index=False, encoding='utf-8-sig')

print('\n# 四向分解合并（逐队列均值）')
C = pd.DataFrame(cells)
if len(C):
    row = dict(k=len(C), TE=float(C['TE'].mean()), CDE=float(C['CDE'].mean()),
               INT_ref=float(C['INT_ref'].mean()), INT_med=float(C['INT_med'].mean()),
               PIE=float(C['PIE'].mean()), NIE=float(C['NIE'].mean()),
               prop_PIE=float(C['prop_PIE'].mean()), prop_NIE=float(C['prop_NIE'].mean()))
    print('  k=%d TE=%.4f CDE=%.4f INTref=%.4f INTmed=%.4f PIE=%.4f  纯间接占比=%.2f'
          % (row['k'], row['TE'], row['CDE'], row['INT_ref'], row['INT_med'], row['PIE'],
             row['prop_PIE'] / row['prop_NIE'] if row['prop_NIE'] else np.nan))
    pd.DataFrame([row]).to_csv(os.path.join(OUT, '_med_4way.csv'), index=False, encoding='utf-8-sig')

print('\nDONE')
