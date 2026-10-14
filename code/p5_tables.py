# -*- coding: utf-8 -*-
"""p5_tables.py —— 由脚本从源数据生成 Table 1/2/3 与补充表 S1/S2（不手工转录数字）
输出：out/Table1.csv、out/Table2A.csv、out/Table2B.csv、out/Table3A.csv、
      out/Table3B.csv、out/Table3C.csv、out/TableS1.csv、out/TableS2.csv、out/Tables.md
"""
import os, json
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
NAME = {'CHARLS': 'CHARLS (China)', 'ELSA': 'ELSA (England)', 'HRS': 'HRS (USA)',
        'KLoSA': 'KLoSA (Korea)', 'MHAS': 'MHAS (Mexico)', 'SHARE': 'SHARE (Europe)'}

surv = {co: pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co)) for co in CO}
p4 = pd.read_csv(os.path.join(OUT, '_m1234.csv'))
pool = pd.read_csv(os.path.join(OUT, '_pool.csv'))


def ci(hr, se):
    return hr * np.exp(-1.96 * se), hr * np.exp(1.96 * se)


# ---------------------------------------------------------------- Table 1
def table1():
    rows = []
    levels = [('0', 0), ('1', 1), ('2', 2), ('3', 3)]
    for co in CO:
        d = surv[co]
        for lab, v in levels:
            s = d[d['dai3'] == v]
            if len(s) < 30:
                continue
            rows.append(dict(cohort=NAME[co], dai=lab, n=len(s),
                             age=round(s['age'].mean(), 1),
                             male=round(100 * s['male'].mean(), 1),
                             lowedu=round(100 * (s['edu'] == 1).mean(), 1),
                             partnered=round(100 * s['partnered'].mean(), 1),
                             current_smoke=round(100 * (s['smoke3'] == 2).mean(), 1),
                             drink=round(100 * s['drink_now'].mean(), 1),
                             bmi=round(s['bmi'].mean(), 1),
                             nchronic=round(s['nchron'].mean(), 2),
                             events=int(s['E'].sum()),
                             py=round(s['T'].sum(), 0),
                             inc_density=round(1000 * s['E'].sum() / max(s['T'].sum(), 1), 1)))
    T = pd.DataFrame(rows)
    T.to_csv(os.path.join(OUT, 'Table1.csv'), index=False, encoding='utf-8-sig')
    return T


# ---------------------------------------------------------------- Table 2B / 3A / 3B / 3C
def design_cols(df, drop=()):
    return L.design_frame(df, drop=drop)


def fit_expo(df, expo_col, drop=(), stable=False):
    X = design_cols(df, drop)
    d = pd.concat([df[['T', 'E', expo_col]], X], axis=1).dropna()
    if len(d) < 100 or d['E'].sum() < 20:
        return None
    cols = [expo_col] + list(X.columns)
    r = (L.cox_stable(d, 'T', 'E', cols, expo=expo_col) if stable
         else L.cox(d, 'T', 'E', cols, penalizer=1e-4, return_frame=True))
    if r is None:
        return None
    s = r[5]                      # cox(..., return_frame=True) → (exp, se, p, n, ev, summary)
    if expo_col not in s.index:
        return None
    return dict(hr=float(s.loc[expo_col, 'exp(coef)']), se=float(s.loc[expo_col, 'se(coef)']),
                p=float(s.loc[expo_col, 'p']), n=int(r[3]), ev=int(r[4]))


# Table 2A 已有（p4）；Table 2B 分类梯度
rows = []
for co in CO:
    d = surv[co].copy()
    for lv in (1, 2, 3):
        d['_x'] = (d['dai3'] == lv).astype(float)
        r = fit_expo(d, '_x')
        if r:
            rows.append(dict(cohort=NAME[co], level='%d vs 0' % lv, **r))
T2B = pd.DataFrame(rows)
T2B.to_csv(os.path.join(OUT, 'Table2B.csv'), index=False, encoding='utf-8-sig')

# Table 3A 组分单独入模 / 3B 互调 / 3C 八类联合
A, B, C = [], [], []
for co in CO:
    d = surv[co].copy()
    for c, lab in [('disab', 'Disability'), ('multi', 'Multimorbidity'), ('dep', 'Depression')]:
        r = fit_expo(d, c)
        if r:
            A.append(dict(cohort=NAME[co], component=lab, **r))
    X = d[['disab', 'multi', 'dep']].copy()
    dd = pd.concat([d[['T', 'E']], X, design_cols(d)], axis=1).dropna()
    if len(dd) >= 100:
        rest = [c for c in dd.columns if c not in ('T', 'E', 'disab', 'multi', 'dep')]
        r = L.cox(dd, 'T', 'E', ['disab', 'multi', 'dep'] + rest, penalizer=1e-4, return_frame=True)
        if r is not None:
            s = r[5]
            for c, lab in [('disab', 'Disability'), ('multi', 'Multimorbidity'), ('dep', 'Depression')]:
                if c in s.index:
                    B.append(dict(cohort=NAME[co], component=lab, hr=float(s.loc[c, 'exp(coef)']),
                                  se=float(s.loc[c, 'se(coef)']), p=float(s.loc[c, 'p']),
                                  n=int(r[3]), ev=int(r[4])))
    for mask, lab in [((0, 0, 1), 'Depression only'), ((0, 1, 0), 'Multimorbidity only'),
                      ((1, 0, 0), 'Disability only'), ((0, 1, 1), 'Multimorbidity+Depression'),
                      ((1, 0, 1), 'Disability+Depression'), ((1, 1, 0), 'Disability+Multimorbidity'),
                      ((1, 1, 1), 'All three')]:
        sel = (d['disab'] == mask[0]) & (d['multi'] == mask[1]) & (d['dep'] == mask[2])
        d['_x'] = sel.astype(float)
        r = fit_expo(d, '_x', stable=True)
        if r:
            C.append(dict(cohort=NAME[co], category=lab, **r))
pd.DataFrame(A).to_csv(os.path.join(OUT, 'Table3A.csv'), index=False, encoding='utf-8-sig')
pd.DataFrame(B).to_csv(os.path.join(OUT, 'Table3B.csv'), index=False, encoding='utf-8-sig')
pd.DataFrame(C).to_csv(os.path.join(OUT, 'Table3C.csv'), index=False, encoding='utf-8-sig')


# ---------------------------------------------------------------- 汇总表 S1 / S2 / 合并
def pool_of(df, key, level='level'):
    out = []
    for lv, s in df.groupby(level):
        if s['cohort'].nunique() < 1:
            continue
        p = L.dl_meta(np.log(s['hr']), s['se'], lv)
        if p:
            out.append(dict(level=lv, k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'], I2=p['I2'], Qp=p['Qp']))
    return pd.DataFrame(out)


P2B = pool_of(T2B, None)
P3A = pool_of(pd.DataFrame(A), None, 'component')
P3C = pool_of(pd.DataFrame(C), None, 'category')

flow = pd.read_csv(os.path.join(OUT, '_surv_flow.csv'))
INTCOLS = ('baseline_respondents', 'cog_available', 'free_of_dementia', 'age_50_105',
           'has_followup_cog', 'alive_at_baseline', 'exposure_complete', 'T_gt_0',
           'N', 'events')
S1 = pd.DataFrame([dict(cohort=NAME[co], baseline_wave=L.BASE_WAVE[co],
                        baseline_year=L.WAVE_YEAR[co][L.BASE_WAVE[co]], **{
                            k: (int(v) if k in INTCOLS else round(float(v), 2))
                            for k, v in flow[flow['cohort'] == co].iloc[0].items()
                            if k != 'cohort'})
                   for co in CO])
S1.to_csv(os.path.join(OUT, 'TableS1.csv'), index=False, encoding='utf-8-sig')

T1 = table1()

# ---------------------------------------------------------------- Markdown 汇总
def md(df, cols=None, floatfmt='%.3f'):
    if df is None or len(df) == 0:
        return '_（空）_\n'
    d = df[cols] if cols else df
    out = '| ' + ' | '.join(str(c) for c in d.columns) + ' |\n'
    out += '|' + '---|' * len(d.columns) + '\n'
    for _, r in d.iterrows():
        cells = []
        for v in r:
            if isinstance(v, float):
                cells.append(floatfmt % v)
            else:
                cells.append(str(v))
        out += '| ' + ' | '.join(cells) + ' |\n'
    return out


with open(os.path.join(OUT, 'Tables.md'), 'w', encoding='utf8') as f:
    f.write('# 重建流水线生成的表（全部由脚本从源数据计算，未手工转录）\n\n')
    f.write('> 生成自 `p5_tables.py`；与稿件声明的对撞见 `核验报告_重建结果_20261012.md`。\n\n')
    f.write('## Table 1 基线特征（按 DAI 分层）\n\n' + md(T1) + '\n')
    f.write('## Table 2A 主模型 M1–M4（各队列 + 合并）\n\n' + md(p4) + '\n')
    f.write('### 合并\n\n' + md(pool) + '\n')
    f.write('## Table 2B 分类梯度（各队列）\n\n' + md(T2B) + '\n')
    f.write('### 合并\n\n' + md(P2B) + '\n')
    f.write('## Table 3A 组分单独入模（各队列）\n\n' + md(pd.DataFrame(A)) + '\n### 合并\n\n' + md(P3A) + '\n')
    f.write('## Table 3B 组分互相调整（各队列）\n\n' + md(pd.DataFrame(B)) + '\n')
    f.write('## Table 3C 八类联合分类（各队列）\n\n' + md(pd.DataFrame(C)) + '\n### 合并\n\n' + md(P3C) + '\n')
    f.write('## Table S1 队列概览与逐级排除\n\n' + md(S1) + '\n')

print('Table 1 行数', len(T1))
print('Table 2B 合并:\n', P2B.to_string(index=False))
print('\nTable 3A 合并:\n', P3A.to_string(index=False))
print('\nTable 3C 合并:\n', P3C.to_string(index=False))
print('\nDONE')
