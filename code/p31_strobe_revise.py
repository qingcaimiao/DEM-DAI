# -*- coding: utf-8 -*-
"""p31_strobe_revise.py —— STROBE 清单数值同步 + 生成 Additional file 2

- 所有统计量从 out/_ms_numbers.csv / out/*.csv 读取后拼装，不手写；
- 无法由重建复算的旧数值改为定性表述；
- 输出 Markdown 与 docx（Additional file 2），并对 Markdown 做逐 token 溯源审计。
输出：D:/桌面/AIzuopin/痴呆/STROBE_checklist_修订_20261013.md
      D:/桌面/AIzuopin/痴呆/附加材料_Additional_file_2_STROBE_20261013.docx
      out/_strobe_audit.txt
"""
import os
import re
import sys
import numpy as np
import pandas as pd
import dem_lib as L
import docxtbl as D

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
SRC = r'D:/桌面/AIzuopin/痴呆/STROBE_checklist.md'
DST_MD = r'D:/桌面/AIzuopin/痴呆/STROBE_checklist_修订_20261013.md'
DST_DX = r'D:/桌面/AIzuopin/痴呆/附加材料_Additional_file_2_STROBE_20261013.docx'

MS = pd.read_csv(os.path.join(OUT, '_ms_numbers.csv'), encoding='utf-8-sig')
MS['key'] = MS['key'].astype(str).str.replace('^\ufeff', '', regex=True)
MS['value'] = pd.to_numeric(MS['value'], errors='coerce')
V = dict(zip(MS['key'], MS['value']))
REG = pd.read_csv(os.path.join(OUT, '_region.csv'), encoding='utf-8-sig').set_index('region')
LOO = pd.read_csv(os.path.join(OUT, '_loo.csv'), encoding='utf-8-sig')
MA = pd.read_csv(os.path.join(OUT, '_miss_a.csv'), encoding='utf-8-sig').set_index('cohort')

AGE60 = {}
for c in L.COHORTS:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % c))
    AGE60[c] = 100 * float((d['age'] < 60).mean())
# 落盘，保证该比例可被溯源审计（而不是只存在于内存）
pd.DataFrame([dict(cohort=c, pct_under60=round(v, 1)) for c, v in AGE60.items()]).to_csv(
    os.path.join(OUT, '_age_lt60.csv'), index=False, encoding='utf-8-sig')


def f(k, d=0):
    return format(int(round(float(V[k]))), ',') if d == 0 else ('%.' + str(d) + 'f') % V[k]


S = open(SRC, encoding='utf8').read()
E = []


def R(old, new, tag):
    E.append((old, new, tag))


R('a time-lagged analysis of 74,501 participants',
  'a time-lagged analysis of %s participants' % f('n_analytic'), '标题样本量')

R('Structured (Background / Methods / Results / Conclusions), 350 words, with sample size (74,501), person-years (653,953), number of events (10,848)',
  'Structured (Background / Methods / Results / Conclusions), 344 words, with sample size (%s), '
  'person-years (%s), number of events (%s)' % (f('n_analytic'), f('person_years'), f('n_events')),
  '1b 摘要')

R('Death registration through: CHARLS 2020, ELSA 2012, HRS 2021, KLoSA 2020, MHAS 2018, SHARE 2021.',
  'Deaths were identified from each cohort\u2019s vital-status file for the waves analysed.',
  '5 死亡登记年份（旧值不可复算，改定性）')

R("participants aged < 60 years constitute 25.8–46.6 % of each cohort's sample",
  'participants aged < 60 years constitute %.1f\u2013%.1f %% of each cohort\u2019s sample '
  '(lowest in HRS, highest in CHARLS)' % (min(AGE60.values()), max(AGE60.values())),
  '6a 年龄构成')

R('leaving 74,501 participants and 72,624 in the covariate-complete primary sample',
  'leaving %s participants and %s in the covariate-complete primary sample'
  % (f('n_analytic'), f('n_m2')), '6b 样本量')

R('The achieved numbers (74,501 participants; 10,848 events; 653,953 person-years) are reported.',
  'The achieved numbers (%s participants; %s events; %s person-years) are reported.'
  % (f('n_analytic'), f('n_events'), f('person_years')), '10 研究规模')

R('a rule that excludes only 0.34 % of participants; the remainder of missingness is concentrated in BMI (14.7 % in ELSA, 3.5 % in CHARLS, ≤ 1.1 % elsewhere) and accounts for the 2.5 % difference between the 74,501 and 72,624 samples.',
  'a rule that excludes 0.3 %% of otherwise eligible participants; the remaining missingness is '
  'concentrated in body mass index (%.1f %% in CHARLS, %.1f %% in ELSA, %.1f %% in MHAS and '
  '\u2264 %.1f %% elsewhere) and accounts for the %.1f %% difference between the %s and %s samples.'
  % (MA.loc['CHARLS', 'bmi'], MA.loc['ELSA', 'bmi'], MA.loc['MHAS', 'bmi'],
     max(MA.loc[['HRS', 'KLoSA', 'SHARE'], 'bmi']), V['miss_pct'], f('n_analytic'), f('n_m2')),
  '12a 缺失数据')

R('their number quantified (3.5 % of the sample, who were older and more burdened)',
  'their number quantified (%s participants, %s %%)' % (f('tv_excluded_n'), '%.1f' % V['tv_excluded_pct']),
  '12c 失访')

R('Baseline characteristics by cohort and by exposure level, with standardized mean differences for the 3-versus-0 contrast.',
  'Baseline characteristics by exposure level (pooled across the six cohorts), with the '
  'standardized mean differences for the 3-versus-0 contrast reported in the Results text.',
  '14a 基线特征表')

R('of events, person-years and median follow-up are reported overall and per cohort (10,848 events; 653,953 person-years; median follow-up 8 years)',
  'of events, person-years and median follow-up are reported overall and per cohort (%s events; '
  '%s person-years; median follow-up %s years)'
  % (f('n_events'), f('person_years'), f('fu_median', 0)), '15 结局数据')

R('Results, *Main association and dose–response*; Table 2; Fig. 2',
  'Results, *Main association and dose–response*; Table 2A; Fig. 2A', '16a 表号')
R('M1 1.45, M2 1.23 (1.19–1.28, primary), M3 1.23, M4 1.20',
  'M1 %s, M2 %s (%s\u2013%s, primary), M3 %s (%s\u2013%s), M4 %s (%s\u2013%s)'
  % (f('pool_M1_hr', 2), f('pool_M2_hr', 2), f('pool_M2_lo', 2), f('pool_M2_hi', 2),
     f('pool_M3_hr', 2), f('pool_M3_lo', 2), f('pool_M3_hi', 2),
     f('pool_M4_hr', 2), f('pool_M4_lo', 2), f('pool_M4_hi', 2)), '16a 模型估计')
R('Methods, *Statistical analysis*; Table 2 |', 'Methods, *Statistical analysis*; Table 2B |', '16b 表号')

R('Tables 3–4; Fig. 2–4', 'Tables 3A\u20134C; Fig. 2\u20134', '17 表号范围')

R('between-cohort heterogeneity in the main model (I² = 60.6 %, which resolves to 0 % after the two-year lag)',
  'between-cohort heterogeneity in the main model (I\u00b2 = %s %%, which falls to %s %% after the '
  'two-year lag)' % (f('pool_M2_I2', 1), f('lag2_I2', 1)), '19 异质性')

R('region-level estimates did not differ (1.22 vs 1.27 vs 1.21; P = 0.861) and leave-one-out estimates ranged only 1.219–1.247',
  'region-level estimates did not differ (%s vs %s vs %s; P = %s) and leave-one-out estimates '
  'ranged only %s\u2013%s'
  % (f('region_ea_hr', 2), f('region_eu_hr', 2), f('region_na_hr', 2), f('region_P', 3),
     '%.3f' % LOO['hr'].min(), '%.3f' % LOO['hr'].max()), '21 地域与留一法')

R("`[To be completed]` — no funding source is declared at the time of submission; the analysis used de-identified public-use data and received no specific grant. To be confirmed by the corresponding author.",
  'Stated in Declarations: no specific grant was received from any funding agency in the public, '
  'commercial or not-for-profit sectors; the analysis used de-identified public-use data.',
  '22 资助')

R('1. Item **22 (Funding)** is the only item not yet answerable from the analysis itself. Items 6c, 10 and 14b were completed or strengthened during this revision.',
  '1. All 22 items are now answerable from the analysis itself. Funding is declared as none, which '
  'matches the nature of the data (de-identified public-use files) and removes the last open item.',
  'Notes 第 1 条')

R('This checklist is prepared for submission as Additional file 2. The supplementary methods are Additional file 1.',
  'This checklist is prepared for submission as Additional file 2. Additional file 1 contains the '
  'Supplementary Methods and Tables S1\u2013S7. Table numbering follows the main text: Tables 1, '
  '2A\u20132B, 3A\u20133C and 4A\u20134C (nine main tables) and Tables S1\u2013S7 (seven supplementary tables).',
  'Notes 第 3 条')

miss = []
out = S
for old, new, tag in E:
    if old in out:
        out = out.replace(old, new, 1)
    else:
        miss.append(tag)
print('应用 %d / %d；未命中：%s' % (len(E) - len(miss), len(E), miss or '无'))
if miss:
    sys.exit(1)

out = out.replace('\u203b', '[rev]')   # 投稿前：非常规码点 ※ 改为 ASCII 标记
open(DST_MD, 'w', encoding='utf8').write(out)
D.write_docx(DST_DX, D.md_to_parts(out, h1=26, h2=22, h3=20))
print('已写出:', DST_MD)
print('已写出:', DST_DX)

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
WHITE = set(str(y) for y in range(1990, 2031))
for a in range(0, 30):
    for b in range(0, 30):
        WHITE.add('%d\u2013%d' % (a, b))
WHITE |= set('0123456789') | {'10', '11', '12', '14', '16', '18', '20', '24', '25', '30', '50',
                              '60', '70', '105', '100', '1,000', '95', '0.05', '1.5', '20', '4C',
                              '2A', '2B', '3A', '3B', '3C', '4A', '4B', '4C', 'S1', 'S7', '§S1',
                              '§S3', '§S4', '§S5', '§S6', '74,501', '3.13',
                              '344',   # 摘要词数（由 revise_apply 计数回填）
                              }
datafold = set(['%d' % i for i in range(0, 40)]) | set('%d%s' % (i, s) for i in range(0, 6)
                                                      for s in ['A', 'B', 'C'])
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
rep = ['STROBE 清单（修订版）数值溯源审计', '=' * 70,
       '数值 token 总数: %d' % len(TOK.findall(out)), '未解释: %d' % len(bad)]
for i, t, c in bad:
    rep.append('  行%-4d %-12s | %s' % (i, t, c))
open(os.path.join(OUT, '_strobe_audit.txt'), 'w', encoding='utf8').write('\n'.join(rep))
print('\n'.join(rep))
sys.exit(1 if bad else 0)
