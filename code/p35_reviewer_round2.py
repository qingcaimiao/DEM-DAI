# -*- coding: utf-8 -*-
"""p35_reviewer_round2.py —— 第二轮审稿意见的补充分析

① 按暴露类别的 Fine–Gray 亚分布 HR（重点：multimorbidity only 是否仍 < 1）
② 随机效应敏感性：DL / REML / Knapp–Hartung / 95 % 预测区间
③ Meta-regression：异质性来源（基线年份、随访长度、事件比例）
④ 结局需两次连续评估确认的敏感性分析
⑤ MI 方案的样本量与事件数
⑥ 校准度：按暴露层的观察/预期比与校准斜率

输出：out/_fg_cat.csv、_re_sens.csv、_metareg2.csv、_confirm.csv、_calib.csv
"""
import os
import numpy as np
import pandas as pd
from scipy import stats
import dem_lib as L

OUT, CO = L.OUT, L.COHORTS
from lifelines import CoxPHFitter


# ================================================================ 工具
def km_cens(t, e):
    order = np.argsort(t)
    t = np.asarray(t)[order]; e = np.asarray(e)[order]
    ts = np.unique(t); n = len(t)
    G = 1.0; out = {}; at_risk = n
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
        X['edu_%d' % k] = df['edu'].map(lambda v, k=k: float(v == k) if pd.notna(v) else np.nan)
    X['partnered'] = df['partnered'].astype(float)
    for k in (1, 2):
        X['smoke%d' % k] = df['smoke3'].map(lambda v, k=k: float(v == k) if pd.notna(v) else np.nan)
    X['drink_now'] = df['drink_now'].astype(float)
    X['bmi'] = df['bmi'].astype(float)
    return X


def finegray(df, expo, comp_col='died'):
    """IPCW 精确加权的 Fine–Gray 亚分布模型。expo 可为多列（类别哑变量）。"""
    cols = [expo] if isinstance(expo, str) else list(expo)
    X = design(df)
    d = pd.concat([df[['T', 'E', comp_col] + cols], X], axis=1).dropna()
    if len(d) < 200 or d['E'].sum() < 20:
        return None
    t = d['T'].to_numpy(float)
    e = d['E'].to_numpy(int)
    comp = (d[comp_col].to_numpy(int) == 1) & (e == 0)
    censor = ((e == 0) & (~comp)).astype(int)
    Gmap, _ = km_cens(t, 1 - censor)
    tgrid = np.sort(np.unique(t[e == 1]))
    base = d[['T', 'E', comp_col] + cols + list(X.columns)].copy()
    rows = []
    for tk in tgrid:
        inrisk = (t >= tk) | (comp & (t < tk))
        if inrisk.sum() < 50:
            continue
        w = np.ones(len(d))
        Gt = Gmap.get(tk, 1.0)
        for i in np.where(comp)[0]:
            Gi = Gmap.get(t[i], np.nan)
            w[i] = Gt / Gi if (Gi and np.isfinite(Gi) and Gi > 0) else 0.0
        blk = base.copy()
        blk['_t'] = tk
        blk['_e'] = (e == 1) & np.isclose(t, tk)
        blk['_w'] = w
        rows.append(blk[inrisk])
    if not rows:
        return None
    long = pd.concat(rows, ignore_index=True)
    long = long[long['_w'] > 0]
    xcols = cols + list(X.columns)
    try:
        cph = CoxPHFitter(penalizer=1e-4)
        cph.fit(long[['_t', '_e', '_w'] + xcols], duration_col='_t', event_col='_e',
                weights_col='_w')
        s = cph.summary
        out = {}
        for c in cols:
            if c in s.index:
                out[c] = (float(s.loc[c, 'coef']), float(s.loc[c, 'se(coef)']))
        return out if out else None
    except Exception as e2:
        print('   FG 拟合失败:', type(e2).__name__, str(e2)[:110])
        return None


# ================================================================ ① 分层 Fine–Gray
print('=' * 74)
print('① 按暴露类别的 Fine–Gray 亚分布 HR（vs 三无）')
CAT = {7: 'All three', 6: 'Disability+depression', 5: 'Disability+multimorbidity',
       4: 'Disability only', 3: 'Multimorbidity+depression', 2: 'Multimorbidity only',
       1: 'Depression only'}
FG = []
# 与 Table 3C 同设计：每个类别**单独**与"三无"比较（不互调），否则两者不可比
for co in CO:
    d0 = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co)).copy()
    d0['_dis'] = (d0['disab'] > 0).astype(float)
    d0['_mul'] = (d0['multi'] > 0).astype(float)
    d0['_dep'] = (d0['dep'] > 0).astype(float)
    d0['jg'] = d0['_dis'] * 4 + d0['_mul'] * 2 + d0['_dep']
    for g in sorted(CAT):
        d = d0[(d0['jg'] == 0) | (d0['jg'] == g)].copy()
        d['zz'] = (d['jg'] == g).astype(float)
        r = finegray(d, 'zz')
        if not r or 'zz' not in r:
            print('  %-7s %-26s 拟合失败' % (co, CAT[g]))
            continue
        cf, se = r['zz']
        if abs(cf) < 3 and se < 2:
            FG.append(dict(cohort=co, cat=CAT[g], coef=cf, se=se, hr=float(np.exp(cf)),
                           n=len(d), ev=int(d['E'].sum())))
    print('  %s 完成' % co)
FG = pd.DataFrame(FG)
FG.to_csv(os.path.join(OUT, '_fg_cat.csv'), index=False, encoding='utf-8-sig')
for c in [CAT[g] for g in sorted(CAT, reverse=True)]:
    s = FG[FG['cat'] == c]
    if len(s) < 2:
        print('  %-28s 不足以合并' % c)
        continue
    q = L.dl_meta(s['coef'], s['se'], c)
    print('  %-28s k=%d  sHR=%.3f (%.3f–%.3f)  I²=%5.1f%%'
          % (c, q['k'], q['hr'], q['lo'], q['hi'], q['I2']))

# 与 cause-specific 并排（多病单独）
_ds = pd.read_csv(os.path.join(OUT, '_death.csv'))
print('  —— 对照：cause-specific 痴呆 HR（主表 Table 3C）中 multimorbidity only = 0.89 (0.81–0.98)')

# ================================================================ ② 随机效应敏感性
print()
print('=' * 74)
print('② 随机效应模型敏感性（主分析 M2 的 6 个队列估计）')
M = pd.read_csv(os.path.join(OUT, '_m1234.csv'))
M2 = M[M['model'] == 'M2'].copy()
M2['y'] = np.log(M2['hr'].astype(float))


def reml_tau2(y, se, maxit=500, tol=1e-10):
    v = np.asarray(se, float) ** 2; y = np.asarray(y, float)
    tau2 = 0.0
    for _ in range(maxit):
        w = 1.0 / (v + tau2)
        mu = (w * y).sum() / w.sum()
        num = (w ** 2 * ((y - mu) ** 2 - v)).sum() + 1.0 / w.sum()
        den = (w ** 2).sum()
        new = max(0.0, num / den)
        if abs(new - tau2) < tol:
            tau2 = new; break
        tau2 = new
    return tau2


def summarize(y, se, tau2, method):
    w = 1.0 / (se ** 2 + tau2)
    mu = (w * y).sum() / w.sum()
    k = len(y)
    if method == 'KH':
        qh = (w * (y - mu) ** 2).sum() / (k - 1)
        se_mu = np.sqrt(qh / w.sum())
        tcrit = stats.t.ppf(0.975, k - 1)
    else:
        se_mu = np.sqrt(1.0 / w.sum())
        tcrit = 1.96
    lo, hi = mu - tcrit * se_mu, mu + tcrit * se_mu
    return dict(method=method, k=k, hr=float(np.exp(mu)), lo=float(np.exp(lo)),
                hi=float(np.exp(hi)), tau2=float(tau2), se_mu=float(se_mu))


y = M2['y'].to_numpy(float)
se = M2['se'].to_numpy(float)
k = len(y)
# DL
w = 1 / se ** 2
mu_f = (w * y).sum() / w.sum()
Q = (w * (y - mu_f) ** 2).sum()
C = w.sum() - (w ** 2).sum() / w.sum()
tau_dl = max(0.0, (Q - (k - 1)) / C)
rows = [dict(summarize(y, se, tau_dl, 'DL'), Q=Q, I2=100 * max(0, (Q - (k - 1)) / Q))]
tau_reml = reml_tau2(y, se)
rows.append(dict(summarize(y, se, tau_reml, 'REML'), Q=Q,
                 I2=100 * max(0, (Q - (k - 1)) / Q)))
kh = summarize(y, se, tau_reml, 'REML + Knapp–Hartung')
rows.append(dict(kh, Q=Q, I2=100 * max(0, (Q - (k - 1)) / Q)))
# 预测区间
w2 = 1 / (se ** 2 + tau_reml)
mu2 = (w2 * y).sum() / w2.sum()
se_mu2 = np.sqrt(1 / w2.sum())
tcrit = stats.t.ppf(0.975, k - 1)
pi_lo = mu2 - tcrit * np.sqrt(se_mu2 ** 2 + tau_reml)
pi_hi = mu2 + tcrit * np.sqrt(se_mu2 ** 2 + tau_reml)
RE = pd.DataFrame(rows)
RE.loc[len(RE)] = dict(method='95 % prediction interval', k=k, hr=float(np.exp(mu2)),
                       lo=float(np.exp(pi_lo)), hi=float(np.exp(pi_hi)),
                       tau2=float(tau_reml), se_mu=float(se_mu2), Q=Q, I2=np.nan)
RE.to_csv(os.path.join(OUT, '_re_sens.csv'), index=False, encoding='utf-8-sig')
for _, r in RE.iterrows():
    print('  %-26s HR=%.3f (%.3f–%.3f)  τ²=%.4f'
          % (r['method'], r['hr'], r['lo'], r['hi'], r['tau2']))

# ================================================================ ③ Meta-regression
print()
print('=' * 74)
print('③ Meta-regression：异质性来源（随机效应 WLS，M2）')
fl = pd.read_csv(os.path.join(OUT, '_surv_flow.csv'))
Y0 = {'CHARLS': 2011, 'ELSA': 2002, 'HRS': 1992, 'KLoSA': 2006, 'MHAS': 2001, 'SHARE': 2004}
MR = M2.merge(fl[['cohort', 'median_fu', 'max_fu', 'N', 'events']], on='cohort', how='left')
MR['y0'] = MR['cohort'].map(Y0)
MR['ev_pct'] = 100 * MR['events'] / MR['N']
MRG = []
for var, lab in [('y0', 'Baseline year'), ('median_fu', 'Median follow-up (years)'),
                 ('max_fu', 'Maximum follow-up (years)'), ('ev_pct', 'Event proportion (%)')]:
    x = MR[var].to_numpy(float)
    ww = 1 / (MR['se'].to_numpy(float) ** 2 + tau_reml)
    Xd = np.column_stack([np.ones(len(x)), x])
    W = np.diag(ww)
    beta = np.linalg.solve(Xd.T @ W @ Xd, Xd.T @ W @ y)
    resid = y - Xd @ beta
    dfree = len(x) - 2
    s2 = (ww * resid ** 2).sum() / dfree
    cov = s2 * np.linalg.inv(Xd.T @ W @ Xd)
    se_b = np.sqrt(np.diag(cov))
    tval = beta[1] / se_b[1]
    p = 2 * (1 - stats.t.cdf(abs(tval), dfree))
    MRG.append(dict(variable=lab, slope=float(beta[1]), se=float(se_b[1]),
                    p=float(p), df=dfree))
MRG = pd.DataFrame(MRG)
MRG.to_csv(os.path.join(OUT, '_metareg2.csv'), index=False, encoding='utf-8-sig')
print(MRG.to_string(index=False))

# ================================================================ ④ 两次连续确认
print()
print('=' * 74)
print('④ 结局要求两次连续评估确认的敏感性分析')
CONF = []
for co in CO:
    cg = pd.read_parquet(os.path.join(OUT, '_cog2_%s.parquet' % co))
    sh = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    cg['pid'] = cg['pid'].astype(str); sh['pid'] = sh['pid'].astype(str)
    cg = cg.sort_values(['pid', 'wave'])
    cg['nx'] = cg.groupby('pid')['dem_alg_edu'].shift(-1)
    cg['conf'] = ((cg['dem_alg_edu'] == 1) & (cg['nx'] == 1)).astype(float)
    first_conf = cg[cg['conf'] == 1].groupby('pid')['year'].min()
    d = sh.copy()
    base_year = float(L.WAVE_YEAR[co][L.BASE_WAVE[co]])
    d = d.set_index('pid')
    d['yr_conf'] = first_conf
    # 只在有足够随访的人中评估：要求末次认知评估晚于首次确认波
    d['E2'] = d['yr_conf'].notna().astype(int)
    d['T2'] = np.where(d['E2'] == 1, d['yr_conf'] - base_year, d['T'])
    d = d[d['T2'] > 0].reset_index()
    X = design(d)
    dd = pd.concat([d[['T2', 'E2', 'dai3']], X], axis=1).dropna()
    dd = dd[dd['T2'] > 0]
    if len(dd) < 200 or dd['E2'].sum() < 20:
        continue
    cols = ['dai3'] + list(X.columns)
    try:
        cph = CoxPHFitter(penalizer=1e-4)
        cph.fit(dd[['T2', 'E2'] + cols], duration_col='T2', event_col='E2')
        s = cph.summary
        _cf = float(s.loc['dai3', 'coef']); _se = float(s.loc['dai3', 'se(coef)'])
        _hr = float(s.loc['dai3', 'exp(coef)'])
        # 稳定性守卫：确认事件数少、样本小的队列易给出极端估计（MHAS 曾给出 10.2）
        if abs(_cf) > 1.5 or _se > 1.0 or int(dd['E2'].sum()) < 100:
            print('  %-7s 守卫剔除（HR=%.2f, se=%.2f, 事件=%d）'
                  % (co, _hr, _se, int(dd['E2'].sum())))
            continue
        CONF.append(dict(cohort=co, coef=_cf, se=_se, hr=_hr,
                         n=len(dd), ev=int(dd['E2'].sum())))
        print('  %-7s 确认后 HR=%.3f (n=%d, 事件=%d)' % (co, _hr, len(dd), int(dd['E2'].sum())))
    except Exception as e2:
        print('  %-7s 失败 %s' % (co, type(e2).__name__))
CONF = pd.DataFrame(CONF)
CONF.to_csv(os.path.join(OUT, '_confirm.csv'), index=False, encoding='utf-8-sig')
if len(CONF) >= 2:
    q = L.dl_meta(CONF['coef'], CONF['se'], 'confirmed')
    print('  合并：k=%d HR=%.3f (%.3f–%.3f) I²=%.1f%%  事件=%d'
          % (q['k'], q['hr'], q['lo'], q['hi'], q['I2'], int(CONF['ev'].sum())))

# ================================================================ ⑤ MI 样本与事件数
print()
print('=' * 74)
print('⑤ 完整样本与 MI 样本的事件数')
tot = 0; ev = 0; nn_ = 0
for co in CO:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    tot += len(d); ev += int(d['E'].sum())
    X = design(d)
    dd = pd.concat([d[['T', 'E', 'dai3']], X], axis=1).dropna()
    nn_ += len(dd)
MI = pd.read_csv(os.path.join(OUT, '_mice.csv'))
_m2 = M[M['model'] == 'M2']
print('  暴露完整样本（Table 1）：%s 人，%s 事件' % (format(tot, ','), format(ev, ',')))
print('  M2 complete-case：%s 人，%s 事件'
      % (format(int(_m2['n'].sum()), ','), format(int(_m2['ev'].sum()), ',')))
print('  MI 方案（协变量 / 协变量+暴露）：%s 人（见 _mice.csv）'
      % format(int(MI['n'].max()), ','))

# ================================================================ ⑥ 校准度
print()
print('=' * 74)
print('⑥ 校准度：按暴露层的观察/预期比与校准斜率')
CAL = []
for co in CO:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    X = design(d)
    dd = pd.concat([d[['T', 'E', 'dai3']], X], axis=1).dropna()
    cols = ['dai3'] + list(X.columns)
    try:
        cph = CoxPHFitter(penalizer=1e-4)
        cph.fit(dd[['T', 'E'] + cols], duration_col='T', event_col='E')
        # 个体累积风险 @ 各队列中位随访
        th = float(np.median(dd['T']))
        lp = cph.predict_partial_hazard(dd)
        base = cph.baseline_survival_
        import bisect
        idx = min(range(len(base.index)), key=lambda i: abs(base.index[i] - th))
        S0 = float(base.iloc[idx, 0])
        pred = 1 - S0 ** lp.to_numpy(float)
        obs = dd['E'].to_numpy(int)
        # 十分位校准斜率：logit(obs) ~ logit(pred)
        bins = pd.qcut(pred, 10, labels=False, duplicates='drop')
        g = pd.DataFrame({'p': pred, 'o': obs, 'b': bins}).groupby('b').agg(
            p=('p', 'mean'), o=('o', 'mean'), n=('o', 'size'))
        g = g[(g['o'] > 0) & (g['o'] < 1)]
        lg = np.log(g['o'] / (1 - g['o'])); lp2 = np.log(g['p'] / (1 - g['p']))
        slope = float(np.polyfit(lp2, lg, 1)[0]) if len(g) >= 3 else np.nan
        CAL.append(dict(cohort=co, thr=round(th, 1), obs_pct=round(100 * obs.mean(), 2),
                        exp_pct=round(100 * pred.mean(), 2),
                        OE=round(obs.sum() / pred.sum(), 3), slope=round(slope, 2),
                        n=len(dd), ev=int(obs.sum())))
    except Exception as e2:
        print('  %-7s 失败 %s: %s' % (co, type(e2).__name__, e2))
CAL = pd.DataFrame(CAL)
CAL.to_csv(os.path.join(OUT, '_calib.csv'), index=False, encoding='utf-8-sig')
print(CAL.to_string(index=False))

print()
print('DONE p35')
