# -*- coding: utf-8 -*-
"""p10_mice.py —— 缺失数据：多重插补敏感性分析（Table S4c）
方案 A = 完整病例（主分析）；B = 插补协变量；C = 插补协变量 + 暴露组分
proper MICE（链式方程，m=ROUNDS 轮）：连续变量 OLS 系数后验抽样 + 残差加噪；
二分类 logit 后验抽样后 Bernoulli 抽样；预测子池含结局指示与 log(随访时间)。
队列内 Rubin 规则合并 → 队列间 DerSimonian-Laird 合并。
输出：out/_mice.csv
"""
import os, sys
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
MIMP = int(os.environ.get('MIMP', 20))
NROUND = 3

COLS = ['dai3', 'age', 'male', 'edu', 'partnered', 'smoke3', 'drink_now', 'bmi']
CONT = ['age', 'bmi']
BIN = ['male', 'partnered', 'drink_now']
CAT = ['edu', 'smoke3']


def design_X(d):
    return L.design_frame(d)


def fit_cox(d, expo='dai3'):
    X = design_X(d)
    dd = pd.concat([d[['T', 'E', expo]], X], axis=1).dropna()
    if len(dd) < 200 or dd['E'].sum() < 20:
        return None
    cols = [expo] + list(X.columns)
    for pen, drop in [(1e-4, False), (1e-4, True)]:
        c = [x for x in cols if not (drop and x == 'age2')]
        r = L.cox(dd, 'T', 'E', c, penalizer=pen, return_frame=True)
        if r is None:
            continue
        s = r[5]
        if expo not in s.index:
            continue
        b, se = float(s.loc[expo, 'coef']), float(s.loc[expo, 'se(coef)'])
        if np.isfinite(b) and np.isfinite(se) and abs(b) < 3 and 0 < se < 2:
            return b, se, len(dd)
    return None


def mice(df, vars_, m=MIMP, seed=11):
    """链式方程插补，返回 m 个完整数据集。"""
    rng = np.random.default_rng(seed)
    miss = {c: df[c].isna() for c in vars_}
    if not any(v.any() for v in miss.values()):
        return [df.copy() for _ in range(m)]
    imps = []
    # 用中位数/众数初始化
    init = df.copy()
    for c in vars_:
        if miss[c].any():
            init.loc[miss[c], c] = df[c].median() if c in CONT else df[c].mode().iloc[0]
    for mi in range(m):
        cur = init.copy()
        for _ in range(NROUND):
            for c in vars_:
                if not miss[c].any():
                    continue
                pred = [x for x in vars_ if x != c] + ['E', 'logT']
                A = cur.loc[~miss[c], pred].astype(float)
                y = cur.loc[~miss[c], c].astype(float)
                A = A.loc[:, A.nunique() > 1]
                A1 = np.column_stack([np.ones(len(A)), A.values])
                tgt = cur.loc[miss[c], pred].astype(float)[A.columns]
                T1 = np.column_stack([np.ones(len(tgt)), tgt.values])
                if c in CONT:
                    beta, *_ = np.linalg.lstsq(A1, y.values, rcond=None)
                    resid = y.values - A1 @ beta
                    s2 = resid.var(ddof=A1.shape[1])
                    cov = s2 * np.linalg.pinv(A1.T @ A1)
                    bdraw = rng.multivariate_normal(beta, cov)
                    cur.loc[miss[c], c] = T1 @ bdraw + rng.normal(0, np.sqrt(s2), T1.shape[0])
                else:
                    import statsmodels.api as sm
                    try:
                        lg = sm.Logit(y.values, A1).fit(disp=0)
                        bdraw = rng.multivariate_normal(lg.params, lg.cov_params())
                        p = 1 / (1 + np.exp(-(T1 @ bdraw)))
                        cur.loc[miss[c], c] = (rng.random(len(p)) < p).astype(float)
                    except Exception:
                        cur.loc[miss[c], c] = y.mode().iloc[0]
        imps.append(cur)
    return imps


def rubin(bs, ses, ns):
    """队列内 Rubin 规则。"""
    m = len(bs)
    q = np.mean(bs)
    u = np.mean(np.array(ses) ** 2)
    b = np.var(bs, ddof=1)
    tv = u + (1 + 1 / m) * b
    return q, np.sqrt(tv), int(np.mean(ns))


print('方案 A：完整病例（主分析，来自 p4）')
A = pd.read_csv(os.path.join(OUT, '_m1234.csv'))
A = A[A['model'] == 'M2'][['cohort', 'hr', 'se', 'n']].copy()
A['coef'] = np.log(A['hr'])
pA = L.dl_meta(A['coef'], A['se'], 'A complete case')
print('  k=%d HR=%.3f (%.3f-%.3f) I2=%.1f%%' % (pA['k'], pA['hr'], pA['lo'], pA['hi'], pA['I2']))

out = []
for scheme, extra_exp in [('B impute covariates', False), ('C impute covariates+exposure', True)]:
    ests = []
    for co in CO:
        d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co)).copy()
        vars_ = list(COLS) + (['disab', 'multi', 'dep'] if extra_exp else [])
        d['logT'] = np.log(d['T'].clip(lower=0.5))
        keep = ['T', 'E'] + vars_ + ['logT']
        base = d[keep].copy()
        if extra_exp:
            base = base.dropna(subset=['dai3']) if False else base
            base = base[base[['disab', 'multi', 'dep']].notna().any(axis=1)]
        else:
            base = base.dropna(subset=['dai3'])
        base['dai3'] = base['dai3'].astype(float)
        imps = mice(base, vars_)
        bs, ses, ns = [], [], []
        for imp in imps:
            if extra_exp:
                imp = imp.copy()
                imp['dai3'] = imp['disab'].fillna(0) + imp['multi'].fillna(0) + imp['dep'].fillna(0)
                imp.loc[imp[['disab', 'multi', 'dep']].isna().all(axis=1), 'dai3'] = np.nan
            r = fit_cox(imp)
            if r:
                bs.append(r[0]); ses.append(r[1]); ns.append(r[2])
        if len(bs) >= 5:
            q, se, n = rubin(bs, ses, ns)
            ests.append(dict(cohort=co, coef=q, se=se, n=n))
            print('  %-7s %s: HR=%.3f (%.3f-%.3f) m=%d n=%d'
                  % (co, scheme, np.exp(q), np.exp(q - 1.96 * se), np.exp(q + 1.96 * se), len(bs), n))
    if len(ests) >= 2:
        e = pd.DataFrame(ests)
        p = L.dl_meta(e['coef'], e['se'], scheme)
        print('  → 合并 %s: k=%d HR=%.3f (%.3f-%.3f) I2=%.1f%%'
              % (scheme, p['k'], p['hr'], p['lo'], p['hi'], p['I2']))
        out.append(dict(scheme=scheme, k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'], I2=p['I2'],
                        n=int(e['n'].sum())))
out.insert(0, dict(scheme='A complete case', k=pA['k'], hr=pA['hr'], lo=pA['lo'], hi=pA['hi'],
                   I2=pA['I2'], n=int(A['n'].sum())))
pd.DataFrame(out).to_csv(os.path.join(OUT, '_mice.csv'), index=False, encoding='utf-8-sig')
print('\nDONE')
