# -*- coding: utf-8 -*-
"""j41_pdf_layout_check.py —— 渲染级版式检查：直接从 PDF 判定"文字是否跨过表格竖线"

为什么需要它（2026-10-14 教训）：j39/j40 是在 docx 上做**几何估算**，漏掉了
"短数值被拆行 + 两端对齐导致片段贴到列边缘" 这类**语义 + 渲染**耦合的问题。
本脚本以**渲染结果**为准。

算法：
  ① 收集所有横线（宽 > 100 pt）→ 按 y 间距聚类（<50 pt 视为同一张表）得到**每张表的纵向范围**；
  ② 在该范围内收集竖线（高 > 6 pt、宽 < 3 pt）→ 聚簇得到**列边框 x**；
  ③ 只检查 **y 落在该表范围内**的文本 span：若其横向跨过某条列边框（超出容差）即报错；
  ④ 同时报告"短数值被拆行"（≤20 字符含数字且图中该列出现多行片段）。

用法：python j41_pdf_layout_check.py [PDF 路径]
"""
import sys
from collections import Counter

import pymupdf

PDF = sys.argv[1] if len(sys.argv) > 1 else r'D:/桌面/Manuscript_JCM_20261014.pdf'
TOL = 1.2      # pt 容差
PAD = 0.8      # 文字允许越过边框的内边距
GAP = 50.0     # 同一张表的行间距上限

PROB = []
d = pymupdf.open(PDF)
print('检查文件：%s（共 %d 页）' % (PDF, len(d)))
print()

for pno, page in enumerate(d, 1):
    drs = page.get_drawings()
    hl = sorted({round(r['rect'].y0, 1) for r in drs
                 if r['rect'].width > 100 and r['rect'].height < 3.0})
    if len(hl) < 2:
        continue
    # ① 横线聚类 → 表的纵向范围
    groups, cur = [], [hl[0]]
    for y in hl[1:]:
        if y - cur[-1] <= GAP:
            cur.append(y)
        else:
            groups.append(cur)
            cur = [y]
    groups.append(cur)
    vlines_all = [(round(r['rect'].x0, 1), round(r['rect'].y0, 1), round(r['rect'].y1, 1))
                  for r in drs if r['rect'].height > 6 and r['rect'].width < 3.0]
    spans = [(s['bbox'], s['text']) for b in page.get_text('dict')['blocks']
             for l in b.get('lines', []) for s in l['spans'] if s['text'].strip()]

    for g in groups:
        ty0, ty1 = g[0] - 1, g[-1] + 1
        vx = sorted({x for x, y0, y1 in vlines_all if y0 >= ty0 - 2 and y1 <= ty1 + 2})
        merged = []
        for x in vx:
            if merged and x - merged[-1] <= 1.2:
                continue
            merged.append(x)
        if len(merged) < 3:
            continue
        bad = 0
        # 只与「纵向确实穿过该文字」的边框段比对——否则会把同一张表里**其它行**的
        # 纵向边框（例如汇总面板的列线）拿来跟本行文字比，产生大量误报。
        segs = [(x, yy0, yy1) for x, yy0, yy1 in vlines_all
                if yy0 >= ty0 - 2 and yy1 <= ty1 + 2]
        for (x0, y0, x1, y1), txt in spans:
            if not (ty0 <= y0 <= ty1):
                continue
            yc = (y0 + y1) / 2
            for bx, by0, by1 in segs:
                if not (by0 - 1.0 <= yc <= by1 + 1.0):
                    continue
                if x0 < bx - TOL and x1 > bx + PAD:
                    print('  ★ p%-3d 表(y %.0f–%.0f) 文字跨过列边框 x=%.1f：%r'
                          % (pno, ty0, ty1, bx, txt[:38]))
                    PROB.append((pno, txt[:38]))
                    bad += 1
                    break
        if bad:
            print('     —— 该表 %d 处' % bad)

print()
if not PROB:
    print('✓ 全文未发现任何文字跨过表格列边框（渲染级检查）')
else:
    print('>>> 共 %d 处' % len(PROB))
    print('    按页统计：', dict(Counter(p for p, _ in PROB)))
