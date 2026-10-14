# -*- coding: utf-8 -*-
"""p37_denominator_check.py —— Table 4D 末行「随访时间改变人数」的分母口径核验

背景（外部审稿 P1）：表注称
  "Every row is estimated on the same 66,765 participants ... changing the
   follow-up time of 13,961 of the 71,867 participants (19.4 %)"
前句行样本 = 66,765（完整暴露 + 完整 M2 协变量）；
后句分母 = 71,867（完整暴露全样本）。两者口径不同，形成歧义。

本脚本从 _surv_*.parquet 直接复算：
  (a) 完整暴露全样本（Table 1 口径）的 N 与 changed 数、百分比
  (b) M2 完整协变量子集（Table 2A/4D 行样本口径）的 N 与 changed 数、百分比
  (c) 逐队列分解，定位差额来源
并打印 13,961 − (M2 内 changed) 的差额，说明差额落在被 M2 剔除的 5,102 人里。

changed 定义与 p17_ms_numbers.py 完全一致：T > T_sens + 1e-9
（即「向死亡年延伸随访」相对「截尾于末次认知评估」多出的随访时间 > 0）。
"""
import os
import glob
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
COHORTS = L.COHORTS


def m2_mask(df):
    """与 p12_outcomes.fitM2 / p4 完全一致：对 [dur, E, dai3] + design_frame 列 dropna。"""
    X = L.design_frame(df)
    d = pd.concat([df[['T', 'E', 'dai3']], X], axis=1)
    return d.notna().all(axis=1)


rows = []
tot_all = ch_all = tot_m2 = ch_m2 = 0
for co in COHORTS:
    p = os.path.join(OUT, '_surv_%s.parquet' % co)
    if not os.path.exists(p):
        continue
    d = pd.read_parquet(p)
    # 完整暴露全样本：dai3 非缺失、E/T 可定义（与 p17 口径一致，p17 未再筛协变量）
    fd = d[d['dai3'].notna() & d['T'].notna() & d['E'].notna()].copy()
    changed_all = int((fd['T'] > fd['T_sens'] + 1e-9).sum())
    # M2 完整协变量子集
    mm = m2_mask(fd)
    sub = fd[mm]
    changed_m2 = int((sub['T'] > sub['T_sens'] + 1e-9).sum())
    rows.append(dict(cohort=co, n_all=len(fd), changed_all=changed_all,
                     n_m2=len(sub), changed_m2=changed_m2,
                     pct_all=100.0 * changed_all / max(len(fd), 1),
                     pct_m2=100.0 * changed_m2 / max(len(sub), 1)))
    tot_all += len(fd); ch_all += changed_all
    tot_m2 += len(sub); ch_m2 += changed_m2

t = pd.DataFrame(rows)
t.to_csv(os.path.join(OUT, '_t4d_denominator_check.csv'), index=False)

print('=== 逐队列分解 ===')
print(t.to_string(index=False, float_format=lambda x: '%.1f' % x))
print()
print('=== 汇总 ===')
print('完整暴露全样本       : N = %d , changed = %d  (%.1f %%)' % (tot_all, ch_all, 100.0 * ch_all / tot_all))
print('M2 完整协变量子集    : N = %d , changed = %d  (%.1f %%)' % (tot_m2, ch_m2, 100.0 * ch_m2 / tot_m2))
print('被 M2 剔除者         : N = %d , 其中 changed = %d' % (tot_all - tot_m2, ch_all - ch_m2))
print()
print('稿件现值核对:')
print('  tsens_changed_n (全样本) = 13961  ->  复算 = %d  %s' % (ch_all, 'OK' if ch_all == 13961 else 'MISMATCH'))
print('  tsens_total_n   (全样本) = 71867  ->  复算 = %d  %s' % (tot_all, 'OK' if tot_all == 71867 else 'MISMATCH'))
print('  13,961 / 71,867 = %.1f %%   (稿件印 19.4 %%)' % (100.0 * ch_all / tot_all))
print('  M2 内 changed / N = %d / %d = %.1f %%' % (ch_m2, tot_m2, 100.0 * ch_m2 / tot_m2))
print()
# 与用户外部复算的 13,339/20.0% 对照
print('外部审稿复算 claim: 13,339 / 66,765 = 20.0 %%  ->  本脚本 = %d / %d = %.1f %%'
      % (ch_m2, tot_m2, 100.0 * ch_m2 / tot_m2))
