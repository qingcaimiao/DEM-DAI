# -*- coding: utf-8 -*-
"""p8_competing.py —— 竞争风险：Fine-Gray 亚分布模型 + Aalen-Johansen 累积发病率（Table 4C/Fig 3）
Fine-Gray 用 IPCW 精确加权实现：权重 = Ĝ(t_k)/Ĝ(T_i)，竞争事件者按亚分布风险集重新入组，
展开到计数过程网格后拟合加权 Cox。
输出：out/_fg.csv、_fg_pool.csv、_cif.csv
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
NAME = {c: c for c in CO}


def km_cens(t, e):
    """删失生存函数 Ĝ(t)：任何原因的事件都离开风险集，只有删失算事件。"""
    order = np.argsort(t)
    t = np.asarray(t)[order]; e = np.asarray(e)[order]
    ts = np.unique(t)
    n = len(t)
    G = 1.0; out = {}
    at_risk = n
    for s in ts:
        d = int(((t == s) & (e == 0)).sum())
        if d > 0:
            G *= (1 - d / at_risk)
        out[s] = G
        at_risk -= int((t == s).sum())
    return out, ts


def design(df):
    X = pd.DataFrame(index=df.index)
    a = df['age'].astype(float)
    X['age_c'] = a - 65.0; X['age2'] = X['age_c'] ** 2
    X['male'] = df['male'].astype(float)
    for k in (2, 3):
        X['edu_%d' % k] = (df['edu'] == k).astype(float)
    X['partnered'] = df['partnered'].astype(float)
    X['smoke1'] = (df['smoke3'] == 1).astype(float)
    X['smoke2'] = (df['smoke3'] == 2).astype(float)
    X['drink_now'] = df['drink_now'].astype(float)
    X['bmi'] = df['bmi'].astype(float)
    return X


def finegray(df, expo='dai3'):
    """返回 (coef, se, p, n, ev)。"""
    from lifelines import CoxPHFitter
    X = design(df)
    d = pd.concat([df[['T', 'E', 'died', expo]], X], axis=1).dropna()
    if len(d) < 300 or d['E'].sum() < 30:
        return None
    t = d['T'].values.astype(float)
    e = d['E'].values.astype(int)          # 1 = 痴呆
    comp = ((d['died'].values == 1) & (e == 0)).astype(int)   # 竞争事件（无痴呆死亡）
    # 删失指示：E=0 且非竞争事件
    censor = ((e == 0) & (comp == 0)).astype(int)
    Gmap, ts = km_cens(t, 1 - censor)      # 对"删失"求 KM（事件=删失）
    tgrid = np.sort(np.unique(t[e == 1]))
    rows = []
    base = d[d.columns.difference(['T', 'E', 'died'])]
    for tk in tgrid:
        # 亚分布风险集：T >= tk，或 竞争事件且 T < tk（仍留在风险集）
        inrisk = (t >= tk) | ((comp == 1) & (t < tk))
        if inrisk.sum() < 50:
            continue
        w = np.ones(len(d))
        Gt = Gmap.get(tk, 1.0)
        for i in np.where(comp == 1)[0]:
            Gi = Gmap.get(t[i], np.nan)
            w[i] = Gt / Gi if (Gi and np.isfinite(Gi) and Gi > 0) else 0.0
        blk = base.copy()
        blk['_t'] = tk
        blk['_e'] = (e == 1) & np.isclose(t, tk)
        blk['_w'] = w
        blk = blk[inrisk]
        rows.append(blk)
    if not rows:
        return None
    long = pd.concat(rows, ignore_index=True)
    long = long[long['_w'] > 0]
    try:
        cph = CoxPHFitter(penalizer=1e-4)
        cph.fit(long, duration_col='_t', event_col='_e', weights_col='_w',
                entry_col=None, robust=False)
        if expo not in cph.summary.index:
            return None
        s = cph.summary
        return (float(s.loc[expo, 'coef']), float(s.loc[expo, 'se(coef)']),
                float(s.loc[expo, 'p']), len(d), int(d['E'].sum()))
    except Exception as e2:
        print('    FG 拟合失败:', type(e2).__name__, e2)
        return None


def cif(df, strat='dai3', tmax=None):
    """Aalen-Johansen 累积发病率，按分层变量；tmax 为评估时点（τ）。"""
    out = []
    if tmax is None:
        tmax = float(df['T'].max())
    levels = sorted(df[strat].dropna().unique())
    for lv in levels:
        s = df[df[strat] == lv]
        if len(s) < 50:
            continue
        t = s['T'].values.astype(float)
        e1 = (s['E'].values == 1)
        e2 = ((s['died'].values == 1) & (~e1))
        ts = np.unique(t)
        n = len(t); S = 1.0
        cifv = 0.0
        for tk in ts:
            if tk > tmax:
                break
            at_risk = int((t >= tk).sum())
            if at_risk <= 0:
                break
            d1 = int((np.isclose(t, tk) & e1).sum())
            d2 = int((np.isclose(t, tk) & e2).sum())
            if d1:
                cifv += S * d1 / at_risk
            if d1 + d2:
                S *= (1 - (d1 + d2) / at_risk)
            out.append(dict(level=lv, t=tk, cif=cifv, n_at_risk=at_risk))
    return pd.DataFrame(out)


rows = []
for co in CO:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    print('=' * 66); print('#', co, ' n=%d 痴呆=%d 无痴呆死亡=%d' % (len(d), d['E'].sum(), ((d['died'] == 1) & (d['E'] == 0)).sum()))
    r = finegray(d)
    if r:
        rows.append(dict(cohort=NAME[co], coef=r[0], se=r[1], p=r[2], n=r[3], ev=r[4],
                         hr=np.exp(r[0])))
        print('  Fine-Gray 亚分布 HR = %.3f (%.3f-%.3f) p=%.2e'
              % (np.exp(r[0]), np.exp(r[0] - 1.96 * r[1]), np.exp(r[0] + 1.96 * r[1]), r[2]))
    # CIF：τ = 各库最大随访，但不超过 10 年（与稿件口径一致）
    tau = float(min(d['T'].max(), 10))
    c = cif(d, 'dai3', tau)
    c['cohort'] = co
    c['tau'] = tau
    c.to_csv(os.path.join(OUT, '_cif_%s.csv' % co), index=False, encoding='utf-8-sig')

FG = pd.DataFrame(rows)
FG.to_csv(os.path.join(OUT, '_fg.csv'), index=False, encoding='utf-8-sig')
if len(FG) >= 2:
    p = L.dl_meta(FG['coef'], FG['se'], 'Fine-Gray')
    print('\nFG 合并: k=%d HR=%.3f (%.3f-%.3f) I2=%.1f%%' % (p['k'], p['hr'], p['lo'], p['hi'], p['I2']))
    pd.DataFrame([dict(k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'], I2=p['I2'])]).to_csv(
        os.path.join(OUT, '_fg_pool.csv'), index=False, encoding='utf-8-sig')

# 汇总 10 年 CIF 表
allc = []
for co in CO:
    f = os.path.join(OUT, '_cif_%s.csv' % co)
    if os.path.exists(f):
        allc.append(pd.read_csv(f))
if allc:
    C = pd.concat(allc, ignore_index=True)
    T10 = C[C['t'] == C.groupby('cohort')['t'].transform('max')]
    T10.to_csv(os.path.join(OUT, '_cif.csv'), index=False, encoding='utf-8-sig')
    print('\n各库最大随访时点的累积发病率（按 DAI 层）:')
    print(T10.pivot_table(index='cohort', columns='level', values='cif').round(4).to_string())
print('\nDONE')
