# -*- coding: utf-8 -*-
"""p14_cindex.py —— 判别力与主成分加权（§5.4/5.5 的数据源）
① Harrell's C：dai3 计数指数 vs 三个二分组各自入模（队列内 + 事件数加权平均）
② PC1 加权：三组分的主成分载荷与解释方差；PC1 加权暴露的 M2 合并 HR（每 1 SD）
输出：out/_cindex.csv、out/_pca.csv
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS


def dcols(df, drop=()):
    return L.design_frame(df, drop=drop)


def cindex_boot(df, cols, B=300, seed=14):
    """配对自助法给出 ΔC = C(index) − C(三个组分组) 的逐队列标准误。

    说明：自助时沿用**已拟合**的线性预测子重新抽样配对观测（不重复拟合 Cox），
    因此该区间刻画的是"给定同一拟合模型"下的抽样变异，不含模型估计本身的变异；
    这是本分析中可接受的近似，已在表注中言明。
    """
    from lifelines import CoxPHFitter
    from lifelines.utils import concordance_index
    d = df.dropna(subset=['T', 'E'] + list(cols))
    if len(d) < 200 or d['E'].sum() < 20:
        return None
    X = dcols(d)
    out = []
    lps = {}
    for tag, cc in [('idx', ['dai3']), ('cmp', ['disab', 'multi', 'dep'])]:
        dd = pd.concat([d[['T', 'E']], d[cc], X], axis=1).dropna()
        # 去掉常数列（否则 lifelines 会因零方差报 ConvergenceError）
        vv = [c for c in cc + list(X.columns) if dd[c].nunique() > 1]
        if len(vv) == 0:
            return None
        try:
            cph = CoxPHFitter(penalizer=1e-4)
            cph.fit(pd.concat([dd[['T', 'E']], dd[vv]], axis=1), duration_col='T', event_col='E')
            lp = cph.predict_log_partial_hazard(dd[vv])
        except Exception as e:
            print('   ΔC 自助跳过（拟合不收敛）:', type(e).__name__)
            return None
        lps[tag] = (dd['T'].to_numpy(float), dd['E'].to_numpy(int), np.asarray(lp, float))
    # 两个模型的行集合可能不同 → 对齐到交集（按索引）
    t1, e1, p1 = lps['idx']
    t2, e2, p2 = lps['cmp']
    m = min(len(t1), len(t2))
    rng = np.random.default_rng(seed)
    deltas = []
    for _ in range(B):
        j = rng.integers(0, m, m)
        c1 = concordance_index(t1[j], -p1[j], e1[j])
        c2 = concordance_index(t2[j], -p2[j], e2[j])
        deltas.append(c1 - c2)
    deltas = np.array([x for x in deltas if np.isfinite(x)])
    if len(deltas) < 30:
        return None
    return float(deltas.mean()), float(deltas.std(ddof=1)), len(deltas), m


def cindex(df, cols):
    """Harrell's C：用 lifelines 的 concordance_index（部分删失不支持 → 用可比对法手算）。"""
    from lifelines.utils import concordance_index
    d = df.dropna(subset=['T', 'E'] + list(cols))
    if len(d) < 200 or d['E'].sum() < 20:
        return None
    # 线性预测子：Cox 拟合后取风险评分
    X = dcols(d)
    dd = pd.concat([d[['T', 'E']], d[list(cols)], X], axis=1).dropna()
    r = L.cox(dd, 'T', 'E', list(cols) + list(X.columns), penalizer=1e-4, return_frame=True)
    if r is None:
        return None
    from lifelines import CoxPHFitter
    cph = CoxPHFitter(penalizer=1e-4)
    cph.fit(pd.concat([dd[['T', 'E']], dd[list(cols) + list(X.columns)]], axis=1),
            duration_col='T', event_col='E')
    lp = cph.predict_log_partial_hazard(
        pd.concat([dd[list(cols) + list(X.columns)]], axis=1))
    c = concordance_index(dd['T'], -lp, dd['E'])
    return float(c), len(dd), int(dd['E'].sum())


rows = []
for co in CO:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    r1 = cindex(d, ['dai3'])
    r2 = cindex(d, ['disab', 'multi', 'dep'])
    if r1 and r2:
        rows.append(dict(cohort=co, C_dai=r1[0], C_components=r2[0], delta=r1[0] - r2[0],
                         n=r1[1], ev=r1[2]))
# ------------------------------------------------ ΔC 的配对自助区间（非劣效性检验的基础）
brows = []
for co in CO:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    b = cindex_boot(d, ['disab', 'multi', 'dep'])
    if b:
        brows.append(dict(cohort=co, dC=b[0], se_dC=b[1], B=b[2], n=b[3]))
        print('  ΔC 自助 %-7s ΔC=%.4f  SE=%.4f  (B=%d, n=%d)' % (co, b[0], b[1], b[2], b[3]))
BO = pd.DataFrame(brows)
if len(BO):
    BO.to_csv(os.path.join(OUT, '_cindex_boot.csv'), index=False, encoding='utf-8-sig')
    # ΔC 是差值尺度，不能取指数：用标准逆方差固定/随机合并（DerSimonian–Laird）
    _e = BO['dC'].to_numpy(float)
    _s = BO['se_dC'].to_numpy(float)
    _w = 1.0 / _s ** 2
    _fe = float((_w * _e).sum() / _w.sum())
    _Q = float((_w * (_e - _fe) ** 2).sum())
    _df = len(_e) - 1
    _C = float(_w.sum() - (_w ** 2).sum() / _w.sum())
    _tau2 = max(0.0, (_Q - _df) / _C) if _C > 0 else 0.0
    _I2 = max(0.0, (_Q - _df) / _Q) * 100 if _Q > 0 else 0.0
    _ws = 1.0 / (_s ** 2 + _tau2)
    _mu = float((_ws * _e).sum() / _ws.sum())
    _sem = float(np.sqrt(1.0 / _ws.sum()))
    _lo, _hi = _mu - 1.96 * _sem, _mu + 1.96 * _sem
    print('ΔC 合并（DL 随机效应）: %.4f (%.4f to %.4f), k=%d, I2=%.1f%%, tau2=%.2e'
          % (_mu, _lo, _hi, len(_e), _I2, _tau2))
    print('  非劣效性：95%% CI 是否完全落在 ±0.01 之内 → %s'
          % ('是' if (_lo > -0.01 and _hi < 0.01) else '否'))
    pd.DataFrame([dict(dC=_mu, lo=_lo, hi=_hi, se=_sem, k=len(_e), I2=_I2, tau2=_tau2,
                       ninferiority_margin=0.01,
                       within_margin=bool(_lo > -0.01 and _hi < 0.01))]).to_csv(
        os.path.join(OUT, '_cindex_boot_pool.csv'), index=False, encoding='utf-8-sig')

CI = pd.DataFrame(rows)
CI.to_csv(os.path.join(OUT, '_cindex.csv'), index=False, encoding='utf-8-sig')
if len(CI):
    w = CI['ev']
    print('Harrell C（逐队列）:')
    print(CI.round(4).to_string(index=False))
    print('事件数加权平均: C(dai3)=%.4f  C(三组分)=%.4f  Δ=%.4f'
          % (np.average(CI['C_dai'], weights=w), np.average(CI['C_components'], weights=w),
             np.average(CI['delta'], weights=w)))
    print('简单平均:      C(dai3)=%.4f  C(三组分)=%.4f  Δ=%.4f'
          % (CI['C_dai'].mean(), CI['C_components'].mean(), CI['delta'].mean()))

# ---------------------------------------------------------------- PC1
pca_rows = []
for co in CO:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    base = L.BASE_WAVE[co]
    dai = pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % co))
    dai['pid'] = dai['pid'].astype(str)
    b = dai[dai['wave'] == base][['pid', 'disab', 'multi', 'dep']].dropna()
    X = b[['disab', 'multi', 'dep']].values
    Xc = X - X.mean(0)
    S = np.cov(Xc, rowvar=False)
    ev, evec = np.linalg.eigh(S)
    idx = np.argsort(ev)[::-1]
    ev, evec = ev[idx], evec[:, idx]
    load = evec[:, 0]
    if load.sum() < 0:
        load = -load
    pc1 = Xc @ load
    pc1 = pc1 / pc1.std()
    b = b.assign(pc1=pc1)
    d['pid'] = d['pid'].astype(str)
    m = d.merge(b[['pid', 'pc1']], on='pid', how='inner')
    Xd = dcols(m)
    dd = pd.concat([m[['T', 'E', 'pc1']], Xd], axis=1).dropna()
    if len(dd) < 200 or dd['E'].sum() < 20:
        continue
    cc = ['pc1'] + list(Xd.columns)
    r = L.cox(dd, 'T', 'E', cc, penalizer=1e-4, return_frame=True)
    if r is None or 'pc1' not in r[5].index:
        continue
    s = r[5]
    pca_rows.append(dict(cohort=co, load_disab=load[0], load_multi=load[1], load_dep=load[2],
                         var_explained=ev[0] / ev.sum(), hr=float(s.loc['pc1', 'exp(coef)']),
                         se=float(s.loc['pc1', 'se(coef)']), n=len(dd)))
PC = pd.DataFrame(pca_rows)
PC.to_csv(os.path.join(OUT, '_pca.csv'), index=False, encoding='utf-8-sig')
if len(PC):
    print('\nPC1 载荷（逐队列）:')
    print(PC.round(3).to_string(index=False))
    # 稳定性守卫：|logHR|>1 或 se>1.5 判为不稳定（事件时点过少导致）
    stable = PC[(PC['hr'].apply(lambda v: abs(np.log(max(v, 1e-9))) < 1) & (PC['se'] < 1.5))]
    if len(stable) < len(PC):
        print('  不稳定队列（已剔除，因事件时点过少）：',
              ', '.join(PC.loc[~PC.index.isin(stable.index), 'cohort']))
    p = L.dl_meta(np.log(stable['hr']), stable['se'], 'PC1')
    print('PC1 加权 M2 合并: k=%d HR=%.3f (%.3f-%.3f) per 1 SD，I2=%.1f%%'
          % (p['k'], p['hr'], p['lo'], p['hi'], p['I2']))
    print('载荷均值: 失能 %.3f / 多病 %.3f / 抑郁 %.3f；解释方差均值 %.1f%%'
          % (stable['load_disab'].mean(), stable['load_multi'].mean(), stable['load_dep'].mean(),
             100 * stable['var_explained'].mean()))
    pd.DataFrame([dict(k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'], I2=p['I2'],
                       cohorts=','.join(sorted(stable['cohort'])),
                       load_disab=stable['load_disab'].mean(), load_multi=stable['load_multi'].mean(),
                       load_dep=stable['load_dep'].mean(),
                       var_explained=stable['var_explained'].mean())]).to_csv(
        os.path.join(OUT, '_pca_pool.csv'), index=False, encoding='utf-8-sig')
print('\nDONE')
