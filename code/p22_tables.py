# -*- coding: utf-8 -*-
"""p22_tables.py —— 生成主文 Table 1/2A/2B/3A/3B/3C/4B/4C 的真实 Word 表格对象

规则：
- 表格内容全部来自 out/*.csv（脚本产物）或本脚本就地 DL 合并/聚合结果，零手工数字
- 表格 XML 仿照文稿既有表格样式（Times New Roman, 边框 CBCDD1, 表头加粗）
- 按正文首次引用位置插入 caption + 表格；Table 4A 既有表格对象补 caption
输出：out/_tables_preview.md（人读预览）、out/_tables_check.txt（数值对撞）
"""
import os
import re
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
CN = {'CHARLS': 'CHARLS (China)', 'ELSA': 'ELSA (England)', 'HRS': 'HRS (USA)',
      'KLoSA': 'KLoSA (Korea)', 'MHAS': 'MHAS (Mexico)', 'SHARE': 'SHARE (Europe)'}
ORDER = ['CHARLS', 'ELSA', 'HRS', 'KLoSA', 'MHAS', 'SHARE']
CHK = []


def csv(name):
    return pd.read_csv(os.path.join(OUT, name))


def hr_ci(hr, lo, hi, d=2):
    return '%.*f (%.*f\u2013%.*f)' % (d, hr, d, lo, d, hi)


def hr_se(hr, se, d=2):
    lo = hr * np.exp(-1.96 * se)
    hi = hr * np.exp(1.96 * se)
    return hr_ci(hr, lo, hi, d)


def fmt_p(p):
    if p is None or not np.isfinite(p):
        return ''
    if p < 0.001:
        return '< 0.001'
    if p < 0.05:
        return '%.3f' % p
    return '%.2f' % p


def n_(x):
    return format(int(round(x)), ',')


def dl(hrs, ses):
    p = L.dl_meta(np.log(np.asarray(hrs, float)), np.asarray(ses, float))
    return p


def chk(name, got, exp, src):
    ok = abs(float(got) - float(exp)) <= max(0.006, 0.006 * abs(float(exp)))
    CHK.append('%s: got=%.4f ms=%.4f %s (%s)' % (name, got, exp, 'OK' if ok else 'MISMATCH', src))
    assert ok, 'MISMATCH %s: %.6f vs %.6f' % (name, got, exp)


MS = csv('_ms_numbers.csv')
MS['key'] = MS['key'].astype(str).str.replace('^\ufeff', '', regex=True)
MS['value'] = pd.to_numeric(MS['value'], errors='coerce')
V = dict(zip(MS['key'], MS['value']))

# =============================================================== 表数据构建
TABLES = []   # (key, anchor_index, caption_label, caption_text, note_text, rows)

# ---------------------------------------------------------------- Table 1
S = {c: pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % c)) for c in CO}
VARS = [('Participants, n', 'n'), ('Person-years of follow-up', 'py'),
        ('Incident dementia cases, n', 'ev'),
        ('Incidence density (per 1,000 person-years)', 'dens'),
        ('Age, years', 'age'), ('Male, %', 'male'), ('Low education, %', 'lowedu'),
        ('Partnered, %', 'partnered'), ('Current smoking, %', 'smoke'),
        ('Current drinking, %', 'drink'), ('Body mass index, kg/m\u00b2', 'bmi'),
        ('Chronic conditions, n', 'nchron')]


def aggr(d):
    return dict(n=len(d), py=float(d['T'].sum()), ev=int(d['E'].sum()),
                dens=1000 * d['E'].sum() / max(d['T'].sum(), 1),
                age=float(d['age'].mean()), male=100 * float(d['male'].mean()),
                lowedu=100 * float((d['edu'] == 1).mean()),
                partnered=100 * float(d['partnered'].mean()),
                smoke=100 * float((d['smoke3'] == 2).mean()),
                drink=100 * float(d['drink_now'].mean()),
                bmi=float(d['bmi'].mean()), nchron=float(d['nchron'].mean()))


ALL = pd.concat([S[c] for c in CO], ignore_index=True)
cols = [aggr(ALL[ALL['dai3'] == k]) for k in [0, 1, 2, 3]] + [aggr(ALL)]
DEC = {'n': 0, 'py': 0, 'ev': 0, 'dens': 1, 'age': 1, 'male': 1, 'lowedu': 1,
       'partnered': 1, 'smoke': 1, 'drink': 1, 'bmi': 1, 'nchron': 1}
t1_rows = []
for lab, k in VARS:
    vals = []
    for c in cols:
        v = c[k]
        vals.append(n_(v) if DEC[k] == 0 else '%.*f' % (DEC[k], v))
    t1_rows.append([lab] + vals)
chk('T1_age_dai0', round(cols[0]['age'], 1), V['dai0_age'], 'pooled Table1')
chk('T1_age_dai3', round(cols[3]['age'], 1), V['dai3_age'], 'pooled Table1')
chk('T1_nchron_dai0', round(cols[0]['nchron'], 1), V['dai0_nchron'], 'pooled Table1')
chk('T1_nchron_dai3', round(cols[3]['nchron'], 1), V['dai3_nchron'], 'pooled Table1')
chk('T1_lowedu_dai0', round(cols[0]['lowedu'], 1), V['dai0_lowedu_pct'], 'pooled Table1')
chk('T1_lowedu_dai3', round(cols[3]['lowedu'], 1), V['dai3_lowedu_pct'], 'pooled Table1')
chk('T1_dens_dai0', round(cols[0]['dens'], 1), V['dai0_density'], 'pooled Table1')
chk('T1_dens_dai3', round(cols[3]['dens'], 1), V['dai3_density'], 'pooled Table1')
chk('T1_total_n', float(cols[4]['n']), V['n_analytic'], 'pooled Table1')
chk('T1_total_ev', float(cols[4]['ev']), V['n_events'], 'pooled Table1')
chk('T1_total_py', float(cols[4]['py']), V['person_years'], 'pooled Table1')
# 落盘合并版 Table 1（供溯源审计，唯一来源仍是本脚本的就地聚合）
T1P = pd.DataFrame([{'characteristic': lab, 'dai0': cols[0][k], 'dai1': cols[1][k],
                     'dai2': cols[2][k], 'dai3': cols[3][k], 'all': cols[4][k]}
                    for lab, k in VARS])
T1P.to_csv(os.path.join(OUT, 'Table1_pooled.csv'), index=False, encoding='utf-8-sig')

TABLES.append(dict(
    key='T1', anchor_text='(Table 1).',
    cap='Table 1 Baseline characteristics of the 71,867 participants by number of '
        'geriatric syndromes',
    note='DAI, disability\u2013multimorbidity\u2013depression index; py, person-years. '
         'Values are means or percentages unless stated otherwise. The DAI counts how many '
         'of the three syndromes (disability, multimorbidity, depression) are present.',
    header=['Characteristic', 'DAI = 0', 'DAI = 1', 'DAI = 2', 'DAI = 3', 'All'],
    rows=t1_rows))

# ---------------------------------------------------------------- Table 2A
M = csv('_m1234.csv')
POOL = csv('_pool.csv')
t2a = [['Pooled (random effects)', '', '', '', '', '', ''],
        ['Model', 'k', 'n', 'Events', 'HR (95 % CI)', 'P', 'I\u00b2 (%)', '\u03c4\u00b2']]
for _, r in POOL.iterrows():
    # n / 事件数取自 p17 落盘的 n_<model>、ev_<model>（由 _m1234.csv 求和），保证可审计
    _lb = r['label'].lower()
    t2a.append([r['label'], int(r['k']), n_(int(float(V['n_%s' % _lb]))),
                n_(int(float(V['ev_%s' % _lb]))),
                hr_ci(r['hr'], r['lo'], r['hi']), fmt_p(r['p']), '%.1f' % r['I2'],
                '%.4f' % r['tau2']])
t2a.append(['Cohort-specific M2', '', '', '', '', '', ''])
t2a.append(['Cohort', 'n', 'Events', 'HR (95 % CI)', 'P', '', ''])
for c in ORDER:
    r = M[(M['model'] == 'M2') & (M['cohort'] == c)].iloc[0]
    t2a.append([CN[c], n_(r['n']), n_(r['ev']), hr_se(r['hr'], r['se']), fmt_p(r['p']), '', ''])
for i, m in enumerate(['M1', 'M2', 'M3', 'M4']):
    chk('T2A_%s_hr' % m, float(POOL[POOL['label'] == m]['hr'].iloc[0]), V['pool_%s_hr' % m], '_pool')
# 不变量：M1 的样本应回到完整的暴露样本；M2 为 M2 协变量完整者
_m1n = int(float(V['n_m1']))
_m2n = int(float(V['n_m2']))
assert _m1n == int(float(V['n_analytic'])), 'M1 样本 %d != 暴露完整样本 %s' % (_m1n, V['n_analytic'])
assert _m2n == int(float(V['n_m2'])), 'M2 样本 %d != 记录值 %s' % (_m2n, V['n_m2'])
TABLES.append(dict(
    key='T2A', anchor_text='(Table 2A; Fig. 2A)',
    cap='Table 2A Association between the geriatric syndrome accumulation index and '
        'incident dementia: pooled models and cohort-specific estimates',
    note='M1 unadjusted; M2 adjusted for age, age\u00b2, sex, education, marital status, '
         'smoking, alcohol use and body mass index; M3 additionally adjusted for urban\u2013rural '
         'residence; M4 additionally adjusted for grip strength and physical activity. '
         'Pooled estimates are DerSimonian\u2013Laird random-effects estimates of the hazard ratio '
         'per one additional syndrome, with \u03c4\u00b2 on the log-hazard scale. '
         'Sample size differs by model because each model contributes its own complete cases for '
         'the covariates it requires. M1 requires no covariates and therefore uses all %s '
         'participants with a complete exposure (%s events) \u2014 the same sample as Table 1 and the '
         'abstract; M2 and M3 use the %s participants (%s events) with complete M2 covariates, '
         'i.e. %s fewer participants, and M4 the %s with complete grip-strength and physical-activity '
         'data. The cohort-specific panel refers to M2.'
         % (n_(_m1n), n_(int(float(V['ev_m1']))), n_(_m2n), n_(int(float(V['ev_m2']))),
            n_(_m1n - _m2n), n_(int(float(V['n_m4'])))),
    header=None, rows=t2a, colw=[1600, 620, 1100, 1100, 1750, 900, 800, 700]))

# ---------------------------------------------------------------- Table 2B
T2B = csv('Table2B.csv')
P2B = csv('_pool_2b.csv')
t2b = [['Cohort', 'n', 'Events', '1 vs 0', '2 vs 0', '3 vs 0']]
for c in ORDER:
    r0 = M[(M['model'] == 'M2') & (M['cohort'] == c)].iloc[0]
    row = [CN[c], n_(r0['n']), n_(r0['ev'])]
    for lv in ['1 vs 0', '2 vs 0', '3 vs 0']:
        g = T2B[(T2B['level'] == lv) & (T2B['cohort'].str.startswith(c))]
        row.append(hr_se(g.iloc[0]['hr'], g.iloc[0]['se']) if len(g) else '\u2013')
    t2b.append(row)
row = ['Pooled (random effects)', '', '']
for lv in ['1 vs 0', '2 vs 0', '3 vs 0']:
    p = P2B[P2B['level'] == lv].iloc[0]
    row.append(hr_ci(p['hr'], p['lo'], p['hi']))
t2b.append(row)
t2b.append(['I\u00b2 (%), pooled', '', ''] + ['%.1f' % float(P2B[P2B['level'] == lv]['I2'].iloc[0])
                                              for lv in ['1 vs 0', '2 vs 0', '3 vs 0']])
for lv in ['1 vs 0', '2 vs 0', '3 vs 0']:
    lv_i = int(lv[0])
    chk('T2B_%d_hr' % lv_i, float(P2B[P2B['level'] == lv]['hr'].iloc[0]), V['grad%d_hr' % lv_i], '_pool_2b')
TABLES.append(dict(
    key='T2B', anchor_text='(Table 2B; Fig. 2B)',
    cap='Table 2B Categorical gradient: pooled and cohort-specific hazard ratios for one, '
        'two and three geriatric syndromes relative to none',
    note='Reference category: none of the three syndromes. Model M2 covariate set. '
         'Pooled estimates are DerSimonian\u2013Laird random-effects estimates.',
    header=None, rows=t2b, colw=[2000, 800, 900, 1450, 1450, 1450]))

# ---------------------------------------------------------------- Table 3A / 3B
def comp_table(fn, cap, note, anchor_text):
    T = csv(fn)
    rows = [['Cohort', 'n', 'Events', 'Disability', 'Multimorbidity', 'Depression']]
    for c in ORDER:
        g = T[T['cohort'].str.startswith(c)]
        if not len(g):
            continue
        r0 = g.iloc[0]
        row = [CN[c], n_(r0['n']), n_(r0['ev'])]
        for comp in ['Disability', 'Multimorbidity', 'Depression']:
            gg = g[g['component'] == comp]
            row.append(hr_se(gg.iloc[0]['hr'], gg.iloc[0]['se']) if len(gg) else '\u2013')
        rows.append(row)
    pool = csv({'_pool_3a.csv': '_pool_3a.csv', '_pool_3b.csv': '_pool_3b.csv'}[
        '_pool_3a.csv' if fn == 'Table3A.csv' else '_pool_3b.csv'])
    row = ['Pooled (random effects)', '', '']
    for comp in ['Disability', 'Multimorbidity', 'Depression']:
        p = pool[pool['component'] == comp].iloc[0]
        row.append(hr_ci(p['hr'], p['lo'], p['hi']))
    rows.append(row)
    row = ['I\u00b2 (%), pooled', '', '']
    for comp in ['Disability', 'Multimorbidity', 'Depression']:
        p = pool[pool['component'] == comp].iloc[0]
        row.append('%.1f' % p['I2'])
    rows.append(row)
    tag = '3A' if fn == 'Table3A.csv' else '3B'
    for comp in ['Disability', 'Multimorbidity', 'Depression']:
        p = pool[pool['component'] == comp].iloc[0]
        chk('T%s_%s' % (tag, comp), float(p['hr']), V['t%s_%s_hr' % (tag, comp)], fn)
    TABLES.append(dict(key='T' + tag, anchor_text=anchor_text, cap=cap, note=note, header=None,
                       rows=rows, colw=[2000, 800, 900, 1450, 1450, 1450]))
    return rows


comp_table('Table3A.csv',
           'Table 3A Each component of the index entered separately',
           'Model M2 covariate set; each component is entered on its own. Within the disability '
           'construct, ADL limitation alone gave a pooled HR of %s and IADL limitation alone %s '
           '(pooled, DerSimonian\u2013Laird random effects). Disability could not be estimated with a '
           'stable fit in MHAS and is left blank there.'
           % (hr_ci(V['adl_only_hr'], V['adl_only_lo'], V['adl_only_hi']),
              hr_ci(V['iadl_only_hr'], V['iadl_only_lo'], V['iadl_only_hi'])),
           'Entered separately, the three components')
comp_table('Table3B.csv',
           'Table 3B The three components entered simultaneously (mutually adjusted)',
           'Model M2 covariate set with all three components entered together.',
           'were entered simultaneously (Table 3B)')

# ---------------------------------------------------------------- Table 3C
T3C = csv('Table3C.csv')
P3C = csv('_pool_3c.csv')
t3c = [['Joint category', 'k', 'HR (95 % CI)', 'I\u00b2 (%)']]
for cat, lab in [('All three', 'All three syndromes'),
                 ('Disability+Depression', 'Disability + depression'),
                 ('Multimorbidity+Depression', 'Multimorbidity + depression'),
                 ('Depression only', 'Depression only'),
                 ('Disability only', 'Disability only'),
                 ('Disability+Multimorbidity', 'Disability + multimorbidity'),
                 ('Multimorbidity only', 'Multimorbidity only')]:
    p = P3C[P3C['category'] == cat].iloc[0]
    t3c.append([lab, int(p['k']), hr_ci(p['hr'], p['lo'], p['hi']), '%.1f' % p['I2']])
    VV = V['t3C_%s_hr' % cat.replace(' ', '_')]
    chk('T3C_%s' % cat, float(p['hr']), VV, '_pool_3c')
t3c.append(['None of the three (reference)', 6, '1.00 (reference)', '\u2013'])
TABLES.append(dict(
    key='T3C', anchor_text='The eight-category model made the structure explicit',
    cap='Table 3C All seven joint combinations of the three syndromes against a common '
        'reference of none',
    note='Estimates are cause-specific hazard ratios for dementia. Subdistribution hazard '
         'ratios for the same categories, which are not distorted by differential depletion '
         'through death, are given in Additional file 1: Table S14. Pooled '
         'DerSimonian\u2013Laird random-effects estimates with the M2 covariate set. k is the '
         'number of cohorts contributing to each contrast.',
    header=None, rows=t3c, colw=[3000, 700, 2400, 900]))

# ---------------------------------------------------------------- Table 4A caption only
TABLES.append(dict(key='T4A', anchor_text='Three independent identification strategies gave', cap_only=True,
                   cap='Table 4A Proportion of the effect of non-depressive burden mediated by '
                       'depression, under three independent identification frameworks',
                   note=None, header=None, rows=None))

# ---------------------------------------------------------------- Table 4B
SENS = csv('_med_sens_pool.csv')
ALT = csv('_alt_pool.csv')
AO = csv('_alt_outcomes.csv')          # 逐队列 coef/se，用于就地算 τ²
TSD = csv('_tsens_pool.csv')
t4b = [['Specification', 'k', 'Proportion mediated (95 % CI), %', 'I\u00b2 (%)']]
SENSLAB = {'two-wave washout': 'Two-wave washout of the mediator',
           'incident depression': 'Mediator restricted to incident depression',
           'with interaction': 'With exposure \u00d7 mediator interaction',
           'multimorbidity only': 'Exposure taken as multimorbidity alone'}
for key, lab in SENSLAB.items():
    r = SENS[SENS['spec'] == key].iloc[0]
    t4b.append([lab, int(r['k']), '%.1f (%.1f\u2013%.1f)' % (r['pct'], r['lo'], r['hi']),
                '%.1f' % r['I2']])
# 2026-10-13：按审稿意见拆表——4B 只保留中介敏感性，结局判定独立为 4D
# 2026-10-13 二次修订：全部行改用与主分析**完全同规则**的管线计算（同一样本、同一随访定义），
# 并补 n / 事件数 / τ²；主结局行必须与主分析 M2 逐位一致，脚本内断言。
ALTLAB = {'dem_alg_edu': 'Education-stratified criterion (primary outcome, as in Table 2A)',
          'dem_alg': 'Non-education-stratified criterion (z \u2264 \u22121.5)',
          'dem_alg25': 'Alternative 25-point rule (memory 0\u201320 plus executive 0\u20135)',
          'dem_pub': 'Classification distributed with the harmonized files'}
t4d = [['Outcome definition', 'k', 'n', 'Events', 'HR (95 % CI) per syndrome', 'I\u00b2 (%)',
        '\u03c4\u00b2']]
for key in ['dem_alg_edu', 'dem_alg', 'dem_alg25', 'dem_pub']:
    r = ALT[ALT['outcome'] == key].iloc[0]
    _ao = AO[AO['outcome'] == key]
    _qq = L.dl_meta(_ao['coef'], _ao['se'], key)
    t4d.append([ALTLAB[key], int(r['k']), n_(r['n']), n_(r['events']),
                hr_ci(r['hr'], r['lo'], r['hi']), '%.1f' % r['I2'], '%.4f' % _qq['tau2']])
# Table 4D 表注必须区分"同样本行"与"异样本行"：dem_pub 只在 3 个队列可得，n 与其余行不同。
# 2026-10-14：原表注写 "Every row is estimated on the same 66,765 participants"，与
# dem_pub 行（k=3, n=27,425）矛盾（外部审稿）。此处从 _alt_outcomes/_alt_pool 取值修正。
_r_pub = ALT[ALT['outcome'] == 'dem_pub'].iloc[0]
_k_pub, _n_pub = int(_r_pub['k']), int(_r_pub['n'])
assert _k_pub == 3 and _n_pub == 27425, 'Table 4D dem_pub 行 k/n 变动：%d/%d' % (_k_pub, _n_pub)
# 保守截尾：与主结局同一结局、不同随访规则
TS2 = csv('_tsens.csv')
_q = L.dl_meta(TS2['coef'], TS2['se'], 'tsens')
t4d.append(['Conservative censoring at the last cognitive assessment (same outcome, '
            'different follow-up rule)', int(float(V['tsens_k'])), n_(int(float(V['tsens_n']))),
            n_(int(float(V['tsens_ev']))), hr_ci(_q['hr'], _q['lo'], _q['hi']),
            '%.1f' % float(V['tsens_I2']), '%.4f' % float(V['tsens_tau2'])])
# 不变量：主结局行必须等于主分析 M2 的合并结果
_r = ALT[ALT['outcome'] == 'dem_alg_edu'].iloc[0]
_m = POOL[POOL['label'] == 'M2'].iloc[0]
assert abs(float(_r['hr']) - float(_m['hr'])) < 1e-6 and abs(float(_r['I2']) - float(_m['I2'])) < 0.05, \
    'Table 4D 主结局行与主分析 M2 不一致：%.6f/%.4f vs %.6f/%.4f' \
    % (_r['hr'], _r['I2'], _m['hr'], _m['I2'])
chk('T4D_primary_hr', float(_r['hr']), V['pool_M2_hr'], '_alt_pool vs _pool')
chk('T4D_primary_I2', float(_r['I2']), V['pool_M2_I2'], '_alt_pool vs _pool')
CHK.append('T4D_primary_n: n=%d 事件=%d  [应为 M2 的 66,765 / 10,297]'
           % (int(_r['n']), int(_r['events'])))
for key, lab in [('two-wave washout', 'tw'), ('incident depression', 'ip'),
                 ('with interaction', 'wi'), ('multimorbidity only', 'mo')]:
    r = SENS[SENS['spec'] == key].iloc[0]
    CHK.append('T4B_%s: pct=%.1f (%.1f\u2013%.1f) I2=%.1f  [Table 4B 源 _med_sens_pool.csv]'
               % (lab, r['pct'], r['lo'], r['hi'], r['I2']))
TABLES.append(dict(
    key='T4B', anchor_text='Four further specifications placed the proportion',
    cap='Table 4B Sensitivity analyses for the proportion mediated by depression',
    note='Pooled DerSimonian\u2013Laird random-effects estimates with the M2 covariate set. '
         'Mediated proportions are percentages of the total effect of non-depressive burden; each '
         'row alters one element of the mediation model, and the primary estimate is given in '
         'Table 4A.',
    header=None, rows=t4b, colw=[3200, 700, 2400, 900]))
TABLES.append(dict(
    key='T4D', anchor_text='A conservative rule censoring every participant at their last',
    cap='Table 4D Alternative definitions of the dementia outcome',
    note='Pooled DerSimonian\u2013Laird random-effects estimates of the hazard ratio per '
         'additional syndrome (M2 covariate set), with \u03c4\u00b2 on the log-hazard scale. '
         'Rows 1\u20133 and the final row are estimated on the same %s participants with a complete '
         'exposure and complete M2 covariates and under the same follow-up rule (event detection at '
         'the scheduled cognitive waves, follow-up extended to the year of death), so they differ '
         'only in the outcome definition. The classification distributed with the harmonized files '
         'was available in only %s cohorts and is therefore estimated on a different, smaller '
         'sample (%s participants), which is why its k and n differ from the other rows. The first '
         'row reproduces the primary analysis in Table 2A exactly. The final row uses the same '
         'outcome as the first but censors every participant at their last cognitive assessment '
         'instead of extending follow-up to death, so it is a sensitivity analysis on the follow-up '
         'rule rather than an alternative outcome, and the two are not duplicates: extending '
         'follow-up to the year of death changes the follow-up time of %s of these %s participants '
         '(%s %%), most of them in HRS, which is why the two rows are close but not identical. k is '
         'the number of cohorts in which the definition was available and estimable; the criteria '
         'differ in sensitivity, which is why the event counts differ between rows.'
         % (n_(int(float(V['n_m2']))), n_(_k_pub), n_(_n_pub),
            n_(int(float(V['tsens_changed_n']))), n_(int(float(V['n_m2']))),
            '%.1f' % float(V['tsens_changed_pct'])),
    header=None, rows=t4d, colw=[3000, 620, 1000, 1000, 1900, 800, 700]))

# ---------------------------------------------------------------- Table 4C
LC = csv('_lag_cum_pool.csv')
LW = csv('_lag_win_pool.csv')
TV = csv('_tv_pool.csv')
TRAJP = csv('_traj_pool.csv')
TRAJD = csv('_traj_dist_pool_summary.csv')
LP = csv('_level_pool.csv')
t4c = [['(a) Cumulative exclusion of early follow-up', 'k', 'HR (95 % CI)', 'I\u00b2 (%)']]
for _, r in LC.iterrows():
    lab = ('No exclusion (primary analysis)' if int(r['Lag']) == 0
           else 'Excluding the first %d years' % int(r['Lag']))
    t4c.append([lab, int(r['k']), hr_ci(r['hr'], r['lo'], r['hi']),
                '\u2013' if int(r['k']) < 2 else '%.1f' % r['I2']])
t4c.append(['(b) Period-specific intervals (nominal midpoints)', 'k', 'HR (95 % CI)', 'I\u00b2 (%)'])
for _, r in LW.iterrows():
    t4c.append(['%d\u2013%d years' % (int(r['bin_from']), int(r['bin_to'])), int(r['k']),
                hr_ci(r['hr'], r['lo'], r['hi']),
                '\u2013' if int(r['k']) < 2 else '%.1f' % r['I2']])
t4c.append(['(c) Interval-based time-varying exposure', 'k', 'HR (95 % CI)', 'I\u00b2 (%)'])
TVLAB = {'time-varying (1 wave)': 'Exposure one wave before outcome ascertainment',
         'lagged (2 waves)': 'Exposure two waves (4\u20136 years) before outcome ascertainment',
         'cumulative mean': 'Cumulative mean exposure to the start of the interval'}
for _, r in TV.iterrows():
    t4c.append([TVLAB[r['variant']], int(r['k']), hr_ci(r['hr'], r['lo'], r['hi']),
                '%.1f' % r['I2']])
t4c.append(['(d) Exposure trajectory (vs persistently low)', 'k', 'HR (95 % CI)', 'I\u00b2 (%)'])
TLAB = {'incident': 'Incident burden (0\u21921)', 'remitted': 'Remitted burden (1\u21920)',
        'persistently affected': 'Persistently affected (1\u21921)'}
for t in ['incident', 'remitted', 'persistently affected']:
    r = TRAJP[TRAJP['traj'] == t].iloc[0]
    t4c.append([TLAB[t], int(r['k']), hr_ci(r['hr'], r['lo'], r['hi']), '%.1f' % r['I2']])
t4c.append(['Persistently low (0\u21920, reference)', 6, '1.00 (reference)', '\u2013'])
t4c.append(['(e) Baseline level versus follow-up level', 'k', 'HR (95 % CI)', 'I\u00b2 (%)'])
LROWS = [('baseline level', 'd0', 'Baseline level, entered alone'),
         ('follow-up level', 'd1', 'Follow-up level, entered alone'),
         ('change', 'dchg', 'Change (\u0394), entered alone'),
         ('baseline+follow-up', 'd0', 'Baseline level, mutually adjusted'),
         ('baseline+follow-up', 'd1', 'Follow-up level, mutually adjusted')]
for mod, term, lab in LROWS:
    r = LP[(LP['model'] == mod) & (LP['term'] == term)].iloc[0]
    t4c.append([lab, int(r['k']), hr_ci(r['hr'], r['lo'], r['hi']), '%.1f' % r['I2']])
chk('T4C_lag0', float(LC['hr'].iloc[0]), V['lag0_hr'], '_lag_cum_pool')
chk('T4C_lag12', float(LC[LC['Lag'] == 12]['hr'].iloc[0]), V['lag12_hr'], '_lag_cum_pool')
chk('T4C_tv1', float(TV[TV['variant'] == 'time-varying (1 wave)']['hr'].iloc[0]),
    V['tv1_hr'], '_tv_pool')
chk('T4C_tv2', float(TV[TV['variant'] == 'lagged (2 waves)']['hr'].iloc[0]), V['tv2_hr'], '_tv_pool')
chk('T4C_tvcum', float(TV[TV['variant'] == 'cumulative mean']['hr'].iloc[0]), V['tvcum_hr'], '_tv_pool')
chk('T4C_traj_inc', float(TRAJP[TRAJP['traj'] == 'incident']['hr'].iloc[0]), V['traj_inc_hr'],
    '_traj_pool')
chk('T4C_traj_rem', float(TRAJP[TRAJP['traj'] == 'remitted']['hr'].iloc[0]), V['traj_rem_hr'],
    '_traj_pool')
chk('T4C_traj_pers', float(TRAJP[TRAJP['traj'] == 'persistently affected']['hr'].iloc[0]),
    V['traj_pers_hr'], '_traj_pool')
TABLES.append(dict(
    key='T4C', anchor_text='If the association were driven by pre-clinical disease',
    cap='Table 4C Reverse-causation, time-varying and trajectory analyses',
    note='All estimates are pooled DerSimonian\u2013Laird random-effects hazard ratios per one '
         'additional syndrome (panels a\u2013c and e) or per trajectory (panel d); k is the number '
         'of contributing cohorts. In panel (c) the number of person-intervals modelled was '
         '%s (one wave), %s (two waves) and %s (cumulative mean).'
         % (n_(TV[TV['variant'] == 'time-varying (1 wave)']['intervals'].iloc[0]),
            n_(TV[TV['variant'] == 'lagged (2 waves)']['intervals'].iloc[0]),
            n_(TV[TV['variant'] == 'cumulative mean']['intervals'].iloc[0])),
    header=None, rows=t4c, colw=[3400, 700, 2000, 900]))

# 轨迹发病密度写入注释（Table S7 用）
CHK.append('traj density summary: ' + '; '.join(
    '%s=%.1f' % (r['traj'], r['density']) for _, r in TRAJD.iterrows()))

# =============================================================== 预览
prev = []
for t in TABLES:
    prev.append('## %s' % t['cap'])
    prev.append('')
    if t.get('rows'):
        prev.append('| ' + ' | '.join(t['rows'][0]) + ' |')
        prev.append('|' + '---|' * len(t['rows'][0]))
        for r in t['rows'][1:]:
            prev.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    if t.get('note'):
        prev.append('')
        prev.append('*%s*' % t['note'])
    prev.append('')
open(os.path.join(OUT, '_tables_preview.md'), 'w', encoding='utf8').write('\n'.join(prev))
open(os.path.join(OUT, '_tables_check.txt'), 'w', encoding='utf8').write('\n'.join(CHK))
print('\n'.join(prev)[:3000])
print('\n\n===== 对撞 %d 项 =====' % len(CHK))
print('\n'.join(CHK))

# =============================================================== 导出 XML
import json
json.dump(TABLES, open(os.path.join(OUT, '_tables.json'), 'w', encoding='utf8'),
          ensure_ascii=False, indent=1)
print('\n_tables.json 已写出：%d 张' % len(TABLES))
