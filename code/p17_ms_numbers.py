# -*- coding: utf-8 -*-
"""p17_ms_numbers.py —— 生成「修订版稿件」要用的全部数字（唯一权威来源）

从 out/ 的中间产物（全部由 p2–p16 从 D:\shujuku 计算落盘）重新汇总，
并对少数尚未算过的量（ADL/IADL 单独入模、DAI 层间 SMD、区域差异检验、
轨迹合并密度、加权年龄/随访）就地补算。

输出 out/_ms_numbers.csv（key,value,src），改稿脚本与校验脚本都只认这个文件。
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
NM = {'CHARLS': 'CHARLS (China)', 'ELSA': 'ELSA (England)', 'HRS': 'HRS (USA)',
      'KLoSA': 'KLoSA (Korea)', 'MHAS': 'MHAS (Mexico)', 'SHARE': 'SHARE (Europe)'}
R = []


def put(k, v, src=''):
    R.append(dict(key=k, value=v, src=src))


# ---------------------------------------------------------------- 载入
S = {co: pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co)) for co in CO}
D = {co: pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % co)) for co in CO}
A = pd.concat([s.assign(co=co) for co, s in S.items()], ignore_index=True)
N, EV, PY = len(A), int(A['E'].sum()), float(A['T'].sum())
put('n_analytic', N, '_surv_*.parquet')
put('n_events', EV, '_surv_*.parquet')
put('person_years', int(PY), '_surv_*.parquet')

# 加权年龄 / 男性 / 随访中位与四分位
nw = A.groupby('co').size()
put('age_mean', round(float(np.average(A.groupby('co')['age'].mean(), weights=nw)), 1), 'surv')
put('male_pct', round(100 * float(np.average(A.groupby('co')['male'].mean(), weights=nw)), 1), 'surv')
t = A['T'].astype(float)
put('fu_median', int(t.median()), 'surv')
put('fu_q1', int(t.quantile(.25)), 'surv')
put('fu_q3', int(t.quantile(.75)), 'surv')
put('incidence_density', round(1000 * EV / PY, 1), 'surv')
put('event_pct', round(100 * EV / N, 1), 'surv')
put('n_cohorts', 6, '')
_FL = pd.read_csv(os.path.join(OUT, '_surv_flow.csv'))
put('baseline_resp', int(_FL['baseline_respondents'].sum()), '_surv_flow.csv')
for _, r in _FL.iterrows():
    put('flow_%s_baseline' % r['cohort'], int(r['baseline_respondents']), '_surv_flow.csv')

# 逐队列
for co in CO:
    s = S[co]
    put('cohort_n_%s' % co, len(s), '_surv')
    put('cohort_ev_%s' % co, int(s['E'].sum()), '_surv')
    put('cohort_py_%s' % co, int(s['T'].sum()), '_surv')
    put('cohort_density_%s' % co, round(1000 * s['E'].sum() / s['T'].sum(), 1), '_surv')
    put('cohort_fu_%s' % co, int(s['T'].max()), '_surv')
put('density_min', round(min(1000 * S[c]['E'].sum() / S[c]['T'].sum() for c in CO), 1), 'surv')
put('density_max', round(max(1000 * S[c]['E'].sum() / S[c]['T'].sum() for c in CO), 1), 'surv')
put('fu_longest', int(max(S[c]['T'].max() for c in CO)), 'surv')
put('fu_shortest', int(min(S[c]['T'].max() for c in CO)), 'surv')

# ---------------------------------------------------------------- DAI 分布与分层特征
vc = A['dai3'].value_counts(normalize=True).sort_index()
for lv in [0, 1, 2, 3]:
    put('dai_pct_%d' % lv, round(100 * float(vc.get(float(lv), 0)), 1), 'surv')
put('dai_mean', round(float(A['dai3'].mean()), 2), 'surv')

for lv in [0, 3]:
    g = A[A['dai3'] == lv]
    put('dai%d_age' % lv, round(float(g['age'].mean()), 1), 'surv')
    put('dai%d_nchron' % lv, round(float(g['nchron'].mean()), 1), 'surv')
    put('dai%d_lowedu_pct' % lv, round(100 * float((g['edu'] == 1).mean()), 1), 'surv')
    put('dai%d_density' % lv, round(1000 * g['E'].sum() / g['T'].sum(), 1), 'surv')


def smd(a, b, col):
    x, y = a[col].dropna().astype(float), b[col].dropna().astype(float)
    sp = np.sqrt((x.var(ddof=1) + y.var(ddof=1)) / 2)
    return float((x.mean() - y.mean()) / sp) if sp > 0 else np.nan


g0, g3 = A[A['dai3'] == 0].copy(), A[A['dai3'] == 3].copy()
g0['_lowedu'] = (g0['edu'] == 1).astype(float)
g3['_lowedu'] = (g3['edu'] == 1).astype(float)
comp_smd = float(np.nanmax([abs(smd(g3, g0, c)) for c in ['disab', 'multi', 'dep', 'nchron']]))
put('smd_component_max', round(comp_smd, 2), 'surv（组分相关变量的最大 |SMD|）')
put('smd_age', round(smd(g3, g0, 'age'), 2), 'surv')
put('smd_lowedu', round(smd(g3, g0, '_lowedu'), 2), 'surv')
put('smd_drink', round(smd(g3, g0, 'drink_now'), 2), 'surv')

# ---------------------------------------------------------------- 合并表（从 CSV 取）
P = pd.read_csv(os.path.join(OUT, '_pool.csv'))
for _, r in P.iterrows():
    m = r['label']
    put('pool_%s_hr' % m, round(r['hr'], 6), '_pool.csv')
    put('pool_%s_lo' % m, round(r['lo'], 6), '_pool.csv')
    put('pool_%s_hi' % m, round(r['hi'], 6), '_pool.csv')
    put('pool_%s_I2' % m, round(r['I2'], 1), '_pool.csv')
    put('pool_%s_tau2' % m, round(float(r['tau2']), 6), '_pool.csv')
    put('pool_%s_k' % m, int(r['k']), '_pool.csv')
put('n_m2', int(pd.read_csv(os.path.join(OUT, '_m1234.csv')).query("model=='M2'")['n'].sum()), '_m1234')
put('n_m2_events', int(pd.read_csv(os.path.join(OUT, '_m1234.csv')).query("model=='M2'")['ev'].sum()), '_m1234')
put('n_m1', int(pd.read_csv(os.path.join(OUT, '_m1234.csv')).query("model=='M1'")['n'].sum()), '_m1234')
put('n_missing_cov', int(pd.read_csv(os.path.join(OUT, '_miss_b_tot.csv'))['n_missing'].iloc[0]), '_miss_b_tot')

# 逐队列 M2
M = pd.read_csv(os.path.join(OUT, '_m1234.csv'))
for _, r in M[M['model'] == 'M2'].iterrows():
    put('m2_%s_hr' % r['cohort'], round(r['hr'], 6), '_m1234')
    put('m2_%s_lo' % r['cohort'], round(r['hr'] * np.exp(-1.96 * r['se']), 6), '_m1234')
    put('m2_%s_hi' % r['cohort'], round(r['hr'] * np.exp(1.96 * r['se']), 6), '_m1234')

# 分类梯度合并
T2B = pd.read_csv(os.path.join(OUT, 'Table2B.csv'))
for lv in [1, 2, 3]:
    g = T2B[T2B['level'] == '%d vs 0' % lv]
    p = L.dl_meta(np.log(g['hr']), g['se'])
    put('grad%d_hr' % lv, round(p['hr'], 2), 'Table2B+D​L')
    put('grad%d_lo' % lv, round(p['lo'], 2), 'Table2B+DL')
    put('grad%d_hi' % lv, round(p['hi'], 2), 'Table2B+DL')
    put('grad%d_I2' % lv, round(p['I2'], 1), 'Table2B+DL')

# Table 3A / 3B / 3C 合并
for tag, fn in [('3A', 'Table3A.csv'), ('3B', 'Table3B.csv'), ('3C', 'Table3C.csv')]:
    T = pd.read_csv(os.path.join(OUT, fn))
    for lv, g in T.groupby('component' if tag != '3C' else 'category'):
        p = L.dl_meta(np.log(g['hr'].astype(float)), g['se'].astype(float))
        key = lv.replace(' ', '_')
        put('t%s_%s_hr' % (tag, key), round(p['hr'], 2), fn + '+DL')
        put('t%s_%s_lo' % (tag, key), round(p['lo'], 2), fn + '+DL')
        put('t%s_%s_hi' % (tag, key), round(p['hi'], 2), fn + '+DL')
        put('t%s_%s_k' % (tag, key), int(p['k']), fn + '+DL')
        put('t%s_%s_I2' % (tag, key), round(p['I2'], 1), fn + '+DL')

# ADL / IADL 单独入模（就地补算）
print('补算 ADL / IADL 单独入模 ...')
for col, lab in [('disab_adl', 'adl_only'), ('disab_iadl', 'iadl_only')]:
    b, s2 = [], []
    for co in CO:
        d = S[co].copy()
        d['_x'] = d[col].astype(float)
        X = L.design_frame(d)
        dd = pd.concat([d[['T', 'E', '_x']], X], axis=1).dropna()
        if len(dd) < 100 or dd['E'].sum() < 20:
            continue
        r = L.cox(dd, 'T', 'E', ['_x'] + list(X.columns), penalizer=1e-4)
        if r is None:
            continue
        b.append(float(np.log(r[0]['_x']))); s2.append(float(r[1]['_x']))
    if len(b) >= 2:
        p = L.dl_meta(np.array(b), np.array(s2))
        put('%s_hr' % lab, round(p['hr'], 2), 'p17 就地补算')
        put('%s_lo' % lab, round(p['lo'], 2), 'p17')
        put('%s_hi' % lab, round(p['hi'], 2), 'p17')
        put('%s_k' % lab, int(p['k']), 'p17')

# ---------------------------------------------------------------- 时距
LC = pd.read_csv(os.path.join(OUT, '_lag_cum_pool.csv'))
LW = pd.read_csv(os.path.join(OUT, '_lag_win_pool.csv'))
for _, r in LC.iterrows():
    Lg = int(r['Lag'])
    if Lg in (0, 2, 12):
        put('lag%d_hr' % Lg, round(r['hr'], 2), '_lag_cum_pool')
        put('lag%d_lo' % Lg, round(r['lo'], 2), '_lag_cum_pool')
        put('lag%d_hi' % Lg, round(r['hi'], 2), '_lag_cum_pool')
        put('lag%d_I2' % Lg, round(r['I2'], 1), '_lag_cum_pool')
for _, r in LW.iterrows():
    b0 = int(r['bin_from'])
    put('win%d_hr' % b0, round(r['hr'], 2), '_lag_win_pool')
    put('win%d_lo' % b0, round(r['lo'], 2), '_lag_win_pool')
    put('win%d_hi' % b0, round(r['hi'], 2), '_lag_win_pool')
    put('win%d_I2' % b0, round(r['I2'], 1), '_lag_win_pool')
    put('win%d_k' % b0, int(r['k']), '_lag_win_pool')


def trend(df, xcol):
    """WLS：logHR ~ x，权重 1/se²（与 p6_lag_hetero.trend 同一口径）。"""
    d = df[[xcol, 'coef', 'se']].dropna()
    w = 1.0 / d['se'].astype(float) ** 2
    A = np.vstack([np.ones(len(d)), d[xcol].astype(float).values]).T
    W = np.diag(w.values)
    beta = np.linalg.solve(A.T @ W @ A, A.T @ W @ d['coef'].astype(float).values)
    resid = d['coef'].astype(float).values - A @ beta
    s2 = (w.values * resid ** 2).sum() / max(len(d) - 2, 1)
    cov = s2 * np.linalg.inv(A.T @ W @ A)
    se = np.sqrt(np.diag(cov))
    from scipy import stats
    tt = beta[1] / se[1]
    pp = 2 * (1 - stats.t.cdf(abs(tt), len(d) - 2))
    return beta[1], se[1], pp


_, _, pc = trend(LC, 'Lag')
_, _, pw = trend(LW, 'bin_from')
put('trend_p_cum', round(float(pc), 6), '_lag_cum_pool 加权回归')
put('trend_p_win', round(float(pw), 6), '_lag_win_pool 加权回归')

# ---------------------------------------------------------------- 时变 / 轨迹 / 水平
TV = pd.read_csv(os.path.join(OUT, '_tv_pool.csv'))
for _, r in TV.iterrows():
    key = {'time-varying (1 wave)': 'tv1', 'lagged (2 waves)': 'tv2',
           'cumulative mean': 'tvcum'}[r['variant']]
    put('%s_hr' % key, round(r['hr'], 2), '_tv_pool')
    put('%s_lo' % key, round(r['lo'], 2), '_tv_pool')
    put('%s_hi' % key, round(r['hi'], 2), '_tv_pool')
    put('%s_I2' % key, round(r['I2'], 1), '_tv_pool')

TR = pd.read_csv(os.path.join(OUT, '_traj_pool.csv'))
for _, r in TR.iterrows():
    key = {'incident': 'traj_inc', 'remitted': 'traj_rem',
           'persistently affected': 'traj_pers'}[r['traj']]
    put('%s_hr' % key, round(r['hr'], 2), '_traj_pool')
    put('%s_lo' % key, round(r['lo'], 2), '_traj_pool')
    put('%s_hi' % key, round(r['hi'], 2), '_traj_pool')
    put('%s_I2' % key, round(r['I2'], 1), '_traj_pool')

TD = pd.read_csv(os.path.join(OUT, '_traj_density.csv')) if os.path.exists(
    os.path.join(OUT, '_traj_density.csv')) else None

# 轨迹合并密度：由逐队列 n/ev/density 反推 py 后加总
from json import dumps
put('traj_density_note', '逐队列密度见 Tables.md Table 4C', '')
# 逐队列密度极值
try:
    tab = open(os.path.join(OUT, 'Tables.md'), encoding='utf8').read()
    import re
    seg = tab.split('暴露轨迹的发病密度')[1].split('###')[0]
    dens = {}
    for line in seg.split('\n'):
        m = re.match(r'\|\s*(\w+)\s*\|\s*([a-z ]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|', line)
        if m:
            dens.setdefault(m.group(2).strip(), []).append(float(m.group(5)))
    for k, v in dens.items():
        put('traj_density_min_%s' % k.replace(' ', '_'), round(min(v), 1), 'Tables.md')
        put('traj_density_max_%s' % k.replace(' ', '_'), round(max(v), 1), 'Tables.md')
except Exception as e:
    print('轨迹密度解析失败', e)

LV = pd.read_csv(os.path.join(OUT, '_level.csv'))
for mdl, lab in [('baseline level', 'lvl_base'), ('follow-up level', 'lvl_fu'), ('change', 'lvl_chg')]:
    g = LV[LV['model'] == mdl]
    if not len(g):
        continue
    p = L.dl_meta(np.log(g['hr'].astype(float)), g['se'].astype(float))
    put('%s_hr' % lab, round(p['hr'], 2), '_level.csv+DL')
    put('%s_lo' % lab, round(p['lo'], 2), '_level.csv+DL')
    put('%s_hi' % lab, round(p['hi'], 2), '_level.csv+DL')
    put('%s_I2' % lab, round(p['I2'], 1), '_level.csv+DL')
# 同时入模
g = LV[LV['model'] == 'baseline+follow-up']
for term, lab in [('d0', 'lvlboth_base'), ('d1', 'lvlboth_fu')]:
    q = g[g['term'] == term]
    p = L.dl_meta(np.log(q['hr'].astype(float)), q['se'].astype(float))
    put('%s_hr' % lab, round(p['hr'], 2), '_level.csv+DL')
    put('%s_lo' % lab, round(p['lo'], 2), '_level.csv+DL')
    put('%s_hi' % lab, round(p['hi'], 2), '_level.csv+DL')
# 时变模型排除者（只有一次可评估认知波 → 无法构成区间）
ex_n, ex_age, ex_dai, ex_fem, ex_fu, in_n, in_age, in_dai, in_fem, in_fu = [], [], [], [], [], [], [], [], [], []
for co in CO:
    dai = pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % co))
    cg = pd.read_parquet(os.path.join(OUT, '_cog2_%s.parquet' % co))
    dai['pid'] = dai['pid'].astype(str); cg['pid'] = cg['pid'].astype(str)
    p = dai.merge(cg[['pid', 'wave', 'dem_alg_edu']], on=['pid', 'wave'], how='inner')
    p = p[p['dai3'].notna() & p['dem_alg_edu'].notna()]
    k = p.groupby('pid').size()
    multi = set(k[k >= 2].index)
    s = S[co].copy(); s['pid'] = s['pid'].astype(str)
    s = s[s['pid'].isin(set(k.index))]
    out_ = s[~s['pid'].isin(multi)]
    inn_ = s[s['pid'].isin(multi)]
    ex_n.append(len(out_)); in_n.append(len(inn_))
    for src, acc in ((out_, (ex_age, ex_dai, ex_fem, ex_fu)), (inn_, (in_age, in_dai, in_fem, in_fu))):
        acc[0].append(src['age'].mean()); acc[1].append(src['dai3'].mean())
        acc[2].append(src['male'].mean()); acc[3].append(src['T'].mean())
TOT = sum(ex_n) + sum(in_n)
W = lambda arr, w=None: float(np.average(arr, weights=w if w is not None else ex_n if arr in (ex_age, ex_dai, ex_fem, ex_fu) else in_n))
put('tv_excluded_n', sum(ex_n), 'p17 由面板重建')
put('tv_excluded_pct', round(100 * sum(ex_n) / TOT, 1), 'p17')
put('tv_excluded_age', round(W(ex_age), 1), 'p17')
put('tv_excluded_dai', round(W(ex_dai), 2), 'p17')
put('tv_excluded_female_pct', round(100 * (1 - W(ex_fem)), 1), 'p17')
put('tv_excluded_fu', round(W(ex_fu), 1), 'p17')
put('tv_included_age', round(W(in_age), 1), 'p17')
put('tv_included_dai', round(W(in_dai), 2), 'p17')
put('tv_included_female_pct', round(100 * (1 - W(in_fem)), 1), 'p17')
put('tv_included_fu', round(W(in_fu), 1), 'p17')

# ---------------------------------------------------------------- 竞争风险
FG = pd.read_csv(os.path.join(OUT, '_fg_pool.csv')).iloc[0]
put('fg_hr', round(FG['hr'], 2), '_fg_pool')
put('fg_lo', round(FG['lo'], 2), '_fg_pool')
put('fg_hi', round(FG['hi'], 2), '_fg_pool')
CIF = pd.read_csv(os.path.join(OUT, '_cif.csv'))
piv = CIF.pivot_table(index='cohort', columns='level', values='cif')
d3 = 100 * (piv[3.0] - piv[0.0])
put('cif_dmin', round(float(d3.min()), 1), '_cif.csv')
put('cif_dmax', round(float(d3.max()), 1), '_cif.csv')
put('cif_tau_min', int(CIF['tau'].min()), '_cif.csv')
put('cif_tau_max', int(CIF['tau'].max()), '_cif.csv')

# ---------------------------------------------------------------- 留一 / 区域 / 元回归 / E
LO = pd.read_csv(os.path.join(OUT, '_loo.csv'))
put('loo_min', round(float(LO['hr'].min()), 2), '_loo.csv')
put('loo_max', round(float(LO['hr'].max()), 2), '_loo.csv')
put('loo_pmax', float(LO['p'].max()), '_loo.csv')
RE = pd.read_csv(os.path.join(OUT, '_region.csv'))
for _, r in RE.iterrows():
    k = {'East Asia': 'ea', 'Europe': 'eu', 'North America': 'na'}[r['region']]
    put('region_%s_hr' % k, round(r['hr'], 2), '_region.csv')
    put('region_%s_lo' % k, round(r['lo'], 2), '_region.csv')
    put('region_%s_hi' % k, round(r['hi'], 2), '_region.csv')
y = np.log(RE['hr'].values)
w = 1 / np.array([0.2678, 0.0189, 0.0179]) ** 2  # placeholder replaced below
# 用 region 的 CI 反推 SE
se_re = (np.log(RE['hi']) - np.log(RE['lo'])) / (2 * 1.96)
w = 1 / se_re ** 2
mu = np.sum(w * y) / np.sum(w)
Q = float(np.sum(w * (y - mu) ** 2))
from scipy import stats as st
PQ = float(1 - st.chi2.cdf(Q, len(y) - 1))
put('region_Q', round(Q, 6), '_region.csv Q 检验')
put('region_P', round(PQ, 6), '_region.csv Q 检验')

EV_ = pd.read_csv(os.path.join(OUT, '_evalue.csv'))
for _, r in EV_.iterrows():
    tag = r['estimand'].replace(' ', '_').replace('>=', 'ge')
    if tag in ('M2', 'M1', 'M4'):
        put('evalue_%s_point' % tag, round(r['E_point'], 2), '_evalue.csv')
        put('evalue_%s_ci' % tag, round(r['E_CI'], 2), '_evalue.csv')

# ---------------------------------------------------------------- 亚组 / 交互
SUB = pd.read_csv(os.path.join(OUT, '_sub.csv'))
put('sub_min_hr', round(float(SUB['hr'].min()), 2), '_sub.csv')
put('sub_n_strata', int(len(SUB)), '_sub.csv')
SD = {'Age group': {'<65': 'age_lt65', '65-74': 'age_6574', '>=75': 'age_ge75'},
      'Sex': {'0.0': 'sex_f', '1.0': 'sex_m'},
      'Education': {'1.0': 'edu_lo', '2.0': 'edu_mid', '3.0': 'edu_hi'},
      'Baseline cognition': {'low': 'cog_lo', 'high': 'cog_hi'},
      'Marital status': {'0.0': 'mar_no', '1.0': 'mar_yes'},
      'BMI': {'<25': 'bmi_lo', '25-29.9': 'bmi_mid', '>=30': 'bmi_hi'}}
for _, r in SUB.iterrows():
    k = SD.get(r['modifier'], {}).get(str(r['stratum']))
    if k:
        put('%s_hr' % k, round(r['hr'], 2), '_sub.csv')
        put('%s_lo' % k, round(r['lo'], 2), '_sub.csv')
        put('%s_hi' % k, round(r['hi'], 2), '_sub.csv')
        put('%s_I2' % k, round(r['I2'], 1), '_sub.csv')
IN = pd.read_csv(os.path.join(OUT, '_int.csv'))
IK = {'Age group': 'age', 'Sex': 'sex', 'Education': 'edu', 'Baseline cognition': 'cog',
      'Marital status': 'mar', 'BMI': 'bmi'}
for _, r in IN.iterrows():
    k = IK[r['modifier']]
    put('int_%s_hr' % k, round(r['hr_int'], 6), '_int.csv')
    put('int_%s_lo' % k, round(r['lo'], 6), '_int.csv')
    put('int_%s_hi' % k, round(r['hi'], 6), '_int.csv')
    put('int_%s_p' % k, round(r['p_int'], 6), '_int.csv')
ST = pd.read_csv(os.path.join(OUT, '_subtrim.csv')).iloc[0]
put('subtrim_hr', round(ST['hr'], 2), '_subtrim.csv')
put('subtrim_lo', round(ST['lo'], 2), '_subtrim.csv')
put('subtrim_hi', round(ST['hi'], 2), '_subtrim.csv')

# ---------------------------------------------------------------- 缺失 / MICE / 替代结局
MB = pd.read_csv(os.path.join(OUT, '_miss_b_tot.csv')).iloc[0]
for k in ['age_missing', 'age_complete', 'disab_missing', 'disab_complete',
          'ev_missing', 'ev_complete']:
    put('miss_%s' % k, round(float(MB[k]), 1), '_miss_b_tot')
put('miss_pct', round(100 * MB['n_missing'] / (MB['n_missing'] + MB['n_complete']), 1), '_miss_b_tot')
MI = pd.read_csv(os.path.join(OUT, '_mice.csv'))
for _, r in MI.iterrows():
    k = {'A complete case': 'cc', 'B impute covariates': 'mib',
         'C impute covariates+exposure': 'mic'}[r['scheme']]
    put('mice_%s_hr' % k, round(r['hr'], 6), '_mice.csv')
    put('mice_%s_lo' % k, round(r['lo'], 6), '_mice.csv')
    put('mice_%s_hi' % k, round(r['hi'], 6), '_mice.csv')
AL = pd.read_csv(os.path.join(OUT, '_alt_pool.csv'))
for _, r in AL.iterrows():
    k = r['outcome']
    put('alt_%s_hr' % k, round(r['hr'], 6), '_alt_pool')
    put('alt_%s_lo' % k, round(r['lo'], 6), '_alt_pool')
    put('alt_%s_hi' % k, round(r['hi'], 6), '_alt_pool')
    put('alt_%s_k' % k, int(r['k']), '_alt_pool')
put('alt_min', round(float(AL['hr'].min()), 2), '_alt_pool')
put('alt_max', round(float(AL['hr'].max()), 2), '_alt_pool')
TS = pd.read_csv(os.path.join(OUT, '_tsens_pool.csv')).iloc[0]
put('tsens_hr', round(TS['hr'], 6), '_tsens_pool')
put('tsens_lo', round(TS['lo'], 6), '_tsens_pool')
put('tsens_hi', round(TS['hi'], 6), '_tsens_pool')
put('tsens_I2', round(float(TS['I2']), 1), '_tsens_pool')
_TSR = pd.read_csv(os.path.join(OUT, '_tsens.csv'))
_tq = L.dl_meta(_TSR['coef'], _TSR['se'], 'tsens')
put('tsens_tau2', round(float(_tq['tau2']), 6), '_tsens.csv')
put('tsens_k', int(len(_TSR)), '_tsens.csv')
put('tsens_n', int(_TSR['n'].sum()), '_tsens.csv')
put('tsens_ev', int(_TSR['ev'].sum()), '_tsens.csv')
# 「改变随访时间的人数」必须与 Table 4D 行样本同口径（M2 完整协变量子集），否则表注出现两个分母。
# 2026-10-13 修正（外部审稿 P1）：此前用完整暴露全样本（71,867）作分母，得到 13,961/19.4 %，
# 而 Table 4D 各行实际估计在 66,765 人上；同一表注并列两个分母构成歧义。现与 p12.fitM2 同一
# dropna 口径（[T, E, dai3] + design_frame 列）复算，并断言分母 == 保守截尾分析样本（_tsens.csv）。
_ch = _tot = 0
for _co in L.COHORTS:
    _d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % _co))
    _X = L.design_frame(_d)
    _dd = pd.concat([_d[['T', 'E', 'dai3']], _X], axis=1)
    _d = _d[_dd.notna().all(axis=1)]          # M2 完整协变量子集（与 p12.fitM2 同口径）
    _ch += int((_d['T'] > _d['T_sens'] + 1e-9).sum())
    _tot += int(len(_d))
assert _tot == int(_TSR['n'].sum()), \
    'Table 4D 分母 %d 与保守截尾分析样本 %d 不一致（口径漂移）' % (_tot, int(_TSR['n'].sum()))
put('tsens_changed_n', _ch, '_surv_*.parquet M2 完整协变量子集现算')
put('tsens_changed_pct', round(100.0 * _ch / _tot, 1), '_surv_*.parquet M2 完整协变量子集现算')
put('tsens_total_n', _tot, '_surv_*.parquet M2 完整协变量子集现算')

# ---------------------------------------------------------------- 判别力 / PC1 / κ
CI = pd.read_csv(os.path.join(OUT, '_cindex.csv'))
put('c_dai', round(float(np.average(CI['C_dai'], weights=CI['ev'])), 6), '_cindex.csv 事件加权')
put('c_comp', round(float(np.average(CI['C_components'], weights=CI['ev'])), 6), '_cindex.csv')
put('c_delta', round(float(np.average(CI['delta'], weights=CI['ev'])), 6), '_cindex.csv')
# ΔC 的配对自助区间（p14）：用于"计数指数不损失判别力"的非劣效性陈述
_CBP = os.path.join(OUT, '_cindex_boot_pool.csv')
if os.path.exists(_CBP):
    _cb = pd.read_csv(_CBP).iloc[0]
    put('dc_boot', round(float(_cb['dC']), 4), '_cindex_boot_pool.csv')
    put('dc_boot_lo', round(float(_cb['lo']), 4), '_cindex_boot_pool.csv')
    put('dc_boot_hi', round(float(_cb['hi']), 4), '_cindex_boot_pool.csv')
    put('dc_boot_k', int(_cb['k']), '_cindex_boot_pool.csv')
    put('dc_boot_I2', round(float(_cb['I2']), 1), '_cindex_boot_pool.csv')
    put('dc_margin', float(_cb['ninferiority_margin']), '_cindex_boot_pool.csv')
    put('dc_within_margin', 'yes' if bool(_cb['within_margin']) else 'no',
        '_cindex_boot_pool.csv')
_M4 = pd.read_csv(os.path.join(OUT, '_m1234.csv'))
for _m in ['M1', 'M2', 'M3', 'M4']:
    _g = _M4[_M4['model'] == _m]
    if len(_g):
        put('n_%s' % _m.lower(), int(_g['n'].sum()), '_m1234.csv 求和')
        put('ev_%s' % _m.lower(), int(_g['ev'].sum()), '_m1234.csv 求和')
        put('k_%s' % _m.lower(), int(len(_g)), '_m1234.csv 计数')

PC = pd.read_csv(os.path.join(OUT, '_pca_pool.csv')).iloc[0]
put('pc1_hr', round(PC['hr'], 2), '_pca_pool')
put('pc1_lo', round(PC['lo'], 2), '_pca_pool')
put('pc1_hi', round(PC['hi'], 2), '_pca_pool')
put('pc1_I2', round(PC['I2'], 1), '_pca_pool')
put('pc1_load_disab', round(PC['load_disab'], 2), '_pca_pool')
put('pc1_load_multi', round(PC['load_multi'], 2), '_pca_pool')
put('pc1_load_dep', round(PC['load_dep'], 2), '_pca_pool')
put('pc1_var', round(100 * PC['var_explained'], 1), '_pca_pool')
KA = pd.read_csv(os.path.join(OUT, '_kappa.csv'))
put('kappa_min', round(float(KA['kappa'].min()), 2), '_kappa.csv')
put('kappa_max', round(float(KA['kappa'].max()), 2), '_kappa.csv')
for _, r in KA.iterrows():
    put('kappa_%s' % r['cohort'], round(r['kappa'], 6), '_kappa.csv')

# ---------------------------------------------------------------- 中介
MD = pd.read_csv(os.path.join(OUT, '_med_pool.csv'))
for _, r in MD.iterrows():
    t = {'cross-sectional': 'cs', 'temporal': 'tp', 'counterfactual': 'cf'}[r['framework']]
    e = {'total HR': 'tot', 'direct HR': 'dir', 'indirect HR': 'ind',
         'mediated %': 'pct', 'ratio of pooled (indirect/total)': 'ratio'}[r['estimand']]
    put('med_%s_%s' % (t, e), round(r['value'], 2) if e != 'pct' else round(r['value'], 1), '_med_pool')
    if pd.notna(r['lo']):
        put('med_%s_%s_lo' % (t, e), round(r['lo'], 2) if e != 'pct' else round(r['lo'], 1), '_med_pool')
        put('med_%s_%s_hi' % (t, e), round(r['hi'], 2) if e != 'pct' else round(r['hi'], 1), '_med_pool')
_mp = MD[MD.estimand == 'mediated %']['value'].astype(float)
put('med_pct_min', round(float(_mp.min()), 1), '_med_pool')
put('med_pct_max', round(float(_mp.max()), 1), '_med_pool')
_rp = MD[MD.estimand.str.startswith('ratio')]['value'].astype(float)
put('med_ratio_min', round(float(_rp.min()), 1), '_med_pool')
put('med_ratio_max', round(float(_rp.max()), 1), '_med_pool')

PA = pd.read_csv(os.path.join(OUT, '_patha.csv'))
pp = L.dl_meta(np.log(PA['or_'].astype(float)),
               ((np.log(PA['hi']) - np.log(PA['lo'])) / (2 * 1.96)).astype(float))
put('patha_hr', round(pp['hr'], 2), '_patha.csv+DL')
put('patha_lo', round(pp['lo'], 2), '_patha.csv+DL')
put('patha_hi', round(pp['hi'], 2), '_patha.csv+DL')

# 时序口径的路径 a（w0 的 dm2 → **w1** 的抑郁）：稿件里"wave 0 → wave 1"的表述必须用这一组
PAT = os.path.join(OUT, '_patha_tv.csv')
if os.path.exists(PAT):
    PT = pd.read_csv(PAT)
    _pt = L.dl_meta(np.log(PT['or_'].astype(float)),
                    ((np.log(PT['hi']) - np.log(PT['lo'])) / (2 * 1.96)).astype(float))
    put('patha_tv_hr', round(_pt['hr'], 2), '_patha_tv.csv+DL')
    put('patha_tv_lo', round(_pt['lo'], 2), '_patha_tv.csv+DL')
    put('patha_tv_hi', round(_pt['hi'], 2), '_patha_tv.csv+DL')
    put('patha_tv_I2', round(_pt['I2'], 1), '_patha_tv.csv+DL')
    put('patha_tv_k', int(_pt['k']), '_patha_tv.csv+DL')

GF = pd.read_csv(os.path.join(OUT, '_gf.csv'))
# 注意：_gf.csv 的 Y10/Y01 是 E[Y(x,M(x'))] 组合量（用于分解）；
#       细胞风险 R10/R01（「有负担无抑郁」「有抑郁无负担」）须用 _gf_cells.csv
_GCELL = pd.read_csv(os.path.join(OUT, '_gf_cells.csv')) if os.path.exists(
    os.path.join(OUT, '_gf_cells.csv')) else None
if _GCELL is not None:
    put('cf_risk_none', round(100 * float(_GCELL['Y00'].mean()), 2), '_gf_cells.csv')
    put('cf_risk_burden', round(100 * float(_GCELL['Y10'].mean()), 2), '_gf_cells.csv')
    put('cf_risk_dep', round(100 * float(_GCELL['Y01'].mean()), 2), '_gf_cells.csv')
    put('cf_risk_both', round(100 * float(_GCELL['Y11'].mean()), 2), '_gf_cells.csv')
    put('cf_risk_none_min', round(100 * float(_GCELL['Y00'].min()), 1), '_gf_cells.csv')
    put('cf_risk_none_max', round(100 * float(_GCELL['Y00'].max()), 1), '_gf_cells.csv')
    put('cf_risk_both_min', round(100 * float(_GCELL['Y11'].min()), 1), '_gf_cells.csv')
    put('cf_risk_both_max', round(100 * float(_GCELL['Y11'].max()), 1), '_gf_cells.csv')
    put('cf_joint_rr', round(float(_GCELL['Y11'].mean()) / float(_GCELL['Y00'].mean()), 2), '_gf_cells.csv')
else:
    put('cf_risk_none', round(100 * float(GF['Y00'].mean()), 2), '_gf.csv')
    put('cf_risk_burden', round(100 * float(GF['Y01'].mean()), 2), '_gf.csv')
    put('cf_risk_dep', round(100 * float(GF['Y10'].mean()), 2), '_gf.csv')
    put('cf_risk_both', round(100 * float(GF['Y11'].mean()), 2), '_gf.csv')
    put('cf_joint_rr', round(float(GF['Y11'].mean()) / float(GF['Y00'].mean()), 2), '_gf.csv')
put('cf_beta_te', round(100 * float(GF['TE'].mean()), 6), '_gf.csv')
put('cf_beta_nde', round(100 * float(GF['NDE'].mean()), 6), '_gf.csv')
put('cf_beta_nie', round(100 * float(GF['NIE'].mean()), 6), '_gf.csv')
put('cf_beta_te_frac', round(float(GF['TE'].mean()), 6), '_gf.csv')
put('cf_beta_nde_frac', round(float(GF['NDE'].mean()), 6), '_gf.csv')
put('cf_beta_nie_frac', round(float(GF['NIE'].mean()), 6), '_gf.csv')
put('cf_ratio', round(100 * (1 - float(GF['NDE'].mean()) / float(GF['TE'].mean())), 1), '_gf.csv 比值口径')
put('cf_k', int(len(GF)), '_gf.csv')
# 中介比例的 I²
for _t in ['cross-sectional', 'temporal']:
    _r = MD[(MD['framework'] == _t) & (MD['estimand'] == 'mediated %')]
    if len(_r):
        put('med_%s_pct_I2' % ('cs' if _t == 'cross-sectional' else 'tp'),
            round(float(_r['I2'].iloc[0]), 1), '_med_pool')
        put('med_%s_pct_k' % ('cs' if _t == 'cross-sectional' else 'tp'),
            int(_r['k'].iloc[0]), '_med_pool')

# 中介 β（对数尺度）与反事实 β（百分点）
_V = {r['key']: r['value'] for r in R}
for t in ['cs', 'tp']:
    for part in ['tot', 'dir', 'ind']:
        _k = 'med_%s_%s' % (t, part)
        put('med_%s_beta_%s' % (t, part), round(float(np.log(float(_V[_k]))), 6), '_med_pool 取对数')

# 三综合征对比的 E-value
def evalue(hr):
    return hr + np.sqrt(hr * (hr - 1)) if hr > 1 else 1.0


put('eval_grad3_point', round(float(evalue(float(_V['grad3_hr']))), 2), 'p17 由 HR 现算')
put('eval_grad3_ci', round(float(evalue(float(_V['grad3_lo']))), 2), 'p17 由 HR CI 现算')
put('eval_grad1_point', round(float(evalue(float(_V['grad1_hr']))), 2), 'p17')
put('eval_grad2_point', round(float(evalue(float(_V['grad2_hr']))), 2), 'p17')

# BMI 缺失率（逐库）
MA = pd.read_csv(os.path.join(OUT, '_miss_a.csv'))
for _, r in MA.iterrows():
    put('miss_bmi_%s' % r['cohort'], round(float(r['bmi']), 1), '_miss_a.csv')

# ---- 中介扩展（p7b 产出）
SP = os.path.join(OUT, '_med_sens_pool.csv')
if os.path.exists(SP):
    SS = pd.read_csv(SP)
    KEY = {'two-wave washout': 'washout', 'incident depression': 'incident',
           'with interaction': 'inter', 'multimorbidity only': 'multi'}
    for _, r in SS.iterrows():
        k = KEY.get(r['spec'])
        if not k:
            continue
        put('sens_%s_pct' % k, round(float(r['pct']), 1), '_med_sens_pool')
        put('sens_%s_lo' % k, round(float(r['lo']), 1), '_med_sens_pool')
        put('sens_%s_hi' % k, round(float(r['hi']), 1), '_med_sens_pool')
        put('sens_%s_I2' % k, round(float(r['I2']), 1), '_med_sens_pool')
FA = os.path.join(OUT, '_med_4way.csv')
if os.path.exists(FA):
    F = pd.read_csv(FA).iloc[0]
    put('fway_te', round(float(F['TE']), 6), '_med_4way')
    put('fway_cde', round(float(F['CDE']), 6), '_med_4way')
    put('fway_intref', round(float(F['INT_ref']), 6), '_med_4way')
    put('fway_intmed', round(float(F['INT_med']), 6), '_med_4way')
    put('fway_pie', round(float(F['PIE']), 6), '_med_4way')
    put('fway_nie', round(float(F['NIE']), 6), '_med_4way')
    put('fway_pie_share', round(float(F['PIE']) / float(F['NIE']), 6), '_med_4way')
    put('fway_pie_pp', round(100 * float(F['PIE']), 6), '_med_4way')
    put('fway_nie_pp', round(100 * float(F['NIE']), 6), '_med_4way')
    put('fway_prop_pie', round(100 * float(F['prop_PIE']), 1), '_med_4way')
FC = os.path.join(OUT, '_gf_cells.csv')
if os.path.exists(FC):
    C = pd.read_csv(FC)
    rr10 = C['Y10'] / C['Y00']; rr01 = C['Y01'] / C['Y00']; rr11 = C['Y11'] / C['Y00']
    reri = rr11 - rr10 - rr01 + 1
    ap = reri / rr11
    syn = (rr11 - 1) / ((rr10 - 1) + (rr01 - 1))
    mult = rr11 / (rr10 * rr01)
    for nm, arr in [('reri', reri), ('ap', ap), ('s', syn), ('mult', mult)]:
        put('%s_mean' % nm, round(float(arr.mean()), 6), '_gf_cells.csv')
        put('%s_min' % nm, round(float(arr.min()), 6), '_gf_cells.csv')
        put('%s_max' % nm, round(float(arr.max()), 6), '_gf_cells.csv')
    put('ap_pct_mean', round(100 * float(ap.mean()), 1), '_gf_cells.csv')
    put('ap_pct_min', round(100 * float(ap.min()), 1), '_gf_cells.csv')
    put('ap_pct_max', round(100 * float(ap.max()), 1), '_gf_cells.csv')
    put('cf_burden_delta', round(100 * (float(C['Y10'].mean()) - float(C['Y00'].mean())), 2), '_gf_cells.csv')
    put('cf_dep_delta', round(100 * (float(C['Y01'].mean()) - float(C['Y00'].mean())), 2), '_gf_cells.csv')
    put('cf_delta_ratio',
        round((float(C['Y01'].mean()) - float(C['Y00'].mean())) /
              (float(C['Y10'].mean()) - float(C['Y00'].mean())), 1), '_gf_cells.csv 现算')

_MI = pd.read_csv(os.path.join(OUT, '_mice.csv'))
put('mice_maxdiff', round(float(_MI['hr'].max() - _MI['hr'].min()), 6), '_mice.csv 现算')

_MP = pd.read_csv(os.path.join(OUT, '_med_cs.csv'))
put('med_min_logtot', round(float(np.log(_MP['tot_hr'].astype(float)).abs().min()), 6), '_med_cs.csv')
put('med_min_logtot_cohort', _MP.loc[int(np.log(_MP['tot_hr'].astype(float)).abs().idxmin()), 'cohort'],
    '_med_cs.csv')

# ================================================================ 2026-10-13 审稿响应补充分析
# 数据来源：p33_supp_fixes.py（A/C/D/E/F/G）与 p34_timevar_cluster.py（B）。
# 一律从落盘 CSV 重算，不在本脚本手写数字。
def _dl(fn, filt, tag):
    fp = os.path.join(OUT, fn)
    if not os.path.exists(fp):
        return None
    d = pd.read_csv(fp)
    for k, v in filt.items():
        d = d[d[k].astype(str) == str(v)]
    if len(d) < 2:
        return None
    return L.dl_meta(d['coef'], d['se'], tag)


def _putq(prefix, q, src):
    if not q:
        return
    put(prefix + '_hr', round(float(q['hr']), 6), src)
    put(prefix + '_lo', round(float(q['lo']), 6), src)
    put(prefix + '_hi', round(float(q['hi']), 6), src)
    put(prefix + '_I2', round(float(q['I2']), 1), src)
    put(prefix + '_k', int(q['k']), src)


# ---- A 基线认知调整
_AF = os.path.join(OUT, '_cogadj.csv')
if os.path.exists(_AF):
    _A = pd.read_csv(_AF)
    _putq('cogadjq', _dl('_cogadj.csv', {'model': 'M2+cog_quartiles'}, 'cogq'), '_cogadj.csv')
    _putq('cogadjc', _dl('_cogadj.csv', {'model': 'M2+cogz_edu'}, 'cogc'), '_cogadj.csv')
    _RAW = pd.read_csv(os.path.join(OUT, '_cogadj_raw.csv'))
    _dropped = _RAW[(_RAW['model'] == 'M2+cogz_edu') & (~_RAW['kept'].astype(bool))]
    put('cogadj_dropped_n', int(len(_dropped)), '_cogadj_raw.csv')
    _bad = pd.read_csv(os.path.join(OUT, '_cogadj_raw.csv'))
    _b = _bad[(~_bad['kept'].astype(bool)) & (_bad['raw'].notna())]
    if len(_b):
        put('cogadj_unstable_n', int(len(_b)), '_cogadj_raw.csv')
        _m = _bad[_bad['cohort'] == 'MHAS'].set_index('model')['raw']
        for _k, _mk in [('sep_a', 'M2+cogz_edu'), ('sep_b', 'M2+cogz'), ('sep_c', 'M2+cogz_edu+cogz')]:
            if _mk in _m.index:
                put('cogadj_%s' % _k, round(float(_m.loc[_mk]), 1), '_cogadj_raw.csv')
        if 'M2+cog_quartiles' in _m.index:
            put('cogadj_quartile_mhas', round(float(_m.loc['M2+cog_quartiles']), 2), '_cogadj_raw.csv')
    put('cogadj_dropped_cohort', ','.join(_dropped['cohort'].tolist()) or 'none',
        '_cogadj_raw.csv')
    # 衰减幅度：以本表内 M2 行为参照（log 尺度）
    _m2r = _A[_A['model'] == 'M2']
    _cqq = _dl('_cogadj.csv', {'model': 'M2+cog_quartiles'}, 'cogq')
    if len(_m2r) >= 2 and _cqq:
        _m2q = L.dl_meta(_m2r['coef'], _m2r['se'], 'M2ref')
        if _m2q and _m2q['hr'] > 1:
            put('cogadjq_atten_pct',
                round(100 * (1 - np.log(float(_cqq['hr'])) / np.log(float(_m2q['hr']))), 1),
                '_cogadj.csv 现算')

# ---- C 死亡风险
_DK = {'Continuous DAI': 'deatha', 'All three': 'death3',
       'Multimorbidity only': 'deathmo', 'Depression only': 'deathdo',
       'Disability only': 'deathdonly', 'Multimorbidity+depression': 'deathmd',
       'Disability+depression': 'deathdd', 'Disability+multimorbidity': 'deathdm'}
if os.path.exists(os.path.join(OUT, '_death.csv')):
    for cat, key in _DK.items():
        _putq(key, _dl('_death.csv', {'cat': cat}, key), '_death.csv')
    _mo = _dl('_death.csv', {'cat': 'Multimorbidity only'}, 'mo')
    if _mo:
        put('deathmo_pct_higher', int(round(100 * (float(_mo['hr']) - 1))), '_death.csv 现算')

# ---- D NNT
_NF = os.path.join(OUT, '_nnt.csv')
if os.path.exists(_NF):
    _N = pd.read_csv(_NF)
    for lab, key in [('Both burdens vs neither', 'both'),
                     ('Non-depressive burden vs neither', 'burden'),
                     ('Depression vs neither', 'dep')]:
        r = _N[_N['contrast'] == lab]
        if len(r):
            r = r.iloc[0]
            put('nnt_%s' % key, round(float(r['NNT']), 1), '_nnt.csv')
            put('x1000_%s' % key, round(float(r['extra_per_1000']), 1), '_nnt.csv')
            put('absdiff_%s' % key, round(float(r['abs_diff_pp']), 2), '_nnt.csv')

# ---- E 等价性
if os.path.exists(os.path.join(OUT, '_equiv.csv')):
    _E = pd.read_csv(os.path.join(OUT, '_equiv.csv'))
    _L12 = _E[_E['lag'] == 12]
    if len(_L12):
        r = _L12.iloc[0]
        put('equiv_lag12_ratio', round(float(r['hr_vs_lag0']), 6), '_equiv.csv')
        put('equiv_lag12_lo', round(float(r['lo']), 6), '_equiv.csv')
        put('equiv_lag12_hi', round(float(r['hi']), 6), '_equiv.csv')
    put('equiv_all_within10', 'yes' if bool(_E['within_10pct'].all()) else 'no', '_equiv.csv')
    put('equiv_min_lo', round(float(_E['lo'].min()), 6), '_equiv.csv')
    put('equiv_max_hi', round(float(_E['hi'].max()), 6), '_equiv.csv')

# ---- F 交互 FDR
if os.path.exists(os.path.join(OUT, '_int_fdr.csv')):
    _F = pd.read_csv(os.path.join(OUT, '_int_fdr.csv'))
    for mod, key in [('Age group', 'age'), ('Marital status', 'marital'),
                     ('Sex', 'sex'), ('Education', 'edu'),
                     ('Baseline cognition', 'cog'), ('BMI', 'bmi')]:
        r = _F[_F['modifier'] == mod]
        if len(r):
            r = r.iloc[0]
            put('intq_%s' % key, round(float(r['q_BH']), 6), '_int_fdr.csv')
    put('int_nsig_bh', int(_F['sig_BH'].sum()), '_int_fdr.csv')

# ---- B 时变聚类稳健（p34）
if os.path.exists(os.path.join(OUT, '_tv_cluster.csv')):
    _TC = pd.read_csv(os.path.join(OUT, '_tv_cluster.csv'))
    for v, key in [('time-varying (1 wave)', 'tv1c'),
                   ('lagged (2 waves)', 'tv2c'),
                   ('cumulative mean', 'tvcmc')]:
        _putq(key, _dl('_tv_cluster.csv', {'variant': v, 'se_type': 'cluster'}, key), '_tv_cluster.csv')
    if os.path.exists(os.path.join(OUT, '_tv_cluster_cmp.csv')):
        _CC = pd.read_csv(os.path.join(OUT, '_tv_cluster_cmp.csv'))
        for v, key in [('time-varying (1 wave)', 'tv1'),
                       ('lagged (2 waves)', 'tv2'),
                       ('cumulative mean', 'tvcm')]:
            c = _CC[_CC['variant'] == v]
            if len(c):
                put('seratio_%s' % key, round(float(c['ratio'].median()), 6), '_tv_cluster_cmp.csv')
        put('seratio_min', round(float(_CC['ratio'].min()), 3), '_tv_cluster_cmp.csv')
        put('seratio_max', round(float(_CC['ratio'].max()), 3), '_tv_cluster_cmp.csv')
        _md = _CC.groupby('variant')['ratio'].median()
        put('seratio_med_min', round(float(_md.min()), 3), '_tv_cluster_cmp.csv')
        put('seratio_med_max', round(float(_md.max()), 3), '_tv_cluster_cmp.csv')
        put('tv_n_persons', int(_CC['n_clusters'].sum()), '_tv_cluster_cmp.csv')
        put('tv_n_rows', int(_CC['n_rows'].sum()), '_tv_cluster_cmp.csv')

# ---- H 第二轮响应分析（p35）
_FG2 = os.path.join(OUT, '_fg_cat.csv')
if os.path.exists(_FG2):
    for cat, key in [('Multimorbidity only', 'fgmo'), ('All three', 'fg3'),
                     ('Depression only', 'fgdo'), ('Disability only', 'fgdonly'),
                     ('Disability+multimorbidity', 'fgdm'),
                     ('Multimorbidity+depression', 'fgmd'),
                     ('Disability+depression', 'fgdd')]:
        _putq('fgcat_' + key, _dl('_fg_cat.csv', {'cat': cat}, key), '_fg_cat.csv')

if os.path.exists(os.path.join(OUT, '_re_sens.csv')):
    _RE = pd.read_csv(os.path.join(OUT, '_re_sens.csv'))
    for meth, key in [('DL', 'dl'), ('REML', 'reml'), ('REML + Knapp–Hartung', 'kh')]:
        r = _RE[_RE['method'] == meth]
        if len(r):
            r = r.iloc[0]
            put('re_%s_hr' % key, round(float(r['hr']), 3), '_re_sens.csv')
            put('re_%s_lo' % key, round(float(r['lo']), 3), '_re_sens.csv')
            put('re_%s_hi' % key, round(float(r['hi']), 3), '_re_sens.csv')
    _pi = _RE[_RE['method'].str.contains('prediction')]
    if len(_pi):
        _pi = _pi.iloc[0]
        put('re_pi_lo', round(float(_pi['lo']), 3), '_re_sens.csv')
        put('re_pi_hi', round(float(_pi['hi']), 3), '_re_sens.csv')

if os.path.exists(os.path.join(OUT, '_metareg2.csv')):
    _MR = pd.read_csv(os.path.join(OUT, '_metareg2.csv'))
    put('metareg_p_min', round(float(_MR['p'].min()), 3), '_metareg2.csv')
    put('metareg_p_max', round(float(_MR['p'].max()), 3), '_metareg2.csv')
    put('metareg_k', int(len(_MR)), '_metareg2.csv')

if os.path.exists(os.path.join(OUT, '_confirm.csv')):
    _CF = pd.read_csv(os.path.join(OUT, '_confirm.csv'))
    if len(_CF) >= 2:
        _q = L.dl_meta(_CF['coef'], _CF['se'], 'confirm')
        _putq('confirm', _q, '_confirm.csv')
        put('confirm_ev', int(_CF['ev'].sum()), '_confirm.csv')
        put('confirm_n', int(_CF['n'].sum()), '_confirm.csv')

if os.path.exists(os.path.join(OUT, '_calib.csv')):
    _CA = pd.read_csv(os.path.join(OUT, '_calib.csv'))
    put('calib_oe_min', round(float(_CA['OE'].min()), 2), '_calib.csv')
    put('calib_oe_max', round(float(_CA['OE'].max()), 2), '_calib.csv')
    put('calib_slope_min', round(float(_CA['slope'].min()), 2), '_calib.csv')
    put('calib_slope_max', round(float(_CA['slope'].max()), 2), '_calib.csv')

# 亚分布分类估计的最大 I²（用于正文说明分类估计不稳定）
_FGX = os.path.join(OUT, '_fg_cat.csv')
if os.path.exists(_FGX):
    _fx = pd.read_csv(_FGX)
    _i2s, _ks = [], []
    for _c in sorted(_fx['cat'].unique()):
        _g = _fx[_fx['cat'] == _c]
        if len(_g) < 2:
            continue
        _q = L.dl_meta(_g['coef'], _g['se'], _c)
        if _q:
            _i2s.append((float(_q['I2']), _c, int(_q['k']), int(_g['ev'].sum())))
            _ks.append(int(_q['k']))
    if _i2s:
        _top = max(_i2s)
        put('fgcat_maxI2', round(_top[0], 1), '_fg_cat.csv 现算')
        put('fgcat_maxI2_cat', _top[1], '_fg_cat.csv')
        put('fgcat_maxI2_k', _top[2], '_fg_cat.csv')
        put('fgcat_maxI2_ev', _top[3], '_fg_cat.csv')
        put('fgcat_k_min', int(min(_ks)), '_fg_cat.csv')
        put('fgcat_n_cat', int(len(_i2s)), '_fg_cat.csv')

# ---- G 各时距样本特征
if os.path.exists(os.path.join(OUT, '_lagspec_pool.csv')):
    _G = pd.read_csv(os.path.join(OUT, '_lagspec_pool.csv'))
    for _, r in _G.iterrows():
        lg = int(r['lag'])
        put('lag%d_n' % lg, int(r['n']), '_lagspec_pool.csv')
        put('lag%d_ev' % lg, int(r['events']), '_lagspec_pool.csv')
        put('lag%d_deaths' % lg, int(r['deaths']), '_lagspec_pool.csv')
        put('lag%d_age' % lg, round(float(r['mean_age']), 1), '_lagspec_pool.csv')
        put('lag%d_disab' % lg, round(float(r['pct_disab']), 1), '_lagspec_pool.csv')

pd.DataFrame(R).to_csv(os.path.join(OUT, '_ms_numbers.csv'), index=False, encoding='utf-8-sig')
print('写出 out/_ms_numbers.csv，共 %d 个数字' % len(R))