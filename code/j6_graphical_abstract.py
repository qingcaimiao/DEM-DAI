# -*- coding: utf-8 -*-
"""j6_graphical_abstract.py —— 生成图形摘要（JCM/MDPI：PNG，宽≥1100 px、高≥560 px）

设计：独立的概念图（非正文任何图的复制，也非其子图拼接），展示
   三种老年综合征 → DAI 计数(0–3) → 新发痴呆，并给出关键数字。
"""
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.stdout.reconfigure(encoding='utf-8')
PKG = r'D:/桌面/AIzuopin/痴呆/投稿包_JCM_20261014'
os.makedirs(PKG, exist_ok=True)

plt.rcParams.update({'font.family': 'Arial', 'text.color': '#111111',
                     'savefig.facecolor': 'white', 'savefig.dpi': 200,
                     'savefig.bbox': 'tight', 'savefig.pad_inches': 0.12})

NAVY, TEAL, AMBER, RED, GREY, LINE = '#1f4e79', '#2e8b8b', '#c97b1e', '#a83232', '#5a6672', '#9aa5b1'

fig = plt.figure(figsize=(11.0, 5.6))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 100)
ax.set_ylim(0, 56)
ax.axis('off')


def box(x, y, w, h, fc, ec, alpha=0.10, r=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.4,rounding_size=%.1f' % r,
                                linewidth=1.4, edgecolor=ec, facecolor=fc, alpha=alpha, zorder=1))


def solid(x, y, w, h, ec, r=1.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.4,rounding_size=%.1f' % r,
                                linewidth=1.8, edgecolor=ec, facecolor='white', zorder=2))


def arrow(x1, y1, x2, y2, color=LINE, lw=2.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=16,
                                 linewidth=lw, color=color, zorder=3,
                                 shrinkA=2, shrinkB=2))


# ---- 左：三种综合征
comps = [('Disability', 'At least one ADL or IADL limitation', NAVY),
         ('Multimorbidity', 'Two or more physician-diagnosed chronic conditions', TEAL),
         ('Depression', 'Above a harmonized cohort-specific threshold', AMBER)]
for i, (name, desc, col) in enumerate(comps):
    y = 36 - i * 11.5
    box(1.5, y, 26, 9.4, col, col)
    ax.text(4.0, y + 6.0, name, fontsize=12.5, fontweight='bold', color=col, va='center')
    ax.text(4.0, y + 2.6, desc, fontsize=8.2, color=GREY, va='center')

# 汇合括号
arrow(28.0, 40.7, 35.0, 33.0)
arrow(28.0, 29.2, 35.0, 29.5)
arrow(28.0, 17.7, 35.0, 26.0)

# ---- 中：DAI 指数
solid(35.5, 22.0, 25.0, 14.5, '#1f4e79')
ax.text(48.0, 32.6, 'Geriatric syndrome', fontsize=12.0, fontweight='bold', color=NAVY, ha='center')
ax.text(48.0, 29.2, 'accumulation index (DAI)', fontsize=12.0, fontweight='bold', color=NAVY, ha='center')
ax.text(48.0, 25.0, 'unweighted count, range 0\u20133', fontsize=9.6, color=GREY, ha='center')

arrow(61.0, 29.2, 68.0, 29.2, color=RED, lw=2.4)

# ---- 右：结局
box(68.5, 21.5, 30.0, 15.5, RED, RED, alpha=0.10)
ax.text(83.5, 32.4, 'Incident dementia', fontsize=13.0, fontweight='bold', color=RED, ha='center')
ax.text(83.5, 27.6, 'per additional syndrome:', fontsize=9.6, color=GREY, ha='center')
ax.text(83.5, 24.3, 'HR 1.27 (95 % CI 1.21\u20131.33)', fontsize=11.6, fontweight='bold',
        color='#111111', ha='center')

# ---- 顶部标题
ax.text(50, 52.0, 'Cumulative burden of three geriatric syndromes and incident dementia',
        fontsize=14.0, fontweight='bold', color='#111111', ha='center')
ax.text(50, 47.8, 'Six harmonized ageing cohorts on three continents; time-lagged analysis',
        fontsize=10.5, color=GREY, ha='center')

# ---- 底部关键数字
ax.plot([1.5, 98.5], [14.0, 14.0], color='#e3e7ea', lw=1.2, zorder=0)
stats = [('71,867', 'participants'),
         ('11,185', 'incident cases'),
         ('694,305', 'person-years'),
         ('12.7\u201317.4 %', 'mediated by depression')]
for i, (big, small) in enumerate(stats):
    x = 14.5 + i * 23.5
    ax.text(x, 9.4, big, fontsize=13.0, fontweight='bold', color=NAVY, ha='center')
    ax.text(x, 6.2, small, fontsize=8.8, color=GREY, ha='center')

ax.text(50, 2.2, 'CHARLS  ·  ELSA  ·  HRS  ·  KLoSA  ·  MHAS  ·  SHARE        |        '
                 'Estimate unchanged after excluding the first 2\u201312 years of follow-up',
        fontsize=8.6, color=GREY, ha='center')

out = os.path.join(PKG, 'Graphical_Abstract_JCM.png')
fig.savefig(out)
plt.close(fig)

from PIL import Image  # noqa: E402
im = Image.open(out)
print('写出 %s  %d × %d px  (最小要求 1100 × 560)' % (out, im.width, im.height))
assert im.width >= 1100 and im.height >= 560
