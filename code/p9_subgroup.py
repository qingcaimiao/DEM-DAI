# -*- coding: utf-8 -*-
"""p9_subgroup.py —— 亚组与交互（Table S5 / Fig 4）
6 个预设修饰变量：年龄、性别、教育、基线认知、婚姻、BMI
每个变量做两件事：① 层内拟合 dai3(M2) → 随机效应合并；② 队列内拟合 dai3×S 交互项 → 合并得 P_interaction
不可违背的口径：修饰变量若已在 M2 协变量中，则从该模型整族移除（防共线）——
  正是留痕 §14.6 记录的 lifelines penalizer=1e-4 静默返回垃圾值的触发条件。
输出：out/_sub.csv、_int.csv、_subtrim.csv
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
NAME = {c: c for c in CO}


def dcols(df, drop=()):
    return L.design_frame(df, drop=drop)


def robust(d, cols, expo):
    """四级稳健拟合，返回 (coef, se, p) 或 None。"""
    def one(pen, dd=d, cc=cols):
        r = L.cox(dd, 'T', 'E', cc, penalizer=pen, return_frame=True)
        if r is None or expo not in r[5].index:
            return None
        s = r[5]
        return float(s.loc[expo, 'coef']), float(s.loc[expo, 'se(coef)']), float(s.loc[expo, 'p'])
    v1, v2 = one(1e-4), one(1e-2)
    if v1 and v2 and abs(v1[0] - v2[0]) <= 0.10 and abs(v1[0]) < 3 and v1[1] < 2:
        return v1
    v3 = one(1e-4)
    if v3 and abs(v3[0]) < 3 and v3[1] < 2:
        return v3
    return None


# 基线认知（队列内 z 化）
cog = {}
for co in CO:
    c = pd.read_parquet(os.path.join(OUT, '_cog_%s.parquet' % co))
    c['pid'] = c['pid'].astype(str)
    bw = L.BASE_WAVE[co]
    b = c[c['wave'] == bw][['pid', 'global_z_edu']].copy()
    b['cogz'] = (b['global_z_edu'] - b['global_z_edu'].mean()) / b['global_z_edu'].std()
    cog[co] = b.set_index('pid')['cogz']

data = {}
for co in CO:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    d['pid'] = d['pid'].astype(str)
    d['cogz'] = d['pid'].map(cog[co])
    d['agegrp'] = pd.cut(d['age'], [49, 64, 74, 106], labels=['<65', '65-74', '>=75'])
    d['bmigrp'] = pd.cut(d['bmi'], [0, 24.999, 29.999, 100], labels=['<25', '25-29.9', '>=30'])
    d['coggrp'] = np.where(d['cogz'] >= d['cogz'].median(), 'high', 'low')
    data[co] = d

MODS = [('agegrp', 'Age group', ['age_c']),
        ('male', 'Sex', ['male']),
        ('edu', 'Education', ['edu_2', 'edu_3']),
        ('coggrp', 'Baseline cognition', []),
        ('partnered', 'Marital status', ['partnered']),
        ('bmigrp', 'BMI', ['bmi'])]

# 修饰变量的有序数值编码（用于交互项；分类/字符串不能直接 to_numeric）
SCODE = {'agegrp': {'<65': 0, '65-74': 1, '>=75': 2},
         'coggrp': {'low': 0, 'high': 1},
         'bmigrp': {'<25': 0, '25-29.9': 1, '>=30': 2}}

sub_rows, int_rows = [], []
for var, label, drop in MODS:
    lvls = sorted(data['CHARLS'][var].dropna().unique()) if var != 'male' else [0.0, 1.0]
    lvls = [x for x in lvls]
    for lv in lvls:
        ests = []
        for co in CO:
            d = data[co]
            s = d[d[var] == lv]
            if len(s) < 200 or s['E'].sum() < 20:
                continue
            X = dcols(s, drop)
            dd = pd.concat([s[['T', 'E', 'dai3']], X], axis=1).dropna()
            r = robust(dd, ['dai3'] + list(X.columns), 'dai3')
            if r:
                ests.append(dict(cohort=co, coef=r[0], se=r[1], n=len(dd), ev=int(dd['E'].sum())))
        if len(ests) >= 2:
            e = pd.DataFrame(ests)
            p = L.dl_meta(e['coef'], e['se'], str(lv))
            sub_rows.append(dict(modifier=label, stratum=str(lv), k=p['k'], hr=p['hr'], lo=p['lo'],
                                 hi=p['hi'], I2=p['I2'], n=int(e['n'].sum()), ev=int(e['ev'].sum())))
    # 交互
    ests = []
    for co in CO:
        d = data[co]
        if d[var].isna().all():
            continue
        xcol = '_S'
        dd = d.copy()
        # 交互用**连续尺度**（与稿件交互表口径一致）：年龄 per 10 岁、BMI per 1 kg/m²、
        # 教育 per 等级、认知 per 1 SD、性别/婚姻为二分类
        if var == 'agegrp':
            dd[xcol] = dd['age'].astype(float) / 10.0
        elif var == 'bmigrp':
            dd[xcol] = dd['bmi'].astype(float)
        elif var == 'coggrp':
            dd[xcol] = dd['cogz'].astype(float)
        elif var == 'edu':
            dd[xcol] = pd.to_numeric(dd['edu'], errors='coerce')
        elif var in SCODE:
            dd[xcol] = dd[var].astype(str).map(SCODE[var])
        else:
            dd[xcol] = pd.to_numeric(dd[var], errors='coerce')
        X = dcols(dd, drop)
        if dd[xcol].nunique() < 2:
            continue
        dd['_XS'] = dd['dai3'].astype(float) * (dd[xcol] - dd[xcol].mean())
        dd['_S'] = dd[xcol] - dd[xcol].mean()
        # 连续尺度交互**必须保留修饰变量主效应**（否则交互项被偏倚）；
        # 只剔除与之完全共线的协变量列（如 age_c 与 age/10）
        cov = ['dai3', '_XS', '_S'] + list(X.columns)
        dz = pd.concat([dd[['T', 'E', 'dai3', '_XS', '_S']], X], axis=1).dropna()
        r = robust(dz, cov, '_XS')
        if r:
            ests.append(dict(cohort=co, coef=r[0], se=r[1]))
    if len(ests) >= 2:
        e = pd.DataFrame(ests)
        p = L.dl_meta(e['coef'], e['se'], label)
        int_rows.append(dict(modifier=label, k=p['k'], hr_int=p['hr'], lo=p['lo'], hi=p['hi'],
                             I2=p['I2'], p_int=p['p']))

S = pd.DataFrame(sub_rows); I = pd.DataFrame(int_rows)
S.to_csv(os.path.join(OUT, '_sub.csv'), index=False, encoding='utf-8-sig')
I.to_csv(os.path.join(OUT, '_int.csv'), index=False, encoding='utf-8-sig')
print('亚组分层:')
print(S.to_string(index=False))
print('\n交互检验:')
print(I.to_string(index=False))

# 补充：排除基线认知最差 10%
tr = []
for co in CO:
    d = data[co]
    thr = d['cogz'].quantile(0.10)
    s = d[d['cogz'] > thr]
    X = dcols(s)
    dd = pd.concat([s[['T', 'E', 'dai3']], X], axis=1).dropna()
    r = robust(dd, ['dai3'] + list(X.columns), 'dai3')
    if r:
        tr.append(dict(cohort=co, coef=r[0], se=r[1], n=len(dd), ev=int(dd['E'].sum())))
if tr:
    e = pd.DataFrame(tr)
    p = L.dl_meta(e['coef'], e['se'], 'trim10')
    print('\n排除基线认知最差 10%%: k=%d HR=%.3f (%.3f-%.3f) I2=%.1f%% n=%d ev=%d'
          % (p['k'], p['hr'], p['lo'], p['hi'], p['I2'], e['n'].sum(), e['ev'].sum()))
    pd.DataFrame([dict(k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'], I2=p['I2'],
                       n=int(e['n'].sum()), ev=int(e['ev'].sum()))]).to_csv(
        os.path.join(OUT, '_subtrim.csv'), index=False, encoding='utf-8-sig')
print('\nDONE')
