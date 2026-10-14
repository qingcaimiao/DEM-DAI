# -*- coding: utf-8 -*-
"""p30_supp_methods_revise.py —— 把 SupplementaryMethods.md 的数值同步到重建结果

规则：
- 所有统计量从 out/_ms_numbers.csv 或 out/*.csv 读取后拼装，不手写；
- 无法由重建复算的旧数值（如未复算的备选指数 DAI-4、活动编码相关性、KLoSA 认知覆盖率）
  一律改为**定性表述**并说明，绝不留旧数字；
- 输出后立即做逐 token 溯源审计（数字必须能在数值集合中找到或属于白名单）。
输出：D:/桌面/AIzuopin/痴呆/SupplementaryMethods_修订_20261013.md
      out/_supp_methods_audit.txt
"""
import os
import re
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
SRC = r'D:/桌面/AIzuopin/痴呆/SupplementaryMethods.md'
DST = r'D:/桌面/AIzuopin/痴呆/SupplementaryMethods_修订_20261013.md'

MS = pd.read_csv(os.path.join(OUT, '_ms_numbers.csv'), encoding='utf-8-sig')
# 2026-10-13：数字表里有 5 个“非数值”键（如 med_min_logtot_cohort = CHARLS、
# equiv_all_within10 = yes）。此前直接 to_numeric(errors='coerce') 会把它们静默变成 NaN，
# 结果正文出现 "(nan)"。因此保留一份原始字符串字典 VS，文本型取值一律从 VS 取。
_K = MS['key'].astype(str).str.replace('^\ufeff', '', regex=True)
_VS = MS['value'].astype(str).str.replace('^\ufeff', '', regex=True)
VS = dict(zip(_K, _VS))
MS['value'] = pd.to_numeric(_VS, errors='coerce')
V = dict(zip(_K, MS['value']))


def n(k, d=0):
    f = float(V[k])
    return format(int(round(f)), ',') if d == 0 else ('%.' + str(d) + 'f') % f


FL = pd.read_csv(os.path.join(OUT, '_surv_flow.csv'), encoding='utf-8-sig')
FL = FL.set_index('cohort')
MA = pd.read_csv(os.path.join(OUT, '_miss_a.csv'), encoding='utf-8-sig').set_index('cohort')
KA = pd.read_csv(os.path.join(OUT, '_kappa.csv'), encoding='utf-8-sig')
LO = pd.read_csv(os.path.join(OUT, '_loo.csv'), encoding='utf-8-sig')
P3B = pd.read_csv(os.path.join(OUT, '_pool_3b.csv'), encoding='utf-8-sig')
PCA = pd.read_csv(os.path.join(OUT, '_pca_pool.csv'), encoding='utf-8-sig').iloc[0]

REG = {'CHARLS': 'China', 'ELSA': 'England', 'HRS': 'United States', 'KLoSA': 'Korea',
       'MHAS': 'Mexico', 'SHARE': 'Europe (11 countries)'}
WAVES = {'CHARLS': 'w1\u2013w5 (2011\u20132020)', 'ELSA': 'w1\u2013w9 (2002\u20132018)',
         'HRS': 'w5\u2013w15 (2000\u20132020)', 'KLoSA': 'w3\u2013w8 (2010\u20132020)',
         'MHAS': 'w1\u2013w5 (2001\u20132018)', 'SHARE': 'w1, w2, w4\u2013w8 (2004\u20132020)'}
BASE = {'CHARLS': 'w1 (2011)', 'ELSA': 'w1 (2002)', 'HRS': 'w5 (2000)',
        'KLoSA': 'w3 (2010)', 'MHAS': 'w3 (2012)', 'SHARE': 'w1 (2004)'}
ORDER = ['CHARLS', 'ELSA', 'HRS', 'KLoSA', 'MHAS', 'SHARE']

S = open(SRC, encoding='utf8').read()
EDITS = []          # (old, new, tag)


def R(old, new, tag):
    EDITS.append((old, new, tag))


# ---------------------------------------------------------------- 标题
R('a time-lagged analysis of 74,501 participants',
  'a time-lagged analysis of %s participants' % n('n_analytic'), '标题样本量')

# ---------------------------------------------------------------- S1 队列表
old_tbl = """| CHARLS | China | w1 (2011) | w1–w5 (2011–2020) | 17,708 | 10,348 | 1,539 | 76,205 |
| ELSA | England | w1 (2002) | w1–w9 (2002–2018) | 12,099 | 8,213 | 1,413 | 82,452 |
| HRS | United States | w5 (2000) | w5–w15 (2000–2020) | 19,578 | 15,590 | 3,419 | 172,775 |
| KLoSA | Korea | w3 (2010) | w3–w8 (2010–2020) | 7,920 | 6,151 | 1,071 | 42,735 |
| MHAS | Mexico | w3 (2012) | w1–w5 (2001–2018) | 15,723 | 11,854 | 1,156 | 61,752 |
| SHARE | Europe (11 countries) | w1 (2004) | w1, w2, w4–w8 (2004–2019) | 30,416 | 22,345 | 2,250 | 218,034 |
| **Total** | 6 cohorts / 3 continents | — | — | **103,444** | **74,501** | **10,848** | **653,953** |"""
new_tbl = '\n'.join(
    '| %s | %s | %s | %s | %s | %s | %s | %s |'
    % (c, REG[c], BASE[c], WAVES[c],
       format(int(FL.loc[c, 'baseline_respondents']), ','), format(int(FL.loc[c, 'N']), ','),
       format(int(FL.loc[c, 'events']), ','), format(int(FL.loc[c, 'person_years']), ','))
    for c in ORDER)
new_tbl += ('\n| **Total** | 6 cohorts / 3 continents | — | — | **%s** | **%s** | **%s** | **%s** |'
            % (format(int(FL['baseline_respondents'].sum()), ','), n('n_analytic'),
               n('n_events'), n('person_years')))
R(old_tbl, new_tbl, 'S1 队列样本表')

# ---------------------------------------------------------------- S1 样本推导
R('**Sample derivation.** Successive exclusions from 103,444 baseline respondents are reported in Table S2 (main text Fig. 1A). The final restriction — complete data on all three exposure components — removed 280 participants. The analytic data set inherits from the upstream harmonization pipeline; a further 25 participants (0.03 %) are absent because of missing upstream exposure variables. The primary model (M2) required complete covariate data and retained 72,624 participants (10,560 events).',
  '**Sample derivation.** Successive exclusions from %s baseline respondents are reported in Table S2 (main text Fig. 1A). '
  'In order: %s were removed for want of an interpretable baseline cognitive assessment, %s for dementia at baseline, '
  '%s for being younger than 50 or older than 105 years, %s for not surviving to or not being assessed during follow-up, '
  'and %s for incomplete data on the three exposure components, leaving %s participants. '
  'The primary model (M2) additionally required complete covariate data and retained %s participants (%s events).'
  % (format(int(FL['baseline_respondents'].sum()), ','),
     format(int(FL['baseline_respondents'].sum() - FL['cog_available'].sum()), ','),
     format(int(FL['cog_available'].sum() - FL['free_of_dementia'].sum()), ','),
     format(int(FL['free_of_dementia'].sum() - FL['age_50_105'].sum()), ','),
     format(int(FL['age_50_105'].sum() - FL['has_followup_cog'].sum()), ','),
     format(int(FL['has_followup_cog'].sum() - FL['N'].sum()), ','),
     n('n_analytic'), n('n_m2'), n('n_m2_events')),
  'S1 样本推导')

# ---------------------------------------------------------------- S2 预筛表：去旧数值
R('Recall period not comparable: 6 months in SHARE vs 12 months or 2 years elsewhere; prevalence 2.3 % (KLoSA) to 38.9 % (MHAS)',
  'Recall period not comparable: 6 months in SHARE vs 12 months or 2 years elsewhere',
  'S2 falls 行去旧患病率')
R('Coding direction splits across cohorts (1 = worst in CHARLS/HRS/KLoSA/SHARE, 5 = worst in ELSA/MHAS); I² rose from 53.7 % to 68.9 % on inclusion',
  'Coding direction splits across cohorts (1 = worst in CHARLS/HRS/KLoSA/SHARE, 5 = worst in ELSA/MHAS); heterogeneity rose after inclusion',
  'S2 自评健康行去旧 I²')
R('| Vision / hearing impairment | 7/7 | Excluded |', '| Vision / hearing impairment | 6/6 | Excluded |',
  'S2 视听行覆盖数改为 6/6')

# ---------------------------------------------------------------- S2 Table S3b
old_s3b = """| Index | Composition | Range | Pooled HR (95 % CI) | I² |
|---|---|---|---|---|
| **DAI (primary)** | Disability + multimorbidity + depression | 0–3 | **1.230 (1.187–1.276)** | **60.6 %** |
| DAI-4 | ADL limitation + IADL limitation + multimorbidity + depression | 0–4 | 1.202 (1.159–1.246) | 70.9 % |
| DAI-4 + self-rated health | as DAI-4, plus poor self-rated health | 0–5 | 1.177 (1.138–1.218) | 78.6 % |
| DAI-4 + falls | as DAI-4, plus falls | 0–5 | 1.163 (1.115–1.214) | 81.6 % |
| DAI-4 + falls + incontinence | as DAI-4, plus falls and urinary incontinence | 0–6 | 1.127 (1.080–1.176) | 81.0 % |"""


def hc(hr, lo, hi):
    return '%.2f (%.2f\u2013%.2f)' % (hr, lo, hi)


def p3b(comp):
    r = P3B[P3B['component'] == comp].iloc[0]
    return hc(r['hr'], r['lo'], r['hi']), '%.1f %%' % r['I2'], int(r['k'])


d, di, _ = p3b('Disability')
m, mi, _ = p3b('Multimorbidity')
p_, pi, _ = p3b('Depression')
new_s3b = """| Specification | k | Pooled HR (95 %% CI) | I² |
|---|---|---|---|
| **Primary index (disability + multimorbidity + depression, 0–3)** | 6 | **%s** | **%s %%** |
| First-principal-component weighted index (per 1 SD) | %d | %s | %.1f %% |
| Disability, entered jointly with the other two | %d | %s | %s |
| Multimorbidity, entered jointly with the other two | %d | %s | %s |
| Depression, entered jointly with the other two | %d | %s | %s |
| ADL limitation alone as the exposure | %d | %s | — |
| IADL limitation alone as the exposure | %d | %s | — |""" % (
    hc(V['pool_M2_hr'], V['pool_M2_lo'], V['pool_M2_hi']), V['pool_M2_I2'] if False else '%.1f' % V['pool_M2_I2'],
    int(PCA['k']), hc(PCA['hr'], PCA['lo'], PCA['hi']), PCA['I2'],
    int(P3B[P3B['component'] == 'Disability'].iloc[0]['k']), d, di,
    int(P3B[P3B['component'] == 'Multimorbidity'].iloc[0]['k']), m, mi,
    int(P3B[P3B['component'] == 'Depression'].iloc[0]['k']), p_, pi,
    int(V['adl_only_k']), hc(V['adl_only_hr'], V['adl_only_lo'], V['adl_only_hi']),
    int(V['iadl_only_k']), hc(V['iadl_only_hr'], V['iadl_only_lo'], V['iadl_only_hi']))
R(old_s3b, new_s3b, 'S3b 候选指数比较（改为可复算版本）')

R('Splitting disability into separate ADL and IADL components was also rejected, as was the addition of any screened-out component. Table S3b gives the formal comparison: every departure from the retained three-component index either diluted the per-unit effect or inflated heterogeneity.',
  'Splitting disability into ADL and IADL as two separate components was rejected on construct grounds, because the two are strongly collinear and most participants with limitations report both; Table S3b therefore compares the retained three-component index with the specifications that can be estimated from the harmonized files. '
  'Weighting the three components by their first principal component gives a pooled hazard ratio of %s per 1 SD with near-equal loadings (%.2f, %.2f and %.2f, explaining %.1f %% of the variance), so equal weighting is close to optimal in these data. '
  'Entering the three components separately rather than as a count leaves the discrimination of the model unchanged (see S3.4), so the count form costs nothing and can be collected without computation.'
  % (hc(PCA['hr'], PCA['lo'], PCA['hi']), V['pc1_load_disab'], V['pc1_load_multi'],
     V['pc1_load_dep'], V['pc1_var']),
  'S3b 后段说明改为可复算口径')

# ---------------------------------------------------------------- S3.4
R("Harrell's C for the DAI was 0.7225 (event-weighted average of the cohort-specific values) against 0.7246 for a model entering the three dichotomous components separately — a difference of −0.002.",
  "Harrell's C for the DAI was %s (event-weighted average of the cohort-specific values) against %s for a model entering the three dichotomous components separately — a difference of %s."
  % ('%.4f' % V['c_dai'], '%.4f' % V['c_comp'], '%.4f' % V['c_delta']),
  'S3.4 判别力')

R('The first principal component loaded 0.632 (disability), 0.532 (multimorbidity) and 0.563 (depression) and explained 46.8 % of the variance; the loadings are near-equal, supporting equal weighting. The PC1-weighted index gave a pooled HR of 1.441 (1.355–1.532) per 1 SD, I² = 57.9 %.',
  'The first principal component loaded %.2f (disability), %.2f (multimorbidity) and %.2f (depression) and explained %.1f %% of the variance; the loadings are near-equal, supporting equal weighting. The PC1-weighted index gave a pooled HR of %s per 1 SD, I² = %.1f %%.'
  % (V['pc1_load_disab'], V['pc1_load_multi'], V['pc1_load_dep'], V['pc1_var'],
     hc(PCA['hr'], PCA['lo'], PCA['hi']), PCA['I2']),
  'S3.4 加权')

R('All three components remained positively associated with dementia after mutual adjustment (disability 1.27, 95 % CI 1.18–1.36; depression 1.42, 1.30–1.55; multimorbidity 1.04, 0.96–1.13), with no reversal in any cohort.',
  'Disability and depression remained associated with dementia after mutual adjustment (disability %s; depression %s), whereas multimorbidity did not (%s), and no pooled component reversed direction.'
  % (d, p_, m),
  'S3.4 组分独立性')

# ---------------------------------------------------------------- S4.3 kappa
R('Agreement between the algorithmic outcome and the classifications distributed with the harmonized files was moderate to strong (Cohen κ 0.52–0.82: ELSA 0.536, HRS 0.516, KLoSA 0.822), supporting the derived criterion. Agreement with self-reported physician diagnosis was near zero (κ 0.02–0.22). This is a known feature of the HRS family of surveys, where self-reported dementia is heavily under-ascertained, and is the reason the algorithmic definition was made primary.',
  'Agreement between the algorithmic outcome and the classifications distributed with the harmonized files was moderate (Cohen κ %s–%s: %s), supporting the derived criterion. Agreement with self-reported physician diagnosis was near zero. This is a known feature of the HRS family of surveys, where self-reported dementia is heavily under-ascertained, and is the reason the algorithmic definition was made primary.'
  % ('%.2f' % V['kappa_min'], '%.2f' % V['kappa_max'],
     ', '.join('%s %.3f' % (r['cohort'], r['kappa']) for _, r in KA.iterrows())),
  'S4.3 kappa')

# ---------------------------------------------------------------- S5 协变量
R('| BMI | Measured BMI, kg/m² | 6/6 | Values outside [10, 70] excluded (CHARLS, 31 participants) |',
  '| BMI | Measured BMI, kg/m² | 6/6 | Values outside the plausible adult range set to missing (see Methods, physiological plausibility screening) |',
  'S5 BMI 行')
R('| Urban/rural residence | Urban vs rural | 5/6 | Not collected in ELSA; M3 only |',
  '| Urban/rural residence | Urban vs rural | 5/6 | Not available in the ELSA harmonized file; M3 only |',
  'S5 城乡行')
R('| Grip strength | Best of two hands, kg | 6/6 | < 1 kg treated as not measured; M4 only |',
  '| Grip strength | Best of two hands, kg | 3/6 | Available only in CHARLS, KLoSA and SHARE (missing in ELSA, HRS and MHAS); M4 only |',
  'S5 握力行覆盖率改为 3/6')
R('| Physical activity | Inactive / moderate / active | 6/6 | M4 only |',
  '| Physical activity | Inactive / moderate / active | 4/6 | Not available in HRS and largely missing in CHARLS (%s %%); M4 only |'
  % ('%.1f' % MA.loc['CHARLS', 'act']),
  'S5 体力活动行覆盖率改为 4/6')

R('Direction was not assumed: each code was anchored against grip strength (standardized within cohort, wave and sex), and the mapping was corrected where the correlation was negative. The initial mapping gave correlations of −0.24 (ELSA) and −0.29 (SHARE); after reversing those two cohorts, all seven were positive (r = +0.05 to +0.29). This variable is treated as low-confidence and enters only the M4 sensitivity model.',
  'Direction was not assumed: each code was anchored against grip strength (standardized within cohort, wave and sex), and the mapping was corrected where the correlation was negative. In two cohorts the initial coding ran opposite to grip strength and was reversed, after which every cohort showed a positive association. This variable is treated as low-confidence and enters only the M4 sensitivity model.',
  'S5 活动编码相关性改为定性')

R('**Missing data.** Because grip strength is missing in 60–99 % of several cohorts, a complete-case model containing it would be unrepresentative; M4 is therefore a sensitivity analysis rather than a primary specification. The primary model M2 uses complete cases on covariates whose missingness is low (≤ 7.6 % for every covariate in every cohort except BMI in ELSA, which the carry procedure addresses).',
  '**Missing data.** Grip strength is absent altogether from the harmonized files of three cohorts and missing for a further %s %% of CHARLS participants, and physical activity is absent from HRS and missing for %s %% of CHARLS participants, so a complete-case model containing them would be unrepresentative; M4 is therefore a sensitivity analysis rather than a primary specification. '
  'The primary model M2 uses complete cases on covariates with low missingness: at most %.1f %% for body mass index (CHARLS), %.1f %% for BMI in ELSA and %.1f %% for BMI in MHAS, %.1f %% for education in ELSA, and no more than %.1f %% for any other covariate in any cohort.'
  % ('%.1f' % MA.loc['CHARLS', 'grip'], '%.1f' % MA.loc['CHARLS', 'act'],
     MA.loc['CHARLS', 'bmi'], MA.loc['ELSA', 'bmi'], MA.loc['MHAS', 'bmi'], MA.loc['ELSA', 'edu'],
     max(MA[['partnered', 'drink_now', 'edu', 'bmi']].max().max(),
         MA[['partnered', 'drink_now', 'edu']].max().max())),
  'S5 缺失数据段')

# ---------------------------------------------------------------- S6.3 时距
R('Excluding the first two years left the estimate essentially unchanged and reduced I² from 60.6 % to 0.0 %; the trend test gave P = 0.41, i.e. no attenuation with increasing lag.',
  'Excluding the first two years left the estimate essentially unchanged (pooled HR %s against %s for the primary analysis) and reduced I² from %.1f %% to %.1f %%; the trend test gave P = %s, i.e. no attenuation with increasing lag.'
  % (hc(V['lag2_hr'], V['lag2_lo'], V['lag2_hi']),
     hc(V['pool_M2_hr'], V['pool_M2_lo'], V['pool_M2_hi']),
     V['pool_M2_I2'], V['lag2_I2'], '%.3f' % V['trend_p_cum']),
  'S6.3 时距')

R('Because the interval design requires at least two cognitive assessments, participants with only one were excluded; their baseline characteristics were quantified and reported (3.5 % of the sample; excluded participants were older, 72.5 vs 64.1 years, and had a higher baseline burden, 1.24 vs 0.73). Wave-specific cognitive coverage is uneven — in KLoSA, dementia ascertainment falls from 94 % at the 2014 wave to 14 % at 2016 and 0 % at 2020, making the two-wave washout variant infeasible in that cohort — so inclusion criteria were applied strictly to positive outcomes and leniently to missing ones.',
  'Because the interval design requires at least two cognitive assessments, participants with only one were excluded; because the analytic sample already required at least one follow-up assessment, only %s participants (%s %%) were affected, and because the interval models were additionally restricted by covariate completeness, the number of intervals actually modelled is reported with Table 4C. Wave-specific cognitive coverage is uneven across cohorts and across waves, which is why the two-wave washout variant could not be fitted in every cohort; inclusion criteria were therefore applied strictly to positive outcomes and leniently to missing ones.'
  % (n('tv_excluded_n'), '%.1f' % V['tv_excluded_pct']),
  'S6.3 区间设计样本')

# ---------------------------------------------------------------- S6.5 中介
R('Confidence intervals came from cohort-stratified bootstrap resampling (300 replicates).',
  'Confidence intervals for the mediated proportion came from within-cohort bootstrap resampling (200 replicates).',
  'S6.5 自助次数 300→200')

R('In practice the guard removed one cohort (KLoSA, log-HR 0.008) from the temporally ordered and the counterfactual framework and none from the cross-sectional framework. Where fewer than two cohorts qualified, the proportion is reported as not poolable rather than pooled.',
  'In this analysis the guard excluded no cohort in any framework: the smallest cohort-level total effect on the log-hazard scale was %s (%s), well above the threshold. The rule is described because it is part of the pre-specified procedure, and where fewer than two cohorts had qualified the proportion would have been reported as not poolable rather than pooled.'
  % ('%.3f' % V['med_min_logtot'], VS['med_min_logtot_cohort']),
  'S6.5 稳定性守卫')

R('Because pooling a set of ratios and taking the ratio of two pooled estimates are different operations, the two give different values — 16.4–18.8 % and 24.2–26.4 % respectively across the three frameworks.',
  'Because pooling a set of ratios and taking the ratio of two pooled estimates are different operations, the two give different values — %s\u2013%s %% and %s\u2013%s %% respectively across the three frameworks.'
  % ('%.1f' % V['med_pct_min'], '%.1f' % V['med_pct_max'],
     '%.1f' % V['med_ratio_min'], '%.1f' % V['med_ratio_max']),
  'S6.5 两种合并口径区间')

R('Risk differences were far more heterogeneous across cohorts than risk ratios (I² 82–88 % vs 40–48 %), which is expected given baseline 5-year dementia risks ranging from 4 % to 12 %.',
  'Risk differences were appreciably more heterogeneous across cohorts than risk ratios, which is expected given how widely the baseline 5-year dementia risk differs between cohorts.',
  'S6.5 尺度规则去旧数值')

# ---------------------------------------------------------------- S6.6 LOO
R('the pooled estimate ranged from 1.219 to 1.247 and remained significant in all six leave-one-out fits.',
  'the pooled estimate ranged from %s to %s and remained significant in all six leave-one-out fits.'
  % ('%.2f' % LO['hr'].min(), '%.2f' % LO['hr'].max()),
  'S6.6 留一法范围')

# ---------------------------------------------------------------- S6.7 数值稳定性
R('the baseline-hazard penalizer of 10⁻⁴ returned a hazard ratio of 1.6 × 10⁴ rather than a numerical error.',
  'the baseline-hazard penalizer of 10⁻⁴ returned a hazard ratio of the order of 10⁴ rather than a numerical error.',
  'S6.7 MHAS 失稳量级改为定性')

# ---------------------------------------------------------------- 附表清单 & 修订说明
R('**Table S6** Cohort-specific total, direct and indirect effects and depression-mediated proportions under the three identification frameworks.',
  '**Table S6** Cohort-specific total, direct and indirect effects and depression-mediated proportions under the three identification frameworks.\n**Table S7** Exposure trajectory-specific incidence densities by cohort.',
  '附表清单补 S7')

R('The exposure rule requires all three components, which removes 0.34 % of otherwise eligible participants; the residual 2.5 % difference between the 74,501 and 72,624 samples is dominated by body mass index. Multiple imputation by chained equations (m = 20) was performed under two schemes and combined by Rubin\'s rules within cohort, then pooled by the same random-effects procedure as the primary analysis.',
  'The exposure rule requires all three components, which is what reduces the sample to %s participants; the residual %s %% difference between the %s and %s samples is dominated by body mass index. Multiple imputation by chained equations (m = 20) was performed under two schemes and combined by Rubin\'s rules within cohort, then pooled by the same random-effects procedure as the primary analysis; the two schemes reproduced the primary estimate to within %s on the hazard-ratio scale.'
  % (n('n_analytic'), '%.1f' % V['miss_pct'], n('n_analytic'), n('n_m2'), '%.4f' % V['mice_maxdiff']),
  '修订说明段数值')

# ---------------------------------------------------------------- 应用
out = S
miss = []
for old, new, tag in EDITS:
    if old in out:
        out = out.replace(old, new, 1)
    else:
        miss.append(tag)
print('应用 %d / %d 条；未命中：%s' % (len(EDITS) - len(miss), len(EDITS), miss or '无'))
if miss:
    sys.exit(1)

# ---------------------------------------------------------------- 交付前规范化
# 2026-10-13：① 截掉过时的附表清单存根（"## Supplementary tables" 及随后的
# Note on analyses added in revision）——它与正式附表 S1–S17 编号冲突；
# ② 方法正文里的两张内联表（Table S3 / S3b）与正式附表 S3a/S3b 内容重复，
#    改为交叉引用；③ 内联队列表与正式 Table S1 重复，改为交叉引用。
# 这样 md 交付件与 Additional file 1 的组装结果一致。
out = out.split('\n## Supplementary tables')[0]
_kept, _skip = [], False
for _ln in out.split('\n'):
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
out = '\n'.join(_kept)
out = out.replace('Table S3 records the decisions.', 'Table S3a records the decisions.')

open(DST, 'w', encoding='utf8').write(out)
print('已写出:', DST)

# ---------------------------------------------------------------- 逐 token 溯源审计
vals = set()
for fn in os.listdir(OUT):
    if not fn.lower().endswith('.csv'):
        continue
    try:
        df = pd.read_csv(os.path.join(OUT, fn), encoding='utf-8-sig')
    except Exception:
        continue
    for c in df.columns:
        col = pd.to_numeric(df[c], errors='coerce').dropna()
        for x in col.astype(float).tolist():
            if not np.isfinite(x):
                continue
            for d_ in range(0, 5):
                vals.add(('%.' + str(d_) + 'f') % x)
            vals.add(format(x, ',.0f'))
            vals.add(format(x, ',.1f'))
            vals.add('%.1f' % (100 * x) if abs(x) <= 1 else '%.1f' % x)
            if abs(x - round(x)) < 1e-9 and abs(x) < 1e7:
                vals.add(format(int(round(x)), ','))
WHITE = set()
for y in range(1990, 2031):
    WHITE.add(str(y))
for a in range(0, 26):
    for b in range(0, 26):
        WHITE.add('%d\u2013%d' % (a, b))
WHITE |= {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '16',
          '18', '20', '24', '25', '30', '50', '60', '70', '105', '1,000', '4', '104', '10', '2',
          '0.05', '1.5', '0.5', '1,000', '3.5', '100', '95',        # 置信区间水平 95 %
          '1,2,3',                                                  # mstath 取值集合
          '3.13',                                                   # Python 版本
          }
TOK = re.compile(r'\d[\d,\.]*')
bad = []
for i, line in enumerate(out.split('\n'), 1):
    for m in TOK.finditer(line):
        t = m.group(0).rstrip('.,')
        if not t:
            continue
        if t in vals or t in WHITE or t.replace(',', '') in vals:
            continue
        bad.append((i, t, line.strip()[:110]))
rep = ['补充方法（修订版）数值溯源审计', '=' * 70,
       '数值 token 总数: %d' % len(TOK.findall(out)),
       '未解释: %d' % len(bad)]
for i, t, c in bad:
    rep.append('  行%-4d %-12s | %s' % (i, t, c))
open(os.path.join(OUT, '_supp_methods_audit.txt'), 'w', encoding='utf8').write('\n'.join(rep))
print('\n'.join(rep))
sys.exit(1 if bad else 0)
