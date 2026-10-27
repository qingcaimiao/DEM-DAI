# -*- coding: utf-8 -*-
"""j50_make_medicine.py —— Medicine (Baltimore, LWW) 投稿包（重写版，顺序正确）

处理顺序（**所有文本改动必须在 newdoc 构建之前**）：
  ① 摘要 329 → ≤250 词，Background/Methods/Results/Conclusion 四段
  ② 一级标题 Background → Introduction
  ③ Competing interests → Conflicts of interest
  ④ "Additional file N" → "Supplemental Digital Content N"；Supplementary → Supplemental
  ⑤ Running title 压到 ≤50 字符
  ⑥ 全文双倍行距
  ⑦ 字数行按最终文本重算
  ⑧ 构建 docx → 回读守卫
"""
import html
import os
import re
import sys
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
D = r'D:/桌面/AIzuopin/痴呆'
SRC = os.path.join(D, '投稿包_BMC_Public_Health_20261020', 'Manuscript_BMC_PublicHealth_20261020.docx')
PKG = os.path.join(D, '投稿包_Medicine_20261020')
DST = os.path.join(PKG, 'Manuscript_Medicine_20261020.docx')
os.makedirs(PKG, exist_ok=True)

P = re.compile(r'<w:p\b[^>]*>.*?</w:p>', re.S)
TXT = re.compile(r'<w:t[^>]*>([^<]*)</w:t>')


def bt(x):
    return html.unescape(''.join(TXT.findall(x))).strip()


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def p_plain(text):
    return ('<w:p><w:pPr><w:spacing w:before="0" w:after="120"/></w:pPr>'
            '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % esc(text))


ABS = [
    ('Background',
     'Disability, multimorbidity and depression co-occur in later life and share upstream '
     'determinants, but they are usually studied separately. We examined whether their cumulative '
     'burden predicts incident dementia and how much of the association is mediated by depression.'),
    ('Methods',
     'We pooled six harmonized ageing cohorts (CHARLS, ELSA, HRS, KLoSA, MHAS and SHARE; 71,867 '
     'participants, 11,185 incident dementia cases, 694,305 person-years) and used an unweighted '
     'count of the three syndromes (0-3). Cohort-specific Cox models were pooled by random-effects '
     'meta-analysis, with time-lagged, counting-process, trajectory, competing-risk and E-value '
     'analyses, and mediation decomposed under three frameworks.'),
    ('Results',
     'The primary model included 66,765 participants (10,297 events). Each additional syndrome '
     'carried a 27 % higher risk of dementia (pooled hazard ratio 1.27, 95 % CI 1.21-1.33; '
     'I\u00b2 = 76.8 %), with a graded increase from one to three syndromes and a per-syndrome '
     'association significant in all six cohorts. Separating exposure from outcome by two survey '
     'waves gave 1.33 (1.28-1.38). Depression (1.50) and disability (1.47) contributed most, '
     'multimorbidity least (1.16); the proportion mediated by depression converged at 12.7-17.4 %.'),
    ('Conclusion',
     'Cumulative geriatric syndrome burden is associated with incident dementia in a graded and '
     'geographically consistent manner, survives designs that separate exposure from outcome, and '
     'is partly channelled through depression. A three-item count performs as well as a full '
     'specification of the same components and offers a low-cost risk-stratification aid.'),
]
N_ABS = sum(len(t.split()) for _, t in ABS)
assert N_ABS <= 250, '摘要超 250 词：%d' % N_ABS

z = zipfile.ZipFile(SRC)
doc = z.read('word/document.xml').decode('utf8')
core = z.read('docProps/core.xml').decode('utf8')
parts = {i.filename: z.read(i.filename) for i in z.infolist() if i.filename != 'word/document.xml'}
infolist = z.infolist()
z.close()

head, rest = doc.split('<w:body>')
inner, tail = rest.split('</w:body>')

# ① 摘要
ab = [m for m in P.finditer(inner) if re.match(r'^(Background|Methods|Results|Conclusions)\.', bt(m.group(0)))]
assert len(ab) == 4, '摘要段数不是 4（实际 %d）' % len(ab)
new_abs = ''.join('<w:p><w:pPr><w:spacing w:before="0" w:after="120"/></w:pPr>'
                  '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">%s: </w:t></w:r>'
                  '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (esc(h), esc(t))
                  for h, t in ABS)
inner = inner[:ab[0].start()] + new_abs + inner[ab[-1].end():]

# ② Background → Introduction（仅文本恰为 Background 的段落）
n = 0
for m in P.finditer(inner):
    if bt(m.group(0)) == 'Background':
        old = m.group(0)
        if '>Background<' in old:
            inner = inner.replace(old, old.replace('>Background<', '>Introduction<', 1), 1)
            n += 1
assert n == 1, 'Background 标题替换次数异常：%d' % n

# ③ Competing interests → Conflicts of interest
assert 'Competing interests.' in inner
inner = inner.replace('>Competing interests.<', '>Conflicts of interest.<', 1)

# ④ Additional file → Supplemental Digital Content；Supplementary → Supplemental
n_sdc = inner.count('Additional file 1') + inner.count('Additional file 2')
assert n_sdc >= 15, 'Additional file 提及数异常：%d' % n_sdc
inner = inner.replace('Additional file 2', 'Supplemental Digital Content 2')
inner = inner.replace('Additional file 1', 'Supplemental Digital Content 1')
inner = inner.replace('Supplementary Methods', 'Supplemental Methods')
assert 'Additional file' not in inner

# ⑤ Running title ≤50 字符
RT_NEW = 'Running title: Geriatric syndrome burden and incident dementia'
assert len(RT_NEW.split(':', 1)[1].strip()) <= 50
_rt_done = False
for _m in P.finditer(inner):
    if bt(_m.group(0)).startswith('Running title:'):
        inner = inner.replace(_m.group(0), p_plain(RT_NEW), 1)
        _rt_done = True
        break
assert _rt_done, '未找到 Running title 段'

# ⑥ 双倍行距（逐段加/改 spacing，不动其他属性）
def dbl(m):
    p = m.group(0)
    if '<w:spacing' in p:
        if 'w:line="480"' in p:
            return p
        def fix(mm):
            t = mm.group(0)
            return re.sub(r'w:line="\d+"', 'w:line="480"', t) if 'w:line=' in t \
                else t[:-2] + ' w:line="480" w:lineRule="auto"/>'
        return re.sub(r'<w:spacing\b[^>]*/>', fix, p, count=1)
    if '<w:pPr>' in p:
        return p.replace('<w:pPr>', '<w:pPr><w:spacing w:line="480" w:lineRule="auto"/>', 1)
    return re.sub(r'(<w:p\b[^>]*>)', r'\1<w:pPr><w:spacing w:line="480" w:lineRule="auto"/></w:pPr>',
                  p, count=1)


inner = re.sub(r'<w:p\b[^>]*>.*?</w:p>', lambda m: dbl(m) if '<w:t' in m.group(0) else m.group(0),
               inner, flags=re.S)

# ⑥b **表格必须保持单倍行距**（LWW 惯例：正文双倍、表格单倍）。
#     若全表也设成 480，Table 4C（34 行）会撑到 2–3 页，且表格可读性变差。
def _tbl_single(m):
    return m.group(0).replace('w:line="480" w:lineRule="auto"', 'w:line="240" w:lineRule="auto"')

_n_tbl = 0
def _fix_tbl(m):
    global _n_tbl
    _n_tbl += m.group(0).count('w:line="480"')
    return _tbl_single(m)
inner = re.sub(r'<w:tbl>.*?</w:tbl>', _fix_tbl, inner, flags=re.S)
assert 'w:line="480"' not in ''.join(re.findall(r'<w:tbl>.*?</w:tbl>', inner, re.S)), '表内仍有双倍行距'
print('表格恢复单倍行距：%d 段' % _n_tbl)

# ⑦ 字数行重算（在所有文本改动之后）
ps = [(m, bt(m.group(0))) for m in P.finditer(inner)]
i_intro = next(k for k, (_, t) in enumerate(ps) if t == 'Introduction')
i_abbr = next(k for k, (_, t) in enumerate(ps) if t == 'List of abbreviations')
n_main = len(' '.join(t for _, t in ps[i_intro:i_abbr]).split())
WC = ('Word count: Abstract %d; main text %s (Introduction to Conclusions, excluding references '
      'and figure legends)' % (N_ABS, format(n_main, ',')))
done = False
for m, t in ps:
    if t.startswith('Word count:'):
        inner = inner.replace(m.group(0), p_plain(WC), 1)
        done = True
        break
assert done, '未找到字数行'

# ⑧ 构建并写出
newdoc = head + '<w:body>' + inner + '</w:body>' + tail
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as out:
    for it in infolist:
        if it.filename == 'word/document.xml':
            out.writestr(it, newdoc)
        elif it.filename == 'docProps/core.xml':
            out.writestr(it, core)
        else:
            out.writestr(it, parts[it.filename])

# 回读守卫
T = re.sub(r'<[^>]+>', '', zipfile.ZipFile(DST).read('word/document.xml').decode('utf8'))
GUARD = [('Introduction 标题', 'Introduction'),
         ('Conflicts of interest', 'Conflicts of interest.'),
         ('SDC 引用', 'Supplemental Digital Content 1'),
         ('Clinical trial number', 'Clinical trial number: not applicable.'),
         ('AI 披露', 'WorkBuddy'),
         ('Zenodo DOI', '10.5281/zenodo.23356045'),
         ('缩写表', 'List of abbreviations')]
bad = [lab for lab, needle in GUARD if needle not in T]
assert not bad, '守卫失败：%s' % bad
assert 'Additional file' not in T, '仍有 Additional file 残留'
assert 'Background to Conclusions' not in T, '字数行仍写 Background'
_x_rt = zipfile.ZipFile(DST).read('word/document.xml').decode('utf8')
_rt = next(bt(m.group(0)) for m in P.finditer(_x_rt) if bt(m.group(0)).startswith('Running title:'))
_rt_len = len(_rt.split(':', 1)[1].strip())
assert _rt_len <= 50, 'Running title 超 50 字符：%d' % _rt_len
print('摘要 %d 词｜主文 %s 词｜SDC 替换 %d 处｜Running title %d 字符' % (N_ABS, format(n_main, ','), n_sdc, _rt_len))
print('守卫：%d 项 + 3 条反向断言 通过' % len(GUARD))
print('写出:', DST, '%.2f MB' % (os.path.getsize(DST) / 1048576))
print('字数行：%s' % WC)
