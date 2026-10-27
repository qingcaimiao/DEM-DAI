# -*- coding: utf-8 -*-
"""j42_package_verify.py —— 投稿包「全文件最新版 + 改动已同步」核对

三层核对：
  A 文件清单与生成时间（是否本轮重建）
  B 每个文件的关键内容标记（本轮各项改动的落地证据）
  C 跨文件一致性（同一事实在多个文件中必须一致）
"""
import hashlib
import html
import os
import re
import sys
import time
import zipfile

from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
PKG = r'D:/桌面/AIzuopin/痴呆/投稿包_JCM_20261014'
OUT = r'D:/workbuddygongzuokongjian/2026-10-12-21-32-15/dem_pipeline/out'
NOW = time.time()
FAIL = []


def ok(cond, label, extra=''):
    print('  %s %s%s' % ('✓' if cond else '★', label, ('  ' + extra) if extra else ''))
    if not cond:
        FAIL.append(label)


def dtext(path):
    x = zipfile.ZipFile(path).read('word/document.xml').decode('utf8')
    b = x.split('<w:body>')[1].split('</w:body>')[0]
    TXT = re.compile(r'<w:t[^>]*>([^<]*)</w:t>')
    return x, html.unescape(''.join(TXT.findall(b)))


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


print('=' * 72)
print('A 文件清单与生成时间（阈值：本次重建 30 分钟内）')
print('=' * 72)
FILES = ['Manuscript_JCM_20261014.docx', 'Cover_Letter_JCM.pdf',
         'Supplementary_Materials_1_Methods_and_Tables.docx',
         'Supplementary_Materials_2_STROBE_Checklist.docx',
         'Supplementary_Materials.zip', 'Figures.zip', 'Graphical_Abstract_JCM.png',
         'Figures/Figure1.png', 'Figures/Figure2.png', 'Figures/Figure3.png', 'Figures/Figure4.png']
for f in FILES:
    p = os.path.join(PKG, f)
    if not os.path.exists(p):
        ok(False, '%-52s 缺失' % f)
        continue
    age = (NOW - os.path.getmtime(p)) / 60.0
    ok(age <= 30, '%-52s %7.1f KB  生成于 %.1f 分钟前' % (f, os.path.getsize(p) / 1024, age))

print()
print('=' * 72)
print('B 关键内容标记（各项改动的落地证据）')
print('=' * 72)
MS = os.path.join(PKG, 'Manuscript_JCM_20261014.docx')
x, t = dtext(MS)
print(' B1 正文')
ok('WorkBuddy' in t and 'DeepSeek-V4.1-Flash' in t, 'AI 声明含工具名与版本')
ok(t.count('WorkBuddy') == 2, 'AI 工具名出现 2 处（Methods + Acknowledgments）', '实测 %d' % t.count('WorkBuddy'))
ok('Cardiology Unit I' in t and 'Cardiac Precision Medicine' in t
   and 'Hebei North University' in t, '三单位制（心内科 / 重点实验室 / 河北北方学院）')
ok('Handan 056000' in t and 'Zhangjiakou 075000' in t and '056002' not in t, '邮编 056000 / 075000，旧邮编 0 残留')
ok('Mediated % (95 % CI)' in t and 'Ratio (pooled)' in t, 'Table 4A 表头已精简')
ok(t.count('Ratio of pooled coefficients') == 0, '旧表头已无残留')
ok('1. Livingston' in t and '43. Hou' in t, '参考文献 1.–43. 带序号')
_refs = len([q for q in re.findall(r'<w:p\b[^>]*>(?:(?!</w:p>).)*</w:p>', x, re.S)][0:0])  # placeholder
ok(x.count('<w:tblHeader') == 8 and x.count('<w:cantSplit') >= 110, '跨页表头 8 张 + 行不截断', '%d / %d' % (x.count('<w:tblHeader'), x.count('<w:cantSplit')))
ok('<dc:title>' in zipfile.ZipFile(MS).read('docProps/core.xml').decode('utf8'), '文档属性已写入')
ok(x.count('descr=') == 4, '4 张图有替代文字')
# 内嵌图 vs 绘图源
z = zipfile.ZipFile(MS)
imgs = sorted([n for n in z.namelist() if n.startswith('word/media/')])
same = all(md5(os.path.join(OUT, 'fig/Fig%d.png' % i)) == hashlib.md5(z.read(n)).hexdigest()
           for i, n in enumerate(imgs, 1))
ok(same and len(imgs) == 4, '内嵌图与 out/fig 源图 md5 一致（4/4）')

print()
print(' B2 投稿信（md 与 PDF）')
cl_md = os.path.join(PKG, '_核对报告', 'Cover_Letter_JCM.md')
clm = open(cl_md, encoding='utf-8').read()
ok('WorkBuddy' in clm and 'DeepSeek-V4.1-Flash' in clm, 'md：AI 声明含工具名版本')
ok('056000' in clm and '056002' not in clm, 'md：落款地址 056000')
ok('Cardiology Unit I' in clm, 'md：落款含科室全称')
import pypdf
clp = ''.join(p.extract_text() for p in pypdf.PdfReader(os.path.join(PKG, 'Cover_Letter_JCM.pdf')).pages)
ok('056000' in clp and '056002' not in clp, 'PDF：落款地址 056000')
ok('1.27' in clp, 'PDF：含主结果 HR')

print()
print(' B3 补充材料')
S1 = os.path.join(PKG, 'Supplementary_Materials_1_Methods_and_Tables.docx')
S2 = os.path.join(PKG, 'Supplementary_Materials_2_STROBE_Checklist.docx')
_, t1 = dtext(S1)
_, t2 = dtext(S2)
ok('cause-specific estimate of 0.89' in t1, '表注 0.89 为取键渲染结果')
ok('zenodo' in t1.lower() and '23356045' in t1, '补充材料含 Zenodo Concept DOI')
ok('WorkBuddy' in t1 or 'AI-assisted' in t1, '补充材料含 AI 说明（如有）', '（若确无则此项可忽略）')
ok('STROBE' in t2, 'STROBE 清单就位')

print()
print(' B4 压缩包与图片')
zs = zipfile.ZipFile(os.path.join(PKG, 'Supplementary_Materials.zip'))
zn = zs.namelist()
ok(sorted(zn) == ['Supplementary_Materials_1_Methods_and_Tables.docx',
                  'Supplementary_Materials_2_STROBE_Checklist.docx'], '补充材料 zip 含 2 件', str(zn))
ok(all(zs.read(n) == open(os.path.join(PKG, n), 'rb').read() for n in zn), 'zip 内文件与包内文件字节一致')
zf = zipfile.ZipFile(os.path.join(PKG, 'Figures.zip'))
ok(sorted(zf.namelist()) == ['Figure1.png', 'Figure2.png', 'Figure3.png', 'Figure4.png'], '图 zip 含 4 件')
ok(all(zf.read(n) == open(os.path.join(PKG, 'Figures', n), 'rb').read() for n in zf.namelist()), '图 zip 与 Figures/ 字节一致')
for i in (1, 2, 3, 4):
    p = os.path.join(PKG, 'Figures', 'Figure%d.png' % i)
    im = Image.open(p)
    dpi = im.info.get('dpi', (0, 0))[0]
    ok(dpi >= 599 and im.width >= 1100, 'Figure%d %d×%d px  %d dpi' % (i, im.width, im.height, dpi))
ga = Image.open(os.path.join(PKG, 'Graphical_Abstract_JCM.png'))
ok(ga.width >= 1100 and ga.height >= 560, 'GA %d×%d（要求 ≥1100×560）' % (ga.width, ga.height))

print()
print('=' * 72)
print('C 跨文件一致性（同一事实必须处处一致）')
print('=' * 72)
DOI = '10.5281/zenodo.23356045'
for lab, txt in [('正文', t), ('补充材料', t1), ('投稿信 md', clm), ('投稿信 PDF', clp)]:
    ok(DOI in txt, '%s 含 Concept DOI %s' % (lab, DOI))
for lab, txt in [('投稿信 md', clm), ('投稿信 PDF', clp)]:
    ok('71,867' in txt and '11,185' in txt, '%s 含 71,867 / 11,185' % lab)
ok('71,867' in t and '11,185' in t and '694,305' in t, '正文含 71,867 / 11,185 / 694,305')
ok('71,867' in t1 and '11,185' in t1, '补充材料含 71,867 / 11,185')
for lab, txt in [('正文', t), ('投稿信 md', clm)]:
    ok('1.27' in txt and '1.21' in txt and '1.33' in txt, '%s 含主结果 1.27 (1.21–1.33)' % lab)
ok('Handan First Hospital' in t and 'Handan First Hospital' in clm, '单位名正文与投稿信一致')

print()
print('=' * 72)
if FAIL:
    print('>>> 未通过 %d 项：' % len(FAIL))
    for f in FAIL:
        print('   - %s' % f)
else:
    print('>>> 全包核对通过：所有文件均为最新版，改动已同步 ✓')
