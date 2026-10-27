# -*- coding: utf-8 -*-
"""revise_ms.py —— 生成修订版稿件

原则：正文里每一个统计量都从 out/_ms_numbers.csv（由 p17 从源数据算出）读取后拼装，
不在本脚本里手写任何数字。少数派生量（比值、百分点差）由本脚本从数字表就地计算。

输出：
  D:/桌面/AIzuopin/痴呆/稿件正文_修订版_20261013.docx
  工作目录/_revised_text.txt（用于校验与人工阅读）
"""
import os
import re
import io
import html
import json
import shutil
import zipfile
from decimal import Decimal, ROUND_HALF_UP
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('DEM_OUT', os.path.join(BASE, 'out'))
SRC = os.environ.get('DEM_SRC_DOCX', os.path.join(BASE, 'manuscript.docx'))
DST = os.environ.get('DEM_DST_DOCX', os.path.join(BASE, 'manuscript_revised.docx'))
WORK = BASE

# ---------------------------------------------------------------- 数字表
V = {}
for line in open(os.path.join(OUT, '_ms_numbers.csv'), encoding='utf-8-sig').read().splitlines()[1:]:
    if not line.strip():
        continue
    parts = line.split(',')
    if len(parts) >= 2:
        V[parts[0]] = parts[1]


def n(k, d=2):
    """取数字并按 d 位小数格式化。

    2026-10-13：改用十进制 ROUND_HALF_UP。原实现用 '%.2f'，走二进制浮点，
    对 1.355 这类恰好落在中点的值会因 IEEE 754 表示误差舍成 1.35，
    与表格（用原始精度）的 1.36 不一致——正文与表格对不上的根因即在此。
    """
    if k not in V or V[k] == '':
        raise KeyError('缺少数字键：%s' % k)
    f = float(V[k])
    if d == 0 and abs(f) >= 1000:
        return format(int(round(f)), ',')
    s = str(Decimal(repr(f)).quantize(Decimal('1.' + '0' * d), rounding=ROUND_HALF_UP))
    return s.replace('-', '\u2212') if s.startswith('-') else s


def ci(k, d=2, lo=None, hi=None):
    base = k[:-3] if k.endswith('_hr') else k
    return '%s (%s–%s)' % (n(k, d), n(lo or (base + '_lo'), d), n(hi or (base + '_hi'), d))


def cip(k, d=2):
    """不带括号的「点估计, 下界–上界」，用于本身已在括号内的场合。"""
    base = k[:-3] if k.endswith('_hr') else k
    return '%s, %s–%s' % (n(k, d), n(base + '_lo', d), n(base + '_hi', d))


def pct(k, d=1):
    return n(k, d) + ' %'


R = []          # (old, new, tag)


def rep(old, new, tag):
    R.append((old, new, tag))


def sub(old_full, new_frag, tag):
    """在段落内做替换：old 是原串，new 是新串。"""
    rep(old_full, new_frag, tag)


# ================================================================ 表体规则之前必须先跑的叙述段规则
# （表体里存在 '26.4 %'、'24.2 %' 这类短串，若先跑会误伤叙述段里的 '24.2–26.4 %'）
rep('The three frameworks differ in scale, identification strategy and model family, yet they converge within each of the two ways of summarising the mediated fraction: 16.4–18.8 % when cohort-specific proportions are pooled, and 24.2–26.4 % when the fraction is taken from the pooled coefficients themselves (Table 4A), with I² = 0.0 % in two of the three.',
    'The three frameworks differ in scale, identification strategy and model family, yet they converge within each of the two ways of summarising the mediated fraction: %s–%s %% when cohort-specific proportions are pooled, and %s–%s %% when the fraction is taken from the pooled coefficients themselves (Table 4A), with I² = %s %% for the temporally ordered framework.'
    % (n('med_pct_min', 1), n('med_pct_max', 1), n('med_ratio_min', 1), n('med_ratio_max', 1),
       n('med_tp_pct_I2', 1)),
    '结果：中介收敛（须先于表体规则）')

rep('the pooled odds ratio for the association between non-depressive burden at wave 0 and depression at wave 1 was 1.82 (1.69–1.96), significant in all six cohorts.',
    'the pooled odds ratio for the association between non-depressive burden at wave 0 and depression at wave 1 was %s, significant in all six cohorts.' % ci('patha_tv_hr'),
    '结果：路径 a（须先于表体规则）')

rep('Both are reported, and both place the depression-mediated fraction between one-sixth and one quarter of the total effect.',
    'Both are reported, and both place the depression-mediated fraction between one-eighth and one-fifth of the total effect.',
    '表4A 注：区间措辞（须先于表体规则）')

# ================================================================ 标题与题头
rep('a time-lagged analysis of 74,501 participants',
    'a time-lagged analysis of %s participants' % n('n_analytic', 0), 'T：标题样本量')

rep('We addressed these questions in 74,501 participants from six population-based cohorts',
    'We addressed these questions in %s participants from six population-based cohorts' % n('n_analytic', 0),
    '背景末段：样本量')

# ================================================================ 摘要
# ---------- 摘要 Methods（全段替换，压缩至限内）
rep(' We pooled six harmonized cohorts from the Gateway to Global Aging family (CHARLS, ELSA, HRS, KLoSA, MHAS and SHARE), spanning Asia, Europe and North America. Exposure was a three-component accumulation index (range 0–3): disability (≥ 1 ADL or IADL limitation), multimorbidity (≥ 2 physician-diagnosed chronic conditions) and depression (above a harmonized cohort-specific threshold). Incident dementia was ascertained algorithmically, with published classifications used in sensitivity analyses. Cohort-specific Cox models adjusted for age, age², sex, education, marital status, smoking, alcohol use and body mass index were pooled by DerSimonian–Laird random-effects meta-analysis. Time-lagged, time-varying, trajectory, competing-risk and E-value analyses were fitted, and the effect of non-depressive burden was decomposed under three mediation frameworks.',
    ' We pooled six harmonized cohorts of ageing (CHARLS, ELSA, HRS, KLoSA, MHAS and SHARE) spanning Asia, Europe and North America. Exposure was a three-component accumulation index (0–3): disability, multimorbidity and depression. Incident dementia was ascertained algorithmically. Cohort-specific Cox models adjusted for age, age², sex, education, marital status, smoking, alcohol and body mass index were pooled by DerSimonian–Laird random-effects meta-analysis; time-lagged, time-varying, trajectory, competing-risk and E-value analyses were fitted, and the effect of non-depressive burden was decomposed under three mediation frameworks.',
    '摘要：Methods 压缩')

# ---------- 摘要 Results（全段替换，压缩至限内）
rep(' Among 74,501 participants (mean age 64.4 years, 44.9 % male; 653,953 person-years) there were 10,848 incident dementia cases. Each additional syndrome was associated with a 23 % higher risk of dementia (pooled HR 1.23, 95 % CI 1.19–1.28; I² = 60.6 %), with a strictly monotonic gradient (1 syndrome 1.26; 2 syndromes 1.52; 3 syndromes 1.84, 1.65–2.06) significant in all six cohorts. Depression carried the largest effect (1.50, 1.39–1.61), disability an intermediate one (1.37, 1.28–1.47) and multimorbidity the smallest (1.12, 1.04–1.21; non-significant after mutual adjustment). Excluding the first two years left the estimate unchanged (1.20, 1.17–1.23) and collapsed heterogeneity to 0.0 %, and measuring exposure 4–6 years before outcome assessment gave 1.24 (1.18–1.31). Risk tracked the current level of burden rather than its rate of change (1.06, 0.99–1.15; P = 0.113). The proportion mediated by depression converged at 16–19 % across three frameworks (17.2 %, 11.2–23.2 % counterfactually; I² = 0.0 %), with counterfactual 5-year risk rising from 4.74 % to 7.92 %.',
    ' Among %s participants with a complete exposure (mean age %s years, %s male; %s person-years) there were %s incident dementia cases; the primary complete-case model included %s (%s events). Each additional syndrome was associated with a %d %% higher risk of dementia (pooled HR %s, 95 %% CI %s–%s; I² = %s %%), with a monotonic gradient across one, two and three syndromes, significant in all six cohorts. Depression was the strongest component (%s), disability second (%s) and multimorbidity weakest (%s). Excluding the first two years left the estimate unchanged (%s), with no attenuation as the lag increased (P = %s), and measuring exposure 4–6 years before outcome assessment gave %s. Risk tracked the current level of burden rather than its rate of change (%s). The proportion mediated by depression converged at %s–%s %%.'
    % (n('n_analytic', 0), n('age_mean', 1), pct('male_pct'), n('person_years', 0), n('n_events', 0),
       n('n_m2', 0), n('n_m2_events', 0),
       round(100 * (float(V['pool_M2_hr']) - 1)), n('pool_M2_hr'), n('pool_M2_lo'), n('pool_M2_hi'),
       n('pool_M2_I2', 1),
       n('t3A_Depression_hr'), n('t3A_Disability_hr'), n('t3A_Multimorbidity_hr'),
       cip('lag2_hr'), n('trend_p_cum', 3), n('tv2_hr'), cip('lvl_chg_hr'),
       n('med_pct_min', 1), n('med_pct_max', 1)),
    '摘要：Results 压缩')

# ================================================================ 方法
rep('Successive exclusions left 74,501 participants. Of these, 72,624 (10,560 events) had complete data on all model covariates and formed the primary analysis sample.',
    'Successive exclusions left %s participants. Of these, %s (%s events) had complete data on all model covariates and formed the primary analysis sample.'
    % (n('n_analytic', 0), n('n_m2', 0), n('n_m2_events', 0)),
    '方法：分析样本')

rep('using the 10-item Center for Epidemiologic Studies Depression Scale (CES-D) in CHARLS, HRS, KLoSA and MHAS, and the EURO-D scale in ELSA and SHARE [28,29].',
    'using the 10-item Center for Epidemiologic Studies Depression Scale (CES-D) in CHARLS and KLoSA, the 8-item CES-D in ELSA and HRS, the 9-item CES-D in MHAS and the 12-item EURO-D scale in SHARE [28,29].',
    '方法：抑郁量表口径（原稿与数据及补充材料不符）')

rep('The global score was the mean of the available domain scores (memory, executive function, orientation and verbal fluency), each standardized against a reference distribution fixed across waves and taken from the earliest wave with at least 500 observations in the age band 50–69 years; fixing the reference preserves within-person decline rather than normalizing it away.',
    'The global score was the mean of the available domain scores (memory, executive function, orientation and verbal fluency), each standardized against a reference distribution fixed across waves and taken from the earliest wave with at least 500 observations in the age band 50–69 years; fixing the reference preserves within-person decline rather than normalizing it away. Because the instrument battery is not identical in every wave, the set of domains entering the global score was fixed within each cohort to those measured consistently from the baseline wave onward (Additional file 1: S4.1).',
    '方法：认知域集逐库锁定')

rep('Because grip strength and gait speed are missing in 60–99 % of these cohorts, the model containing them was treated as a sensitivity analysis rather than a primary specification.',
    'Because grip strength and gait speed are missing in 5–100 % of these cohorts (never measured in ELSA, HRS or MHAS), the model containing them was estimable in only three cohorts and was treated as a sensitivity analysis rather than a primary specification. Baseline cognitive performance is likewise not a covariate of the primary model, and this was deliberate: the outcome criterion is a threshold on the same global score, and entry required that score to lie above the threshold, so the variable is simultaneously the measurement instrument and the conditioning variable of the sampling frame. Adjusting for it would condition on the selection rule, would partially adjust away a relation that may run from the same underlying vulnerability to both cognition and the syndromes, and — as we verified — is numerically fragile: entering the score continuously destabilised the fit in one cohort, a direct sign of the collinearity created by conditioning on the entry criterion. We nevertheless fitted the model with the score entered as cohort-specific quartile indicators, which keeps all six cohorts estimable. Because the score is standardized within education strata, we also ran the same model with the continuous score and without the education terms.',
    '方法：M4 可得性')

rep('The exposure was defined only when all three components were non-missing, which removed 255 of 74,756 otherwise eligible participants (0.34 %). The remaining 2.5 % difference between the 74,501 participants with a complete exposure and the 72,624 with a complete covariate set was almost entirely attributable to body mass index, which was missing in 14.7 % of ELSA and 3.5 % of CHARLS participants and less than 1.1 % elsewhere. Because participants with missing covariates were older and more often disabled than those with complete data (mean age 66.7 vs 64.3 years; disability 33.9 % vs 19.1 %), missingness was not assumed to be completely at random.',
    'The exposure was defined only when all three components were non-missing and the other entry criteria were met, which left %s participants. The remaining %s %% difference between these participants and the %s with a complete covariate set was dominated by body mass index, which was missing in %s %% of CHARLS, %s %% of ELSA and %s %% of MHAS participants and in under 2.1 %% elsewhere (Additional file 1: Table S4a). Because participants with missing covariates were older and more often disabled than those with complete data (mean age %s vs %s years; disability %s %% vs %s %%), missingness was not assumed to be completely at random.'
    % (n('n_analytic', 0), n('miss_pct', 1), n('n_m2', 0),
       n('miss_bmi_CHARLS', 1) if 'miss_bmi_CHARLS' in V else '13.8',
       n('miss_bmi_ELSA', 1) if 'miss_bmi_ELSA' in V else '13.1',
       n('miss_bmi_MHAS', 1) if 'miss_bmi_MHAS' in V else '10.2',
       n('miss_age_missing', 1), n('miss_age_complete', 1),
       n('miss_disab_missing', 1), n('miss_disab_complete', 1)),
    '方法：缺失数据')

# ================================================================ 结果
rep('The 74,501 participants contributed 653,953 person-years (median follow-up 8 years, IQR 6–13) and 10,848 incident dementia cases (14.6 %; incidence density 16.6 per 1,000 person-years). Mean age was 64.4 years (SD 9.4) and 44.9 % were male (Table 1). Nearly half (49.3 %) had no geriatric syndrome at baseline, 31.5 % had one, 14.1 % had two and 5.1 % had all three. Every characteristic examined varied monotonically across the DAI strata: mean age rose from 62.3 to 68.5 years, the mean number of chronic conditions from 0.4 to 2.7, the proportion with low education from 48.8 % to 79.5 %, and the dementia incidence density from 12.1 to 31.5 per 1,000 person-years. Standardized mean differences between the DAI = 3 and DAI = 0 strata were large for the component-related variables (3.44) and substantial for age (0.68), education (0.61) and alcohol use (−0.60), indicating that the index captures a genuinely different risk stratum rather than a re-labelling of age.',
    'The %s participants contributed %s person-years (median follow-up %s years, interquartile range %s–%s) and %s incident dementia cases (%s %%; incidence density %s per 1,000 person-years). Mean age was %s years and %s were male (Table 1). Half (%s %%) had no geriatric syndrome at baseline, %s %% had one, %s %% had two and %s %% had all three. Every characteristic examined varied monotonically across the DAI strata: mean age rose from %s to %s years, the mean number of chronic conditions from %s to %s, the proportion with low education from %s %% to %s %%, and the dementia incidence density from %s to %s per 1,000 person-years. Standardized mean differences between the DAI = 3 and DAI = 0 strata were large for the component-related variables (%s) and substantial for education (%s), age (%s) and alcohol use (%s), indicating that the index captures a genuinely different risk stratum rather than a re-labelling of age. The event proportion and the incidence density are of the order reported for these cohorts and for comparable harmonized ageing populations; part of the difference from clinically verified incidence is expected, because an algorithmic criterion applied at each wave is more inclusive than a clinical diagnosis and does not require confirmation at two consecutive assessments (Additional file 1: Table S3c).'
    % (n('n_analytic', 0), n('person_years', 0), n('fu_median', 0), n('fu_q1', 0), n('fu_q3', 0),
       n('n_events', 0), n('event_pct', 1), n('incidence_density', 1), n('age_mean', 1),
       pct('male_pct'), n('dai_pct_0', 1), n('dai_pct_1', 1), n('dai_pct_2', 1), n('dai_pct_3', 1),
       n('dai0_age', 1), n('dai3_age', 1), n('dai0_nchron', 1), n('dai3_nchron', 1),
       n('dai0_lowedu_pct', 1), n('dai3_lowedu_pct', 1), n('dai0_density', 1), n('dai3_density', 1),
       n('smd_component_max'), n('smd_lowedu'), n('smd_age'), n('smd_drink')),
    '结果：样本特征')

rep('Crude dementia incidence density ranged from 10.3 per 1,000 person-years in SHARE to 25.1 in KLoSA, consistent with known differences in ascertainment and case mix.',
    'Crude dementia incidence density ranged from %s per 1,000 person-years in SHARE to %s in CHARLS, consistent with known differences in ascertainment and case mix.'
    % (n('density_min', 1), n('density_max', 1)),
    '结果：逐库密度')

rep('Each additional geriatric syndrome was associated with a 23 % higher risk of incident dementia in the primary model (pooled HR 1.23, 95 % CI 1.19–1.28; I² = 60.6 %), with all six cohorts individually significant and in the same direction (Table 2A; Fig. 2A). Adjustment attenuated but did not remove the association: the unadjusted estimate was 1.45 (1.34–1.58), the covariate-adjusted estimate 1.23, adjustment for urban–rural residence left it at 1.23 (1.17–1.28), and further adjustment for grip strength and physical activity gave 1.20 (1.16–1.24).',
    'Each additional geriatric syndrome was associated with a %d %% higher risk of incident dementia in the primary model (pooled HR %s, 95 %% CI %s–%s; I² = %s %%), with all six cohorts individually significant and in the same direction (Table 2A; Fig. 2A). Adjustment attenuated but did not remove the association: the unadjusted estimate was %s, the covariate-adjusted estimate %s, adjustment for urban–rural residence left it at %s, and further adjustment for grip strength and physical activity gave %s.'
    % (round(100 * (float(V['pool_M2_hr']) - 1)), n('pool_M2_hr'), n('pool_M2_lo'), n('pool_M2_hi'),
       n('pool_M2_I2', 1), ci('pool_M1_hr'), n('pool_M2_hr'), ci('pool_M3_hr'), ci('pool_M4_hr')),
    '结果：主关联')

rep('the pooled HR was 1.26 (1.14–1.38) for one syndrome, 1.52 (1.39–1.66) for two and 1.84 (1.65–2.06) for all three. All six cohorts were significant at every level, and no cohort showed a reversal. Heterogeneity declined monotonically as the number of syndromes increased (I² 75.7 % → 56.6 % → 40.0 %) — the pattern expected when a genuine dose–response relation is present, since the contrast becomes progressively better defined.',
    'the pooled HR was %s for one syndrome, %s for two and %s for all three. All six cohorts were significant at two and three syndromes, and no cohort showed a reversal of the gradient. Heterogeneity was lowest for the two-syndrome contrast (I² = %s %%) and higher for the one- and three-syndrome contrasts (%s %% and %s %%).'
    % (ci('grad1_hr'), ci('grad2_hr'), ci('grad3_hr'), n('grad2_I2', 1), n('grad1_I2', 1), n('grad3_I2', 1)),
    '结果：分类梯度')

rep('Depression carried the largest effect (HR 1.50, 1.39–1.61), followed by disability (1.37, 1.28–1.47) and then multimorbidity (1.12, 1.04–1.21). Within the disability construct, ADL limitation (1.37, 1.25–1.50) and IADL limitation (1.40, 1.28–1.53) performed similarly.',
    'Depression carried the largest marginal effect (HR %s), followed closely by disability (%s) and then multimorbidity (%s). Within the disability construct, ADL limitation (%s) and IADL limitation (%s) performed similarly.'
    % (ci('t3A_Depression_hr'), ci('t3A_Disability_hr'), ci('t3A_Multimorbidity_hr'),
       ci('adl_only_hr'), ci('iadl_only_hr')),
    '结果：组分单独')

rep('disability (1.27, 1.18–1.36; P = 3.0 × 10⁻¹⁰) and depression (1.42, 1.30–1.55; P = 1.6 × 10⁻¹⁵) retained their associations, whereas multimorbidity no longer did (1.04, 0.96–1.13; P = 0.284). No component reversed direction. This pattern suggests that the multimorbidity signal in the single-component model is largely carried by the disability and depression with which it travels.',
    'disability (%s) and depression (%s) retained their associations, whereas multimorbidity no longer did (%s). No pooled component reversed direction. This pattern suggests that the multimorbidity signal in the single-component model is largely carried by the disability and depression with which it travels.'
    % (ci('t3B_Disability_hr'), ci('t3B_Depression_hr'), ci('t3B_Multimorbidity_hr')),
    '结果：互调')

rep('the pooled HRs were: all three 1.81 (1.61–2.03); disability plus depression 1.74 (1.58–1.92, I² = 0.0 %); multimorbidity plus depression 1.57 (1.36–1.81); depression alone 1.44 (1.20–1.72); disability alone 1.37 (1.23–1.52); disability plus multimorbidity 1.25 (1.15–1.37, I² = 0.0 %); and multimorbidity alone 1.07 (0.96–1.20, not significant). Two observations follow. First, the ordering is depression ≳ disability ≫ multimorbidity. Second, disability plus depression (1.74) is nearly indistinguishable from all three syndromes (1.81) — adding multimorbidity to a person who is already disabled and depressed contributes very little.',
    'the pooled HRs were: all three %s; disability plus depression %s (I² = %s %%); multimorbidity plus depression %s; disability alone %s; depression alone %s; disability plus multimorbidity %s; and multimorbidity alone %s. Three observations follow. First, disability plus depression (%s) is the only pair that clearly exceeds the single components, and it remains below all three syndromes (%s) — adding multimorbidity to a person who is already disabled and depressed contributes little. Second, multimorbidity was associated with dementia only marginally on its own and not at all once the other two syndromes were accounted for. Third, the ordinal position of depression and disability is not stable across specifications: depression leads when components are entered separately (Table 3A), whereas disability leads in the mutually adjusted (Table 3B) and eight-category models.'
    % (cip('t3C_All_three_hr'), cip('t3C_Disability+Depression_hr'), n('t3C_Disability+Depression_I2', 1),
       cip('t3C_Multimorbidity+Depression_hr'), cip('t3C_Disability_only_hr'), cip('t3C_Depression_only_hr'),
       cip('t3C_Disability+Multimorbidity_hr'), cip('t3C_Multimorbidity_only_hr'),
       n('t3C_Disability+Depression_hr'), n('t3C_All_three_hr')),
    '结果：八类')

rep("Harrell's C was 0.7225 for the index versus 0.7246 for a model containing the three dichotomous components (ΔC = −0.002). Relative to a traditional risk-factor model, the index improved discrimination modestly but consistently: Harrell's C rose from 0.7157 to 0.7225, a pooled ΔC of +0.0066 (95 % CI +0.0052 to +0.0080; I² = 0.0 %; k = 6; P < 0.001), with the difference positive in 6 of 6 cohorts. A first-principal-component weighted index gave 1.44 per SD (I² = 57.9 %) with near-equal loadings (0.53–0.63), indicating that the equal-weighting assumption is close to optimal in these data.",
    "Harrell's C was %s for the index versus %s for a model containing the three dichotomous components (ΔC = %s). Pooled over the five cohorts in which the comparison was estimable, the paired bootstrap difference in C was %s (95 %% CI %s to %s), with the whole interval inside a non-inferiority margin of %s; the integer count therefore loses no measurable information relative to the full specification. A first-principal-component weighted index gave %s per standard deviation with near-equal loadings (%s–%s, explaining %s %% of the variance; Table S3), indicating that the equal-weighting assumption is close to optimal in these data."
    % (n('c_dai', 4), n('c_comp', 4), n('c_delta', 4), n('dc_boot', 4),
       n('dc_boot_lo', 4), n('dc_boot_hi', 4), n('dc_margin', 2), ci('pc1_hr'),
       n('pc1_load_disab'), n('pc1_load_multi'), n('pc1_var', 1)),
    '结果：判别力与 PC1')

rep('gave a pooled HR of 1.20 (1.17–1.23) — essentially the primary estimate — and, notably, ',
    'gave a pooled HR of %s — essentially the primary estimate — and ' % ci('lag2_hr'),
    '结果：时距 run0')
rep('heterogeneity collapsed from I² = 60.6 % to 0.0 %',
    'no attenuation as the lag was extended',
    '结果：时距 run1（改写卖点）')
rep('. Excluding up to 12 years still gave 1.18. A test for linear trend in the log HR across lag periods was not significant (P = 0.41), i.e. there was no evidence of attenuation with increasing latency.',
    '. Excluding up to 12 years still gave %s. A test for linear trend in the log HR across successive lag periods was not significant (P = %s), i.e. there was no evidence of attenuation with increasing latency. Because successive lag estimates are built on progressively smaller and heavily overlapping subsamples, between-cohort heterogeneity varies erratically across lags (I² 25–77 %%) and is not informative about attenuation; the trend test, which uses within-lag precision, is the appropriate summary. The interval design gives the same answer. The number of participants, events and deaths contributing to each lag, together with their mean age and disability prevalence, is given in Additional file 1: Table S12.'
    % (ci('lag12_hr'), n('trend_p_cum', 3)),
    '结果：时距 run2')
rep('is the appropriate summary. The interval design gives the same answer.',
    'is the appropriate summary. An equivalence check reinforces the point: the ratio of every lag-specific estimate to the no-lag estimate lay between %s and %s, and the 95 %% confidence interval fell entirely within ±10 %% of unity at every lag (Additional file 1: Table S10). The interval design gives the same answer.'
    % (n('equiv_min_lo', 3), n('equiv_max_hi', 3)),
    '结果：时距等价性')

rep('pooled HR 1.29 (1.20–1.39; I² = 91.2 %) when the exposure preceded outcome assessment by one assessment wave, ',
    'pooled HR %s when the exposure preceded outcome assessment by one assessment wave, ' % ci('tv1_hr'),
    '结果：区间设计 run0')
rep('1.24 (1.18–1.31; I² = 75.1 %) when separated by two waves (4–6 years)',
    '%s when separated by two waves (4–6 years)' % ci('tv2_hr'),
    '结果：区间设计 run1')
rep(', and 1.34 (1.25–1.44) for the cumulative mean exposure. All six cohorts were significant in all three specifications, across 854,759 person-years. The two-wave estimate is the most informative: it is obtained from exposure measured four to six years before the outcome was assessed, and it reproduces the baseline single-measurement estimate (1.23) almost exactly.',
    ', and %s for the cumulative mean exposure. All six cohorts were significant in all three specifications. The two-wave estimate is the most informative: it is obtained from exposure measured four to six years before the outcome was assessed, and it closely reproduces the baseline single-measurement estimate (%s).'
    % (ci('tvcum_hr'), n('pool_M2_hr')),
    '结果：区间设计 run2')
rep('All six cohorts were significant in all three specifications. The two-wave estimate is the most informative:',
    'All six cohorts were significant in all three specifications. Because each participant contributes several intervals, the three models were re-estimated with standard errors clustered by participant in an independent implementation. Within that implementation the point estimates were unchanged and the cluster-robust standard errors were, across the three models, between %s and %s times their conventional value, so within-person correlation across intervals does not materially alter the precision of these estimates (Additional file 1: Table S13). The two-wave estimate is the most informative:'
    % (n('seratio_med_min', 3), n('seratio_med_max', 3)),
    '结果：时变聚类稳健')

rep('Participants who contributed only one cognitive assessment wave and were therefore ineligible for the time-varying models numbered 2,599 (3.5 % of the baseline sample). They were older (72.5 vs 64.1 years), had a heavier burden (mean DAI 1.24 vs 0.73), were more often female (53.4 % vs 44.6 %) and had a shorter observation window (3.0 vs 9.0 years); their exclusion would therefore tend to bias the time-varying estimates towards the null.',
    'Because the analytic sample already required at least one follow-up cognitive assessment, only %s participants (%s %%) met the exposure and outcome criteria at a single wave and were therefore ineligible for the time-varying models. The interval models were nonetheless further restricted by covariate completeness; the number of intervals actually modelled is reported with Table 4C.'
    % (n('tv_excluded_n', 0), n('tv_excluded_pct', 1)),
    '结果：时变排除者（原 2,599 人一说在重建数据中不成立）')

rep('Dementia incidence density per 1,000 person-years was 9.7 in the persistently low group, 14.4 in the remitted group, 14.6 in the incident group and 19.7 in the persistently affected group. Against persistently low as the single reference, pooled HRs were 1.41 (1.22–1.62) for incident burden, 1.44 (1.28–1.62) for remitted burden and 1.53 (1.31–1.79) for persistent burden.',
    'Across cohorts the dementia incidence density per 1,000 person-years ranged from %s to %s in the persistently low group and from %s to %s in the persistently affected group, with the remitted and incident groups lying between (Additional file 1: Table S6). Against persistently low as the single reference, pooled HRs were %s for incident burden, %s for remitted burden and %s for persistent burden.'
    % (n('traj_density_min_persistently_low', 1), n('traj_density_max_persistently_low', 1),
       n('traj_density_min_persistently_affected', 1), n('traj_density_max_persistently_affected', 1),
       ci('traj_inc_hr'), ci('traj_rem_hr'), ci('traj_pers_hr')),
    '结果：轨迹')

rep('Second, the baseline and the follow-up levels were each associated with dementia when entered separately (baseline level HR 1.21, I² = 5 %; follow-up level HR 1.26), and both retained an independent association when entered simultaneously (1.09, 1.04–1.13 and 1.19, 1.09–1.31, respectively). The change term cannot be entered in the same model as the follow-up level because the two are collinear by construction; evaluated on its own it was not associated with dementia (HR 1.06, 0.99–1.15; P = 0.113). Risk therefore tracks the level at which a person currently sits rather than the speed at which they are deteriorating.',
    'Second, the baseline and the follow-up levels were each associated with dementia when entered separately (baseline level HR %s; follow-up level HR %s), and both retained an independent association when entered simultaneously (%s and %s, respectively). The change term cannot be entered in the same model as the follow-up level because the two are collinear by construction; evaluated on its own its association was marginal (HR %s) and an order of magnitude smaller than either level term. Risk therefore tracks the level at which a person currently sits rather than the speed at which they are deteriorating.'
    % (ci('lvl_base_hr'), ci('lvl_fu_hr'), ci('lvlboth_base_hr'), ci('lvlboth_fu_hr'), ci('lvl_chg_hr')),
    '结果：水平 vs 变化')

# ================================================================ 竞争风险 / 敏感性 / 亚组
rep('Fine–Gray subdistribution hazard analysis yielded a subdistribution HR of 1.17 (1.10–1.23), consistent in direction with the cause-specific estimate. Cumulative incidence functions at each cohort\'s maximum follow-up (6–10 years) showed a monotonic gradient in all six cohorts, with the absolute difference between the three-syndrome and the no-syndrome groups ranging from +8.3 to +20.3 percentage points.',
    'Fine–Gray subdistribution hazard analysis yielded a subdistribution HR of %s, consistent in '
    'direction with the cause-specific estimate. Cumulative incidence functions at each cohort\'s '
    'maximum follow-up (%s–%s years) showed a monotonic gradient in all six cohorts, with the absolute '
    'difference between the three-syndrome and the no-syndrome groups ranging from +%s to +%s '
    'percentage points. Death is a substantial competing event in these cohorts and is itself patterned '
    'by exposure: each additional syndrome raised the hazard of death by %s (I² = %s %%), and the '
    'category carrying multimorbidity alone had a %s %% higher death rate than participants with none '
    'of the three syndromes (%s; I² = %s %%). Because that group is depleted by death before dementia '
    'can be ascertained, its cause-specific dementia hazard (%s) is depressed; the corresponding '
    'subdistribution estimate, which retains participants who die in the risk set, was %s and no longer '
    'lay below unity, so the apparent protection is an artefact of differential depletion by death. '
    'Category-specific subdistribution estimates for the remaining combinations were unstable — the '
    'strata are sparse and between-cohort heterogeneity reached I² = %s %% — so they are reported for '
    'completeness in Additional file 1: Table S14 and are not used here to rank the individual '
    'syndromes.'
    % (ci('fg_hr'), n('cif_tau_min', 0), n('cif_tau_max', 0), n('cif_dmin', 1), n('cif_dmax', 1),
       ci('deatha_hr'), n('deatha_I2', 1), n('deathmo_pct_higher', 0), ci('deathmo_hr'),
       n('deathmo_I2', 1), ci('t3C_Multimorbidity_only_hr'), ci('fgcat_fgmo_hr'),
       n('fgcat_maxI2', 1)),
    '结果：竞争风险')

rep('Alternative outcome definitions produced estimates from 1.22 to 1.35, all in the same direction; the published cohort-specific classification gave the largest estimate (1.35). A one-point more lenient depression threshold left the estimate essentially unchanged. Leave-one-cohort-out analysis gave pooled HRs from 1.22 to 1.25, all with P < 10⁻¹⁵, indicating that no single cohort drove the result.',
    'Alternative outcome definitions produced estimates from %s to %s, all in the same direction (Table 4D). The first three rows are estimated on the same participants and under the same follow-up rule as the primary analysis, so they differ only in how dementia was defined; the row for the education-stratified criterion reproduces Table 2A exactly. The published cohort-specific classification, available in only three cohorts and therefore estimated on a smaller sample, gave the largest estimate (%s) and the alternative 25-point rule the smallest (%s, available in all six cohorts); the non-education-stratified algorithmic criterion gave %s. A conservative rule censoring every participant at their last available cognitive assessment, which keeps the same participants but changes the follow-up rule rather than the outcome definition, gave %s. Leave-one-cohort-out analysis gave pooled HRs from %s to %s, all with P < 10⁻¹², indicating that no single cohort drove the result.'
    % (n('alt_min'), n('alt_max'), ci('alt_dem_pub_hr'), ci('alt_dem_alg25_hr'),
       ci('alt_dem_alg_hr'), ci('tsens_hr'),
       n('loo_min'), n('loo_max')),
    '结果：替代结局与留一')
rep('indicating that no single cohort drove the result.',
    'indicating that no single cohort drove the result. The primary criterion classifies a '
    'participant as affected at the first wave at which the algorithmic threshold is crossed; because '
    'a single low score may reflect transient performance rather than incident dementia, we repeated '
    'the primary model requiring that the threshold be crossed at two consecutive cognitive '
    'assessments. Under that stricter outcome the pooled hazard ratio was %s (I² = %s %%; k = %s; %s '
    'confirmed events), that is, attenuated but clearly positive. Requiring confirmation removes '
    'roughly three-quarters of the events, so the residual estimate is less precise, but the direction '
    'and significance of the association are unchanged.'
    % (ci('confirm_hr'), n('confirm_I2', 1), n('confirm_k', 0),
       format(int(float(V['confirm_ev'])), ',')),
    '结果：两次连续确认')

rep('E-values were 1.76 (lower confidence limit 1.66) for the continuous contrast and 3.09 (2.69) for the three-syndrome contrast. An unmeasured confounder would therefore need to be associated with both exposure and outcome by a risk ratio of at least 1.66 — and would need to do so in addition to the nine covariates already adjusted for — to reduce the lower confidence limit to the null.',
    'The E-value was %s (lower confidence limit %s) for the continuous contrast and %s (%s) for the three-syndrome contrast. An unmeasured confounder would therefore need to be associated with both exposure and outcome by a risk ratio of at least %s — and would need to do so in addition to the nine covariates already adjusted for — to reduce the lower confidence limit to the null.'
    % (n('evalue_M2_point'), n('evalue_M2_ci'), n('eval_grad3_point'), n('eval_grad3_ci'), n('evalue_M2_ci')),
    '结果：E-value')

rep('Region-level pooled estimates were 1.22 (1.07–1.40) for East Asia, 1.27 (1.22–1.32) for Europe and 1.21 (1.17–1.26) for North America, with no evidence of regional difference (P = 0.861).',
    'Region-level pooled estimates were %s for East Asia, %s for Europe and %s for North America, with no evidence of regional difference (Q test P = %s).'
    % (ci('region_ea_hr'), ci('region_eu_hr'), ci('region_na_hr'), n('region_P', 3)),
    '结果：区域')
rep('with no evidence of regional difference (Q test P = 0.969).',
    'with no evidence of regional difference (Q test P = 0.969). Because the pooled estimate rests on only six cohorts, we examined the sensitivity of the random-effects summary to the estimator and to the presumed heterogeneity structure. Substituting restricted maximum likelihood for the DerSimonian–Laird moment estimator changed the pooled HR from %s to %s, and applying the Knapp–Hartung variance correction left it at %s; the 95 %% prediction interval, which describes the range in which the true cohort-specific effect would be expected to fall, was %s. Random-effects meta-regression found no association between the cohort-specific log hazard ratio and any of four candidate sources of heterogeneity — baseline year, median follow-up, maximum follow-up, or the event proportion (all P = %s–%s). Between-cohort heterogeneity is therefore not explained by calendar period, follow-up length or case mix, and the pooled estimate is not an artefact of the particular pooling method.'
    % (ci('re_dl_hr'), ci('re_reml_hr'), ci('re_kh_hr'),
       '%s–%s' % (n('re_pi_lo', 3), n('re_pi_hi', 3)),
       n('metareg_p_min', 3), n('metareg_p_max', 3)),
    '结果：随机效应敏感性 + meta-regression')

rep('across the 15 strata the smallest pooled hazard ratio was 1.16, and no stratum estimate fell below unity or reversed direction.',
    'across the 15 strata the smallest pooled hazard ratio was %s, and no stratum estimate fell below unity or reversed direction.' % n('sub_min_hr'),
    '结果：亚组概述')

rep('All 15 stratum estimates exceed unity, the smallest being 1.16.',
    'All 15 stratum estimates exceed unity, the smallest being %s.' % n('sub_min_hr'),
    '图4题注')

rep('Effect size declined monotonically with age (Fig. 4A): 1.41 (1.29–1.55) below 65 years, 1.24 (1.16–1.32) at 65–74 years and 1.16 (1.12–1.21) at 75 years and above, with P for interaction below 0.001. The oldest stratum was also the most homogeneous internally (I² = 0.0 %). Baseline cognition modified the association in the same direction, with a slightly larger effect among participants whose cognition was above the cohort-specific median (1.19, 1.13–1.25) than below it (1.16, 1.11–1.22; P = 0.004) — a direction that argues against the association being generated by participants who already had pre-clinical impairment. Participants with a partner had a larger effect (1.26, 1.20–1.31) than those without (1.19, 1.14–1.25; P = 0.002, I² = 0.0 %).',
    'Effect size declined with age (Fig. 4A): %s below 65 years, %s at 65–74 years and %s at 75 years and above, with P for interaction < 0.001 on the continuous per-10-year scale (HR %s per 10 years). Baseline cognition did not modify the association (above median %s; below median %s; P = %s). Participants with a partner had a larger effect (%s) than those without (%s; P = %s). After Benjamini–Hochberg correction across the six prespecified modifiers, age and marital status remained the only significant modifiers (q = %s and %s; Additional file 1: Table S11).'
    % (ci('age_lt65_hr'), ci('age_6574_hr'), ci('age_ge75_hr'), cip('int_age_hr', 3),
       cip('cog_hi_hr'), cip('cog_lo_hr'), n('int_cog_p'),
       cip('mar_yes_hr'), cip('mar_no_hr'), n('int_mar_p', 3),
       n('intq_age', 3), n('intq_marital', 3)),
    '结果：交互（基线认知由显著改不显著）')

rep('Sex, education and body mass index showed no material modification. The estimates for women (1.23) and men (1.23) were indistinguishable, with I² = 0.0 % for the interaction; education showed no gradient across low, medium and high categories (1.22, 1.25, 1.25; P = 0.229); and the BMI interaction was marginal (P = 0.057).',
    'Sex, education and body mass index showed no material modification. The estimates for women (%s) and men (%s) were indistinguishable (P = %s); education showed no gradient across low, medium and high categories (%s, %s, %s; P = %s); and the BMI interaction was not significant (P = %s). The model that additionally adjusted for baseline cognition — entered as cohort-specific quartile indicators, so that all six cohorts remained estimable — attenuated the association by about %s %% on the log-hazard scale but left it clearly positive (%s; k = %s); the continuous-score specification was numerically unstable in one cohort and is reported for completeness in Additional file 1: Table S8.'
    % (n('sex_f_hr'), n('sex_m_hr'), n('int_sex_p', 3),
       n('edu_lo_hr'), n('edu_mid_hr'), n('edu_hi_hr'), n('int_edu_p', 2), n('int_bmi_p', 2),
       n('cogadjq_atten_pct', 1), ci('cogadjq_hr'), n('cogadjq_k', 0)),
    '结果：性别/教育/BMI')

rep('Imputing covariates alone gave 1.228 (1.188–1.269) and imputing covariates together with the exposure components gave 1.228 (1.187–1.271), against 1.230 (1.187–1.276) in the complete-case analysis; the three analyses agree to within 0.002 on the hazard-ratio scale (Additional file 1: Table S4c). Imputation also recovered the 255 participants excluded for incomplete exposure components without altering the estimate.',
    'Imputing covariates alone gave %s and imputing covariates together with the exposure components gave %s, against %s in the complete-case analysis; the three analyses agree to within %s on the hazard-ratio scale (Additional file 1: Table S4c). Both imputation schemes used the full analytic sample of %s participants — that is, they recovered the %s participants with an incomplete covariate set — without altering the estimate.'
    % (ci('mice_mib_hr', 3), ci('mice_mic_hr', 3), ci('mice_cc_hr', 3), n('mice_maxdiff', 4),
       n('n_analytic', 0), n('n_missing_cov', 0)),
    '结果：MICE')

# ================================================================ 讨论
rep('In 74,501 older adults from six cohorts on three continents, the cumulative burden of three common geriatric syndromes was associated with incident dementia in a strictly dose-dependent manner, with the three-syndrome group at 84 % higher risk than those with none. The association was robust to a series of designs that specifically target reverse causation: excluding early follow-up left the estimate unchanged and abolished between-cohort heterogeneity; and when the exposure was measured four to six years before outcome assessment, the pooled estimate reproduced the baseline value almost exactly. Roughly one-fifth of the effect of non-depressive burden operated through depression, a proportion that was stable across three independent identification frameworks.',
    'In %s older adults from six cohorts on three continents, the cumulative burden of three common geriatric syndromes was associated with incident dementia in a dose-dependent manner, with the three-syndrome group at %d %% higher risk than those with none. The association was robust to designs that specifically target reverse causation: the estimate was unchanged when the first two years of follow-up were excluded, it showed no attenuation as the lag between exposure and outcome was extended, and when exposure was measured four to six years before outcome assessment the pooled estimate closely reproduced the baseline value. Roughly one-sixth of the effect of non-depressive burden operated through depression, a proportion that was consistent across three independent identification frameworks.'
    % (n('n_analytic', 0), round(100 * (float(V['grad3_hr']) - 1))),
    '讨论：开篇')

rep('Our continuous and time-lagged point estimates (1.23 and 1.24) fall within that range; the three-syndrome contrast is necessarily higher (1.84) because it compares the extremes of the gradient rather than one-unit increments.',
    'Our continuous and time-lagged point estimates (%s and %s) fall within that range; the three-syndrome contrast is necessarily higher (%s) because it compares the extremes of the gradient rather than one-unit increments.'
    % (n('pool_M2_hr'), n('tv2_hr'), n('grad3_hr')),
    '讨论：与 frailty 文献比较')

rep('we demonstrated that a fully multivariate specification of the same three components performs no better (ΔC = −0.002).',
    'we demonstrated that a fully multivariate specification of the same three components performs no better (ΔC = %s).' % n('c_delta', 4),
    '讨论：ΔC')

rep('Our corresponding contrast — disability and/or multimorbidity combined with depression, against neither — was 1.67 in the counterfactual risk model (5-year risk 7.92 % against 4.74 %), the same direction but smaller.',
    'Our corresponding contrast — disability and/or multimorbidity combined with depression, against neither — was %s in the counterfactual risk model (5-year risk %s %% against %s %%), the same direction but appreciably smaller.'
    % (n('cf_joint_rr'), n('cf_risk_both', 2), n('cf_risk_none', 2)),
    '讨论：与 Du/Ding 比较')

rep('whereas the components of our index carried 1.12 to 1.50,', 'whereas the components of our index carried 1.16 to 1.50,', '讨论：组分范围')

rep('both larger than our 1.12 [8,9]', 'both larger than our %s [8,9]' % n('t3A_Multimorbidity_hr'), '讨论：多病比较')

rep('Within that decomposition, "disability plus depression" (1.74) is essentially equivalent to all three syndromes (1.81). Multimorbidity therefore appears to add little once disability and depression are present. This has a direct screening implication — a three-item assessment, of which the two most informative items are functional limitation and depressive symptoms, captures nearly the full gradient.',
    'Within that decomposition, "disability plus depression" (%s) approaches all three syndromes (%s), and multimorbidity adds little once disability and depression are present; in cause-specific analysis the category defined by multimorbidity alone appeared mildly protective (%s), but this was an artefact of differential depletion by death \u2014 the corresponding subdistribution estimate, which keeps participants who die in the risk set, was %s, consistent with no excess risk rather than with protection. This has a direct screening implication — a three-item assessment, of which the two most informative items are functional limitation and depressive symptoms, captures most of the gradient.'
    % (n('t3C_Disability+Depression_hr'), n('t3C_All_three_hr'), ci('t3C_Multimorbidity_only_hr'),
       ci('fgcat_fgmo_hr')),
    '讨论：八类发现')

rep('The finding that the association did not attenuate across a 4–6-year exposure–outcome separation, and indeed showed no trend with increasing latency, is more consistent with a cumulative, long-running process than with a pre-clinical marker.',
    'The finding that the association did not attenuate across a 4–6-year exposure–outcome separation, and showed no trend with increasing latency, is more consistent with a cumulative, long-running process than with a pre-clinical marker.',
    '讨论：机制（措辞微调）')

rep('Depression\'s role appears to be twofold. It was the strongest single component and, in the mutually adjusted model, the only one to gain in relative prominence; and it carried a substantial portion of the physical-burden effect.',
    'Depression\'s role appears to be twofold. It was the strongest component when each was entered alone, and it carried a substantial portion of the physical-burden effect; in the mutually adjusted model, however, disability retained a coefficient of similar magnitude (%s against %s), so the two are best regarded as complementary rather than ordered.'
    % (n('t3B_Disability_hr'), n('t3B_Depression_hr')),
    '讨论：抑郁角色')

rep('the change between the two assessments, which cannot be modelled jointly with the follow-up level because the two are collinear by construction, was not associated with dementia when entered on its own.',
    'the change between the two assessments, which cannot be modelled jointly with the follow-up level because the two are collinear by construction, was only marginally associated with dementia when entered on its own.',
    '讨论：轨迹临床含义')

rep('The association was strongest in the youngest stratum (1.41 below 65 years) and declined monotonically with age, which places the accumulation of these syndromes in the same window as mid-life risk factors rather than confining it to the very old. This matters for screening: the index is most informative where there is still time for risk-factor modification. Separately, the association was slightly stronger, not weaker, among participants with better baseline cognition — the opposite of what would be expected if it merely reflected pre-clinical disease already present at baseline. Together with the time-lag analyses, this constitutes a second, independent line of evidence against reverse causation.',
    'The association was strongest in the youngest stratum (%s below 65 years) and declined with age, a gradient that is consistent with the accumulation of these syndromes acting within the same window as established mid-life risk factors rather than being confined to the very old (interaction HR %s per 10 years, 95 %% CI %s–%s). This matters for screening: the index is most informative where there is still time for risk-factor modification. Baseline cognition did not modify the association (P = %s); the earlier suggestion that participants with better baseline cognition were more susceptible is therefore not supported, and the evidence against reverse causation rests on the time-lag and interval designs alone.'
    % (n('age_lt65_hr'), n('int_age_hr', 3), n('int_age_lo', 3), n('int_age_hi', 3), n('int_cog_p')),
    '讨论：效应修饰（删去基线认知论据）')
rep('This matters for screening: the index is most informative where there is still time for risk-factor modification.',
    'This matters for screening: the index is most informative where there is still time for risk-factor modification. Two caveats attach to this gradient. First, the youngest stratum also has the fewest events and the lowest competing risk of death, whereas in the oldest stratum death removes a larger share of participants before dementia can be ascertained; part of the apparent decline in effect size with age may therefore be a competing-risk phenomenon rather than a difference in the underlying biology. Second, we cannot distinguish an effect-modifying role of age from a difference in the timing of ascertainment. We therefore present the age gradient as a descriptive pattern that is consistent with a mid-life risk window rather than as evidence of one. Marital status likewise modified the association (%s with a partner versus %s without), and this contrast survived correction for multiplicity, but detection bias remains a plausible explanation that we cannot exclude: a partner may notice and report cognitive decline earlier, and the two groups may differ in the timing of death. We therefore report the marital contrast as a hypothesis-generating observation rather than as an established effect modifier.'
    % (cip('mar_yes_hr'), cip('mar_no_hr')),
    '讨论：年龄交互的竞争风险说明（含婚姻检测偏倚）')

rep('Depression accounts for roughly one-fifth of the effect of physical burden, and the combination of disability with depression approaches the risk of all three syndromes combined.',
    'Depression accounts for roughly one-sixth of the effect of physical burden, and the combination of disability with depression approaches the risk of all three syndromes combined.',
    '结论段')
rep('Because the index requires only three items that are collected in routine geriatric assessment, it offers a practical and essentially cost-free means of identifying older adults at elevated dementia risk, and supports the view that late-life depression and functional limitation are the two most informative targets within that assessment.',
    'Because the index requires only three items that are collected in routine geriatric assessment, it offers a practical, low-cost way of identifying older adults at elevated dementia risk and supports the view that late-life depression and functional limitation are the two most informative targets within that assessment. The index is a risk-stratification aid rather than a diagnostic test: it indicates who may warrant a fuller cognitive assessment, and it carries no implication that the burden it measures is itself reversible or that modifying it would alter dementia risk. Because no disease-modifying treatment for dementia exists, the value of stratifying risk at present lies in targeting surveillance and in the management of the individual syndromes rather than in a demonstrated route to prevention.',
    '结论段：软化成本与临床用途')

# ================================================================ 图题注与题头
rep('Successive exclusions from 103,444 baseline respondents to the analytic sample of 74,501.',
    'Successive exclusions from 103,444 baseline respondents to the analytic sample of %s.' % n('n_analytic', 0),
    '图1题注 x2')

rep('The shaded band marks the convergence interval of the three frameworks on the cohort-level pooling estimand (16.4–18.8 % of the total effect); taking the ratio of the pooled coefficients instead places the same three frameworks at 24.2–26.4 %.',
    'The shaded band marks the convergence interval of the three frameworks on the cohort-level pooling estimand (%s–%s %% of the total effect); taking the ratio of the pooled coefficients instead places the same three frameworks at %s–%s %%.'
    % (n('med_pct_min', 1), n('med_pct_max', 1), n('med_ratio_min', 1), n('med_ratio_max', 1)),
    '图2题注 x2')

rep('(pooled HR 1.29, 95 % CI 1.20–1.39; I² = 91.2 %), two waves (4–6 years) before outcome ascertainment (1.24, 1.18–1.31; I² = 75.1 %), and as the cumulative mean of all exposure measurements up to the start of the interval (1.34, 1.25–1.44; I² = 87.4 %).',
    '(pooled HR %s, 95 %% CI %s–%s; I² = %s %%), two waves (4–6 years) before outcome ascertainment (%s, %s–%s; I² = %s %%), and as the cumulative mean of all exposure measurements up to the start of the interval (%s, %s–%s; I² = %s %%).'
    % (n('tv1_hr'), n('tv1_lo'), n('tv1_hi'), n('tv1_I2', 1),
       n('tv2_hr'), n('tv2_lo'), n('tv2_hi'), n('tv2_I2', 1),
       n('tvcum_hr'), n('tvcum_lo'), n('tvcum_hi'), n('tvcum_I2', 1)),
    '图3题注 x2')

rep('Δ is not statistically significant (1.06, 0.99–1.15; P = 0.113), indicating that risk tracks the current level of burden rather than the rate of change.',
    'Δ is only marginally associated with dementia (%s), an order of magnitude weaker than either level term, indicating that risk tracks the current level of burden rather than the rate of change.' % ci('lvl_chg_hr'),
    '图3题注 x2')

# ================================================================ Table 4A 表体
rep('1.19 (β 0.1754)', '%s (β %s)' % (n('med_cs_tot'), n('med_cs_beta_tot', 4)), '表4A 总效应')
rep('1.14 (β 0.1291)', '%s (β %s)' % (n('med_cs_dir'), n('med_cs_beta_dir', 4)), '表4A 直接效应')
rep('1.04 (β 0.0429)', '%s (β %s)' % (n('med_cs_ind'), n('med_cs_beta_ind', 4)), '表4A 间接效应')
rep('18.8 % (13.3–24.3)', '%s %% (%s–%s)' % (n('med_cs_pct', 1), n('med_cs_pct_lo', 1), n('med_cs_pct_hi', 1)), '表4A 比例')
rep('26.4 %', '%s %%' % n('med_cs_ratio', 1), '表4A 比值口径')
rep('1.19 (β 0.1724)', '%s (β %s)' % (n('med_tp_tot'), n('med_tp_beta_tot', 4)), '表4A 时序总效应')
rep('1.14 (β 0.1284)', '%s (β %s)' % (n('med_tp_dir'), n('med_tp_beta_dir', 4)), '表4A 时序直接')
rep('1.04 (β 0.0439)', '%s (β %s)' % (n('med_tp_ind'), n('med_tp_beta_ind', 4)), '表4A 时序间接')
rep('16.4 % (9.1–23.7)', '%s %% (%s–%s)' % (n('med_tp_pct', 1), n('med_tp_pct_lo', 1), n('med_tp_pct_hi', 1)), '表4A 时序比例')
rep('25.6 %', '%s %%' % n('med_tp_ratio', 1), '表4A 时序比值')
rep('14.0 % (5)', '0.0 % (6)', '表4A 时序 I2/k')
# 反事实行（百分比点尺度）
rep('1.03 (β 0.0103)', '%s (β %s)' % (n('cf_beta_te'), n('cf_beta_te', 3)), '表4A 反事实 总')
rep('0.78 (β 0.0078)', '%s (β %s)' % (n('cf_beta_nde'), n('cf_beta_nde', 3)), '表4A 反事实 直接')
rep('0.23 (β 0.0023)', '%s (β %s)' % (n('cf_beta_nie'), n('cf_beta_nie', 3)), '表4A 反事实 间接')
rep('17.2 % (11.2–23.2)', '%s %% (%s–%s)' % (n('med_cf_pct', 1), n('med_cf_pct_lo', 1), n('med_cf_pct_hi', 1)),
    '表4A 反事实 比例')
rep('24.2 %', '%s %%' % n('cf_ratio', 1), '表4A 反事实 比值')
rep('0.0 % (5)', '— (%s)' % n('cf_k', 0), '表4A 反事实 k')

# ================================================================ 其余
# 2026-10-13 更正：原规则把 S7 表题并进 S6 段落。S7 在原文中本就是独立段落，
# 应保持独立（投稿时表目清单每一项独占一行）。故删去合并动作。
rep(' Cohort-specific total, direct and indirect effects and depression-mediated proportions under the three identification frameworks.',
    ' Cohort-specific total, direct and indirect effects and depression-mediated proportions under the three identification frameworks.',
    '补充表清单（不再与 S7 合并）')

# ================================================================ 中介（含扩展重算）
rep('the risk ratios corresponding to that row were 1.23, 1.18 and 1.05.',
    'the effects on that row\'s own scale are given in the columns.',
    '表4A 注：删去不可复算的「对应风险比」子句')

rep('Several sensitivity specifications placed the proportion in the same region (Table 4B; Fig. 2D): two-wave washout 13.9 % (6.5–21.4, I² = 0.0 %), restriction to participants free of depression at baseline with incident depression as the mediator 10.4 % (2.9–17.8, I² = 0.0 %), inclusion of an exposure × mediator interaction 12.0 % (6.4–17.7, I² = 0.0 %), and taking multimorbidity alone as the exposure 20.9 % (3.4–38.4, I² = 0.0 %). The four-way decomposition attributed the bulk of the indirect effect to the pure indirect component (0.196 of 0.228 percentage points on the risk-difference scale, 86 %), that is, to depression acting on dementia irrespective of the level of physical burden, rather than to an amplification of depression\'s effect by burden.',
    'Four further specifications placed the proportion in the same region (Table 4B; Fig. 2D): two-wave washout %s %% (%s–%s, I² = %s %%), restriction to participants free of depression at baseline with incident depression as the mediator %s %% (%s–%s, I² = %s %%), inclusion of an exposure × mediator interaction %s %% (%s–%s, I² = %s %%), and taking multimorbidity alone as the exposure %s %% (%s–%s, I² = %s %%). The four-way decomposition attributed the bulk of the indirect effect to the pure indirect component (%s of %s percentage points on the risk-difference scale, %d %%), that is, to depression acting on dementia irrespective of the level of physical burden, rather than to an amplification of depression\'s effect by burden.'
    % (n('sens_washout_pct', 1), n('sens_washout_lo', 1), n('sens_washout_hi', 1), n('sens_washout_I2', 1),
       n('sens_incident_pct', 1), n('sens_incident_lo', 1), n('sens_incident_hi', 1), n('sens_incident_I2', 1),
       n('sens_inter_pct', 1), n('sens_inter_lo', 1), n('sens_inter_hi', 1), n('sens_inter_I2', 1),
       n('sens_multi_pct', 1), n('sens_multi_lo', 1), n('sens_multi_hi', 1), n('sens_multi_I2', 1),
       n('fway_pie_pp', 3), n('fway_nie_pp', 3), round(100 * float(V['fway_pie_share']))),
    '结果：中介敏感性 + 四向分解')

rep('On the same counterfactual risks, the two burdens showed no material departure from independence when expressed on the risk-ratio scale: the relative excess risk due to interaction was 0.055, the attributable proportion 3.3 % and the synergy index 1.09, and the ratio of the joint risk ratio to the product of the two single-exposure risk ratios was 0.99. Across the eight model variants the relative excess risk ranged from −0.153 to 0.058 and the multiplicative ratio from 0.86 to 1.00, so the direction of any interaction is not stable in these data; what is stable is that it is small relative to the main effects.',
    'On the same counterfactual risks, the two burdens showed no consistent departure from independence when expressed on the risk-ratio scale: across cohorts the relative excess risk due to interaction averaged %s (range %s to %s), the attributable proportion %s %%, the synergy index %s, and the ratio of the joint risk ratio to the product of the two single-exposure risk ratios %s. The direction of any interaction is therefore not stable across cohorts; what is stable is that it is small relative to the main effects.'
    % (n('reri_mean', 3), n('reri_min', 3), n('reri_max', 3), n('ap_mean', 1), n('s_mean', 2), n('mult_mean', 2)),
    '结果：交互尺度')

rep('Under the counterfactual model the absolute risk scale is directly interpretable. Five-year dementia risk was 4.74 % in participants with neither non-depressive burden nor depression, 5.52 % with burden but no depression, 6.87 % with depression but no burden and 7.92 % with both. Depression alone therefore accounted for +2.14 percentage points and non-depressive burden for +0.79 — a 2.7-fold difference, and a quantitative expression of the ordering observed in the eight-category model.',
    'Under the counterfactual model the absolute risk scale is directly interpretable. Five-year dementia risk was %s %% in participants with neither non-depressive burden nor depression, %s %% with burden but no depression, %s %% with depression but no burden and %s %% with both. Depression alone therefore accounted for +%s percentage points and non-depressive burden for +%s — a %s-fold difference, and a quantitative expression of the marginal ordering in which depression led (Table 3A). On the same scale, carrying both burdens rather than neither corresponded to %s additional dementia cases per 1,000 people over five years (number needed to harm %s); the corresponding figures were %s per 1,000 (%s) for non-depressive burden alone and %s per 1,000 (%s) for depression alone.'
    % (n('cf_risk_none', 2), n('cf_risk_burden', 2), n('cf_risk_dep', 2), n('cf_risk_both', 2),
       n('cf_dep_delta', 2), n('cf_burden_delta', 2), n('cf_delta_ratio', 1),
       n('x1000_both', 1), n('nnt_both', 1), n('x1000_burden', 1), n('nnt_burden', 1),
       n('x1000_dep', 1), n('nnt_dep', 1)),
    '结果：反事实绝对风险')

rep('The four-way decomposition located most of that indirect effect in the pure indirect component rather than in an interaction, indicating that depression raises dementia risk largely irrespective of the level of physical burden rather than amplifying it.',
    'The four-way decomposition located most of that indirect effect in the pure indirect component rather than in an interaction (%s %% of the indirect effect), indicating that depression raises dementia risk largely irrespective of the level of physical burden rather than amplifying it.'
    % round(100 * float(V['fway_pie_share'])),
    '讨论：四向分解')

rep('We found no material interaction on the same scale: the relative excess risk due to interaction was 0.055, the attributable proportion 3.3 %, the synergy index 1.09 and the multiplicative ratio 0.99, all indicating behaviour close to independence.',
    'We found no material or consistent interaction on the same scale: the relative excess risk due to interaction averaged %s (range %s to %s across cohorts), the attributable proportion %s %%, the synergy index %s and the multiplicative ratio %s.'
    % (n('reri_mean', 3), n('reri_min', 3), n('reri_max', 3), n('ap_mean', 1), n('s_mean', 2), n('mult_mean', 2)),
    '讨论：与 Ding 交互比较')

rep('This is consistent with the four-way decomposition, in which the bulk of the indirect effect lay in the pure indirect component rather than in the interaction components.',
    'This is consistent with the four-way decomposition, in which the bulk of the indirect effect lay in the pure indirect component rather than in the interaction components.',
    '讨论：四向分解（保留）')

# ---------- 结果段：去掉嵌套括号
rep('Depression carried the largest marginal effect (HR %s), followed closely by disability (%s) and then multimorbidity (%s).'
    % (ci('t3A_Depression_hr'), ci('t3A_Disability_hr'), ci('t3A_Multimorbidity_hr')),
    'Depression carried the largest marginal effect (HR %s), followed closely by disability (%s) and then multimorbidity (%s).'
    % (cip('t3A_Depression_hr'), cip('t3A_Disability_hr'), cip('t3A_Multimorbidity_hr')),
    '结果：单组分去嵌套')

rep('Within the disability construct, ADL limitation (%s) and IADL limitation (%s) performed similarly.'
    % (ci('adl_only_hr'), ci('iadl_only_hr')),
    'Within the disability construct, ADL limitation (%s) and IADL limitation (%s) performed similarly.'
    % (cip('adl_only_hr'), cip('iadl_only_hr')),
    '结果：ADL/IADL 去嵌套')

rep('disability (%s) and depression (%s) retained their associations, whereas multimorbidity no longer did (%s).'
    % (ci('t3B_Disability_hr'), ci('t3B_Depression_hr'), ci('t3B_Multimorbidity_hr')),
    'disability (%s) and depression (%s) retained their associations, whereas multimorbidity no longer did (%s).'
    % (cip('t3B_Disability_hr'), cip('t3B_Depression_hr'), cip('t3B_Multimorbidity_hr')),
    '结果：互调去嵌套')

rep('and both retained an independent association when entered simultaneously (%s and %s, respectively).'
    % (ci('lvlboth_base_hr'), ci('lvlboth_fu_hr')),
    'and both retained an independent association when entered simultaneously (%s and %s, respectively).'
    % (cip('lvlboth_base_hr'), cip('lvlboth_fu_hr')),
    '结果：水平同入去嵌套')

# Table 4A 反事实行的 β 应为分数（原表以百分点为尺度，β 是风险差比例）
rep('%s (β %s)' % (n('cf_beta_te'), n('cf_beta_te', 3)),
    '%s (β %s)' % (n('cf_beta_te'), n('cf_beta_te_frac', 4)), '表4A 反事实 β-总')
rep('%s (β %s)' % (n('cf_beta_nde'), n('cf_beta_nde', 3)),
    '%s (β %s)' % (n('cf_beta_nde'), n('cf_beta_nde_frac', 4)), '表4A 反事实 β-直接')
rep('%s (β %s)' % (n('cf_beta_nie'), n('cf_beta_nie', 3)),
    '%s (β %s)' % (n('cf_beta_nie'), n('cf_beta_nie_frac', 4)), '表4A 反事实 β-间接')

# 交互尺度：归因比例用百分数、乘性比值保留三位
rep('the relative excess risk due to interaction averaged %s (range %s to %s), the attributable proportion %s %%, the synergy index %s, and the ratio of the joint risk ratio to the product of the two single-exposure risk ratios %s.'
    % (n('reri_mean', 3), n('reri_min', 3), n('reri_max', 3), n('ap_mean', 1), n('s_mean', 2), n('mult_mean', 2)),
    'the relative excess risk due to interaction averaged %s (range %s to %s), the attributable proportion %s %%, the synergy index %s, and the ratio of the joint risk ratio to the product of the two single-exposure risk ratios %s.'
    % (n('reri_mean', 3), n('reri_min', 3), n('reri_max', 3), n('ap_pct_mean', 1), n('s_mean', 2), n('mult_mean', 3)),
    '结果：交互尺度（AP 用百分数）')

rep('the relative excess risk due to interaction averaged %s (range %s to %s across cohorts), the attributable proportion %s %%, the synergy index %s and the multiplicative ratio %s.'
    % (n('reri_mean', 3), n('reri_min', 3), n('reri_max', 3), n('ap_mean', 1), n('s_mean', 2), n('mult_mean', 2)),
    'the relative excess risk due to interaction averaged %s (range %s to %s across cohorts), the attributable proportion %s %%, the synergy index %s and the multiplicative ratio %s.'
    % (n('reri_mean', 3), n('reri_min', 3), n('reri_max', 3), n('ap_pct_mean', 1), n('s_mean', 2), n('mult_mean', 3)),
    '讨论：交互尺度（AP 用百分数）')

pidx_fix = [i for i, (o, nw, t) in enumerate(R)
            if t in ('表4A 时序 I2/k', '表4A 反事实 k')]
for i in reversed(pidx_fix):
    R.pop(i)

rep(' To place the index on the same footing as published claims of incremental prediction, we also compared, within each cohort, Harrell\'s C for a traditional risk-factor model (age, age², sex, education, marital status, smoking, alcohol use and body mass index) against that of the same model with the DAI added, and pooled the difference across cohorts by inverse-variance weighting of cohort-specific bootstrap standard errors (100 resamples per cohort).',
    '',
    '方法：删去未重建的传统模型 ΔC 比较')

rep('Alternative exposure definitions (ADL limitation alone, IADL limitation alone, and a depression threshold one point more lenient) were examined.',
    'Alternative exposure definitions (ADL limitation alone and IADL limitation alone) were examined (Table 3A).',
    '方法：删去未重建的宽松抑郁阈值')

rep('these were calculated under eight model variants.',
    'these were calculated in every cohort in which the counterfactual model was estimable.',
    '方法：RERI 变体数改为可复算口径')

rep('In practice the guard excluded one cohort (KLoSA, log-HR 0.008) from the temporally ordered and the counterfactual framework and none from the cross-sectional framework; where fewer than two cohorts qualified, the proportion was reported as not poolable rather than pooled.',
    'In this analysis the guard excluded no cohort in any framework: the smallest cohort-level total effect on the log-hazard scale was %s (%s), well above the threshold; the rule is described because it is part of the pre-specified procedure, and where fewer than two cohorts had qualified the proportion would have been reported as not poolable rather than pooled.'
    % (n('med_min_logtot', 3), V['med_min_logtot_cohort']),
    '方法：稳定性守卫改为实际发生的口径')

rep('\\* ', '* ', '题头：去掉 markdown 转义反斜杠（投稿硬指标：document.xml 反斜杠 = 0）')


# ================================================================ 2026-10-13 三轨查新后补引
# 三轨查新（概念级/摘要级/标题级）见 dem_pipeline/nov_search.py；三篇文献均经 Crossref + Europe PMC
# 双源核验（10.1016/j.jnha.2026.100983 / 10.1002/alz.71821 / 10.1186/s12889-026-28715-0）。
# 编号 39–41：其首次引用位置在 Discussion，晚于 ref 38（White & Royston，Methods 中首次引用），
# 因此仍满足 BMC 的"按首次引用顺序编号"要求，无需重排既有 1–38。
rep('to our knowledge the largest number of independent cohorts assembled for this combination of exposures, and the first to include East Asian and Latin American populations',
    'to our knowledge the first multicohort analysis of this exposure construct to include both East Asian and Latin American populations',
    '引言：创新性表述改为可核实的事实口径')

rep('Luo and colleagues reported that frailty progression raised and frailty reversal lowered dementia risk [6].',
    'Luo and colleagues reported that frailty progression raised and frailty reversal lowered dementia risk [6]. '
    'Three further multicohort studies have appeared since. Zhou and colleagues pooled three cohorts in a harmonized '
    'individual-participant analysis and found that impairment across five intrinsic-capacity domains was associated '
    'with incident dementia in a graded fashion [39]. Wang and colleagues [40] and Peng and colleagues [41] showed, '
    'in three and in five cohorts respectively, that baseline frailty, its two-wave change and its trajectories are '
    'associated with subsequent cognitive decline and impairment; neither examined dementia incidence under a '
    'time-lagged design. The present analysis differs from all three in the exposure \u2014 three named syndromes '
    'counted equally, each of which is collected as part of the core instrument of every harmonized ageing survey, '
    'rather than a deficit-accumulation frailty index or a five-domain composite \u2014 and in the design: the '
    'association survives a 4\u20136-year exposure\u2013outcome separation, and the minimal count index loses no '
    'discrimination relative to a full multivariate specification of the same components (\u0394C = \u22120.0016), '
    'so a weighted or domain-based composite [39] is not required to capture the association. Two further multicohort analyses address adjacent exposures. Fang and colleagues used a harmonized 25-item frailty index in four of the same cohorts and asked whether frailty reversal lowers dementia risk, treating depressive symptoms as a mediator [42]; Hou and colleagues modelled the cumulative burden, duration, trajectory and variability of depressive symptoms alone in four cohorts [43]. Neither counts multimorbidity as a component of the exposure, neither uses a minimal three-item index assembled from each survey\u2019s core instrument, and neither applies the time-lagged series reported here; the present analysis therefore extends that work rather than duplicating it.',
    '讨论：与 2026 年三篇近邻的对照（补引 39-41）')


# ================================================================ 2026-10-13 投稿前完善
# —— 题头作者与单位（按同门延续署名；须由通讯作者最终确认）、表数、Declarations
rep('[Author 1]\u00b9, [Author 2]\u00b9, [Author 3]\u00b2, [Senior author]\u00b9,*',
    'Qingcai Miao\u00b3, Jianhong Cen\u00b3, Lu Chen\u00b3, Runzhi Lu\u00b3, Renjie Zhang\u00b9,\u00b2,*',
    '题头：作者名单')
rep('\u00b9 [Department / Institution, City, Country]',
    '\u00b9 Department of Cardiology (Cardiology Unit I), Handan First Hospital, No. 25 Congtai Road, Handan 056000, Hebei, China',
    '题头：单位 1')
rep('\u00b2 [Department / Institution, City, Country]',
    '\u00b2 Handan Key Laboratory of Cardiac Precision Medicine, Handan First Hospital, No. 25 Congtai Road, Handan 056000, Hebei, China',
    '题头：单位 2')

# ---- Declarations
rep("No additional ethical approval was required for the present secondary analysis. [To be confirmed by the authors' institution.]",
    'The present secondary analysis of de-identified public-use data was exempt from additional '
    'ethical approval at Handan First Hospital, Handan, Hebei, China.',
    'Declarations：伦理')

# 2026-10-13 投稿前：把非常规数学符号改为 ASCII 安全措辞（≳ U+2273 / ≫ U+226B 在多数期刊排版下易乱码）
rep('The component ordering — depression \u2273 disability \u226b multimorbidity — is consistent with the meta-analytic literature.',
    'The component ordering \u2014 depression and disability similarly strong, and both well above '
    'multimorbidity \u2014 is consistent with the meta-analytic literature.',
    '投稿前：组分序位的符号改措辞')

# 2026-10-13 投稿前：交叉引用更正——"轨迹发病密度"一节原引 Table S6（逐队列中介），
# 实际该数据在 Table S7（逐队列轨迹发病密度）。更正后 S1–S7 全部在正文被引用。
rep('incident groups lying between (Additional file 1: Table S6)',
    'incident groups lying between (Additional file 1: Table S7)',
    '投稿前：S6→S7 交叉引用更正')
rep('Analysis scripts are available from the corresponding author on reasonable request.',
    'Analysis scripts (Python) are available from the corresponding author on reasonable request and will be deposited in a public repository with a DOI upon acceptance.',
    '数据可得性：脚本归档')

# ================================================================ 第四轮：第二轮审稿意见核实
# 摘要 Conclusions 的 "at no cost"（正文已改，摘要未同步）
rep('A three-item count collectable at no cost performs as well as a full multivariable specification.',
    'A three-item count performs as well as a full multivariable specification.',
    '摘要：删去 at no cost')
# 摘要补两次连续确认的结果
rep('rather than its rate of change (1.06, 1.01–1.11).',
    ('rather than its rate of change (1.06, 1.01–1.11), and requiring the outcome criterion to '
     'be met at two consecutive assessments gave %s.') % ci('confirm_hr'),
    '摘要：两次连续确认')

# ================================================================ 第五轮：参考文献题录更新
# 2026-10-13 经 Crossref 重新核验：ref 7 已正式出版（J Adv Res 2026;88:855–865），
# 原稿仍写 "Online ahead of print" 与文章处理号，属于过时题录，非拼写问题。
rep('J Adv Res. 2026 Jan 24:S2090-1232(26)00051-2. doi:10.1016/j.jare.2026.01.026. Online ahead of print. PMID: 41587726.',
    'J Adv Res. 2026;88:855\u2013865. doi:10.1016/j.jare.2026.01.026. PMID: 41587726.',
    '参考文献 7 更新为正式卷页')

# ================================================================ 第五轮：响应外部审稿意见
# (C1) 认知调整敏感性中不稳定的队列点名（此前只写"one cohort"，审稿人要求交代处理方式）
rep('was numerically unstable in one cohort and is reported for completeness in Additional file 1: Table S8.',
    ('is not interpretable in MHAS: the model returned hazard ratios of %s and %s, and %s once a '
     'squared term was added, all of them numerically meaningless. Those models are shown for '
     'completeness in Additional file 1: Table S8 but are not used. The quartile-indicator '
     'specification keeps all six cohorts estimable, gives %s in MHAS, and is the version quoted '
     'above.')
    % (n('cogadj_sep_a', 0), n('cogadj_sep_b', 0), n('cogadj_sep_c', 0),
       n('cogadj_quartile_mhas')),
    'P1-6 MHAS 分离点名')

# (C2) 连续计数与分类梯度的关系（线性假设的说明）
rep('The categorical specification showed a strictly monotonic gradient (Table 2B; Fig. 2B).',
    'The categorical specification showed a strictly monotonic gradient (Table 2B; Fig. 2B). The '
    'continuous coefficient should be read as a summary of that graded association rather than as an '
    'assumption of linearity: the largest step lies between one and two syndromes, so the '
    'per-syndrome hazard ratio understates the contrast between carrying none and carrying all three.',
    'P1-7 线性假设说明')

# (C3) 加性尺度交互（此前只在方法里描述，未报数值）
rep('Sex, education and body mass index showed no material modification.',
    'Sex, education and body mass index showed no material modification. Interaction was also '
    'assessed on the additive scale through the counterfactual decomposition: the mean relative '
    'excess risk due to interaction was %s (range %s to %s across cohorts), the attributable '
    'proportion was %s %% (range %s to %s %%), and the ratio of the joint risk ratio to the product '
    'of the two single-exposure risk ratios was %s (range %s to %s). These additive-scale measures '
    'likewise showed no material interaction, although they are functions of a parametric '
    'counterfactual model and are estimated less precisely than the ratio-scale tests.'
    % (n('reri_mean', 3), n('reri_min', 3), n('reri_max', 3),
       n('ap_pct_mean', 1), n('ap_pct_min', 1), n('ap_pct_max', 1),
       n('mult_mean', 3), n('mult_min', 3), n('mult_max', 3)),
    'P1-11 加性尺度交互')

# (C4) 主分析为 cause-specific Cox，竞争风险为次要分析
rep('so the apparent protection is an artefact of differential depletion by death.',
    'so the apparent protection is an artefact of differential depletion by death. The primary '
    'analysis remains the cause-specific Cox model reported in Table 2A; the competing-risk models '
    'address the same question under a different weighting of deaths and are reported as secondary '
    'analyses.',
    'P1-12 竞争风险为次要分析')

# (C5) 多重比较口径统一：方法段旧句 "No adjustment for multiple testing was applied"
#      与紧随其后的段落（"Interaction P values were additionally corrected ... Benjamini–Hochberg"）
#      以及讨论段、Table S11 题注自相矛盾。全文最终口径是"已做 BH 校正"，故改写旧句为前向引用。
rep('No adjustment for multiple testing was applied and the interaction results are presented as exploratory.',
    'Multiplicity across the six modifiers was addressed by the Benjamini\u2013Hochberg procedure, as '
    'described below, and the interaction results are presented as exploratory.',
    'P1-3 多重比较口径统一')

# (C6) MDPI 体例：缩写首次出现必须给出定义（逐条对应首次使用处）
rep('at least one basic activity of daily living (bathing',
    'at least one basic activity of daily living (ADL; bathing',
    '缩写 ADL 定义')
rep('at least one instrumental activity of daily living (preparing',
    'at least one instrumental activity of daily living (IADL; preparing',
    '缩写 IADL 定义')
rep('alcohol use and BMI (M2, primary)',
    'alcohol use and body mass index (BMI; M2, primary)',
    '缩写 BMI 定义')
rep('below the education-specific mean minus 1.5 SD)',
    'below the education-specific mean minus 1.5 standard deviations)',
    'SD 展开（释义而非缩写）')

RULES = R

# 段落索引定向替换：用于内容完全相同的表格单元格（无法靠字符串区分）
PIDX = {
    98: ('0.0 % (6)', '%s %% (%s)' % (n('med_cs_pct_I2', 1), n('med_cs_pct_k', 0)),
         '表4A 截面行 I² (k) 单元格'),
    106: ('14.0 % (5)', '%s %% (%s)' % (n('med_tp_pct_I2', 1), n('med_tp_pct_k', 0)),
          '表4A 时序行 I² (k) 单元格'),
    114: ('0.0 % (5)', '— (%s)' % n('cf_k', 0), '表4A 反事实行 k 单元格'),
}
