# -*- coding: utf-8 -*-
"""p11_assemble.py —— 汇总所有模块结果为投稿件表格（Markdown + CSV）
Table 1 基线特征 / 2A 主模型 / 2B 分类梯度 / 3A 组分单入 / 3B 组分互调 / 3C 八类联合
Table 4A 中介三框架 / 4B 稳健性 / 4C 时距与竞争风险
Table S1 队列概览 / S2 逐级排除 / S4 缺失与插补 / S5 亚组与交互 / S6 中介逐队列
输出：out/Tables.md、out/Tables_all.csv
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS


def rd(name):
    p = os.path.join(OUT, name)
    return pd.read_csv(p) if os.path.exists(p) else None


def md(df, title, fmt='%.3f'):
    if df is None or len(df) == 0:
        return '### %s\n\n_（本轮未产出）_\n\n' % title
    d = df.copy()
    for c in d.columns:
        if d[c].dtype.kind == 'f':
            d[c] = d[c].map(lambda v: '' if pd.isna(v) else (fmt % v))
    out = '### %s\n\n| ' % title + ' | '.join(str(c) for c in d.columns) + ' |\n'
    out += '|' + '---|' * len(d.columns) + '\n'
    for _, r in d.iterrows():
        out += '| ' + ' | '.join('' if pd.isna(v) else str(v) for v in r) + ' |\n'
    return out + '\n'


T1 = rd('Table1.csv')
T2B = rd('Table2B.csv')
T3A = rd('Table3A.csv')
T3B = rd('Table3B.csv')
T3C = rd('Table3C.csv')
M1234 = rd('_m1234.csv')
POOL = rd('_pool.csv')
MED = rd('_med_cs.csv')
MEDP = rd('_med_pool.csv')
GF = rd('_gf.csv')
FGP = rd('_gf_pool.csv')
CIF = rd('_cif.csv')
LAGC = rd('_lag_cum_pool.csv')
LAGW = rd('_lag_win_pool.csv')
LOO = rd('_loo.csv')
REG = rd('_region.csv')
MREG = rd('_metareg.csv')
EV = rd('_evalue.csv')
SUB = rd('_sub.csv')
INT = rd('_int.csv')
SUBTRIM = rd('_subtrim.csv')
MICE = rd('_mice.csv')
S1 = rd('TableS1.csv')
FLOW = rd('_surv_flow.csv')
PATHA = rd('_patha.csv')
GFI = rd('_gf.csv')
ALT = rd('_alt_pool.csv')
ALTC = rd('_alt_outcomes.csv')
TSENS = rd('_tsens_pool.csv')
KAPPA = rd('_kappa.csv')
TV = rd('_tv_pool.csv')
TVc = rd('_tv.csv')
TRAJ = rd('_traj_pool.csv')
TRAJD = rd('_traj_dist.csv')
LEVEL = rd('_level.csv')
CIND = rd('_cindex.csv')
PCA = rd('_pca_pool.csv')
PCAC = rd('_pca.csv')
MISSA = rd('_miss_a.csv')
MISSB = rd('_miss_b.csv')
MISSBT = rd('_miss_b_tot.csv')
PREV = None

# 合并主模型（Table 2A）
P2A = POOL.copy() if POOL is not None else None

doc = ['# 痴呆课题重建流水线 · 投稿件表格\n',
       '> 全部数值由脚本从 `D:\\shujuku` 源数据计算，未经手工转录。',
       '> 脚本链：`p2_build_cog.py` → `p3_build_dai.py` → `p4_surv_cox.py` → `p5_tables.py` → `p6_lag_hetero.py` → `p7_mediation.py` → `p8_competing.py` → `p9_subgroup.py` → `p10_mice.py` → `p11_assemble.py`\n',
       '---\n']

doc.append(md(T1, 'Table 1 · 基线特征（按 DAI 分层）'))
doc.append(md(P2A, 'Table 2A · 主模型 M1–M4 合并（DerSimonian–Laird）'))
doc.append(md(M1234, 'Table 2A-逐队列 · 各队列 M1–M4'))
doc.append(md(T2B, 'Table 2B · 分类梯度（1、2、3 项 vs 0，各队列）'))
doc.append(md(T3A, 'Table 3A · 三个组分各自单独入模'))
doc.append(md(T3B, 'Table 3B · 三个组分互相调整'))
doc.append(md(T3C, 'Table 3C · 八类联合分类（vs 三项均无）'))
if MED is not None:
    keep = ['cohort', 'variant', 'n', 'ev', 'tot_hr', 'tot_se', 'dir_hr', 'dir_se', 'ind_hr',
            'ind_se', 'prop', 'prop_se', 'boot_ok', 'dep_hr']
    d = MED[[c for c in keep if c in MED.columns]].copy()
    d['prop'] = 100 * d['prop']
    d['prop_se'] = 100 * d['prop_se']
    doc.append(md(d, 'Table 4A · 中介（逐队列，中介比例为 %）'))
doc.append(md(MEDP, 'Table 4A-合并 · 三种识别框架的中介比例', '%.2f'))
doc.append(md(PATHA, '路径 a · 负担 → 抑郁（logistic OR）'))
doc.append(md(MICE, 'Table 4B / S4c · 缺失数据三方案'))
doc.append(md(ALT, 'Table 4B · 替代结局定义（M2 合并）'))
doc.append(md(ALTC, 'Table 4B-逐队列 · 替代结局'))
doc.append(md(TSENS, 'Table 4B · 保守截尾（末次认知评估，不向死亡年延伸）'))
doc.append(md(KAPPA, 'Table 4B/S4 · 自制判据 vs 预置已发表分类的 Cohen κ'))
doc.append(md(TV, 'Table 4C · 时变暴露（区间设计，合并）'))
doc.append(md(TVc, 'Table 4C-逐队列 · 时变暴露'))
doc.append(md(TRAJD, 'Table 4C · 暴露轨迹的发病密度（逐队列）'))
doc.append(md(TRAJ, 'Table 4C · 轨迹 HR（vs 持续低，合并）'))
doc.append(md(LEVEL, 'Table 4C · 水平 vs 变化（逐队列）'))
doc.append(md(LAGC, 'Table 4C-1 · 累积法（排除随访前 L 年）'))
doc.append(md(LAGW, 'Table 4C-2 · 期段法（按名义中点并入 2 年箱）'))
doc.append(md(GF, 'Table 4C-3 · Fine–Gray 亚分布模型（逐队列）'))
doc.append(md(FGP, 'Table 4C-3-合并 · Fine–Gray'))
if CIF is not None:
    piv = CIF.pivot_table(index='cohort', columns='level', values='cif').reset_index()
    piv.columns = ['cohort'] + ['DAI=%d' % c for c in piv.columns[1:]]
    doc.append(md(piv, 'Table 4C-4 · 累积发病率（Aalen–Johansen，τ=各库最大随访且≤10 年）'))
doc.append(md(LOO, '留一法（逐队列剔除）'))
doc.append(md(REG, '区域亚组'))
doc.append(md(MREG, '队列层面元回归'))
doc.append(md(EV, 'E-value（未测混杂敏感性）'))
doc.append(md(SUB, 'Table S5a · 亚组分层估计'))
doc.append(md(INT, 'Table S5b · 交互检验（连续尺度）'))
doc.append(md(SUBTRIM, 'Table S5c · 排除基线认知最差 10%'))
doc.append(md(CIND, 'Table S3 · 判别力（Harrell C：计数指数 vs 三组分各自）'))
doc.append(md(PCAC, 'Table S3 · PC1 加权（逐队列载荷）'))
doc.append(md(PCA, 'Table S3 · PC1 加权 M2 合并'))
doc.append(md(MISSA, 'Table S4a · 逐变量逐队列缺失率（%）'))
doc.append(md(MISSB, 'Table S4b · 有/无协变量缺失者的基线特征'))
doc.append(md(MISSBT, 'Table S4b-合计 · 缺失者 vs 完整者'))
doc.append(md(S1, 'Table S1/S2 · 队列概览与逐级排除'))
doc.append(md(FLOW, 'Table S2-原始 · 纳入链（按队列）', '%.0f'))

open(os.path.join(OUT, 'Tables.md'), 'w', encoding='utf8').write('\n'.join(doc))

# 合并为一张长表便于核对
allrows = []
for nm, df in [('Table1', T1), ('Table2A_pool', P2A), ('Table2A_cohort', M1234), ('Table2B', T2B),
               ('Table3A', T3A), ('Table3B', T3B), ('Table3C', T3C), ('Table4A', MED),
               ('Table4A_pool', MEDP), ('patha', PATHA), ('mice', MICE), ('lag_cum', LAGC),
               ('lag_win', LAGW), ('finegray', GF), ('finegray_pool', FGP), ('cif', CIF),
               ('loo', LOO), ('region', REG), ('metareg', MREG), ('evalue', EV),
               ('subgroup', SUB), ('interaction', INT), ('subtrim', SUBTRIM),
               ('alt_pool', ALT), ('alt_cohort', ALTC), ('tsens', TSENS), ('kappa', KAPPA),
               ('timevarying_pool', TV), ('timevarying_cohort', TVc),
               ('traj_pool', TRAJ), ('traj_density', TRAJD), ('level', LEVEL),
               ('cindex', CIND), ('pca_pool', PCA), ('pca_cohort', PCAC),
               ('miss_a', MISSA), ('miss_b', MISSB)]:
    if df is None:
        continue
    d = df.copy(); d.insert(0, 'table', nm)
    allrows.append(d)
pd.concat(allrows, ignore_index=True).to_csv(os.path.join(OUT, 'Tables_all.csv'),
                                             index=False, encoding='utf-8-sig')
print('Tables.md 已生成，长度', os.path.getsize(os.path.join(OUT, 'Tables.md')))
print('节数:', sum(1 for l in doc if l.startswith('### ')))
print('\nDONE')
