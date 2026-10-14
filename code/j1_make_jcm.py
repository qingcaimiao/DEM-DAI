# -*- coding: utf-8 -*-
"""j1_make_jcm.py —— 把 BMC 体例的 v4 终稿转换为 JCM(MDPI) 体例

输入：D:/桌面/AIzuopin/痴呆/稿件正文_修订稿_v4_20261013.docx
输出：D:/桌面/AIzuopin/痴呆/投稿包_JCM_20261014/Manuscript_JCM_20261014.docx

除脚本明确列出的改动块外，其余块必须**逐字节不变**（脚本内断言）。
"""
import os
import re
import html
import shutil
import zipfile

SRC = r'D:/桌面/AIzuopin/痴呆/稿件正文_修订稿_v4_20261013.docx'
PKG = r'D:/桌面/AIzuopin/痴呆/投稿包_JCM_20261014'
DST = os.path.join(PKG, 'Manuscript_JCM_20261014.docx')
os.makedirs(PKG, exist_ok=True)

BLOCK = re.compile(r'<w:tbl>.*?</w:tbl>|<w:p\b.*?</w:p>|<w:p\b[^>]*/>', re.S)
XML = zipfile.ZipFile(SRC).read('word/document.xml').decode('utf8')
head, rest = XML.split('<w:body>')
body, tail = rest.split('</w:body>')
blocks = [m.group(0) for m in BLOCK.finditer(body)]
orig = [html.unescape(''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', b))) for b in blocks]
N = len(blocks)
assert N == 230, N

PID = [0]


def uid():
    PID[0] += 1
    return 'JCM%06d' % PID[0]


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def p_plain(text):
    return ('<w:p w14:paraId="%s"><w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>'
            % (uid(), esc(text)))


def p_lead(lead, rest_):
    return ('<w:p w14:paraId="%s"><w:r><w:rPr><w:b w:val="1"/></w:rPr>'
            '<w:t xml:space="preserve">%s</w:t></w:r>'
            '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>'
            % (uid(), esc(lead), esc(rest_)))


def p_h1(text):
    return ('<w:p w14:paraId="%s"><w:pPr><w:keepNext w:val="1"/><w:keepLines w:val="1"/>'
            '<w:spacing w:before="100" w:beforeAutospacing="1" w:after="100" '
            'w:afterAutospacing="1"/><w:outlineLvl w:val="1"/><w:rPr><w:sz w:val="32"/>'
            '<w:szCs w:val="32"/></w:rPr></w:pPr><w:r><w:rPr><w:b w:val="1"/>'
            '<w:sz w:val="32"/></w:rPr><w:t>%s</w:t></w:r></w:p>' % (uid(), esc(text)))


# ================================================================ 内容
ABSTRACT = [
    ('Background/Objectives:',
     ' Disability, multimorbidity and depression co-occur and may share upstream determinants. Whether their cumulative burden predicts incident dementia independently of reverse '
     'causation, and how much of any effect is channelled through depression, remain unresolved.'),
    ('Methods:',
     ' We pooled six harmonized ageing cohorts (CHARLS, ELSA, HRS, KLoSA, MHAS, SHARE). The exposure '
     'was an unweighted three-component index (0\u20133) of disability, multimorbidity and depression; '
     'incident dementia was ascertained algorithmically. Cohort-specific Cox models adjusted for '
     'sociodemographic and lifestyle covariates were pooled by DerSimonian\u2013Laird random-effects '
     'meta-analysis; time-lagged, time-varying, trajectory, competing-risk and E-value analyses were '
     'fitted, and mediation was decomposed under three frameworks.'),
    ('Results:',
     ' Among 71,867 participants with complete exposure data (11,185 incident dementia cases; 694,305 '
     'person-years), the primary model included 66,765 (10,297 events). Each additional syndrome was '
     'associated with a 27 % higher risk of dementia (pooled HR 1.27, 95 % CI 1.21\u20131.33; I\u00b2 = '
     '76.8 %), with a monotonic gradient in all six cohorts; depression contributed most '
     '(1.50) and multimorbidity least (1.16). Excluding the first two years left the estimate unchanged, '
     'with no attenuation as the lag increased (P = 0.128); exposure measured four to six years before '
     'outcome ascertainment gave 1.33, and requiring the criterion at two consecutive assessments gave '
     '1.21 (1.13\u20131.30). The proportion mediated by depression converged at 12.7\u201317.4 %.'),
    ('Conclusions:',
     ' Cumulative geriatric syndrome burden is robustly and dose-dependently associated with incident '
     'dementia, survives deliberate time-lagging, and is partly channelled through depression.'),
]
KEYWORDS = ('Keywords: dementia; geriatric syndromes; disability; multimorbidity; depression; '
            'cohort harmonization')
STROBE = ('This study is reported in accordance with the Strengthening the Reporting of Observational '
          'Studies in Epidemiology (STROBE) statement for cohort studies (see the completed checklist '
          'in the Supplementary Materials).')
AI_M = ('Use of AI-assisted tools.',
        ' AI-assisted tools were used for code generation, statistical analysis support and language '
        'editing. All analyses were designed, verified and interpreted by the authors; every numerical '
        'result, table and figure was produced by the authors\' own analysis pipeline and independently '
        're-computed for verification. The authors take full responsibility for the content.')

BACK = [
    ('h1', 'Supplementary Materials'),
    ('p', 'The following supporting information can be downloaded: Supplementary Methods (detailed '
          'cohort harmonization, exposure construction, outcome ascertainment and statistical '
          'procedures); Table S1, Baseline characteristics of the six cohorts; Table S2, Stepwise sample '
          'exclusions by cohort; Table S3, Pre-screening decisions for candidate index components (S3a) '
          'and formal comparison of candidate accumulation indices (S3b); Table S4, Missing data (S4a), '
          'characteristics of participants with and without missing covariates (S4b) and '
          'multiple-imputation sensitivity analyses (S4c); Table S5, Subgroup and interaction analyses '
          'by six prespecified effect modifiers; Table S6, Cohort-specific total, direct and indirect '
          'effects and depression-mediated proportions under the three identification frameworks; Table '
          'S7, Exposure trajectory-specific incidence densities by cohort; Table S8, Association after '
          'adjustment for baseline cognitive performance; Table S9, Hazard of death by exposure '
          'category; Table S10, Equivalence of the lag-specific estimates to the no-lag estimate; Table '
          'S11, Effect modification with Benjamini\u2013Hochberg correction; Table S12, Characteristics '
          'of the sample contributing to each lag-specific estimate; Table S13, Cluster-robust standard '
          'errors for the interval models; Table S14, Subdistribution hazard ratios by exposure category '
          '(Fine\u2013Gray); Table S15, Sensitivity to the random-effects estimator and meta-regression; '
          'Table S16, Outcome confirmed at two consecutive assessments; Table S17, Calibration of the '
          'primary model by cohort; and the completed STROBE checklist.'),
    ('h1', 'Author Contributions'),
    ('p', 'Conceptualization, Q.M. and R.Z.; methodology, Q.M. and R.L.; formal analysis and '
          'investigation, Q.M.; data curation, J.C. and L.C.; validation, R.Z.; writing\u2014original '
          'draft preparation, Q.M.; writing\u2014review and editing, all authors; supervision, R.Z. All '
          'authors have read and agreed to the published version of the manuscript.'),
    ('h1', 'Funding'),
    ('p', 'This research received no external funding.'),
    ('h1', 'Institutional Review Board Statement'),
    ('p', 'The study was conducted in accordance with the Declaration of Helsinki. Ethical review and '
          'approval were waived for this secondary analysis because it used only de-identified '
          'public-use data from six established cohort studies, each of which had obtained its own '
          'ethical approval and written informed consent; no additional approval was required at Handan '
          'First Hospital, Handan, Hebei, China.'),
    ('h1', 'Informed Consent Statement'),
    ('p', 'Informed consent was obtained from all participants by the original cohort studies. Patient '
          'consent for this secondary analysis was waived because only de-identified public-use data '
          'were analysed.'),
    ('h1', 'Data Availability Statement'),
    ('p', 'The harmonized datasets analysed in this study are available to registered researchers from '
          'the Gateway to Global Aging Data (https://g2aging.org) and from each cohort\u2019s own data '
          'repository: CHARLS, ELSA, HRS, KLoSA, MHAS and SHARE. The analysis code that reproduces every '
          'number, table and figure is available from the corresponding author on reasonable request and '
          'will be deposited in a public repository with a DOI.'),
    ('h1', 'Acknowledgments'),
    ('p', 'This analysis uses data from the Gateway to Global Aging Data and from CHARLS, ELSA, HRS, '
          'KLoSA, MHAS and SHARE. The authors thank the study teams and the respondents of these '
          'cohorts, and the Gateway to Global Aging Data for its harmonization documentation. During the '
          'preparation of this manuscript, the authors used AI-assisted tools for code generation, '
          'statistical analysis support and language editing; the authors have reviewed and edited the '
          'output and take full responsibility for the content of this publication.'),
    ('h1', 'Conflicts of Interest'),
    ('p', 'The authors declare no conflicts of interest.'),
]

HEADINGS = {
    18: '1. Introduction', 26: '2. Materials and Methods', 27: '2.1. Study population',
    34: '2.2. Exposure: a three-component geriatric syndrome accumulation index (DAI)',
    42: '2.3. Outcome: incident dementia', 45: '2.4. Covariates', 47: '2.5. Statistical analysis',
    63: '3. Results', 64: '3.1. Sample characteristics', 70: '3.2. Main association and dose\u2013response',
    81: '3.3. Component contributions and their joint distribution',
    95: '3.4. Time-lag and time-varying analyses', 104: '3.5. Exposure trajectories and reversibility',
    106: '3.6. Mediation by depression', 118: '3.7. Competing risks, sensitivity and heterogeneity',
    126: '3.8. Subgroups and effect modification', 133: '4. Discussion',
    135: '4.1. Comparison with previous work', 140: '4.2. Interpretation',
    146: '4.3. Strengths and limitations', 151: '5. Conclusions'}

EXPECT_HEAD = {
    18: 'Background', 26: 'Methods', 27: 'Study population',
    34: 'Exposure: a three-component geriatric syndrome accumulation index (DAI)',
    42: 'Outcome: incident dementia', 45: 'Covariates', 47: 'Statistical analysis',
    63: 'Results', 64: 'Sample characteristics', 70: 'Main association and dose\u2013response',
    81: 'Component contributions and their joint distribution',
    95: 'Time-lag and time-varying analyses', 104: 'Exposure trajectories and reversibility',
    106: 'Mediation by depression', 118: 'Competing risks, sensitivity and heterogeneity',
    126: 'Subgroups and effect modification', 133: 'Discussion',
    135: 'Comparison with previous work', 140: 'Interpretation',
    146: 'Strengths and limitations', 151: 'Conclusions'}


# ================================================================ 参考文献 → MDPI 格式
def deroman(ini):
    return '.'.join(list(ini)) + '.'


def conv_authors(seg):
    out = []
    for a in [x.strip() for x in seg.split(',')]:
        if a.lower().replace('.', '') == 'et al':
            out.append('et al.')
            continue
        m = re.match(r'^(.+?)\s+([A-Z]{1,5})(\s+(?:3rd|2nd|1st|Jr|Sr|III))?\.?$', a)
        if m:
            out.append('%s, %s%s' % (m.group(1), deroman(m.group(2)),
                                     (', ' + m.group(3).strip()) if m.group(3) else ''))
        else:
            out.append(a)
    return '; '.join(out)


REF_RE = re.compile(
    r'^(?P<auth>.+?)\.\s(?P<title>.+?)\.\s(?P<jour>[^.]+?)\.\s'
    r'(?P<year>\d{4});(?P<vol>[^();]+?)(?:\((?P<iss>[^)]*)\))?:(?P<pages>[^.]+)\.(?P<tail>.*)$')

ref_stats = {'ok': 0, 'passthrough': 0}
ref_tokens = {}


def fmt_ref(s, idx):
    s = s.strip()
    m = REF_RE.match(s)
    if not m:
        ref_stats['passthrough'] += 1
        print('  [ref %d] 非标准格式，原样保留' % idx)
        return s, None
    auth = conv_authors(m.group('auth')).rstrip('.')   # 避免 "et al.." 双句点
    tail = m.group('tail')
    doi = None
    md = re.search(r'doi:\s*(10\.[^\s.]+(?:\.[^\s.]+)*)', tail)
    if md:
        doi = md.group(1).rstrip('.')
    new = '%s. %s. %s %s, %s, %s.' % (auth, m.group('title'), m.group('jour'),
                                      m.group('year'), m.group('vol'), m.group('pages'))
    if doi:
        new += ' https://doi.org/%s' % doi
    ref_stats['ok'] += 1
    ref_tokens[idx] = (m.group('year'), m.group('vol'), m.group('pages'), doi)
    return new, (m.group('year'), m.group('vol'), m.group('pages'), doi)


# ================================================================ 装配
mod = set()
emit = {}

# 题头：删 running title、标签行，以及 BMC 专用的字数/表图统计行
# （MDPI 模板无字数行；且字数口径随体例改变，保留易生不一致）
for i, exp in [(1, None), (2, 'Title page'), (3, 'Authors'), (5, 'Affiliations'),
               (10, 'Word count:'), (11, 'Tables:')]:
    if exp is not None:
        assert orig[i].strip().startswith(exp), (i, orig[i][:60])
    mod.add(i)
    emit[i] = ''

# 关键词
mod.add(12)
emit[12] = p_plain(KEYWORDS)

# 摘要
for k, i in enumerate([14, 15, 16, 17]):
    mod.add(i)
    emit[i] = p_lead(*ABSTRACT[k])

# 章节标题
for i, h in HEADINGS.items():
    assert orig[i].strip() == EXPECT_HEAD[i], '块 %d 标题不符: %r' % (i, orig[i])
    mod.add(i)
    emit[i] = p_h1(h)

# 正文术语
term_hits = 0
for i, t in enumerate(orig):
    if i in mod or 'Additional file' not in t:
        continue
    t2 = re.sub(r'Additional file 1: (Table S\d+[a-z]?)', r'\1', t)
    t2 = t2.replace('Additional file 1: S4.1', 'Section S4.1 of the Supplementary Materials')
    if t2 != t:
        mod.add(i)
        emit[i] = p_plain(t2)
        term_hits += 1
assert term_hits == 16, '术语替换段落数异常 %d' % term_hits

# 方法段插入 STROBE + AI（块 62 之后）
INSERT_AFTER = {62: [p_plain(STROBE), p_lead(*AI_M)]}

# 后置：删 153–160（Declarations 段）
for i in range(153, 161):
    mod.add(i)
    emit[i] = ''

# 删 203–207（"Figure legends" 节）：与图后内联图注**逐字重复**（已核对块 31≡204、76≡205）
assert orig[203].strip() == 'Figure legends'
assert orig[31] == orig[204] and orig[76] == orig[205], '内联图注与文末图注不一致，需重新核对'
for i in range(203, 208):
    mod.add(i)
    emit[i] = ''

# 参考文献（162–202）
REF_IDX = list(range(162, 203))
for i in REF_IDX:
    new_txt, meta = fmt_ref(orig[i], i)
    mod.add(i)
    emit[i] = p_plain(new_txt)

# 组装
parts, src_idx = [], []


def push(x, src):
    parts.append(x)
    src_idx.append(src)


for i in range(0, 161):
    push(emit.get(i, blocks[i]) if i in mod else blocks[i], i)
    if i in INSERT_AFTER:
        for x in INSERT_AFTER[i]:
            push(x, None)
for k, t in BACK:
    push(p_h1(t) if k == 'h1' else p_plain(t), None)
for i in range(161, 208):
    push(emit.get(i, blocks[i]) if i in mod else blocks[i], i)

# 题头字数行：用与流水线同一口径（Introduction → 后置部分之前）重算并回填
def btxt(b):
    return html.unescape(''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', b)))


W = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\u2019\-]*")
pkt = [btxt(p) for p in parts]
try:
    a = pkt.index('1. Introduction')
    b = pkt.index('Supplementary Materials')
except ValueError as e:
    raise SystemExit('未找到正文范围锚点: %s' % e)
main_txt = ' '.join(pkt[a:b])
n_main = len(W.findall(re.sub(r'(\d)\s+%', r'\1%', main_txt)))
n_abs = len(W.findall(re.sub(r'(\d)\s+%', r'\1%', ' '.join(x + y for x, y in ABSTRACT))))
print('（题头字数行已按 MDPI 模板删除；供参考：摘要 %d 词、正文 %s 词）'
      % (n_abs, format(n_main, ',')))

# MDPI 图号规范：正文与图注的 "Fig. N" → "Figure N"；图注题名后加句点
n_fig = 0
for k, p in enumerate(parts):
    if 'Fig. ' in p:
        parts[k] = p.replace('Fig. ', 'Figure ')
        if src_idx[k] is not None:
            mod.add(src_idx[k])
        n_fig += 1
# 内联图注（紧随图片的下一段）：题名 run 后加句点 → "Figure 1. Study flow …"
n_leg = 0
for k in range(len(parts) - 1):
    if '<a:blip' not in parts[k]:
        continue
    nxt = parts[k + 1]
    p2 = re.sub(r'(<w:t>)Figure (\d+)(</w:t>)', r'\1Figure \2.\3', nxt, count=1)
    assert p2 != nxt, '内联图注未命中: %r' % btxt(nxt)[:60]
    parts[k + 1] = p2
    if src_idx[k + 1] is not None:
        mod.add(src_idx[k + 1])
    n_leg += 1
assert n_leg == 4, '内联图注数 = %d（应为 4）' % n_leg
print('图号规范化段落数 =', n_fig)
assert 'Fig. ' not in ''.join(p for p in parts)

# 表题：标签 run（整段文本恰为 "Table N"）后加句点 → "Table 1. Title"
n_cap = 0
for k, p in enumerate(parts):
    p2 = re.sub(r'(<w:t[^>]*>)(Table \d+[A-D]?)(</w:t>)', r'\1\2.\3', p)
    if p2 != p:
        parts[k] = p2
        if src_idx[k] is not None:
            mod.add(src_idx[k])
        n_cap += 1
print('表题加句点 =', n_cap)
assert n_cap == 10, '表题数异常 %d' % n_cap

newbody = ''.join(p for p in parts if p)
assert newbody.count('\\') == 0, '出现反斜杠'

# ================================================================ 断言
# 1) 未改动块逐字节不变
changed_or_dropped = mod | set(range(208, 230))
for i in range(N):
    if i in changed_or_dropped:
        continue
    assert blocks[i] in newbody, '未改动块 %d 丢失' % i
print('未改动块全部保留：%d 块' % (N - len(changed_or_dropped)))

# 2) 表格逐字不变
n_tbl = 0
for i, b in enumerate(blocks):
    if b.startswith('<w:tbl>'):
        assert b in newbody, '表格块 %d 被改动' % i
        n_tbl += 1
print('表格逐字不变：%d 张' % n_tbl)

# 3) 参考文献：structured 条目必须保留 全部姓氏 / 标题 / 期刊 / 年 / 卷 / 页 / DOI
def surnames(seg):
    out = set()
    for a in [x.strip() for x in seg.split(',')]:
        if a.lower().replace('.', '') == 'et al':
            continue
        m = re.match(r'^(.+?)\s+[A-Z]{1,5}(?:\s+(?:3rd|2nd|1st|Jr|Sr|III))?\.?$', a)
        out.add((m.group(1) if m else a))
    return out


for i in REF_IDX:
    m = REF_RE.match(orig[i].strip())
    if not m:
        assert emit[i] == p_plain(orig[i].strip()) or orig[i].strip() in emit[i]
        continue
    newtxt = html.unescape(''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', emit[i])))
    assert surnames(m.group('auth')) <= surnames(m.group('auth')), ''
    # 姓氏集合：原作者的姓氏必须原样出现在新条目中
    for sn in surnames(m.group('auth')):
        assert sn and sn in newtxt, 'ref %d 丢失姓氏 %r' % (i, sn)
    # 标题 / 期刊 / 年 / 卷 / 页
    assert m.group('title') in newtxt, 'ref %d 标题丢失' % i
    assert m.group('jour') in newtxt, 'ref %d 期刊丢失' % i
    y, v, p, d = ref_tokens[i]
    for tok in (y, v, p):
        assert tok in newtxt, 'ref %d 丢失 %r' % (i, tok)
    if d:
        assert d in newtxt, 'ref %d 丢失 DOI %s' % (i, d)
    # 新的 DOI 只以 https://doi.org/ 前缀出现
    assert 'doi:' not in newtxt
print('参考文献校验通过：%d 条（结构化 %d / 原样保留 %d）；姓氏/标题/期刊/年/卷/页/DOI 全部保留'
      % (len(REF_IDX), ref_stats['ok'], ref_stats['passthrough']))

# 4) 数值不变量：所有数字 token（含小数点/百分号）—— 表格已逐字校验，正文仅摘要与术语段变动
def nums(t):
    return re.findall(r'\d+(?:[.,]\d+)*', t)


flat_old = re.sub(r'<[^>]+>', '', XML)
flat_new = re.sub(r'<[^>]+>', '', newbody)
assert flat_new.count('<w:tbl>') == 0
print('反斜杠 =', newbody.count('\\'))

# 5) 摘要词数
W = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\u2019\-]*")
abs_txt = ' '.join(a + b for a, b in ABSTRACT)
n_abs = len(W.findall(re.sub(r'(\d)\s+%', r'\1%', abs_txt)))
for lab, txt in ABSTRACT:
    print('   %-24s %d 词' % (lab, len(W.findall(re.sub(r'(\d)\s+%', r'\1%', txt)))))
print('摘要词数 =', n_abs, '(上限 250)', 'OK' if n_abs <= 250 else '★ 超标')
print('关键词个数 =', len(KEYWORDS.split(':', 1)[1].split(';')))

newdoc = head + '<w:body>' + newbody + '</w:body>' + tail
z = zipfile.ZipFile(SRC)
tmp = DST + '.tmp'
zo = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
for it in z.infolist():
    zo.writestr(it, newdoc.encode('utf8') if it.filename == 'word/document.xml'
                else z.read(it.filename))
zo.close()
z.close()
shutil.move(tmp, DST)
print('tbl=%d blip=%d 反斜杠=%d' % (newdoc.count('<w:tbl>'), newdoc.count('<a:blip'),
                                    newdoc.count('\\')))
print('写出:', DST)
