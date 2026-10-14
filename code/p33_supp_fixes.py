# -*- coding: utf-8 -*-
"""p33_supp_fixes.py —— 响应外部审稿意见的补充分析

A 基线认知调整：多种稳健规格（连续 z 分层/不分层、四分位哑变量），含稳定性守卫
B 时变（counting-process）三模型的**聚类稳健标准误**（按 pid）与非聚类对比
C 死亡风险（竞争风险）：连续 DAI 与七个联合类别各自的死亡 HR，含稳定性守卫
D NNT / 每 1000 人额外病例（由反事实 5 年风险格）
E 时距分析的等价性检验（各 lag vs lag 0 的比值及 CI）
F 交互 P 的 Benjamini–Hochberg FDR 校正
G 各时距的样本特征（n / 事件 / 年龄 / 残疾比例 / 死亡数），守卫与 p6 对齐

所有结果落盘 CSV，供 p18/p26 审计溯源。2026-10-13。
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT, CO = L.OUT, L.COHORTS
GUARD = dict(abs_coef=3.0, max_se=2.0)


def raw_fit(d, expo, extra=(), dur='T', ev='E', drop=(), pen=1e-4,
            entry=None, cluster=None):
    """单队列拟合（支持左截断 entry 与聚类 cluster）。返回原始摘要 dict。"""
    X = L.design_frame(d, extra=extra, drop=drop)
    cols = [expo] + list(X.columns)
    carry = [dur, ev, expo]
    if entry:
        carry.append(entry)
    if cluster:
        carry.append(cluster)
    dd = pd.concat([d[carry], X], axis=1).dropna()
    if len(dd) < 100 or dd[ev].sum() < 20:
        return None
    from lifelines import CoxPHFitter
    kw = dict(duration_col=dur, event_col=ev)
    if entry:
        kw['entry_col'] = entry
    if cluster:
        kw['cluster_col'] = cluster
    try:
        cph = CoxPHFitter(penalizer=pen)
        fit_cols = cols + [dur, ev] + ([entry] if entry else []) + ([cluster] if cluster else [])
        cph.fit(dd[fit_cols].copy(), **kw)
        s = cph.summary
        if expo not in s.index:
            return None
        return dict(coef=float(s.loc[expo, 'coef']), se=float(s.loc[expo, 'se(coef)']),
                    hr=float(s.loc[expo, 'exp(coef)']), n=len(dd), ev=int(dd[ev].sum()))
    except Exception:
        return None


def stable(r):
    """稳定性守卫：|coef|<3 且 se<2。不通过则返回 None 并记账。"""
    if r is None:
        return None
    if abs(r['coef']) > GUARD['abs_coef'] or r['se'] > GUARD['max_se']:
        return None
    return r


def pooled(rows, label=''):
    if not rows:
        return None
    s = pd.DataFrame(rows)
    q = L.dl_meta(s['coef'], s['se'], label)
    if q:
        q['n'] = int(s['n'].sum())
        q['ev'] = int(s['ev'].sum())
    return q


def show(m, q, extra=''):
    if not q:
        print('  %-18s 不可合并' % m)
        return
    print('  %-18s k=%d  HR=%.3f (%.3f-%.3f)  I2=%5.1f%%  n=%d ev=%d %s'
          % (m, q['k'], q['hr'], q['lo'], q['hi'], q['I2'], q['n'], q['ev'], extra))


SURV = {c: pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % c)) for c in CO}

# ==================================================== A 基线认知调整
print('=' * 78)
print('A  基线认知调整')
AR, dump = [], []
for co in CO:
    d = SURV[co].copy()
    d['cogz'] = d['global_z'].astype(float)            # 不按教育分层
    d['cogze'] = d['global_z_edu'].astype(float)       # 教育分层（结局判据的同一测量）
    q4 = pd.qcut(d['cogze'].rank(method='first'), 4, labels=False)
    for k in (1, 2, 3):
        d['cq%d' % k] = (q4 == k).astype(float)
    specs = [('M2', {}),
             ('M2+cogz_edu', dict(extra=['cogze'])),
             ('M2+cogz', dict(extra=['cogz'])),
             ('M2+cogz_edu+cogz', dict(extra=['cogze', 'cogz'])),
             ('M2+cog_quartiles', dict(extra=['cq1', 'cq2', 'cq3'])),
             ('M2-edu+cogz', dict(extra=['cogz'], drop=['edu_2', 'edu_3']))]
    for tag, kw in specs:
        r = raw_fit(d, 'dai3', **kw)
        dump.append(dict(cohort=co, model=tag, raw=(r or {}).get('hr', np.nan),
                         raw_se=(r or {}).get('se', np.nan),
                         n=(r or {}).get('n', np.nan), ev=(r or {}).get('ev', np.nan),
                         kept=bool(stable(r))))
        rs = stable(r)
        if rs:
            AR.append(dict(cohort=co, model=tag, **rs))
A = pd.DataFrame(AR)
A.to_csv(os.path.join(OUT, '_cogadj.csv'), index=False, encoding='utf-8-sig')
pd.DataFrame(dump).to_csv(os.path.join(OUT, '_cogadj_raw.csv'), index=False, encoding='utf-8-sig')
for m in ['M2', 'M2+cogz_edu', 'M2+cogz', 'M2+cogz_edu+cogz', 'M2+cog_quartiles', 'M2-edu+cogz']:
    s = A[A['model'] == m]
    nall = int((pd.DataFrame(dump)['model'] == m).sum())
    show(m, pooled(s.to_dict('records'), m),
         '(守卫剔除 %d/%d 队列)' % (nall - len(s), nall))

# ==================================================== B 时变模型聚类稳健
# 见 p34_timevar_cluster.py（独立脚本，跑时较长）

# ==================================================== C 死亡风险
print()
print('=' * 78)
print('C  死亡风险（cause-specific，事件 = 死亡）')
CAT = {7: 'All three', 6: 'Disability+depression', 5: 'Disability+multimorbidity',
       4: 'Disability only', 3: 'Multimorbidity+depression', 2: 'Multimorbidity only',
       1: 'Depression only'}
CDn, CD = [], []
for co in CO:
    d = SURV[co].copy()
    r = stable(raw_fit(d, 'dai3', dur='T', ev='died'))
    if r:
        CD.append(dict(cohort=co, cat='Continuous DAI', **r))
        CDn.append(dict(cohort=co, cat='Continuous DAI', kept=True))
    d['_dis'] = (d['disab'] > 0).astype(float)
    d['_mul'] = (d['multi'] > 0).astype(float)
    d['_dep'] = (d['dep'] > 0).astype(float)
    d['jg'] = (d['_dis'] * 4 + d['_mul'] * 2 + d['_dep']).astype(float)
    for gg in sorted(CAT):
        d['zz'] = (d['jg'] == gg).astype(float)
        sub = d[(d['jg'] == 0) | (d['jg'] == gg)].copy()
        rr = stable(raw_fit(sub, 'zz', dur='T', ev='died'))
        CDn.append(dict(cohort=co, cat=CAT[gg], kept=bool(rr),
                        raw=(raw_fit(sub, 'zz', dur='T', ev='died') or {}).get('hr', np.nan)))
        if rr:
            CD.append(dict(cohort=co, cat=CAT[gg], **rr))
CD = pd.DataFrame(CD)
CD.to_csv(os.path.join(OUT, '_death.csv'), index=False, encoding='utf-8-sig')
CDn = pd.DataFrame(CDn)
CDn.to_csv(os.path.join(OUT, '_death_guard.csv'), index=False, encoding='utf-8-sig')
for c in ['Continuous DAI'] + [CAT[g] for g in sorted(CAT, reverse=True)]:
    s = CD[CD['cat'] == c]
    nn = CDn[CDn['cat'] == c]
    show(c, pooled(s.to_dict('records'), c),
         '(守卫剔除 %d/%d)' % (int((~nn['kept']).sum()), len(nn)))

# ==================================================== D NNT
print()
print('=' * 78)
print('D  NNT 与每 1000 人额外病例（反事实 5 年风险）')
G = pd.read_csv(os.path.join(OUT, '_gf_cells.csv'), encoding='utf-8-sig')
r00, r10, r01, r11 = (float(G['Y00'].mean()), float(G['Y10'].mean()),
                      float(G['Y01'].mean()), float(G['Y11'].mean()))
NT = []
for lab, rr_, ref in [('Both burdens vs neither', r11, r00),
                      ('Non-depressive burden vs neither', r10, r00),
                      ('Depression vs neither', r01, r00)]:
    arr = rr_ - ref
    NT.append(dict(contrast=lab, risk_exposed=round(100 * rr_, 2), risk_ref=round(100 * ref, 2),
                   abs_diff_pp=round(100 * arr, 2), extra_per_1000=round(1000 * arr, 1),
                   NNT=round(1 / arr, 1) if arr > 0 else np.nan))
NT = pd.DataFrame(NT)
NT.to_csv(os.path.join(OUT, '_nnt.csv'), index=False, encoding='utf-8-sig')
print(NT.to_string(index=False))

# ==================================================== E 等价性
print()
print('=' * 78)
print('E  时距分析等价性检验（各 lag 与 lag 0 的比值）')
LP = pd.read_csv(os.path.join(OUT, '_lag_cum_pool.csv'), encoding='utf-8-sig')
b = LP[LP['Lag'] == 0].iloc[0]
EQ = []
for _, r in LP.iterrows():
    dl = float(r['coef']) - float(b['coef'])
    se = float(np.sqrt(float(r['se']) ** 2 + float(b['se']) ** 2))
    EQ.append(dict(lag=int(r['Lag']), k=int(r['k']), hr=round(float(r['hr']), 3),
                   events=int(r['events']), hr_vs_lag0=round(float(np.exp(dl)), 3),
                   lo=round(float(np.exp(dl - 1.96 * se)), 3),
                   hi=round(float(np.exp(dl + 1.96 * se)), 3),
                   within_10pct=bool(max(abs(dl - 1.96 * se), abs(dl + 1.96 * se)) < np.log(1.10))))
EQ = pd.DataFrame(EQ)
EQ.to_csv(os.path.join(OUT, '_equiv.csv'), index=False, encoding='utf-8-sig')
print(EQ.to_string(index=False))

# ==================================================== F 交互 FDR
print()
print('=' * 78)
print('F  交互 P 的 BH-FDR 校正')
I = pd.read_csv(os.path.join(OUT, '_int.csv'), encoding='utf-8-sig')
pv = I['p_int'].to_numpy(float)
order = np.argsort(pv)
mm = len(pv)
q = np.empty(mm)
prev = 1.0
for rank in range(mm - 1, -1, -1):
    idx = order[rank]
    prev = min(prev, pv[idx] * mm / (rank + 1))
    q[idx] = prev
I['q_BH'] = q
I['sig_raw'] = I['p_int'] < 0.05
I['sig_BH'] = I['q_BH'] < 0.05
I.to_csv(os.path.join(OUT, '_int_fdr.csv'), index=False, encoding='utf-8-sig')
print(I[['modifier', 'k', 'hr_int', 'lo', 'hi', 'p_int', 'q_BH', 'sig_raw', 'sig_BH']]
      .to_string(index=False))

# ==================================================== G 各时距样本特征
print()
print('=' * 78)
print('G  各时距的样本特征（守卫与 p6 的 _lag_cum 对齐）')
GS = []
for co in CO:
    d = SURV[co].copy()
    for lag in [0, 2, 4, 6, 8, 10, 12]:
        sub = d[d['T'] > lag].copy()
        sub['T2'] = sub['T'] - lag
        r = stable(raw_fit(sub, 'dai3', dur='T2', ev='E'))
        if not r or r['n'] < 300 or r['ev'] < 30:
            continue
        X = L.design_frame(sub)
        dd = pd.concat([sub[['T2', 'E', 'died', 'age', 'disab', 'dai3']], X], axis=1).dropna()
        GS.append(dict(lag=lag, cohort=co, n=r['n'], events=r['ev'],
                       deaths=int(dd['died'].sum()),
                       mean_age=round(float(dd['age'].mean()), 1),
                       pct_disab=round(100 * float((dd['disab'] > 0).mean()), 1),
                       mean_dai=round(float(dd['dai3'].mean()), 2)))
GS = pd.DataFrame(GS)
GS.to_csv(os.path.join(OUT, '_lagspec.csv'), index=False, encoding='utf-8-sig')
agg = GS.groupby('lag').agg(k=('cohort', 'nunique'), n=('n', 'sum'), events=('events', 'sum'),
                            deaths=('deaths', 'sum'), mean_age=('mean_age', 'mean'),
                            pct_disab=('pct_disab', 'mean')).reset_index()
agg.to_csv(os.path.join(OUT, '_lagspec_pool.csv'), index=False, encoding='utf-8-sig')
print(agg.round(2).to_string(index=False))

print()
print('DONE p33')
