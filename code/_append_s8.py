# -*- coding: utf-8 -*-
"""给 p25_supp_tables.py 追加 S8–S13（2026-10-13 审稿响应补充表）"""
import io
import ast

p = 'p25_supp_tables.py'
s = io.open(p, encoding='utf8').read()
anchor = "# ---------------------------------------------------------------- 写出"
assert anchor in s

BLOCK = '''
# ================================================================ S8–S13：审稿响应补充分析
# ---------------- S8 基线认知调整
_cg = C('_cogadj.csv')
if len(_cg):
    rows = [['Model', 'k', 'Pooled HR (95 % CI)', 'I\u00b2 (%)']]
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
            rows.append([LAB[m], int(q['k']), '%.2f (%.2f\\u2013%.2f)' % (q['hr'], q['lo'], q['hi']),
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
_dc = C('_death.csv')
if len(_dc):
    rows = [['Exposure category', 'k', 'Pooled HR for death (95 % CI)', 'I\u00b2 (%)']]
    ORD = ['Continuous DAI', 'All three', 'Disability+depression', 'Multimorbidity+depression',
           'Disability only', 'Disability+multimorbidity', 'Multimorbidity only', 'Depression only']
    for cat in ORD:
        g = _dc[_dc['cat'] == cat]
        if len(g) < 2:
            continue
        q = L.dl_meta(g['coef'], g['se'], cat)
        if q:
            rows.append([cat, int(q['k']), '%.2f (%.2f\\u2013%.2f)' % (q['hr'], q['lo'], q['hi']),
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
_eq = C('_equiv.csv')
if len(_eq):
    rows = [['Lag (years)', 'k', 'Pooled HR', 'Events', 'Ratio to the no-lag estimate (95 % CI)',
             'Within \u00b110 % of unity']]
    for _, r in _eq.iterrows():
        rows.append([int(r['lag']), int(r['k']), '%.3f' % r['hr'], n_(int(r['events'])),
                     '%.3f (%.3f\\u2013%.3f)' % (r['hr_vs_lag0'], r['lo'], r['hi']),
                     'yes' if r['within_10pct'] else 'no'])
    add_table('S10 Equivalence of the lag-specific estimates to the no-lag estimate', rows,
              'Each row compares the estimate obtained after excluding the first L years of '
              'follow-up with the estimate obtained with no exclusion (L = 0), on the log-hazard '
              'scale. The confidence interval of every ratio lies entirely within \\u00b110 % of '
              'unity, so the data are consistent with the absence of any material attenuation, '
              'which a non-significant trend test alone cannot establish.',
              colw=[1000, 700, 1200, 1100, 2600, 1600])

# ---------------- S11 交互 FDR
_iv = C('_int_fdr.csv')
if len(_iv):
    rows = [['Effect modifier', 'k', 'Interaction HR (95 % CI)', 'P', 'BH-adjusted q',
             'Significant after correction']]
    for _, r in _iv.iterrows():
        rows.append([r['modifier'], int(r['k']),
                     '%.3f (%.3f\\u2013%.3f)' % (r['hr_int'], r['lo'], r['hi']),
                     ('%.4f' % r['p_int']) if r['p_int'] >= 0.0001 else '< 0.0001',
                     '%.4f' % r['q_BH'], 'yes' if r['sig_BH'] else 'no'])
    add_table('S11 Effect modification: multiplicative interaction with Benjamini\\u2013Hochberg '
              'correction', rows,
              'Interaction hazard ratios are per one additional syndrome across levels of the '
              'modifier; P values are pooled across cohorts from the index-by-modifier product term. '
              'Six prespecified modifiers were tested and corrected jointly.',
              colw=[2200, 700, 2200, 1100, 1200, 1600])

# ---------------- S12 各时距样本特征
_ls = C('_lagspec_pool.csv')
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
_tc = C('_tv_cluster_cmp.csv')
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

'''
s = s.replace(anchor, BLOCK + anchor, 1)
io.open(p, 'w', encoding='utf8').write(s)
ast.parse(s)
print('p25 已追加 S8–S13')
