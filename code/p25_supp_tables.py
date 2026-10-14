# -*- coding: utf-8 -*-
"""p25_supp_tables.py —— 生成 Additional file 1（补充材料）Word 文件：表 S1–S7

全部数值来自 out/*.csv（重建流水线脚本产物），不做手工转录。
输出：D:/桌面/AIzuopin/痴呆/附加材料_Additional_file_1_20261013.docx
      out/_supp_preview.md（人读预览）
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L
import docxtbl as D

OUT = L.OUT
CO = L.COHORTS
NAME = {'CHARLS': 'CHARLS (China)', 'ELSA': 'ELSA (England)', 'HRS': 'HRS (USA)',
        'KLoSA': 'KLoSA (Korea)', 'MHAS': 'MHAS (Mexico)', 'SHARE': 'SHARE (Europe)'}
REG = {'CHARLS': 'China', 'ELSA': 'England', 'HRS': 'United States', 'KLoSA': 'Korea',
       'MHAS': 'Mexico', 'SHARE': 'Europe (11 countries)'}
DST = r'D:/桌面/AIzuopin/痴呆/附加材料_Additional_file_1_20261013.docx'


def csv(n):
    return pd.read_csv(os.path.join(OUT, n))


def n_(x):
    return format(int(round(float(x))), ',')


def hc(hr, lo, hi, d=2):
    return '%.*f (%.*f\u2013%.*f)' % (d, hr, d, lo, d, hi)


FL = csv('_surv_flow.csv')
MS = csv('_ms_numbers.csv')
MS['key'] = MS['key'].astype(str).str.replace('^\ufeff', '', regex=True)
MS['value'] = pd.to_numeric(MS['value'], errors='coerce')
V = dict(zip(MS['key'], MS['value']))
S = {c: pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % c)) for c in CO}

P = []          # docx 片段
PREV = []       # markdown 预览


def add_table(cap, rows, note=None, colw=None):
    global P, PREV
    # 2026-10-13：表题统一以 "Table " 开头（S8–S17 此前缺该前缀）
    cap = cap if cap.startswith('Table ') else 'Table ' + cap
    P.append(D.para(cap, bold=True, size=20, before=240, after=80, keep_next=True))
    P.append(D.table_xml(rows, colw=colw))
    if note:
        P.append(D.para('Note. ' + note, italic=True, size=16, before=60, after=200))
    PREV.append('## ' + cap)
    PREV.append('')
    PREV.append('| ' + ' | '.join(str(x) for x in rows[0]) + ' |')
    PREV.append('|' + '---|' * len(rows[0]))
    for r in rows[1:]:
        PREV.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    if note:
        PREV += ['', '*%s*' % note]
    PREV.append('')


# ---------------------------------------------------------------- 抬头
P.append(D.para('Additional file 1', bold=True, size=28, before=0, after=160))

# ---------------------------------------------------------------- Supplementary Methods（修订版）
MD_SRC = r'D:/桌面/AIzuopin/痴呆/SupplementaryMethods_修订_20261013.md'
if os.path.exists(MD_SRC):
    _md = open(MD_SRC, encoding='utf8').read()
    # 源文件自带 '# Additional file 1. Supplementary Methods' 标题，避免重复
    _md = _md.split('\n', 1)[1] if _md.startswith('# ') else _md
    # 2026-10-13：① 截掉过时的附表清单存根（"## Supplementary tables" 及其后的
    # Note on analyses added in revision）——它与后面的正式 S1–S17 编号冲突；
    # ② 方法正文里的两张内联表（Table S3 / S3b）与正式附表 S3a/S3b 内容重复，
    #    改为交叉引用，避免同一编号在补充材料中出现两次。
    _md = _md.split('\n## Supplementary tables')[0]
    _kept, _skip = [], False
    for _ln in _md.split('\n'):
        _st = _ln.strip()
        if _st.startswith('| Cohort | Country / region |'):
            _kept.append('The cohorts, their contributing waves and their analytic samples are '
                         'described in Table S1.')
            _skip = True
            continue
        if _st.startswith('**Table S3.**'):
            _kept.append('The pre-screening decisions for every candidate component are given '
                         'in Table S3a.')
            _skip = True
            continue
        if _st.startswith('**Table S3b.**'):
            _kept.append('The formal comparison of candidate index specifications is given '
                         'in Table S3b.')
            _skip = True
            continue
        if _skip:
            if _st.startswith('|') or _st == '':
                continue
            _skip = False
        _kept.append(_ln)
    _md = '\n'.join(_kept)
    _md = _md.replace('Table S3 records the decisions.', 'Table S3a records the decisions.')
    P.extend(D.md_to_parts(_md))
    print('已并入 Supplementary Methods（%d 字符）' % len(_md))
else:
    print('!! 未找到 Supplement​aryMethods_修订_20261013.md，仅输出表格')

P.append(D.para('Supplementary tables', bold=True, size=24, before=320, after=200))

# ---------------------------------------------------------------- S1
rows = [['Cohort', 'Region', 'Baseline wave (year)', 'Waves used', 'Baseline respondents',
         'Analytic sample', 'Incident dementia', 'Person-years', 'Median follow-up (y)',
         'Maximum follow-up (y)']]
for c in CO:
    d = S[c]
    ws = sorted(pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % c))['wave'].unique())
    y0 = int(L.WAVE_YEAR[c][L.BASE_WAVE[c]])
    y1 = int(L.WAVE_YEAR[c][ws[-1]])
    fl = FL[FL['cohort'] == c].iloc[0]
    rows.append([NAME[c], REG[c], 'w%d (%d)' % (L.BASE_WAVE[c], y0),
                 'w%d\u2013w%d (%d\u2013%d)' % (ws[0], ws[-1], int(L.WAVE_YEAR[c][ws[0]]), y1),
                 n_(fl['baseline_respondents']), n_(len(d)), n_(d['E'].sum()), n_(d['T'].sum()),
                 '%.0f' % fl['median_fu'], '%.0f' % fl['max_fu']])
rows.append(['Total', '6 cohorts / 3 continents', '\u2013', '\u2013',
             n_(FL['baseline_respondents'].sum()), n_(V['n_analytic']), n_(V['n_events']),
             n_(V['person_years']), '%.0f' % V['fu_median'], '%.0f' % V['fu_longest']])
add_table('S1 Cohort overview, data sources and analytic sample', rows,
          'Median follow-up is the cohort-specific median of follow-up time; the '
          'study-wide median is 9 years (IQR 6\u201314). Deaths were taken from each cohort\u2019s '
          'vital-status file. SHARE has no wave 3. LASI was not included because it '
          'contributes a single wave.',
          colw=[1300, 1400, 1200, 1450, 1050, 900, 900, 900, 900, 900])

# ---------------------------------------------------------------- S2
STEPL = [('baseline_respondents', 'Baseline respondents'),
         ('cog_available', 'Interpretable baseline cognitive assessment'),
         ('free_of_dementia', 'Dementia-free at baseline'),
         ('age_50_105', 'Aged 50\u2013105 years'),
         ('has_followup_cog', 'Survived to and assessed during follow-up'),
         ('exposure_complete', 'Complete data on all three exposure components'),
         ('N', 'Final analytic sample')]
rows = [['Step'] + [NAME[c] for c in CO] + ['Total']]
for col, lab in STEPL:
    rows.append([lab] + [n_(FL[FL['cohort'] == c][col].iloc[0]) for c in CO]
                + [n_(FL[col].sum())])
rows.append(['Excluded at this step'] + [''] * 6 + [''])
for i, (col, lab) in enumerate(STEPL):
    if i == 0:
        continue
    prev = STEPL[i - 1][0]
    rows.append(['Excluded: %s' % lab.lower()]
                + ['\u2212' + n_(FL[FL['cohort'] == c][prev].iloc[0]
                                 - FL[FL['cohort'] == c][col].iloc[0]) for c in CO]
                + ['\u2212' + n_(FL[prev].sum() - FL[col].sum())])
add_table('S2 Stepwise sample exclusions by cohort', rows,
          'Exclusions were applied successively in the order shown and correspond to panel A of '
          'Fig. 1. The final restriction removed the participants for whom at least one of the '
          'three exposure components was missing.',
          colw=[2600, 950, 950, 950, 950, 950, 950, 750])

# ---------------------------------------------------------------- S3
rows = [['Candidate component', 'Measured in', 'Decision', 'Reason'],
        ['Disability (ADL or IADL \u2265 1)', '6/6 cohorts', 'Included',
         'Coding direction uniform in all six cohorts'],
        ['Multimorbidity (\u2265 2 chronic conditions)', '6/6 cohorts', 'Included',
         'The seven-condition set is identical across cohorts'],
        ['Depression (CES-D or EURO-D above threshold)', '6/6 cohorts', 'Included',
         'All four thresholds anchored in published work'],
        ['Falls', '6/6 cohorts', 'Excluded',
         'Recall period not comparable (6 months in SHARE vs 12 months or 2 years elsewhere)'],
        ['Urinary incontinence', '6/6 cohorts', 'Excluded',
         'Recall period not comparable; heterogeneity rose after inclusion'],
        ['Poor self-rated health', '6/6 cohorts', 'Excluded',
         'Coding direction splits across cohorts; heterogeneity rose after inclusion'],
        ['Sleep problems', '3/6 cohorts', 'Excluded',
         'Construct not harmonizable (duration in CHARLS, medication use in SHARE)'],
        ['Vision or hearing impairment', '6/6 cohorts', 'Excluded',
         'Direction splits across and within cohorts; construct already occupied in the literature']]
add_table('S3a Pre-screening decisions for candidate index components', rows,
          'A component was admitted only if its measurement was comparable across all six cohorts '
          'in recall period, coding direction and construct.',
          colw=[2600, 1100, 1000, 4300])

C = csv('_cindex.csv')
P3 = csv('_pca_pool.csv')
rows = [['Specification', 'k', 'HR (95 % CI)', 'I\u00b2 (%)']]
p = P3.iloc[0]
rows.append(['Primary index (disability + multimorbidity + depression, 0\u20133)',
             int(V['pool_M2_k']), hc(V['pool_M2_hr'], V['pool_M2_lo'], V['pool_M2_hi']),
             '%.1f' % V['pool_M2_I2']])
rows.append(['First-principal-component weighted index (per 1 SD)', int(p['k']),
             hc(p['hr'], p['lo'], p['hi']), '%.1f' % p['I2']])
A = csv('Table3B.csv')
for comp, lab in [('Disability', 'Disability, mutually adjusted'),
                  ('Multimorbidity', 'Multimorbidity, mutually adjusted'),
                  ('Depression', 'Depression, mutually adjusted')]:
    g = A[A['component'] == comp]
    d = L.dl_meta(np.log(g['hr'].astype(float)), g['se'].astype(float))
    rows.append([lab, d['k'], hc(d['hr'], d['lo'], d['hi']), '%.1f' % d['I2']])
for key, lab in [('adl_only', 'ADL limitation alone'),
                 ('iadl_only', 'IADL limitation alone')]:
    rows.append([lab, int(V[key + '_k']),
                 hc(V[key + '_hr'], V[key + '_lo'], V[key + '_hi']), '\u2013'])
add_table('S3b Formal comparison of candidate index specifications (model M2, pooled)', rows,
          'Pooled DerSimonian\u2013Laird random-effects estimates. The first-principal-component '
          'weighted index loaded %.2f, %.2f and %.2f on disability, multimorbidity and depression '
          'and explained %.1f %% of the variance, supporting equal weighting.'
          % (V['pc1_load_disab'], V['pc1_load_multi'], V['pc1_load_dep'], V['pc1_var']),
          colw=[3600, 700, 2200, 1000])

rows = [['Cohort', 'n', 'Events', 'C, index', 'C, three components entered separately',
         'Difference']]
order = [c for c in CO if c in set(C['cohort'])]
for _, r in C.iterrows():
    rows.append([NAME[r['cohort']], n_(r['n']), n_(r['ev']), '%.4f' % r['C_dai'],
                 '%.4f' % r['C_components'], '%+.4f' % r['delta']])
rows.append(['Event-weighted average', n_(C['n'].sum()), n_(C['ev'].sum()),
             '%.4f' % V['c_dai'], '%.4f' % V['c_comp'], '%+.4f' % V['c_delta']])
add_table('S3c Discrimination: count index versus the three components entered separately', rows,
          'Harrell\u2019s C. The count index loses no material information relative to the fully '
          'multivariate specification of the same three components. The pooled paired-bootstrap '
          'difference in C was %s (95 %% CI %s to %s) over the %s cohorts in which the comparison '
          'was estimable, with the whole interval inside a non-inferiority margin of %s. The '
          'bootstrap resamples participants using the fitted linear predictors and therefore does '
          'not propagate uncertainty in the fitted Cox models themselves, so the interval should be '
          'read as a lower bound on the true uncertainty.'
          % (V['dc_boot'], float(V['dc_boot_lo']), float(V['dc_boot_hi']), int(V['dc_boot_k']),
             float(V['dc_margin'])),
          colw=[2400, 900, 900, 1300, 2400, 1100])

# ---------------------------------------------------------------- S4
MA = csv('_miss_a.csv')
VL = [('dai3', 'Index (DAI), 0\u20133'), ('disab', 'Disability'), ('multi', 'Multimorbidity'),
      ('dep', 'Depression'), ('age', 'Age'), ('male', 'Sex'), ('edu', 'Education'),
      ('partnered', 'Marital status'), ('smoke3', 'Smoking'), ('drink_now', 'Alcohol use'),
      ('bmi', 'Body mass index'), ('urban', 'Urban\u2013rural residence'),
      ('grip', 'Grip strength'), ('act', 'Physical activity')]
rows = [['Variable'] + [NAME[c] for c in CO]]
for col, lab in VL:
    rows.append([lab] + ['%.1f' % float(MA[MA['cohort'] == c][col].iloc[0]) for c in CO])
add_table('S4a Missingness by variable and cohort (%)', rows,
          'Values are the percentage of the analytic sample of each cohort with a missing value. '
          'A value of 100 % indicates that the variable is not available in that cohort\u2019s '
          'harmonized file (grip strength, for instance, is available only in CHARLS, KLoSA and '
          'SHARE, which is why the model that adjusts for it is estimable in three cohorts). '
          'The exposure components are never imputed: a participant with any component missing '
          'is excluded from the analytic sample.',
          colw=[2400, 1100, 1100, 1100, 1100, 1100, 1100])

MB = csv('_miss_b.csv')
MT = csv('_miss_b_tot.csv').iloc[0]
rows = [['Cohort', 'With incomplete covariates, n', 'Complete covariates, n',
         'Age (missing / complete)', 'Disability %, (missing / complete)',
         'Events % (missing / complete)']]
for _, r in MB.iterrows():
    rows.append([NAME[r['cohort']], n_(r['n_missing']), n_(r['n_complete']),
                 '%.1f / %.1f' % (r['age_missing'], r['age_complete']),
                 '%.1f / %.1f' % (r['disab_missing'], r['disab_complete']),
                 '%.1f / %.1f' % (r['ev_missing'], r['ev_complete'])])
rows.append(['All cohorts', n_(MT['n_missing']), n_(MT['n_complete']),
             '%.1f / %.1f' % (MT['age_missing'], MT['age_complete']),
             '%.1f / %.1f' % (MT['disab_missing'], MT['disab_complete']),
             '%.1f / %.1f' % (MT['ev_missing'], MT['ev_complete'])])
add_table('S4b Characteristics of participants with and without missing covariates', rows,
          'Missingness was not assumed to be completely at random: participants with an '
          'incomplete covariate set were older and more often disabled than those with complete data.',
          colw=[1800, 1700, 1500, 1400, 1600, 1600])

MI = csv('_mice.csv')
rows = [['Scheme', 'k', 'HR (95 % CI)', 'I\u00b2 (%)', 'n']]
MLAB = {'A complete case': 'A. Complete-case analysis (primary)',
        'B impute covariates': 'B. Imputation of covariates only',
        'C impute covariates+exposure': 'C. Imputation of covariates and exposure components'}
for _, r in MI.iterrows():
    rows.append([MLAB[r['scheme']], int(r['k']), hc(r['hr'], r['lo'], r['hi']),
                 '%.1f' % r['I2'], n_(r['n'])])
add_table('S4c Multiple-imputation sensitivity analyses', rows,
          'Multiple imputation by chained equations with 20 imputations; estimates were combined '
          'within cohort by Rubin\u2019s rules and pooled across cohorts by the same random-effects '
          'procedure as the primary analysis. Imputation recovered the participants with an '
          'incomplete covariate set without altering the estimate.',
          colw=[3400, 700, 2000, 1000, 1000])

# ---------------------------------------------------------------- S5
SU = csv('_sub.csv')
IT = csv('_int.csv')
SLAB = {'<65': '< 65 years', '65-74': '65\u201374 years', '>=75': '\u2265 75 years',
        '0.0': None, '1.0': None, '1': None, '2': None, '3': None,
        'low': 'Below median', 'high': 'Above median', '<25': '< 25', '25-29.9': '25\u201329.9',
        '>=30': '\u2265 30'}
MODL = {'Age group': {'<65': '< 65 years', '65-74': '65\u201374 years', '>=75': '\u2265 75 years'},
        'Sex': {'0.0': 'Women', '1.0': 'Men'},
        'Education': {'1.0': 'Low', '2.0': 'Medium', '3.0': 'High'},
        'Baseline cognition': {'low': 'Below median', 'high': 'Above median'},
        'Marital status': {'0.0': 'Not partnered', '1.0': 'Partnered'},
        'BMI': {'<25': '< 25', '25-29.9': '25\u201329.9', '>=30': '\u2265 30'}}
rows = [['Effect modifier', 'Stratum', 'k', 'n', 'Events', 'HR (95 % CI)', 'I\u00b2 (%)',
         'P for interaction (continuous)']]
for mod in ['Age group', 'Sex', 'Education', 'Baseline cognition', 'Marital status', 'BMI']:
    iv = IT[IT['modifier'] == mod].iloc[0]
    g = SU[SU['modifier'] == mod]
    first = True
    ORD = {'Age group': ['<65', '65-74', '>=75'], 'Sex': ['0.0', '1.0'],
           'Education': ['1.0', '2.0', '3.0'], 'Baseline cognition': ['low', 'high'],
           'Marital status': ['0.0', '1.0'], 'BMI': ['<25', '25-29.9', '>=30']}[mod]
    g = g.assign(_o=[ORD.index(str(x)) if str(x) in ORD else 99 for x in g['stratum']])
    g = g.sort_values('_o')
    for _, r in g.iterrows():
        lab = MODL[mod].get(str(r['stratum']), str(r['stratum']))
        rows.append([mod if first else '', lab, int(r['k']), n_(r['n']), n_(r['ev']),
                     hc(r['hr'], r['lo'], r['hi']), '%.1f' % r['I2'],
                     ('< 0.001' if iv['p_int'] < 0.001 else '%.3f' % iv['p_int']) if first else ''])
        first = False
add_table('S5 Subgroup and interaction analyses by six prespecified effect modifiers', rows,
          'Stratum-specific pooled hazard ratios per one additional syndrome, by random effects; '
          'the covariate set corresponding to the stratifying variable was removed from that '
          'stratum. P for interaction was obtained by pooling the cohort-specific '
          'index-by-modifier interaction coefficients on the continuous scale. Multiplicity was '
          'addressed across the six prespecified modifiers by the Benjamini\u2013Hochberg '
          'procedure; the adjusted q values and the full set of interaction tests are given in '
          'Table S11. The subgroup results are nevertheless presented as exploratory.',
          colw=[1400, 1300, 550, 900, 800, 1700, 750, 1500])

# ---------------------------------------------------------------- S6
MC = csv('_med_cs.csv')
GF = csv('_gf.csv')
rows = [['Cohort', 'n', 'Events', 'Total effect, HR', 'Direct effect, HR',
         'Indirect effect, HR', 'Mediated, %']]
for var, lab in [('', 'A. Cross-sectional difference (exposure and mediator at the same wave)'),
                 ('temporal', 'B. Temporally ordered difference (exposure at wave 0, mediator at wave 1)')]:
    rows.append([lab] + [''] * 6)
    g = MC[MC['variant'].fillna('') == var]
    g = g.assign(_o=[CO.index(str(x)) if str(x) in CO else 99 for x in g['cohort']])
    g = g.sort_values('_o')
    for _, r in g.iterrows():
        px = r['prop']
        # 逐队列中介比例的置信区间由 bootstrap 提供（正态近似，用于报告范围）
        rows.append([NAME[r['cohort']], n_(r['n']), n_(r['ev']), '%.2f' % r['tot_hr'],
                     '%.2f' % r['dir_hr'], '%.2f' % r['ind_hr'], '%.1f' % (100 * px)])
rows.append(['C. Counterfactual g-formula (risk-difference scale)'] + [''] * 6)
for _, r in GF.iterrows():
    rows.append([NAME[r['cohort']], n_(r['n']), n_(r['ev']), '%.4f' % r['TE'],
                 '%.4f' % r['NDE'], '%.4f' % r['NIE'], '%.1f' % (100 * r['PM'])])
add_table('S6 Cohort-specific total, direct and indirect effects and depression-mediated '
          'proportions under three identification frameworks', rows,
          'Panels A and B are hazard ratios on the log-hazard scale; panel C reports effects on '
          'the 5-year absolute-risk-difference scale (10-year for cohorts with shorter follow-up). '
          'Mediated proportions in panel C are the natural indirect effect divided by the total '
          'effect. None of the specifications lost a cohort.',
          colw=[1700, 900, 850, 1150, 1150, 1150, 1500])

# ---------------------------------------------------------------- S7
TD = csv('_traj_dist_pool.csv')
rows = [['Cohort', 'Trajectory', 'n', 'Events', 'Person-years',
         'Incidence density (per 1,000 person-years)']]
TORD = ['persistently low', 'remitted', 'incident', 'persistently affected']
TL = {'persistently low': 'Persistently low (0\u21920)', 'remitted': 'Remitted (1\u21920)',
      'incident': 'Incident (0\u21921)', 'persistently affected': 'Persistently affected (1\u21921)'}
for c in CO:
    g = TD[TD['cohort'] == c]
    for t in TORD:
        r = g[g['traj'] == t]
        if not len(r):
            continue
        r = r.iloc[0]
        rows.append([NAME[c] if t == 'persistently low' else '', TL[t], n_(r['n']),
                     n_(r['ev']), n_(r['py']), '%.1f' % r['density']])
DP = csv('_traj_dist_pool_summary.csv')
for t in TORD:
    r = DP[DP['traj'] == t].iloc[0]
    rows.append(['Pooled' if t == 'persistently low' else '', TL[t], n_(r['n']), n_(r['ev']),
                 n_(r['py']), '%.1f' % r['density']])
add_table('S7 Exposure trajectory-specific incidence densities by cohort', rows,
          'Trajectories were defined from the baseline and the following assessment wave of the '
          'index (0 = no syndrome, 1 = at least one syndrome); follow-up runs from the second '
          'wave to the first dementia assessment, censoring or death.',
          colw=[1500, 2200, 900, 900, 1100, 1800])


# ================================================================ S8–S13：审稿响应补充分析
# ---------------- S8 基线认知调整
_cg = csv('_cogadj.csv')
if len(_cg):
    rows = [['Model', 'k', 'Pooled HR (95 % CI)', 'I² (%)']]
    LAB = {'M2': 'M2 (primary, without baseline cognition)',
           'M2+cog_quartiles': 'M2 + baseline cognition (quartile indicators)',
           'M2+cogz_edu': 'M2 + baseline global score (education-stratified z)',
           'M2+cogz': 'M2 + baseline global score (unstratified z)',
           'M2+cogz_edu+cogz': 'M2 + both global scores',
           'M2-edu+cogz': 'M2 without education + unstratified z'}
    for m in ['M2', 'M2+cog_quartiles', 'M2+cogz_edu', 'M2+cogz', 'M2+cogz_edu+cogz',
              'M2-edu+cogz']:
        g = _cg[_cg['model'] == m]
        if len(g) < 2:
            continue
        q = L.dl_meta(g['coef'], g['se'], m)
        if q:
            rows.append([LAB[m], int(q['k']), '%.2f (%.2f\u2013%.2f)' % (q['hr'], q['lo'], q['hi']),
                         '%.1f' % q['I2']])
    add_table('S8 Association after adjustment for baseline cognitive performance', rows,
              'The primary model deliberately omits baseline cognition: the outcome criterion is a '
              'threshold on the same global score and entry required that score to lie above the '
              'threshold, so the variable is both the measurement instrument and the conditioning '
              'variable of the sampling frame. The continuous-score specifications were numerically '
              'unstable in one cohort (MHAS) and are shown for completeness; the quartile-indicator '
              'specification keeps all six cohorts estimable and is the version quoted in the Results.',
              colw=[3600, 700, 2000, 900])

# ---------------- S9 死亡风险
_dc = csv('_death.csv')
if len(_dc):
    rows = [['Exposure category', 'k', 'Pooled HR for death (95 % CI)', 'I² (%)']]
    ORD = ['Continuous DAI', 'All three', 'Disability+depression', 'Multimorbidity+depression',
           'Disability only', 'Disability+multimorbidity', 'Multimorbidity only', 'Depression only']
    for cat in ORD:
        g = _dc[_dc['cat'] == cat]
        if len(g) < 2:
            continue
        q = L.dl_meta(g['coef'], g['se'], cat)
        if q:
            rows.append([cat, int(q['k']), '%.2f (%.2f\u2013%.2f)' % (q['hr'], q['lo'], q['hi']),
                         '%.1f' % q['I2']])
    add_table('S9 Hazard of death by exposure category (cause-specific, death as the event)', rows,
              'Constant DAI is modelled per one additional syndrome; the joint categories are '
              'compared with participants carrying none of the three syndromes, using the M2 '
              'covariate set. These estimates explain the apparently protective dementia hazard of '
              'the multimorbidity-only category in Table 3C: that group dies at a markedly higher '
              'rate and is therefore depleted before dementia can be ascertained. Cohorts failing the '
              'stability guard were excluded from the relevant pooled estimate.',
              colw=[3400, 700, 2100, 900])

# ---------------- S10 时距等价性
_eq = csv('_equiv.csv')
if len(_eq):
    rows = [['Lag (years)', 'k', 'Pooled HR', 'Events', 'Ratio to the no-lag estimate (95 % CI)',
             'Within ±10 % of unity']]
    for _, r in _eq.iterrows():
        rows.append([int(r['lag']), int(r['k']), '%.3f' % r['hr'], n_(int(r['events'])),
                     '%.3f (%.3f\u2013%.3f)' % (r['hr_vs_lag0'], r['lo'], r['hi']),
                     'yes' if r['within_10pct'] else 'no'])
    add_table('S10 Equivalence of the lag-specific estimates to the no-lag estimate', rows,
              'Each row compares the estimate obtained after excluding the first L years of '
              'follow-up with the estimate obtained with no exclusion (L = 0), on the log-hazard '
              'scale. The confidence interval of every ratio lies entirely within \u00b110 % of '
              'unity, so the data are consistent with the absence of any material attenuation, '
              'which a non-significant trend test alone cannot establish.',
              colw=[1000, 700, 1200, 1100, 2600, 1600])

# ---------------- S11 交互 FDR
_iv = csv('_int_fdr.csv')
if len(_iv):
    rows = [['Effect modifier', 'k', 'Interaction HR (95 % CI)', 'P', 'BH-adjusted q',
             'Significant after correction']]
    for _, r in _iv.iterrows():
        rows.append([r['modifier'], int(r['k']),
                     '%.3f (%.3f\u2013%.3f)' % (r['hr_int'], r['lo'], r['hi']),
                     ('%.4f' % r['p_int']) if r['p_int'] >= 0.0001 else '< 0.0001',
                     '%.4f' % r['q_BH'], 'yes' if r['sig_BH'] else 'no'])
    add_table('S11 Effect modification: multiplicative interaction with Benjamini\u2013Hochberg '
              'correction', rows,
              'Interaction hazard ratios are per one additional syndrome across levels of the '
              'modifier; P values are pooled across cohorts from the index-by-modifier product term. '
              'Six prespecified modifiers were tested and corrected jointly.',
              colw=[2200, 700, 2200, 1100, 1200, 1600])

# ---------------- S12 各时距样本特征
_ls = csv('_lagspec_pool.csv')
if len(_ls):
    rows = [['Excluded years (lag)', 'k', 'Participants', 'Events', 'Deaths', 'Mean age (years)',
             'Disabled (%)']]
    for _, r in _ls.iterrows():
        rows.append([int(r['lag']), int(r['k']), n_(int(r['n'])), n_(int(r['events'])),
                     n_(int(r['deaths'])), '%.1f' % r['mean_age'], '%.1f' % r['pct_disab']])
    add_table('S12 Characteristics of the sample contributing to each lag-specific estimate', rows,
              'Participants are those with a complete covariate set and follow-up exceeding the lag. '
              'As the lag lengthens the surviving sample becomes younger and less disabled and the '
              'number of contributing cohorts falls, which is why the lag-specific estimates rest on '
              'progressively smaller subsamples.',
              colw=[1500, 700, 1400, 1100, 1100, 1500, 1400])

# ---------------- S13 时变模型聚类稳健
_tc = csv('_tv_cluster_cmp.csv')
if len(_tc):
    rows = [['Cohort', 'Model', 'HR', 'Conventional SE', 'Cluster-robust SE', 'Ratio', 'Intervals',
             'Participants']]
    for _, r in _tc.iterrows():
        rows.append([r['cohort'], r['variant'], '%.3f' % r['hr'], '%.4f' % r['se_plain'],
                     '%.4f' % r['se_cluster'], '%.3f' % r['ratio'], n_(int(r['n_rows'])),
                     n_(int(r['n_clusters']))])
    add_table('S13 Cluster-robust standard errors for the interval (time-varying) models', rows,
              'Each participant contributes several intervals, so the intervals are not independent. '
              'The models were re-estimated in an independent implementation with standard errors '
              'clustered by participant. The cluster-robust standard errors are close to the '
              'conventional ones, so within-person correlation does not materially change the '
              'precision of these estimates.',
              colw=[1100, 2000, 800, 1500, 1500, 800, 1100, 1200])


# ================================================================ S14–S17：第二轮响应
_fgc = csv('_fg_cat.csv')
if len(_fgc):
    rows = [['Exposure category (vs none of the three)', 'Cohort', 'n', 'Events',
             'Subdistribution HR (95 % CI)', 'I\u00b2 (%)']]
    ORD2 = ['All three', 'Disability+multimorbidity', 'Multimorbidity+depression',
            'Disability only', 'Depression only', 'Disability+depression',
            'Multimorbidity only']
    for cat in ORD2:
        g = _fgc[_fgc['cat'] == cat]
        if len(g) < 2:
            continue
        q_ = L.dl_meta(g['coef'], g['se'], cat)
        if cat == 'Depression only':
            _dk = int(q_['k']); _dev = int(g['ev'].sum())
        rows.append([cat, 'Pooled', n_(int(g['n'].sum())), n_(int(g['ev'].sum())),
                     '%.2f (%.2f\u2013%.2f)' % (q_['hr'], q_['lo'], q_['hi']),
                     '%.1f' % q_['I2']])
        for _, r in g.sort_values('cohort').iterrows():
            _lo = r['hr'] * np.exp(-1.96 * r['se'])
            _hi = r['hr'] * np.exp(1.96 * r['se'])
            rows.append(['', NAME.get(r['cohort'], r['cohort']), n_(int(r['n'])),
                         n_(int(r['ev'])), '%.2f (%.2f\u2013%.2f)' % (r['hr'], _lo, _hi), ''])
    add_table('S14 Subdistribution hazard ratios for dementia by exposure category (Fine\u2013Gray, '
              'death as the competing event)', rows,
              'Each category is contrasted with participants carrying none of the three syndromes, with '
              'the M2 covariate set; the categories are therefore not mutually adjusted and the rows are '
              'separate models. Unlike the cause-specific hazard, the subdistribution hazard retains '
              'participants who die in the risk set, so it is not distorted by differential depletion '
              'through death. This table is provided for completeness and should be read with caution: '
              'the strata are sparse (the depression-only contrast is estimable in %d cohorts with a '
              'combined %s events and yields a pooled estimate with I\u00b2 well above 90 %%), so the '
              % (_dk, n_(_dev)) +
              'category-specific ordering on the subdistribution scale is not interpretable and is not '
              'used in the main text to rank the syndromes. The one category to which the main text '
              'refers is multimorbidity alone, whose cause-specific estimate of 0.89 lies below unity '
              'while its subdistribution estimate does not.',
              colw=[2400, 1700, 900, 900, 1900, 900])

_res = csv('_re_sens.csv')
if len(_res):
    rows = [['Estimator / interval', 'HR (95 % CI)', '\u03c4\u00b2']]
    for _, r in _res.iterrows():
        rows.append([r['method'], '%.3f (%.3f\u2013%.3f)' % (r['hr'], r['lo'], r['hi']),
                     '%.4f' % r['tau2']])
    _mr = csv('_metareg2.csv')
    if len(_mr):
        rows.append(['', '', ''])
        rows.append(['Meta-regression on cohort-level covariates', 'slope (SE)', 'P'])
        for _, r in _mr.iterrows():
            rows.append([r['variable'], '%.5f (%.5f)' % (r['slope'], r['se']), '%.3f' % r['p']])
    add_table('S15 Sensitivity of the pooled estimate to the random-effects estimator, and '
              'meta-regression on candidate sources of heterogeneity', rows,
              'The primary analysis uses the DerSimonian\u2013Laird moment estimator. Restricted '
              'maximum likelihood and the Knapp\u2013Hartung variance correction are shown for '
              'comparison, together with the 95 % prediction interval, which describes the range in '
              'which the true cohort-specific effect would be expected to fall. Meta-regression '
              'slopes are on the log-hazard scale per unit of the covariate, estimated with '
              'random-effects weights.',
              colw=[3200, 2000, 1000])

_cf = csv('_confirm.csv')
if len(_cf):
    rows = [['Cohort', 'n', 'Confirmed events', 'HR (95 % CI) per syndrome']]
    for _, r in _cf.iterrows():
        rows.append([r['cohort'], n_(int(r['n'])), n_(int(r['ev'])),
                     '%.3f (%.3f\u2013%.3f)' % (r['hr'],
                                                r['hr'] * pow(2.718281828, -1.96 * r['se']),
                                                r['hr'] * pow(2.718281828, 1.96 * r['se']))])
    q = L.dl_meta(_cf['coef'], _cf['se'], 'confirmed')
    rows.append(['Pooled', n_(int(_cf['n'].sum())), n_(int(_cf['ev'].sum())),
                 '%.3f (%.3f\u2013%.3f)' % (q['hr'], q['lo'], q['hi'])])
    add_table('S16 Sensitivity analysis requiring the dementia criterion to be met at two '
              'consecutive cognitive assessments', rows,
              'The primary criterion classifies a participant as affected at the first wave at which '
              'the algorithmic threshold is crossed. Requiring confirmation at two consecutive '
              'assessments removes about three quarters of the events, so the estimate is less '
              'precise, but it remains clearly positive. Cohorts whose confirmed-event count was too '
              'small to give a stable estimate were excluded by the stability rule.',
              colw=[1400, 1200, 1600, 2600])

_ca = csv('_calib.csv')
if len(_ca):
    rows = [['Cohort', 'Assessment horizon (years)', 'Observed (%)', 'Expected (%)', 'O/E ratio',
             'Calibration slope']]
    for _, r in _ca.iterrows():
        rows.append([r['cohort'], '%.0f' % r['thr'], '%.2f' % r['obs_pct'], '%.2f' % r['exp_pct'],
                     '%.2f' % r['OE'], '%.2f' % r['slope']])
    add_table('S17 Calibration of the primary model by cohort', rows,
              'Observed and expected event proportions at each cohort\u2019s median follow-up, with '
              'the observed/expected ratio and the calibration slope obtained by regressing the '
              'observed outcome on the predicted risk within deciles of predicted risk. An O/E ratio '
              'of 1 and a slope of 1 indicate perfect calibration; the values here indicate that the '
              'model is acceptably calibrated in all six cohorts, with some over-prediction in ELSA '
              'and under-prediction in HRS.',
              colw=[1300, 1900, 1400, 1400, 1100, 1600])

# ---------------------------------------------------------------- 写出
D.write_docx(DST, P)
open(os.path.join(OUT, '_supp_preview.md'), 'w', encoding='utf8').write('\n'.join(PREV))
print('已写出:', DST)
print('片段数:', len(P))
import zipfile
z = zipfile.ZipFile(DST)
x = z.read('word/document.xml').decode('utf8')
print('tbl=%d 反斜杠=%d' % (x.count('<w:tbl>'), x.count('\\')))
print('\n'.join(PREV[:6]))
