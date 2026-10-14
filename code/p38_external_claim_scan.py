# -*- coding: utf-8 -*-
"""p38_external_claim_scan.py —— 外部（AI/PDF）审稿意见的「回源计数」检查器（可每轮复用）

原则：外部意见多以 PDF 页码+表象描述，而 PDF 会系统性制造假错误（LaTeX 化、连字符断行、
分页错位、MathType/OMML 双写、字体替换 I²→F、上标丢失、破折号丢失）。因此**一律回 docx/md
源文件做字符串计数**，再判定"成立 / 不成立 / 已正确"。

用法：把新一版的 docx 路径填到 MS，运行本脚本，逐项看计数。
输出：out/_external_claim_scan.txt（同时打印到终端）
"""
import hashlib
import os
import re
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
D = r'D:/桌面/AIzuopin/痴呆'
MS = os.environ.get('DEM_DOCX', os.path.join(D, '稿件正文_修订稿_v4_20261013.docx'))
AF1 = os.path.join(D, '附加材料_Additional_file_1_20261013.docx')
AF2 = os.path.join(D, '附加材料_Additional_file_2_STROBE_20261013.docx')
SM = os.path.join(D, 'SupplementaryMethods_修订_20261013.md')
FIG = os.path.join(OUT, 'fig')


def docx_text(p):
    x = zipfile.ZipFile(p).read('word/document.xml').decode('utf8')
    return x, re.sub(r'<[^>]+>', '', x)


x, ms = docx_text(MS)
_, af1 = docx_text(AF1)
sm = open(SM, encoding='utf-8').read()

L = []
L.append('外部意见回源核实 —— %s' % os.path.basename(MS))
L.append('=' * 78)

# ---- A. 「拼写/排版级」指控：源文件计数（>0 才可能是真问题）----
A = [
    ('连续单字符数字串 4+（"1 1 1 1" 乱码）', r'(?:\b\d\b[ ]){4,}', ms),
    ('公式/对象/文本框/域（PDF 乱码来源）', r'<m:oMath|<w:object|<w:txbxContent|<w:instrText', x),
    ('F (%) 表头', 'F (%)', ms),
    ('I² (%) 表头', 'I\u00b2 (%)', ms),
    ('KLoSAS', 'KLoSAS', ms),
    ('KLoS A', 'KLoS A', ms),
    ('ndustd', 'ndustd', ms),
    ('"age, age,"（缺上标）', 'age, age,', ms),
    ('multicolo(u)r', 'multicolo', ms),
    ('multichort', 'multichort', ms),
    ('timevarying', 'timevarying', ms),
    ('fcaF222', 'fcaF222', ms),
    ('fca422', 'fca422', ms),
    ('j.jnh.2026（缺 a）', 'j.jnh.2026', ms),
    ('"Every row is estimated on the same"', 'Every row is estimated on the same', ms),
    ('"No adjustment for multiple testing"', 'No adjustment for multiple testing', ms),
]
for label, pat, txt in A:
    n = len(re.findall(pat, txt)) if pat.startswith('(') else txt.count(pat)
    L.append('  %-46s : %d' % (label, n))

# ---- B. 应为「正确形」的计数（0 反而要警惕）----
B = [
    ('age²（上标）', 'age\u00b2', ms),
    ('multicohort', 'multicohort', ms),
    ('time-varying', 'time-varying', ms),
    ('fcaf222（Brain Commun 正确文章号）', 'fcaf222', ms),
    ('j.jnha.2026', 'j.jnha.2026', ms),
    ('M1 unadjusted', 'M1 unadjusted', ms),
    ('Benjamini–Hochberg procedure', 'Benjamini\u2013Hochberg procedure', ms),
    ('"1.05 (0.97"（分类梯度起点）', '1.05 (0.97', ms),
    ('"Qingcai Miao¹²"（作者上标）', 'Qingcai Miao\u00b9\u00b2', ms),
    ('"factors — in particular"（破折号）', 'factors \u2014 in particular', ms),
    ('Table 2B Categorical gradient（应=1）', 'Table 2B Categorical gradient', ms),
]
for label, pat, txt in B:
    L.append('  %-46s : %d' % (label, txt.count(pat)))

# ---- C. 结构不变量 ----
L.append('')
L.append('  tbl=%d  blip=%d  反斜杠=%d  段落=%d'
         % (x.count('<w:tbl>'), x.count('<a:blip'), x.count(chr(92)),
            x.count('<w:p ') + x.count('<w:p>')))

# ---- D. 图片必须 == 重绘图 ----
L.append('')
allok = True
for i in (1, 2, 3, 4):
    a = hashlib.md5(zipfile.ZipFile(MS).read('word/media/image%d.png' % i)).hexdigest()
    b = hashlib.md5(open(os.path.join(FIG, 'Fig%d.png' % i), 'rb').read()).hexdigest()
    same = a == b
    allok &= same
    L.append('  image%d %s' % (i, '== 重绘图 OK' if same else '!= 重绘图 BAD ← 需补跑 p21'))
L.append('  ALL_IMAGE_OK = %s' % allok)

# ---- E. 补充材料同句检查 ----
L.append('')
L.append('  AF1 multichort=%d multicolo=%d ; SM multicolo=%d'
         % (af1.count('multichort'), af1.count('multicolo'), sm.count('multicolo')))

rep = '\n'.join(L)
print(rep)
open(os.path.join(OUT, '_external_claim_scan.txt'), 'w', encoding='utf8').write(rep)
