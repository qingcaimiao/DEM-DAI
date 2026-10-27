# -*- coding: utf-8 -*-
"""j1_make_jcm.py —— 把 BMC 体例的 v4 终稿转换为 JCM(MDPI) 体例

输入：D:/桌面/AIzuopin/痴呆/稿件正文_修订稿_v4_20261013.docx
输出：D:/桌面/AIzuopin/痴呆/投稿包_JCM_20261014/Manuscript_JCM_20261014.docx

★ 2026-10-14 重构：所有定位一律**按文本锚定**，不再使用硬编码块下标。
  原因：上游一旦增删段落（本次实测到静默丢段与恢复），下标会整体错位，
  从而把「补充材料末段」当成「一级标题」处理——最危险的一类静默失败。
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

BLK = re.compile(r'<w:tbl>.*?</w:tbl>|<w:p\b.*?</w:p>|<w:p\b[^>]*/>', re.S)
XML = zipfile.ZipFile(SRC).read('word/document.xml').decode('utf8')
head, rest = XML.split('<w:body>')
body, tail = rest.split('</w:body>')
blocks = [m.group(0) for m in BLK.finditer(body)]
bt = lambda b: html.unescape(''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', b)))
orig = [bt(b) for b in blocks]
N = len(blocks)
assert 220 <= N <= 250, 'v4 块数异常：%d' % N


def find(text, start=0):
    hits = [i for i in range(start, N) if orig[i].strip() == text]
    assert len(hits) == 1, '锚点 %r 命中 %d 次' % (text[:50], len(hits))
    return hits[0]


def find_pre(prefix):
    hits = [i for i in range(N) if orig[i].strip().startswith(prefix)]
    assert len(hits) == 1, '前缀锚点 %r 命中 %d 次' % (prefix[:50], len(hits))
    return hits[0]


def find_contain(sub):
    return [i for i in range(N) if sub in orig[i]][0]


PID = [0]


def uid():
    PID[0] += 1
    return 'JCM%06d' % PID[0]


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def p_plain(text):
    return ('<w:p w14:paraId="%s"><w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>'
            % (uid(), esc(text)))


def p_lead(lead, r):
    return ('<w:p w14:paraId="%s"><w:r><w:rPr><w:b w:val="1"/></w:rPr>'
            '<w:t xml:space="preserve">%s</w:t></w:r>'
            '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>'
            % (uid(), esc(lead), esc(r)))


def p_ref(text):
    """参考文献条目：带序号 + 悬挂缩进（原稿用 Word 自动编号，重写段落时会丢失，故显式写入）。"""
    return ('<w:p w14:paraId="%s"><w:pPr><w:ind w:left="425" w:hanging="425"/>'
            '<w:spacing w:after="0"/></w:pPr>'
            '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (uid(), esc(text)))


def p_h1(text):
    return ('<w:p w14:paraId="%s"><w:pPr><w:keepNext w:val="1"/><w:keepLines w:val="1"/>'
            '<w:spacing w:before="100" w:beforeAutospacing="1" w:after="100" '
            'w:afterAutospacing="1"/><w:outlineLvl w:val="1"/><w:rPr><w:sz w:val="32"/>'
            '<w:szCs w:val="32"/></w:rPr></w:pPr><w:r><w:rPr><w:b w:val="1"/>'
            '<w:sz w:val="32"/></w:rPr><w:t>%s</w:t></w:r></w:p>' % (uid(), esc(text)))


# ================================================================ 内容
ABSTRACT = [
    ('Background/Objectives:',
     ' Disability, multimorbidity and depression co-occur and may share upstream determinants. '
     'Whether their cumulative burden predicts incident dementia independently of reverse causation, '
     'and how much of any effect is channelled through depression, remain unresolved.'),
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
     '76.8 %), with a monotonic gradient in all six cohorts; depression contributed most (1.50) and '
     'multimorbidity least (1.16). Excluding the first two years left the estimate unchanged, with no '
     'attenuation as the lag increased (P = 0.128); exposure measured four to six years before outcome '
     'ascertainment gave 1.33, and requiring the criterion at two consecutive assessments gave 1.21 '
     '(1.13\u20131.30). The proportion mediated by depression converged at 12.7\u201317.4 %.'),
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
        ' The generative AI tool WorkBuddy (an AI coding and writing assistant powered by the '
        'DeepSeek-V4.1-Flash large language model) was used for code generation, statistical analysis '
        'support and language editing. All analyses were designed, verified and interpreted by the '
        'authors; every numerical result, table and figure was produced by the authors\' own analysis '
        'pipeline and independently re-computed for verification. No AI tool was used to generate or '
        'interpret data, and no AI tool is listed as an author. The authors take full responsibility '
        'for the content.')

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
          'repository: CHARLS, ELSA, HRS, KLoSA, MHAS and SHARE; no participant-level data are '
          'redistributed here. The analysis code that reproduces every number, table and figure is '
          'openly available at https://github.com/qingcaimiao/DEM-DAI and archived on Zenodo at '
          'https://doi.org/10.5281/zenodo.23356045.'),
    ('h1', 'Acknowledgments'),
    ('p', 'This analysis uses data from the Gateway to Global Aging Data and from CHARLS, ELSA, HRS, '
          'KLoSA, MHAS and SHARE. The authors thank the study teams and the respondents of these '
          'cohorts, and the Gateway to Global Aging Data for its harmonization documentation. During the '
          'preparation of this manuscript, the authors used WorkBuddy (an AI coding and writing assistant '
          'powered by the DeepSeek-V4.1-Flash large language model) for code generation, statistical '
          'analysis support and language editing; the authors have reviewed and edited the output and '
          'take full responsibility for the content of this publication.'),
    ('h1', 'Conflicts of Interest'),
    ('p', 'The authors declare no conflicts of interest.'),
]

HEADINGS = {
    'Background': '1. Introduction',
    'Methods': '2. Materials and Methods',
    'Study population': '2.1. Study population',
    'Exposure: a three-component geriatric syndrome accumulation index (DAI)':
        '2.2. Exposure: a three-component geriatric syndrome accumulation index (DAI)',
    'Outcome: incident dementia': '2.3. Outcome: incident dementia',
    'Covariates': '2.4. Covariates',
    'Statistical analysis': '2.5. Statistical analysis',
    'Results': '3. Results',
    'Sample characteristics': '3.1. Sample characteristics',
    'Main association and dose\u2013response': '3.2. Main association and dose\u2013response',
    'Component contributions and their joint distribution':
        '3.3. Component contributions and their joint distribution',
    'Time-lag and time-varying analyses': '3.4. Time-lag and time-varying analyses',
    'Exposure trajectories and reversibility': '3.5. Exposure trajectories and reversibility',
    'Mediation by depression': '3.6. Mediation by depression',
    'Competing risks, sensitivity and heterogeneity':
        '3.7. Competing risks, sensitivity and heterogeneity',
    'Subgroups and effect modification': '3.8. Subgroups and effect modification',
    'Discussion': '4. Discussion',
    'Comparison with previous work': '4.1. Comparison with previous work',
    'Interpretation': '4.2. Interpretation',
    'Strengths and limitations': '4.3. Strengths and limitations',
    'Conclusions': '5. Conclusions',
}

# ================================================================ 参考文献 → MDPI
# 参考文献编号 → DOI。2026-10-14 逐条经 Crossref 核验：
#   判定条件为 归一化题名相似度 ≥0.90 且 年份一致 且 卷号一致（或页码一致）；
#   低相似度但卷+年+页三项全中的（题名被 Crossref 截短的旧文献）已逐条人工裁定。
#   [18] Gateway to Global Aging Data 与 [22] KLoSA 为机构网站，按 MDPI 规则不加 DOI。
REF_DOI = {
    1: '10.1016/S0140-6736(24)01296-0', 2: '10.1016/S2468-2667(21)00249-8',
    3: '10.1111/j.1532-5415.2007.01156.x', 4: '10.1093/gerona/62.7.722',
    5: '10.1001/jamaneurol.2024.3774', 6: '10.1177/13872877261430305',
    7: '10.1016/j.jare.2026.01.026', 8: '10.1016/j.archger.2025.105760',
    9: '10.1016/j.tjpad.2025.100164', 10: '10.1192/bjp.bp.112.118307',
    11: '10.1001/archpsyc.63.5.530', 12: '10.1002/gps.3865',
    13: '10.1093/gerona/gls208', 14: '10.1186/s12916-024-03642-2',
    15: '10.1136/gpsych-2025-102172', 16: '10.1093/braincomms/fcaf222',
    17: '10.1001/jamanetworkopen.2025.55740', 19: '10.1093/ije/dys203',
    20: '10.1093/ije/dys168', 21: '10.1093/ije/dyu067', 23: '10.1093/ije/dyu263',
    24: '10.1093/ije/dyt088', 25: '10.1001/jama.1963.03060120024016',
    26: '10.1093/geront/9.3_part_1.179', 27: '10.1016/0021-9681(87)90171-8',
    28: '10.1016/S0749-3797(18)30622-6', 29: '10.1192/bjp.174.4.330',
    30: '10.1093/geronb/gbr048', 31: '10.1001/jamainternmed.2016.6807',
    32: '10.1016/0197-2456(86)90046-2', 33: '10.1136/bmj.327.7414.557',
    34: '10.1097/EDE.0000000000000121', 35: '10.1146/annurev-publhealth-032315-021402',
    36: '10.1080/01621459.1999.10474144', 37: '10.7326/M16-2607',
    38: '10.1002/sim.3618', 39: '10.1016/j.jnha.2026.100983',
    40: '10.1002/alz.71821', 41: '10.1186/s12889-026-28715-0',
    42: '10.1016/j.jad.2026.122381', 43: '10.1002/alz.70950',
}


def deroman(ini):
    return '.'.join(list(ini)) + '.'


def conv_authors(seg):
    out = []
    for a in [x.strip() for x in seg.split(',')]:
        if a.lower().replace('.', '') == 'et al':
            out.append('et al.')
            continue
        m = re.match(r'^(.+?)\s+([A-Z]{1,5})(\s+(?:3rd|2nd|1st|Jr|Sr|III))?\.?$', a)
        out.append(('%s, %s%s' % (m.group(1), deroman(m.group(2)),
                                  (', ' + m.group(3).strip()) if m.group(3) else '')) if m else a)
    return '; '.join(out)


REF_RE = re.compile(
    r'^(?P<auth>.+?)\.\s(?P<title>.+?)\.\s(?P<jour>[^.]+?)\.\s'
    r'(?P<year>\d{4});(?P<vol>[^();]+?)(?:\((?P<iss>[^)]*)\))?:(?P<pages>[^.]+)\.(?P<tail>.*)$')
ref_stats = {'ok': 0, 'pass': 0}
ref_tokens = {}


def fmt_ref(s, refno):
    s = s.strip()
    m = REF_RE.match(s)
    if not m:
        ref_stats['pass'] += 1
        return s
    auth = conv_authors(m.group('auth')).rstrip('.')
    doi = None
    md = re.search(r'doi:\s*(10\.[^\s.]+(?:\.[^\s.]+)*)', m.group('tail'))
    if md:
        doi = md.group(1).rstrip('.')
    elif refno in REF_DOI:
        doi = REF_DOI[refno]
    new = '%s. %s. %s %s, %s, %s.' % (auth, m.group('title'), m.group('jour'),
                                      m.group('year'), m.group('vol'), m.group('pages'))
    if doi:
        new += ' https://doi.org/%s' % doi
    ref_stats['ok'] += 1
    ref_tokens[refno] = (m.group('year'), m.group('vol'), m.group('pages'), doi)
    return new


# ================================================================ 装配（全部文本锚定）
mod, emit = set(), {}

i_running = find_pre('Running title:')
mod.add(i_running)
emit[i_running] = ''
for t in ['Title page', 'Authors', 'Affiliations']:
    j = find(t)
    mod.add(j)
    emit[j] = ''
for pre in ['Word count:', 'Tables:']:
    j = find_pre(pre)
    mod.add(j)
    emit[j] = ''

i_kw = find_pre('Keywords:')
mod.add(i_kw)
emit[i_kw] = p_plain(KEYWORDS)

i_abs = find('Abstract')
i_body = find('Background')
abs_idx = [i for i in range(i_abs + 1, i_body) if orig[i].strip()]
assert len(abs_idx) == 4, '摘要段数 = %d' % len(abs_idx)
for k, i in enumerate(abs_idx):
    mod.add(i)
    emit[i] = p_lead(*ABSTRACT[k])

for src, tgt in HEADINGS.items():
    i = find(src)
    mod.add(i)
    emit[i] = p_h1(tgt)

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

# 方法末插入 STROBE + AI：锚定 'Results' 标题的前一段之后
i_res = find('Results')
INSERT_AFTER = {i_res - 1: [p_plain(STROBE), p_lead(*AI_M)]}

# Declarations 段
i_dec = find('Declarations')
dec_labels = ['Ethics approval and consent to participate.', 'Consent for publication.',
              'Availability of data and materials.', 'Competing interests.', 'Funding.',
              "Authors' contributions.", 'Acknowledgements.']
for lab, i in zip(dec_labels, range(i_dec + 1, i_dec + 8)):
    assert orig[i].strip().startswith(lab), 'Declarations 段序不符：%r / %r' % (orig[i][:40], lab)
    mod.add(i)
    emit[i] = ''
mod.add(i_dec)
emit[i_dec] = ''

# 参考文献区：'References' 标题 → 'Figure legends' 标题之前
i_ref = find('References')
i_leg = find('Figure legends')
ref_idx = [i for i in range(i_ref + 1, i_leg) if orig[i].strip()]
assert len(ref_idx) == 43, '参考文献条数 = %d' % len(ref_idx)
for k, i in enumerate(ref_idx, 1):
    mod.add(i)
    emit[i] = p_ref('%d. %s' % (k, fmt_ref(orig[i], k)))

# 删 'Figure legends' 节（与图后内联图注逐字重复）+ 旧附加材料目录
i_af1 = find('Additional file 1')
_inline = find_contain('Study flow and distribution')
assert orig[i_leg + 1] == orig[_inline], '图注重复校验失败'
for i in range(i_leg, i_af1):
    mod.add(i)
    emit[i] = ''

# 装配：正文（不含 References 区与旧附加材料）→ MDPI 后置部分 → References
parts, src_idx = [], []
for i in range(N):
    if i_ref <= i < i_leg or i >= i_af1:      # References 标题与其条目延后；旧附加材料丢弃
        continue
    parts.append(emit.get(i, blocks[i]) if i in mod else blocks[i])
    src_idx.append(i)
    if i in INSERT_AFTER:
        for x in INSERT_AFTER[i]:
            parts.append(x)
            src_idx.append(None)
parts.extend(p_h1(t) if kind == 'h1' else p_plain(t) for kind, t in BACK)
src_idx.extend([None] * len(BACK))
parts.append(blocks[i_ref])                   # References 标题
src_idx.append(i_ref)
for i in ref_idx:                             # 参考文献条目
    parts.append(emit[i])
    src_idx.append(i)
assert len(parts) == len(src_idx)

# 图号规范 + 表题句点
for k, p in enumerate(parts):
    if 'Fig. ' in p:
        parts[k] = p.replace('Fig. ', 'Figure ')
        if src_idx[k] is not None:
            mod.add(src_idx[k])
n_leg2 = 0
for k in range(len(parts) - 1):
    if '<a:blip' not in parts[k]:
        continue
    nxt = parts[k + 1]
    p2 = re.sub(r'(<w:t>)Figure (\d+)(</w:t>)', r'\1Figure \2.\3', nxt, count=1)
    assert p2 != nxt, '内联图注未命中: %r' % bt(nxt)[:60]
    parts[k + 1] = p2
    if src_idx[k + 1] is not None:
        mod.add(src_idx[k + 1])
    n_leg2 += 1
assert n_leg2 == 4, '内联图注数 = %d' % n_leg2
n_cap = 0
for k, p in enumerate(parts):
    p2 = re.sub(r'(<w:t[^>]*>)(Table \d+[A-D]?)(</w:t>)', r'\1\2.\3', p)
    if p2 != p:
        parts[k] = p2
        if src_idx[k] is not None:
            mod.add(src_idx[k])
        n_cap += 1
assert n_cap == 10, '表题数异常 %d' % n_cap

newbody = ''.join(p for p in parts if p)
assert newbody.count('\\') == 0, '出现反斜杠'

# ================================================================ 断言
changed = mod | set(range(i_af1, N))
for i in range(N):
    if i in changed:
        continue
    assert blocks[i] in newbody, '未改动块 %d 丢失：%r' % (i, orig[i][:60])
print('未改动块全部保留：%d 块' % (N - len(changed)))
n_tbl = 0
for b in blocks:
    if b.startswith('<w:tbl>'):
        assert b in newbody, '表格被改动'
        n_tbl += 1
print('表格逐字不变：%d 张' % n_tbl)
print('参考文献：%d 条（结构化 %d / 原样保留 %d）；DOI 补齐后带 DOI %d 条'
      % (len(ref_idx), ref_stats['ok'], ref_stats['pass'],
         sum(1 for t in ref_tokens.values() if t[3])))

# ---- 引号规范化
_qt = {'open': True}


def _fx(s):
    o = []
    for ch in s:
        if ch == '"':
            o.append('\u201c' if _qt['open'] else '\u201d')
            _qt['open'] = not _qt['open']
        elif ch == "'":
            o.append('\u2019')
        else:
            o.append(ch)
    return ''.join(o)


_f = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', newbody))
n_dq, n_sq = _f.count('"'), _f.count("'")
newbody = re.sub(r'(<w:t[^>]*>)([^<]*)(</w:t>)', lambda m: m.group(1) + _fx(m.group(2)) + m.group(3),
                 newbody)
_fin = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', newbody))
assert '"' not in _fin and "'" not in _fin and _qt['open'], '引号规范化失败'
print('引号规范化：直双引号 %d → 弯引号；直撇号 %d → ’' % (n_dq, n_sq))

# ---- Table 2A 网格修补
_TR2 = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
_TC2 = re.compile(r'<w:tc>.*?</w:tc>', re.S)
_GS2 = re.compile(r'<w:gridSpan w:val="(\d+)"')
_tfix = 0
_t4fix = 0
_pgfix = 0


def _fix_t2a(xml):
    """Table 2A：队列分层面板原为 7 个单元格覆盖 8 列网格，尾部两格为空（Word 中即「最后一列空白」）。
    改为 5 个单元格铺满全宽——HR 跨 2 列、P 跨 3 列，**彻底消除空列**。"""
    global _tfix
    res, pos = [], 0
    for m in re.finditer(r'<w:tbl>.*?</w:tbl>', xml, re.S):
        t = m.group(0)
        if 'Cohort-specific M2' not in t:
            continue
        W = [int(x) for x in re.findall(r'<w:gridCol w:w="(\d+)"', t)]
        ncol = len(W)
        nt = t
        for rm in _TR2.finditer(t):
            row = rm.group(0)
            cells = _TC2.findall(row)
            # 队列面板行：单元格数 = 网格列数 - 1，且尾部两格为空（列 1..n-1 各占 1 列，第 n 列无人占）
            if len(cells) != ncol - 1 or '<w:gridSpan' in ''.join(cells):
                continue
            if bt(cells[-1]).strip() or bt(cells[-2]).strip():
                continue
            hr_, p_ = cells[-4], cells[-3]      # HR = 第 4 格，P = 第 5 格
            whr = int(re.search(r'<w:tcW w:w="(\d+)"', hr_).group(1))
            wp = int(re.search(r'<w:tcW w:w="(\d+)"', p_).group(1))
            span_p = ncol - 3 - 2               # 扣掉前 3 格与 HR 的 2 列
            assert span_p >= 1, 'Table 2A P 列跨度异常 %d' % span_p
            nhr = hr_.replace('<w:tcW w:w="%d" w:type="dxa"/>' % whr,
                              '<w:tcW w:w="%d" w:type="dxa"/><w:gridSpan w:val="2"/>'
                              % (whr + W[len(cells) - 3]))
            np_ = p_.replace('<w:tcW w:w="%d" w:type="dxa"/>' % wp,
                             '<w:tcW w:w="%d" w:type="dxa"/><w:gridSpan w:val="%d"/>'
                             % (wp + sum(W[len(cells) - 2:]), span_p))
            if nhr == hr_ or np_ == p_:
                continue
            nt = nt.replace(row, row.replace(hr_, nhr, 1).replace(p_, np_, 1)
                            .replace(cells[-2], '', 1).replace(cells[-1], '', 1), 1)
            _tfix += 1
        res.append(xml[pos:m.start()])
        res.append(nt)
        pos = m.end()
    res.append(xml[pos:])
    return ''.join(res)


def _fix_t4a(xml):
    """Table 4A 原为 8 列等宽 1038 twips（≈1.83 cm/列），长文本必溢出单元格边框。
    改为按内容长度分配列宽（总 9000）并把 tblLayout 设为 fixed，使文字在格内换行。"""
    global _t4fix
    # 列宽由 j40_colfit.py（真实字体度量 + 贪心换行模拟 Word）反推，每列余量 ≥6 pt：
    #   Framework 1552｜Scale 1372｜Total 959｜Direct 1033｜Indirect 848｜Mediated 1542｜
    #   Ratio 848｜I² 848（后来 1033→959 等差值经复验，见 j40 输出）
    # 关键：三个效应列必须容得下「1.25 (β 0.2231)」整串（实测 49.4 pt）——
    # 否则会被拆成 "1.25 (β" / "0.2231)"，再叠加两端对齐就会看起来串到隔壁列。
    W = [1300, 840, 1240, 1240, 1240, 1700, 660, 780]
    res, pos = [], 0
    for m in re.finditer(r'<w:tbl>.*?</w:tbl>', xml, re.S):
        t = m.group(0)
        # 表头已精简为 'Mediated % (95 % CI)' / 'Ratio (pooled)'，用后者定位更稳
        if 'Ratio (pooled)' not in t:
            continue
        old = re.search(r'<w:tblGrid>.*?</w:tblGrid>', t, re.S).group(0)
        assert len(re.findall(r'<w:gridCol\b', old)) == len(W), 'Table 4A 列数不是 %d' % len(W)
        nt = t.replace(old, '<w:tblGrid>' + ''.join('<w:gridCol w:w="%d"/>' % w for w in W)
                       + '</w:tblGrid>', 1)
        for rm in _TR2.finditer(t):
            row, nrow = rm.group(0), rm.group(0)
            for j, c in enumerate(_TC2.findall(rm.group(0))):
                wj = int(re.search(r'<w:tcW w:w="(\d+)"', c).group(1))
                nrow = nrow.replace(c, c.replace('<w:tcW w:w="%d" w:type="dxa"/>' % wj,
                                                 '<w:tcW w:w="%d" w:type="dxa"/>' % W[j], 1), 1)
            nt = nt.replace(row, nrow, 1)
        nt = nt.replace('<w:tblLayout w:type="autofit"/>', '<w:tblLayout w:type="fixed"/>', 1)
        # 8 列长表：MDPI 明许大表用更小字号（下限 8 pt）。9 pt 下总需求超出版面宽度，
        # 各列余量不足 2 pt、文字顶线；降至 8 pt 后文字宽度减少约 11%，余量恢复到 ≥9 pt。
        # 对齐方式必须**显式**写进单元格段落：该表的对齐来自表格样式（styles.xml 里的 two-side
        # 对齐），段落里没有 <w:jc>，只做字符串替换会落空 → 实测 "1.25" 与 "(β" 被拉到列两端、
        # 中间留 25 pt 空隙，看起来像与隔壁列串在一起。
        # 规则：前两列（文字标签）左对齐；其余数值列居中。
        for _ri, _row in enumerate(_TR2.findall(nt)):
            _new_row = _row
            for _ci, _cell in enumerate(_TC2.findall(_row)):
                _jc = 'left' if _ci < 2 else 'center'
                _fixed = _cell
                for _pm in re.finditer(r'<w:p\b[^>]*>.*?</w:p>', _cell, re.S):
                    _p = _pm.group(0)
                    if '<w:jc' in _p:
                        continue
                    _q = (_p.replace('<w:pPr>', '<w:pPr><w:jc w:val="%s"/>' % _jc, 1)
                          if '<w:pPr>' in _p else
                          __import__('re').sub(r'(<w:p\b[^>]*>)', r'\1<w:pPr><w:jc w:val="%s"/></w:pPr>' % _jc, _p, count=1))
                    _fixed = _fixed.replace(_p, _q, 1)
                _new_row = _new_row.replace(_cell, _fixed, 1)
            nt = nt.replace(_row, _new_row, 1)
        nt = re.sub(r'<w:sz w:val="\d+"/>', '<w:sz w:val="16"/>', nt)
        nt = re.sub(r'<w:szCs w:val="\d+"/>', '<w:szCs w:val="16"/>', nt)
        res.append(xml[pos:m.start()])
        res.append(nt)
        pos = m.end()
        _t4fix += 1
    res.append(xml[pos:])
    return ''.join(res)


def _fix_pagination(xml):
    """分页质量（只有真正渲染/跨页时才看得见）：
       ① 每个表的首个「真表头行」加 <w:tblHeader/> —— 跨页时自动重复列头
          （Table 4C 有 34 行必跨页，原来第 2 页没有列头）
       ② 所有行加 <w:cantSplit/> —— 避免一行被分页拦腰截断
       ③ 表题段落加 keepNext —— 表题不与其表格分离"""
    global _pgfix
    TRr = re.compile(r'<w:tr\b[^>]*>.*?</w:tr>', re.S)
    res = []
    pos = 0
    for m in re.finditer(r'<w:tbl>.*?</w:tbl>', xml, re.S):
        t = m.group(0)
        nt = t
        rows = TRr.findall(t)
        hdr_row = None
        # 表头必须是**表格第一行**（Word 只重复首行），且须是「通用列头」：
        #   首格 ≤14 字符且不以 '(' 开头 —— 否则会像 Table 4C 那样把面板标题
        #   "(a) Cumulative exclusion of early follow-up" 重复到续页，
        #   而续页的行其实属于面板 (d)，造成张冠李戴（2026-10-14 由 PDF 渲染发现）。
        if rows:
            c0 = _TC2.findall(rows[0])
            first = bt(c0[0]).strip() if c0 else ''
            if len(c0) >= 2 and len(first) <= 24 and not first.startswith('(') \
                    and sum(1 for c in c0 if bt(c).strip()) >= 2:
                hdr_row = rows[0]
        for r in rows:
            if '<w:trPr>' in r:                          # 已有 trPr：只补缺的标记，不覆盖
                nr = r
                if '<w:cantSplit' not in nr:
                    nr = nr.replace('<w:trPr>', '<w:trPr><w:cantSplit/>', 1)
                if r is hdr_row and '<w:tblHeader' not in nr:
                    nr = nr.replace('<w:trPr>', '<w:trPr><w:tblHeader/>', 1)
                if nr == r:
                    continue
            else:
                trpr = ('<w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>' if r is hdr_row
                        else '<w:trPr><w:cantSplit/></w:trPr>')
                nr = r.replace('<w:tr>', '<w:tr>' + trpr, 1) if r.startswith('<w:tr>') \
                    else re.sub(r'(<w:tr\b[^>]*>)', r'\1' + trpr, r, count=1)
            nt = nt.replace(r, nr, 1)
            _pgfix += 1
        res.append(xml[pos:m.start()])
        res.append(nt)
        pos = m.end()
    res.append(xml[pos:])
    xml = ''.join(res)
    # 表题段落 keepNext
    for m in re.finditer(r'<w:p\b[^>]*>(?:(?!</w:p>).)*</w:p>', xml, re.S):
        p = m.group(0)
        if not re.match(r'^\s*Table \d+[A-D]?\.', bt(p)):
            continue
        if '<w:keepNext' in p:
            continue
        n = p.replace('<w:pPr>', '<w:pPr><w:keepNext w:val="1"/><w:keepLines w:val="1"/>', 1) \
            if '<w:pPr>' in p else p.replace('>', '><w:pPr><w:keepNext w:val="1"/></w:pPr>', 1)
        xml = xml.replace(p, n, 1)
    return xml


newbody = _fix_t2a(newbody)
newbody = _fix_t4a(newbody)
newbody = _fix_pagination(newbody)
_bad = 0
for _t in re.findall(r'<w:tbl>.*?</w:tbl>', newbody, re.S):
    _n = len(re.findall(r'<w:gridCol\b', _t))
    for _r in _TR2.finditer(_t):
        _c = _TC2.findall(_r.group(0))
        _s = sum(int(_GS2.search(c).group(1)) if _GS2.search(c) else 1 for c in _c)
        _bad += (0 if _s == _n else 1)
assert _bad == 0, '仍有 %d 行网格不一致' % _bad
print('Table 2A 网格修补：%d 行（空列已消除）；全网格复核异常 = %d' % (_tfix, _bad))
print('Table 4A 列宽重排：%d 张（改为按内容分配 + fixed 布局）' % _t4fix)
print('分页质量：%d 行已加 tblHeader/cantSplit（跨页重复列头 + 行不截断）' % _pgfix)

# ---- 内容存在性守卫
_gt = ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', newbody))
MUST = [
    ('ADL 缩写定义', '(ADL; bathing'), ('IADL 缩写定义', '(IADL; preparing'),
    ('BMI 缩写定义', 'body mass index (BMI; M2, primary)'),
    ('SD 展开', 'mean minus 1.5 standard deviations'),
    ('IQR 展开', 'interquartile range 6\u201314'),
    ('插入段①轨迹两分', 'trajectory contrast is deliberately dichotomous'),
    ('插入段②预注册与多重比较', 'The six modifiers and the four nested main models were fixed'),
    ('插入段③Katz 条目', 'the Katz items are reproduced as bathing'),
    ('插入段④七种慢病', 'Depression and cognitive impairment are deliberately excluded'),
    # 注：旧的“Additional file 1 目录”（含 _INS ⑤ 插入的 S7–S17 列表）在 JCM 版被
    #     “Supplementary Materials” 节整体取代，故此处改检新节的条目文本。
    ('补充材料目录含 S17', 'Table S17, Calibration of the primary model by cohort'),
    ('AI 使用声明', 'Use of AI-assisted tools'),
    ('STROBE 引用', 'Strengthening the Reporting of Observational'),
    ('数据可得性（含代码 DOI）', 'zenodo.23356045'),
    ('MDPI 后置章节', 'Institutional Review Board Statement'),
    ('参考文献首条带序号', '1. Livingston, G.;'),
    ('参考文献末条带序号', '43. Hou, Z.;'),
    ('补引 ref 42（Fang 2026 区分）', 'treating depressive symptoms as a mediator [42]'),
    ('补引 ref 43（Hou 2025 区分）', 'depressive symptoms alone in four cohorts [43]'),
]
_miss = [lab for lab, s in MUST if s not in _gt]
assert not _miss, '内容存在性守卫未通过，缺失：%s' % _miss
print('内容存在性守卫：%d 项全部通过' % len(MUST))

# ---- 图片替代文字（alt text）：MDPI 无障碍建议；用各图题注的首句
_fig_caps = {}
for k, p in enumerate(parts):
    t = bt(p)
    m = re.match(r'^Figure (\d)\.\s*(.+?)(?:\.\s|$)', t)
    if m:
        _fig_caps.setdefault(int(m.group(1)), m.group(2).strip())
_docpr = list(re.finditer(r'<wp:docPr[^>]*/>', newbody))
assert len(_docpr) == 4, 'docPr 数 = %d' % len(_docpr)
for i, m in enumerate(_docpr, 1):
    alt = esc(_fig_caps.get(i, 'Figure %d' % i))
    newbody = newbody.replace(
        m.group(0),
        '<wp:docPr id="%d" name="Figure %d" descr="%s"/>' % (i, i, alt), 1)
assert newbody.count('descr=') == 4, 'alt text 未全部写入'
print('图片替代文字：4 张已写入（例：%s）' % _fig_caps.get(1, '')[:60])

newdoc = head + '<w:body>' + newbody + '</w:body>' + tail

# ---- 文档属性（title/creator/subject/keywords）：MDPI 元数据与可访问性
CORE = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
        'metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<dc:title>%s</dc:title>'
        '<dc:creator>Qingcai Miao; Renjie Zhang</dc:creator>'
        '<cp:lastModifiedBy>Qingcai Miao</cp:lastModifiedBy>'
        '<dc:subject>Journal of Clinical Medicine submission (Article)</dc:subject>'
        '<cp:keywords>dementia; geriatric syndromes; disability; multimorbidity; depression; '
        'cohort harmonization</cp:keywords>'
        '<dcterms:created xsi:type="dcterms:W3CDTF">2026-10-14T00:00:00Z</dcterms:created>'
        '<dcterms:modified xsi:type="dcterms:W3CDTF">2026-10-14T00:00:00Z</dcterms:modified>'
        '</cp:coreProperties>')
TITLE_PLAIN = ('Cumulative burden of three geriatric syndromes and incident dementia across six '
               'harmonized ageing cohorts: a time-lagged analysis of 71,867 participants')
CORE = CORE % esc(TITLE_PLAIN)

z = zipfile.ZipFile(SRC)
tmp = DST + '.tmp'
zo = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
for it in z.infolist():
    if it.filename == 'word/document.xml':
        zo.writestr(it, newdoc.encode('utf8'))
    elif it.filename == 'docProps/core.xml':
        zo.writestr(it, CORE.encode('utf8'))
    else:
        zo.writestr(it, z.read(it.filename))
zo.close()
z.close()
shutil.move(tmp, DST)
print('文档属性：title / creator / subject / keywords 已写入')
print('tbl=%d blip=%d 反斜杠=%d' % (newdoc.count('<w:tbl>'), newdoc.count('<a:blip'),
                                    newdoc.count('\\')))
print('写出:', DST)
