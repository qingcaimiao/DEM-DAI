# -*- coding: utf-8 -*-
"""dem_lib.py —— 痴呆课题分析基础库（重建版）
提供：数据读入、DerSimonian-Laird 合并（对数尺度与原始尺度）、
Cox 拟合与双惩罚自诊断 cox_stable、设计矩阵构造。
"""
import os, re, warnings
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings('ignore')
ROOT = 'D:/shujuku/'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)

FILES = {'CHARLS': 'Charls/charls.csv', 'ELSA': 'Elsa/elsa.csv', 'HRS': 'HRS/hrs.csv',
         'KLoSA': 'KLOSA/klosa.csv', 'LASI': 'LASI/lasi.csv', 'SHARE': 'SHARE/share.csv',
         'MHAS': 'mhas/mhas.csv'}
# 主分析 6 队列（LASI 单波，不进主分析）
COHORTS = ['CHARLS', 'ELSA', 'HRS', 'KLoSA', 'MHAS', 'SHARE']
ID = {'CHARLS': 'ID', 'ELSA': 'idauniqc', 'HRS': 'hhidpn', 'KLoSA': 'pid',
      'LASI': 'prim_key', 'SHARE': 'mergeid', 'MHAS': 'rahhidnp'}
# 基线波：由各库暴露与结局联合可得性决定（与留痕一致）
BASE_WAVE = {'CHARLS': 1, 'ELSA': 1, 'HRS': 5, 'KLoSA': 3, 'MHAS': 3, 'SHARE': 1, 'LASI': 1}
# 各库可用波（HRS 到 15，其 w14/15 用 cog27）
WAVES = {'CHARLS': [1, 2, 3, 4, 5], 'ELSA': [1, 2, 3, 4, 5, 6, 7, 8, 9], 'HRS': list(range(5, 16)),
         'KLoSA': [3, 4, 5, 6, 7, 8], 'MHAS': [1, 2, 3, 4, 5], 'SHARE': [1, 2, 4, 5, 6, 7, 8],
         'LASI': [1]}
# 各库波次年份（实测中位 iwy；HRS 用官方波年）
WAVE_YEAR = {
 'CHARLS': {1: 2011, 2: 2013, 3: 2015, 4: 2018, 5: 2020},
 'ELSA':   {1: 2002, 2: 2004, 3: 2006, 4: 2008, 5: 2010, 6: 2012, 7: 2014, 8: 2016, 9: 2018},
 'HRS':    {5: 2000, 6: 2002, 7: 2004, 8: 2006, 9: 2008, 10: 2010, 11: 2012, 12: 2014, 13: 2016, 14: 2018, 15: 2020},
 'KLoSA':  {3: 2010, 4: 2012, 5: 2014, 6: 2016, 7: 2018, 8: 2020},
 'MHAS':   {1: 2001, 2: 2003, 3: 2012, 4: 2015, 5: 2018},
 'SHARE':  {1: 2004, 2: 2007, 4: 2011, 5: 2013, 6: 2015, 7: 2017, 8: 2020},
 'LASI':   {1: 2018},
}

_hdr = {}


def pa(**kw):
    """并行列表长度自检：所有传入序列必须等长，否则立即 AssertionError。

    用户要求：凡是两个及以上并行索引的列表，必须 assert len(a)==len(b)，
    并同时打印变量名与系数（调用方负责打印系数）。
    """
    lens = {k: len(v) for k, v in kw.items()}
    if len(set(lens.values())) > 1:
        raise AssertionError('并行列表长度不一致: %s' % lens)
    return lens


def print_coef(names, values, tag=''):
    """打印变量名与系数，用于人工核对。"""
    pa(names=names, values=values)
    print('      [coef] %s %s' % (tag, '; '.join('%s=%.4f' % (n, v)
                                                  for n, v in zip(names, values))))


def header(co):
    if co not in _hdr:
        p = ROOT + FILES[co]
        h = open(p, encoding='utf8', errors='replace').readline().rstrip('\r\n')
        cols = [c.strip().strip('"') for c in h.split('","')]
        nms = [re.sub(r'\s*\(.*\)$', '', c).strip() for c in cols]
        _hdr[co] = (cols, nms)
    return _hdr[co]


def load(co, want, force_str=()):
    """按列名读入（自动用位置索引规避中文列名问题），全部转数值（除 force_str）。

    ⚠️ 关键：pd.read_csv(usecols=[整数...]) 会按**列位置升序**返回列，
    因此 idx 与 nam 必须同步按 index 排序，否则列名与数据静默错配。
    """
    p = ROOT + FILES[co]
    cols, nms = header(co)
    pos = {}
    for i, n in enumerate(nms):
        pos.setdefault(n, i)          # 同名取首次出现
    pairs = sorted((pos[n], n) for n in dict.fromkeys(want) if n in pos)
    idx = [i for i, _ in pairs]
    nam = [n for _, n in pairs]
    df = pd.read_csv(p, usecols=idx, dtype=str, low_memory=False,
                     encoding='utf-8', encoding_errors='replace')
    assert len(df.columns) == len(nam), (co, len(df.columns), len(nam))
    df.columns = nam
    fail = set(force_str) | {ID.get(co, '')}
    for c in df.columns:
        if c in fail:
            continue
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df


# ---------------------------------------------------------------- meta analysis
def dl_meta(est, se, label=None):
    """DerSimonian-Laird 随机效应合并（est 为对数尺度，如 logHR）。返回 dict。"""
    est = np.asarray(est, float); se = np.asarray(se, float)
    ok = np.isfinite(est) & np.isfinite(se) & (se > 0)
    est, se = est[ok], se[ok]
    k = len(est)
    if k == 0:
        return None
    w = 1.0 / se ** 2
    fe = float(np.sum(w * est) / np.sum(w))
    Q = float(np.sum(w * (est - fe) ** 2))
    dfree = k - 1
    C = float(np.sum(w) - np.sum(w ** 2) / np.sum(w))
    tau2 = max(0.0, (Q - dfree) / C) if C > 0 else 0.0
    ws = 1.0 / (se ** 2 + tau2)
    mu = float(np.sum(ws * est) / np.sum(ws))
    sem = float(np.sqrt(1.0 / np.sum(ws)))
    z = mu / sem
    I2 = max(0.0, (Q - dfree) / Q) * 100 if Q > 0 else 0.0
    qp = float(1 - stats.chi2.cdf(Q, dfree)) if dfree > 0 else np.nan
    return dict(label=label, k=k, hr=float(np.exp(mu)), lo=float(np.exp(mu - 1.96 * sem)),
                hi=float(np.exp(mu + 1.96 * sem)), p=float(2 * (1 - stats.norm.cdf(abs(z)))),
                loghr=mu, se=sem, I2=float(I2), tau2=tau2, Q=Q, Qp=qp)


def dl_meta_raw(est, se, label=None):
    """原始尺度合并（比例、风险差等不可取对数者）。"""
    est = np.asarray(est, float); se = np.asarray(se, float)
    ok = np.isfinite(est) & np.isfinite(se) & (se > 0)
    est, se = est[ok], se[ok]
    k = len(est)
    if k == 0:
        return None
    w = 1.0 / se ** 2
    fe = float(np.sum(w * est) / np.sum(w))
    Q = float(np.sum(w * (est - fe) ** 2)); dfree = k - 1
    C = float(np.sum(w) - np.sum(w ** 2) / np.sum(w))
    tau2 = max(0.0, (Q - dfree) / C) if C > 0 else 0.0
    ws = 1.0 / (se ** 2 + tau2)
    mu = float(np.sum(ws * est) / np.sum(ws)); sem = float(np.sqrt(1.0 / np.sum(ws)))
    I2 = max(0.0, (Q - dfree) / Q) * 100 if Q > 0 else 0.0
    return dict(label=label, k=k, est=mu, lo=mu - 1.96 * sem, hi=mu + 1.96 * sem,
                se=sem, I2=float(I2), tau2=tau2)


# ---------------------------------------------------------------- 设计矩阵
def design_frame(df, drop=(), extra=()):
    """统一的 M2 设计矩阵（全流程唯一实现，防各脚本口径漂移）。

    ⚠️ 关键：分类变量的哑变量必须**传播缺失**。
    若写成 `(df['edu']==2).astype(float)`，缺失会被静默编码成 0
    （= 参照组"低教育"/"从不吸烟"），导致含缺失的行不被 dropna 剔除 →
    分析样本被虚增、参照组被污染。此处用 map 保留 NaN。
    """
    def dum(col, k):
        return df[col].map(lambda v: 1.0 if (pd.notna(v) and v == k)
                           else (0.0 if pd.notna(v) else np.nan))
    X = pd.DataFrame(index=df.index)
    a = df['age'].astype(float)
    X['age_c'] = a - 65.0
    X['age2'] = X['age_c'] ** 2
    X['male'] = df['male'].astype(float)
    X['edu_2'] = dum('edu', 2)
    X['edu_3'] = dum('edu', 3)
    X['partnered'] = df['partnered'].astype(float)
    X['smoke1'] = dum('smoke3', 1)
    X['smoke2'] = dum('smoke3', 2)
    X['drink_now'] = df['drink_now'].astype(float)
    X['bmi'] = df['bmi'].astype(float)
    for e in extra:
        X[e] = df[e].astype(float)
    return X.drop(columns=[c for c in drop if c in X.columns])

def design(df, xcols, cat_cols):
    """构造设计矩阵：分类变量全哑变量（不设参照，用于无截距的 Cox）。"""
    import statsmodels.api as sm
    X = df[xcols].astype(float).copy()
    for c in cat_cols:
        d = pd.get_dummies(df[c].astype('Int64').astype(str), prefix=c, drop_first=False, dtype=float)
        X = pd.concat([X, d], axis=1)
    X = X.loc[:, X.nunique(dropna=True) > 1]
    X = X.fillna(0.0)
    return sm.add_constant(X, has_constant='add')


def cox(df, dur, event, xcols, cat_cols=(), penalizer=1e-4, return_frame=False,
        cluster_col=None):
    """Cox 比例风险；返回 (HR, se, p, n, nevent)。xcols 中不得含常数。

    cluster_col: 若给出，则按该列聚类计算稳健（sandwich）标准误。
    用于 counting-process（区间）数据——同一受试者贡献多个区间，区间之间不独立，
    必须聚类，否则 CI 偏窄。2026-10-13 加入（响应审稿意见）。
    """
    from lifelines import CoxPHFitter
    cols = list(xcols) + list(cat_cols)
    need = [dur, event] + cols + ([cluster_col] if cluster_col else [])
    d = df[need].copy()
    for c in cat_cols:
        d[c] = d[c].astype('Int64').astype(str)
    d = pd.get_dummies(d, columns=list(cat_cols), drop_first=True, dtype=float)
    d[dur] = pd.to_numeric(d[dur], errors='coerce')
    d[event] = pd.to_numeric(d[event], errors='coerce')
    d = d.dropna()
    # 去掉常数列（聚类列本身不作为协变量）
    keep = [c for c in d.columns
            if c not in (dur, event, cluster_col) and d[c].nunique() > 1]
    X = d[[dur, event] + keep + ([cluster_col] if cluster_col else [])].copy()
    if len(X) < 50 or X[event].sum() < 10:
        return None
    try:
        cph = CoxPHFitter(penalizer=penalizer)
        if cluster_col:
            cph.fit(X, duration_col=dur, event_col=event, cluster_col=cluster_col)
        else:
            cph.fit(X, duration_col=dur, event_col=event)
        s = cph.summary
        out = (s['exp(coef)'], s['se(coef)'], s['p'], len(X), int(X[event].sum()))
        return (out + (s,)) if return_frame else out
    except Exception as e:
        return None


def cox_stable(df, dur, event, xcols, cat_cols=(), tol=0.10, expo=None):
    """双惩罚自诊断：pen 1e-4 与 1e-2 各拟合一次。
    稳定性判据**只作用于暴露列**（`expo`，默认 xcols[0]）——对全部协变量设阈会把
    整库误剔除（罕见类别的哑变量天然可能出现大系数）。
    返回值与 cox(..., return_frame=True) 一致：(exp, se, p, n, ev, summary)。"""
    expo = expo or xcols[0]
    r1 = cox(df, dur, event, xcols, cat_cols, penalizer=1e-4, return_frame=True)
    if r1 is None or expo not in r1[5].index:
        return None
    s1 = r1[5]
    r2 = cox(df, dur, event, xcols, cat_cols, penalizer=1e-2, return_frame=True)
    if r2 is None or expo not in r2[5].index:
        return None
    s2 = r2[5]
    if abs(float(s1.loc[expo, 'coef']) - float(s2.loc[expo, 'coef'])) > tol:
        return None
    if abs(float(s1.loc[expo, 'coef'])) > 3 or float(s1.loc[expo, 'se(coef)']) > 2:
        return None
    return r1


def cox_multi(df, dur, event, xsets, cat_cols=(), penalizer=1e-4):
    """对多个暴露列分别单独入模，返回 {列名: (HR, se, p, n, ev)}。"""
    res = {}
    for c in xsets:
        r = cox(df, dur, event, [c], cat_cols, penalizer=penalizer)
        if r is not None:
            res[c] = r
    return res


def rng(df, c, lo=None, hi=None):
    """计数：列 c 在 [lo,hi] 闭区间内的行数（可含缺失判读）。"""
    v = df[c]
    m = v.notna()
    if lo is not None:
        m &= v >= lo
    if hi is not None:
        m &= v <= hi
    return int(m.sum())
