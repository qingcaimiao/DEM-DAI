# -*- coding: utf-8 -*-
"""j40_colfit.py —— 列宽拟合器：用真实字体度量 + 贪心换行，精确模拟 Word 排版

为什么需要它（2026-10-14 教训）：`j39_layout_audit.py` 只比"最长不可断词"与列宽，
因此**放过了"行有余量但仅 0.5–1.5 pt"的顶格情况**——渲染出来就像文字压线/出格。
本脚本按 Word 实际规则做**贪心换行**：逐词填行，任何一行的宽度超过列宽即判为溢出，
并给出每列**余量**与**建议列宽**。

用法：
  python j40_colfit.py            # 体检：逐表逐列报告余量
  python j40_colfit.py --fit      # 按内容反推列宽（总宽固定 9000 twips），输出建议数组
"""
import html
import os
import re
import sys

from PIL import ImageFont

sys.stdout.reconfigure(encoding='utf-8')
MS = os.environ.get('DEM_DOCX',
                    r'D:/桌面/AIzuopin/痴呆/投稿包_JCM_20261014/Manuscript_JCM_20261014.docx')
FONT_R = 'C:/Windows/Fonts/times.ttf'
FONT_B = 'C:/Windows/Fonts/timesbd.ttf'
FIT = '--fit' in sys.argv

BLK = re.compile(r'<w:tbl>.*?</w:tbl>', re.S)
TR = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
TC = re.compile(r'<w:tc>.*?</w:tc>', re.S)
GS = re.compile(r'<w:gridSpan w:val="(\d+)"')
SZ = re.compile(r'<w:sz w:val="(\d+)"/>')
TXT = re.compile(r'<w:t[^>]*>([^<]*)</w:t>')
TEXTW = 9360          # 默认值；实际从文档 pgSz/pgMar 读取（见下方）
CELLPAD = 30          # 单元格左右内边距合计（twips）
NAMES = ['Table 1', 'Table 2A', 'Table 2B', 'Table 3A', 'Table 3B', 'Table 3C',
         'Table 4C', 'Table 4A', 'Table 4B', 'Table 4D']


def wpt(text, pt, bold=False):
    if not text:
        return 0.0
    f = ImageFont.truetype(FONT_B if bold else FONT_R, max(8, int(round(pt * 8))))
    return f.getlength(text) / 8.0


def wrap_max_line(text, pt, bold, avail_pt):
    """贪心换行，返回（最大行宽, 行数, 是否溢出）。按空格断行；连字符后可断。"""
    if not text.strip():
        return 0.0, 0, False
    words = []
    for w in text.split():
        parts = re.split(r'(?<=-)', w)
        words.extend([p for p in parts if p] or [w])
    lines, cur, mx, over = [], '', 0.0, False
    for w in words:
        t = (cur + ' ' + w).strip()
        if cur and wpt(t, pt, bold) > avail_pt:
            lines.append(cur)
            mx = max(mx, wpt(cur, pt, bold))
            if wpt(cur, pt, bold) > avail_pt:
                over = True
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
        mx = max(mx, wpt(cur, pt, bold))
        if wpt(cur, pt, bold) > avail_pt:
            over = True
    return mx, len(lines), over


import zipfile  # noqa: E402

x = zipfile.ZipFile(MS).read('word/document.xml').decode('utf8')
_pg = re.search(r'<w:pgSz[^>]*w:w="(\d+)"', x)
_ml = re.search(r'<w:pgMar[^>]*w:left="(\d+)"', x)
_mr = re.search(r'<w:pgMar[^>]*w:right="(\d+)"', x)
if _pg and _ml and _mr:
    TEXTW = int(_pg.group(1)) - int(_ml.group(1)) - int(_mr.group(1))
    print('正文可用宽度（读自文档）= %d twips = %.2f cm' % (TEXTW, TEXTW / 567))
else:
    print('正文可用宽度 = %d twips（文档未声明，按 Word 默认）' % TEXTW)
body = x.split('<w:body>')[1].split('</w:body>')[0]
tbls = BLK.findall(body)

for ti, t in enumerate(tbls):
    nm = NAMES[ti] if ti < len(NAMES) else 'T%d' % (ti + 1)
    cols = [int(v) for v in re.findall(r'<w:gridCol w:w="(\d+)"', t)]
    n = len(cols)
    scale = TEXTW / sum(cols)
    avail = [(c * scale - CELLPAD) / 20.0 for c in cols]      # pt
    need = [0.0] * n
    for r in TR.findall(t):
        j = 0
        for c in TC.findall(r):
            span = int(GS.search(c).group(1)) if GS.search(c) else 1
            a = sum(avail[j:j + span])
            sz = (max(int(v) for v in SZ.findall(c)) / 2.0) if SZ.findall(c) else 10.0
            bold = '<w:b w:val="1"/>' in c or '<w:b/>' in c
            mx, nl, over = wrap_max_line(html.unescape(''.join(TXT.findall(c))), sz, bold, a)
            # 该格若要单行放下需要多宽（用最长词估下界），用于拟合
            need[j] = max(need[j], (mx + CELLPAD / 20.0))
            # 语义约束（几何检查抓不到）：短数值/区间**不允许被拆行**。
            # 例：Table 4A 的 "1.25 (β 0.2231)" 若列宽不足会被拆成
            #     "1.25 (β" / "0.2231)"，再叠加两端对齐就看起来串到隔壁列。
            txt = html.unescape(''.join(TXT.findall(c))).strip()
            _is_hdr = ('<w:b w:val="1"/>' in c or '<w:b/>' in c)
            if nl > 1 and len(txt) <= 20 and re.search(r'\d', txt) and not _is_hdr:
                print('  ★ %s 短数值被拆行（列%d）：%r → %d 行，列宽 %.1f pt 不够'
                      % (nm, j + 1, txt, nl, a))
            if over:
                print('  ★ %s 行内溢出：列%d 需 %.1fpt > 可用 %.1fpt | %s'
                      % (nm, j + 1, mx, a, html.unescape(''.join(TXT.findall(c)))[:40]))
            j += span
    slack = [avail[i] - need[i] for i in range(n)]
    flag = '' if min(slack) >= 6 else '  ← 有列余量 <6 pt'
    print('  %-9s 列宽(pt) %s' % (nm, ' '.join('%5.1f' % a for a in avail)))
    print('  %-9s 最长行  %s%s' % ('', ' '.join('%5.1f' % v for v in need), flag))
    print('  %-9s 余量    %s' % ('', ' '.join('%+5.1f' % v for v in slack)))
    if FIT:
        total = 9000
        req = [max(v, 40.0) for v in need]
        s = total / sum(req)
        sug = [max(int(round(v * s)), 300) for v in req]
        print('  %-9s 建议列宽(twips) %s  (合计 %d)' % ('', sug, sum(sug)))
    print()
