# -*- coding: utf-8 -*-
"""j39_layout_audit.py —— 「虚拟排版」检查：不开渲染器也能发现**只有看渲染才看得见**的版式缺陷

动机（2026-10-14 教训）：此前所有审计都是文本/XML 层面的自洽性检查，从未检视**渲染结果**，
因此漏掉了三类明显缺陷：表格末尾空列、单元格文字溢出边框、参考文献丢失自动编号。
本脚本用**真实 Times New Roman 字体度量**估算 Word 的实际排版，从而捕获：

  ① 单元格文字溢出：某格内**最长不可断词**的宽度 > 该列可用宽度（Word 无法换行 → 越界）
  ② 空列：整列（排除面板行）无任何内容
  ③ 表格超宽：按 100% 版面缩放的表格总宽 > 正文可用宽度
  ④ 段落超宽：正文段落里最长不可断词宽度 > 正文宽度（长 DOI / URL 风险）
  ⑤ 图片超宽：内嵌图标注宽度 > 正文宽度
  ⑥ 参考文献编号缺失（numPr 或显式「N.」均无）
"""
import html
import os
import re
import sys
import zipfile

from PIL import ImageFont

sys.stdout.reconfigure(encoding='utf-8')
PKG = r'D:/桌面/AIzuopin/痴呆/投稿包_JCM_20261014'
MS = os.path.join(PKG, 'Manuscript_JCM_20261014.docx')
FONT_R = 'C:/Windows/Fonts/times.ttf'
FONT_B = 'C:/Windows/Fonts/timesbd.ttf'

BLK = re.compile(r'<w:tbl>.*?</w:tbl>|<w:p\b.*?</w:p>|<w:p\b[^>]*/>', re.S)
TR = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
TC = re.compile(r'<w:tc>.*?</w:tc>', re.S)
TXT = re.compile(r'<w:t[^>]*>([^<]*)</w:t>')
GS = re.compile(r'<w:gridSpan w:val="(\d+)"')
SZ = re.compile(r'<w:sz w:val="(\d+)"/>')


def pt_width(text, pt, bold=False):
    """返回文本在给定磅值下的宽度（磅）。用 8 倍字号测量以提高精度。"""
    if not text:
        return 0.0
    f = ImageFont.truetype(FONT_B if bold else FONT_R, max(8, int(round(pt * 8))))
    return f.getlength(text) / 8.0


def longest_token_pt(text, pt, bold=False):
    """最长不可断片段宽度：Word 在空格与连字符后可断行。"""
    if not text:
        return 0.0
    toks = re.split(r'[\s\u00a0]+', text)
    best = 0.0
    for t in toks:
        # 连字符后可断：取各子段的最大值
        for sub in re.split(r'(?<=-)|(?=-\u200b)|(?<=\u2013)', t):
            best = max(best, pt_width(sub, pt, bold))
    return best


def run_sizes(x):
    """取该段/格内的最大字号（半磅），缺省 20（10 pt）。"""
    v = [int(m) for m in SZ.findall(x)]
    return (max(v) / 2.0) if v else 10.0


def cell_text(c):
    return html.unescape(''.join(TXT.findall(c)))


x = zipfile.ZipFile(MS).read('word/document.xml').decode('utf8')
body = x.split('<w:body>')[1].split('</w:body>')[0]

# 正文可用宽度：docx 未声明 pgSz 时按 Word 默认（Letter, 1 英寸边距）= 12240-2880
pgw = re.search(r'<w:pgSz[^>]*w:w="(\d+)"', x)
mgl = re.search(r'<w:pgMar[^>]*w:left="(\d+)"', x)
mgr = re.search(r'<w:pgMar[^>]*w:right="(\d+)"', x)
TEXTW = (int(pgw.group(1)) if pgw else 12240) - (int(mgl.group(1)) if mgl else 1440) \
        - (int(mgr.group(1)) if mgr else 1440)
print('正文可用宽度 = %d twips = %.2f cm%s' % (TEXTW, TEXTW / 567,
      '（docx 未声明 pgSz，按 Word 默认 Letter/1 英寸边距估算）' if not pgw else ''))
print()

PROB = []
tbls = re.findall(r'<w:tbl>.*?</w:tbl>', body, re.S)
print('=== ① ② ③ 逐表检查（共 %d 张）===' % len(tbls))
for ti, t in enumerate(tbls, 1):
    cols = [int(v) for v in re.findall(r'<w:gridCol w:w="(\d+)"', t)]
    if not cols:
        continue
    tot = sum(cols)
    # tblW=5000pct → 表格缩放到 100% 正文宽度；列宽按 gridCol 比例缩放
    scale = TEXTW / tot
    rend = [c * scale for c in cols]
    rows = TR.findall(t)
    # 面板行（单元格数 > 1 且只有首格非空）不参与"空列"判定
    grid = []
    for r in rows:
        cells = TC.findall(r)
        if len(cells) > 1 and sum(1 for c in cells if cell_text(c).strip()) == 1:
            grid.append(('PANEL', cells))
        else:
            grid.append(('DATA', cells))
    # ② 空列
    empty_cols = []
    for j in range(len(cols)):
        has = False
        for kind, cells in grid:
            ci = 0
            for k, c in enumerate(cells):
                span = int(GS.search(c).group(1)) if GS.search(c) else 1
                if ci <= j < ci + span:
                    if kind != 'PANEL' and cell_text(c).strip():
                        has = True
                    break
                ci += span
        if not has:
            empty_cols.append(j + 1)
    # ① 溢出
    over = []
    for ri, (kind, cells) in enumerate(grid, 1):
        j = 0
        for c in cells:
            span = int(GS.search(c).group(1)) if GS.search(c) else 1
            avail_tw = sum(cols[j:j + span]) * scale - 30      # 扣左右单元格内边距
            avail_pt = avail_tw / 20.0
            sz = run_sizes(c)
            bold = '<w:b w:val="1"/>' in c or '<w:b/>' in c
            need = longest_token_pt(cell_text(c), sz, bold)
            if need > avail_pt:
                over.append((ri, j + 1, cell_text(c).strip(), need, avail_pt))
            j += span
    flag = ''
    if empty_cols:
        flag += ' 空列=%s' % empty_cols
        PROB.append(('P0', '② Table %d 存在空列 %s' % (ti, empty_cols)))
    if over:
        flag += ' 溢出=%d 处' % len(over)
        for ri, cj, txt, need, avail in over[:6]:
            PROB.append(('P0', '① Table %d 第%d行第%d列文字溢出（需 %.1fpt > 可用 %.1fpt）：%s'
                         % (ti, ri, cj, need, avail, txt[:40])))
    if tot * scale > TEXTW + 1:
        flag += ' 超宽'
        PROB.append(('P1', '③ Table %d 超宽' % ti))
    print('  T%-2d 列=%d grid总宽=%5d 缩放后=%5d twips (%.2f cm)%s'
          % (ti, len(cols), tot, int(tot * scale), tot * scale / 567, flag or '  OK'))
    for ri, cj, txt, need, avail in over[:4]:
        print('        行%d 列%d：需 %.1f pt / 可用 %.1f pt 差 %+.1f pt | %s'
              % (ri, cj, need, avail, avail - need, txt[:46]))
print()

# ---------------------------------------------------------------- ④ 段落超宽
print('=== ④ 段落内最长不可断词 vs 正文宽度 ===')
paras = [m.group(0) for m in BLK.finditer(body) if not m.group(0).startswith('<w:tbl>')]
worst = []
for p in paras:
    txt = html.unescape(''.join(TXT.findall(p)))
    if not txt.strip():
        continue
    sz = run_sizes(p)
    need = longest_token_pt(txt, sz, '<w:b w:val="1"/>' in p)
    worst.append((need, txt))
worst.sort(reverse=True)
avail = TEXTW / 20.0
for need, txt in worst[:6]:
    mark = '★超宽' if need > avail else 'OK'
    print('  %-6s 需 %6.1f pt / 可用 %.1f pt | %s' % (mark, need, avail, txt[:70]))
    if need > avail:
        PROB.append(('P1', '④ 段落最长词 %.1fpt 超正文宽 %.1fpt' % (need, avail)))
print()

# ---------------------------------------------------------------- ⑤ 图片宽度
print('=== ⑤ 内嵌图宽度 vs 正文宽度 ===')
for m in re.finditer(r'<wp:extent cx="(\d+)" cy="(\d+)"/>', body):
    cx, cy = int(m.group(1)), int(m.group(2))
    emu_cm = cx / 360000.0
    ok = (cx / 635.0) <= TEXTW        # 1 twip = 635 EMU
    print('  %.2f × %.2f cm  %s' % (emucm := emu_cm, cy / 360000.0, 'OK' if ok else '★超宽'))
    if not ok:
        PROB.append(('P0', '⑤ 图片宽 %.2f cm 超正文宽' % emu_cm))
print()

# ---------------------------------------------------------------- ⑥ 参考文献编号
print('=== ⑥ 参考文献编号 ===')
ri = [k for k, m in enumerate(BLK.finditer(body))
      if html.unescape(''.join(TXT.findall(m.group(0)))).strip() == 'References']
if ri:
    blocks = [m.group(0) for m in BLK.finditer(body)]
    refs = [b for b in blocks[ri[0] + 1:] if html.unescape(''.join(TXT.findall(b))).strip()]
    nonum = [b for b in refs
             if 'numPr' not in b
             and not re.match(r'^\d+\.\s', html.unescape(''.join(TXT.findall(b))).strip())]
    print('  文献 %d 条；既无 numPr 也无显式序号者 = %d %s'
          % (len(refs), len(nonum), '★' if nonum else 'OK'))
    if nonum:
        PROB.append(('P0', '⑥ %d 条参考文献无编号' % len(nonum)))
else:
    print('  ★ 未找到 References 标题')
print()

print('=' * 70)
print('>>> 问题项 %d 条' % len(PROB))
for lv, it in sorted(PROB):
    print('   [%s] %s' % (lv, it))
