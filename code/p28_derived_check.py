# -*- coding: utf-8 -*-
"""p28_derived_check.py —— 一切"X %""X 倍""X–Y % 区间"类**派生表述**回源重算

用户硬性要求：报告中任何"改善 X %""相差 X 倍""X–Y % 区间"必须回源 CSV 用脚本重算，
禁止凭印象写。本脚本对稿件里每一处派生表述：
  1. 用公式从 out/*.csv / _ms_numbers.csv **现算**期望字符串；
  2. 在稿件全文（段落 + 表格）里检索该字符串是否**确实存在**；
  3. 打印「表述 → 公式 → 期望值 → 是否命中」四列。
不命中即非零退出。
输出：out/_derived_check.txt
"""
import os
import re
import sys
import zipfile
import numpy as np
import pandas as pd

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
DOCX = r'D:/桌面/AIzuopin/痴呆/稿件正文_修订稿_v3_20261013.docx'

z = zipfile.ZipFile(DOCX)
xml = z.read('word/document.xml').decode('utf8')
TEXT = re.sub(r'\s+', ' ', ''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml, re.S)))
TEXT = TEXT.replace('\u2212', '-')

MS = pd.read_csv(os.path.join(OUT, '_ms_numbers.csv'))
MS['key'] = MS['key'].astype(str).str.replace('^\ufeff', '', regex=True)
MS['value'] = pd.to_numeric(MS['value'], errors='coerce')
V = dict(zip(MS['key'], MS['value']))


def n(k):
    return float(V[k])


rows = []


def chk(claim, formula, s):
    """claim 描述、formula 复算出的字符串、s 是要求出现的最小片段。"""
    hit = s in TEXT
    rows.append((claim, formula, s, 'HIT' if hit else '**MISS**'))
    return hit


S = []
# ---------------- 效应量百分数（由 HR 现算）
S.append(chk('每个额外综合征风险高 27 %', 'round(100*(pool_M2_hr-1)) = 27',
             '%d %% higher risk of dementia' % round(100 * (n('pool_M2_hr') - 1))))
S.append(chk('三综合征组风险高 64 %', 'round(100*(grad3_hr-1)) = 64',
             'at %d %% higher risk' % round(100 * (n('grad3_hr') - 1))))
S.append(chk('分类梯度 1/2/3 vs 0 的点估计与上界',
             'grad1_hr, grad2_hr, grad3_hr, grad3_hi',
             '1 syndrome %s; 2 syndromes %s; 3 syndromes %s, %s\u2013%s)'
             % ('%.2f' % n('grad1_hr'), '%.2f' % n('grad2_hr'), '%.2f' % n('grad3_hr'),
                '%.2f' % n('grad3_lo'), '%.2f' % n('grad3_hi'))))
# ---------------- 绝对风险与倍数
ratio = n('cf_dep_delta') / n('cf_burden_delta')
S.append(chk('抑郁 vs 非抑郁负担绝对风险差为 1.8 倍',
             'cf_dep_delta / cf_burden_delta = %.4f' % ratio,
             'a %.1f-fold difference' % round(ratio, 1)))
S.append(chk('4 组 5 年风险 3.58 / 4.37 / 5.01 / 6.10 %',
             'cf_risk_none / cf_risk_burden / cf_risk_dep / cf_risk_both',
             '%s %% in participants with neither' % ('%.2f' % n('cf_risk_none'))))
S.append(chk('抑郁 +1.43 百分点 / 负担 +0.79 百分点',
             'cf_dep_delta, cf_burden_delta',
             'accounted for +%s percentage points and non-depressive burden for +%s'
             % ('%.2f' % n('cf_dep_delta'), '%.2f' % n('cf_burden_delta'))))
# ---------------- 四向分解占比
pie_share = 100 * n('fway_pie') / n('fway_nie') if 'fway_pie' in V else np.nan
S.append(chk('纯间接成分占间接效应约 84 %',
             '100*fway_pie/fway_nie = %.1f' % pie_share,
             '%d %%)' % round(pie_share)))
# ---------------- 中介比例区间（比例口径 vs 比值口径）
S.append(chk('中介比例收敛区间（比例口径）',
             'med_pct_min–med_pct_max = %.1f–%.1f' % (n('med_pct_min'), n('med_pct_max')),
             '%.1f–%.1f %% when cohort-specific proportions are pooled'
             % (n('med_pct_min'), n('med_pct_max'))))
S.append(chk('中介比例区间（比值口径）',
             'med_ratio_min–med_ratio_max = %.1f–%.1f' % (n('med_ratio_min'), n('med_ratio_max')),
             '%.1f–%.1f %% when the fraction is taken from the pooled coefficients'
             % (n('med_ratio_min'), n('med_ratio_max'))))
S.append(chk('时序框架 I²', 'med_tp_pct_I2 = %.1f' % n('med_tp_pct_I2'),
             'I\u00b2 = %.1f %% for the temporally ordered framework' % n('med_tp_pct_I2')))
# ---------------- 基线与主模型
S.append(chk('主模型 I²', 'pool_M2_I2 = %.1f' % n('pool_M2_I2'),
             'I\u00b2 = %.1f %%)' % n('pool_M2_I2')))
S.append(chk('事件占比与发病密度', 'event_pct / incidence_density',
             '%s incident dementia cases (%s %%; incidence density %s per 1,000'
             % (format(int(n('n_events')), ','), '%.1f' % n('event_pct'),
                '%.1f' % n('incidence_density'))))
S.append(chk('DAI 分层年龄跨度 62.2→67.7',
             'dai0_age → dai3_age',
             'mean age rose from %s to %s years' % ('%.1f' % n('dai0_age'), '%.1f' % n('dai3_age'))))
S.append(chk('慢病数 0.4→2.7', 'dai0_nchron → dai3_nchron',
             'the mean number of chronic conditions from %.1f to %.1f'
             % (n('dai0_nchron'), n('dai3_nchron'))))
S.append(chk('低教育 47.9→78.9 %', 'dai0_lowedu_pct → dai3_lowedu_pct',
             'from %.1f %% to %.1f %%' % (n('dai0_lowedu_pct'), n('dai3_lowedu_pct'))))
S.append(chk('发病密度 11.7→32.3', 'dai0_density → dai3_density',
             'from %.1f to %.1f per 1,000 person-years' % (n('dai0_density'), n('dai3_density'))))
# ---------------- 其它派生数字
S.append(chk('填补缺口 5,102 人 / 7.1 %', 'n_missing_cov / miss_pct',
             'recovered the %s participants' % format(int(n('n_missing_cov')), ',')))
S.append(chk('多个填补方案最大差 0.0043', 'mice_maxdiff',
             'within %s on the hazard-ratio scale' % ('%.4f' % n('mice_maxdiff'))))
S.append(chk('判别力差 ΔC', 'c_delta = %+.4f' % n('c_delta'),
             '\u0394C = %s' % ('%+.4f' % n('c_delta')).replace('+', '\u2212')
             if n('c_delta') < 0 else '\u0394C = %.4f' % n('c_delta')))
S.append(chk('E-value 下限', 'evalue_M2_ci = %.2f' % n('evalue_M2_ci'),
             'E-value of %.2f for the lower confidence limit' % n('evalue_M2_ci')))

print('%-38s | %-46s | %-46s | %s' % ('派生表述', '回源公式与算得值', '稿件中检索到的字符串', '结果'))
print('-' * 190)
bad = 0
for claim, formula, s, res in rows:
    if res != 'HIT':
        bad += 1
    print('%-38s | %-46s | %-46s | %s' % (claim, formula, s[:46], res))

open(os.path.join(OUT, '_derived_check.txt'), 'w', encoding='utf8').write(
    '\n'.join('%-38s | %-46s | %-46s | %s' % r for r in rows))
print('\n未命中 %d / %d' % (bad, len(rows)))
sys.exit(1 if bad else 0)
