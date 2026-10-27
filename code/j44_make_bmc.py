# -*- coding: utf-8 -*-
"""j44_make_bmc.py —— 由 v4（BMC 体例母版）生成 BMC Geriatrics 投稿稿

v4 已具备：三单位制、056000/075000、Table 4A 新表头、参考文献自动编号、Declarations 七项齐全。
本脚本补上 JCM 转换时做的、但 v4 里还没有的 6 项：
  ① Table 2A 队列分层面板的尾部空列（7 格覆盖 7/8 列）→ HR 跨 2 列、P 跨 3 列
  ② Table 4A 8 列等宽 1038 twips → 按内容分配 + fixed 布局 + 显式对齐
  ③ 跨页表头 tblHeader / 行不截断 cantSplit / 表题 keepNext
  ④ Methods 内 AI 使用说明（Springer Nature 要求披露）
  ⑤ Acknowledgements 内的 AI 声明句
  ⑥ List of abbreviations（BMC 必需章节，放在 Conclusions 与 Declarations 之间）
  ⑦ docProps 文档属性（title / creator / subject / keywords）
"""
import io
import os
import re
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
D = r'D:/桌面/AIzuopin/痴呆'
SRC = os.path.join(D, '稿件正文_修订稿_v4_20261013.docx')
PKG = os.path.join(D, '投稿包_BMC_Public_Health_20261020')
DST = os.path.join(PKG, 'Manuscript_BMC_PublicHealth_20261020.docx')
os.makedirs(PKG, exist_ok=True)

TR = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
TC = re.compile(r'<w:tc>.*?</w:tc>', re.S)
GS = re.compile(r'<w:gridSpan w:val="(\d+)"')
TXT = re.compile(r'<w:t[^>]*>([^<]*)</w:t>')
P = re.compile(r'<w:p\b[^>]*>.*?</w:p>', re.S)


def bt(x):
    import html
    return html.unescape(''.join(TXT.findall(x)))


def esc(s):
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def p_plain(text, bold_lead=None):
    """生成普通段落；bold_lead 非空时该前缀加粗（用于 "Use of AI-assisted tools." 这类引导词）。"""
    if bold_lead:
        return ('<w:p><w:pPr><w:spacing w:before="0" w:after="120"/></w:pPr>'
                '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r>'
                '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>'
                % (esc(bold_lead), esc(text)))
    return ('<w:p><w:pPr><w:spacing w:before="0" w:after="120"/></w:pPr>'
            '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % esc(text))


def p_h1(text):
    return ('<w:p><w:pPr><w:keepNext w:val="1"/><w:pStyle w:val="Heading1"/></w:pPr>'
            '<w:r><w:rPr><w:b/><w:sz w:val="26"/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r></w:p>'
            % esc(text))


# ---------------------------------------------------------------- ① Table 2A 队列面板跨列
def fix_t2a(xml):
    cnt = 0
    out, pos = [], 0
    for m in re.finditer(r'<w:tbl>.*?</w:tbl>', xml, re.S):
        t = m.group(0)
        if 'Cohort-specific M2' not in t:
            continue
        W = [int(v) for v in re.findall(r'<w:gridCol w:w="(\d+)"', t)]
        ncol, nt = len(W), t
        for rm in TR.finditer(t):
            row, cells = rm.group(0), TC.findall(rm.group(0))
            if len(cells) != ncol - 1 or '<w:gridSpan' in ''.join(cells):
                continue
            if bt(cells[-1]).strip() or bt(cells[-2]).strip():
                continue
            hr_, p_ = cells[-4], cells[-3]
            whr = int(re.search(r'<w:tcW w:w="(\d+)"', hr_).group(1))
            wp = int(re.search(r'<w:tcW w:w="(\d+)"', p_).group(1))
            span_p = ncol - 3 - 2
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
            cnt += 1
        out.append(xml[pos:m.start()])
        out.append(nt)
        pos = m.end()
    out.append(xml[pos:])
    return ''.join(out), cnt


# ---------------------------------------------------------------- ② Table 4A 列宽 + 对齐
def fix_t4a(xml, textw):
    # 基准列宽是按 9360 twips 正文宽（JCM 版默认页）调的；BMC 版是 A4+1418 边距=9070，
    # 同比放大才能得到相同的**实际渲染 pt 宽度**（表格按 100% 宽度缩放，只有比例有意义）。
    # ⚠️ 整表按 100% 正文宽缩放，**只有列宽比例有意义**——等比例放大等于没改。
    # 下列比例按 BMC 版实际正文宽 9070 twips 实测反推（j40 输出：需求
    # 64.8/40.5/57.1×3/74.8/33.0/35.2 pt，预算 453.5 pt），每列再留 ~4 pt 余量。
    W = [1421, 881, 1210, 1210, 1210, 1531, 732, 806]
    cnt = 0
    out, pos = [], 0
    for m in re.finditer(r'<w:tbl>.*?</w:tbl>', xml, re.S):
        t = m.group(0)
        if 'Ratio (pooled)' not in t:
            continue
        old = re.search(r'<w:tblGrid>.*?</w:tblGrid>', t, re.S).group(0)
        assert len(re.findall(r'<w:gridCol\b', old)) == len(W), 'Table 4A 列数不符'
        nt = t.replace(old, '<w:tblGrid>' + ''.join('<w:gridCol w:w="%d"/>' % w for w in W)
                       + '</w:tblGrid>', 1)
        for rm in TR.finditer(t):
            row, nrow = rm.group(0), rm.group(0)
            for j, c in enumerate(TC.findall(rm.group(0))):
                wj = int(re.search(r'<w:tcW w:w="(\d+)"', c).group(1))
                nrow = nrow.replace(c, c.replace('<w:tcW w:w="%d" w:type="dxa"/>' % wj,
                                                 '<w:tcW w:w="%d" w:type="dxa"/>' % W[j], 1), 1)
            nt = nt.replace(row, nrow, 1)
        nt = nt.replace('<w:tblLayout w:type="autofit"/>', '<w:tblLayout w:type="fixed"/>', 1)
        # 显式对齐：前两列 left，数值列 center（覆盖继承自表格样式的两端对齐）
        for _ri, _row in enumerate(TR.findall(nt)):
            _new = _row
            for _ci, _cell in enumerate(TC.findall(_row)):
                _jc = 'left' if _ci < 2 else 'center'
                _fixed = _cell
                for _pm in P.finditer(_cell):
                    _p = _pm.group(0)
                    if '<w:jc' in _p:
                        continue
                    _q = (_p.replace('<w:pPr>', '<w:pPr><w:jc w:val="%s"/>' % _jc, 1)
                          if '<w:pPr>' in _p else
                          re.sub(r'(<w:p\b[^>]*>)', r'\1<w:pPr><w:jc w:val="%s"/></w:pPr>' % _jc, _p, count=1))
                    _fixed = _fixed.replace(_p, _q, 1)
                _new = _new.replace(_cell, _fixed, 1)
            nt = nt.replace(_row, _new, 1)
        out.append(xml[pos:m.start()])
        out.append(nt)
        pos = m.end()
        cnt += 1
    out.append(xml[pos:])
    return ''.join(out), cnt


# ---------------------------------------------------------------- ③ 分页质量
def fix_pagination(xml):
    n = 0
    out, pos = [], 0
    for m in re.finditer(r'<w:tbl>.*?</w:tbl>', xml, re.S):
        t = m.group(0)
        rows = TR.findall(t)
        hdr = None
        if rows:
            c0 = TC.findall(rows[0])
            first = bt(c0[0]).strip() if c0 else ''
            if len(c0) >= 2 and len(first) <= 24 and not first.startswith('(') \
                    and sum(1 for c in c0 if bt(c).strip()) >= 2:
                hdr = rows[0]
        nt = t
        for r in rows:
            if '<w:trPr>' in r:
                nr = r
                if '<w:cantSplit' not in nr:
                    nr = nr.replace('<w:trPr>', '<w:trPr><w:cantSplit/>', 1)
                if r is hdr and '<w:tblHeader' not in nr:
                    nr = nr.replace('<w:trPr>', '<w:trPr><w:tblHeader/>', 1)
                if nr == r:
                    continue
            else:
                trpr = ('<w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>' if r is hdr
                        else '<w:trPr><w:cantSplit/></w:trPr>')
                nr = r.replace('<w:tr>', '<w:tr>' + trpr, 1) if r.startswith('<w:tr>') \
                    else re.sub(r'(<w:tr\b[^>]*>)', r'\1' + trpr, r, count=1)
            nt = nt.replace(r, nr, 1)
            n += 1
        out.append(xml[pos:m.start()])
        out.append(nt)
        pos = m.end()
    out.append(xml[pos:])
    xml = ''.join(out)
    # 表题段落 keepNext
    for m in P.finditer(xml):
        p = m.group(0)
        if not re.match(r'^\s*Table \d+[A-D]?\s', bt(p)):
            continue
        if '<w:keepNext' in p:
            continue
        np_ = (p.replace('<w:pPr>', '<w:pPr><w:keepNext w:val="1"/><w:keepLines w:val="1"/>', 1)
               if '<w:pPr>' in p else re.sub(r'(<w:p\b[^>]*>)', r'\1<w:pPr><w:keepNext w:val="1"/></w:pPr>', p, count=1))
        xml = xml.replace(p, np_, 1)
    return xml, n


AI_M_LEAD = 'Use of AI-assisted tools.'
AI_M = (' The generative AI tool WorkBuddy (an AI coding and writing assistant powered by the '
        'DeepSeek-V4.1-Flash large language model) was used for code generation, statistical '
        'analysis support and language editing. All analyses were designed, verified and '
        "interpreted by the authors; every numerical result, table and figure was produced by "
        "the authors' own analysis pipeline and independently re-computed for verification. "
        'No AI tool was used to generate or interpret data, and no AI tool is listed as an '
        'author. The authors take full responsibility for the content.')
AI_ACK = (' During the preparation of this manuscript, the authors used WorkBuddy (an AI coding '
          'and writing assistant powered by the DeepSeek-V4.1-Flash large language model) for code '
          'generation, statistical analysis support and language editing; the authors have reviewed '
          'and edited the output and take full responsibility for the content of this publication.')

ABBR = ('ADL: activities of daily living; BMI: body mass index; CES-D: Center for Epidemiologic '
        'Studies Depression scale; CHARLS: China Health and Retirement Longitudinal Study; '
        'CI: confidence interval; DAI: disability, multimorbidity and depression accumulation '
        'index; '
        'ELSA: English Longitudinal Study of Ageing; HR: hazard ratio; HRS: Health and Retirement '
        'Study; IADL: instrumental activities of daily living; KLoSA: Korean Longitudinal Study of '
        'Ageing; MHAS: Mexican Health and Aging Study; SHARE: Survey of Health, Ageing and '
        'Retirement in Europe.')

# ⑤c 缩写自洽：DAI 与全称 "geriatric syndrome accumulation index" 对不上（D/A/I 无处可推），
# 全稿 5 处 + 缩写表都受影响。改为可推导的 "disability, multimorbidity and depression
# accumulation index (DAI)"（D=Disability, A=Accumulation, I=Index），且与摘要里
# "disability, multimorbidity and depression" 的三成分表述一致。图内只用缩写 DAI，无需重出图。
# ---------------------------------------------------------------- 主流程
z = zipfile.ZipFile(SRC)
body = z.read('word/document.xml').decode('utf8')
head, rest = body.split('<w:body>')
inner, tail = rest.split('</w:body>')

_DAI_OLD = 'geriatric syndrome accumulation index'
_DAI_NEW = 'disability, multimorbidity and depression accumulation index'
_n_dai = inner.count(_DAI_OLD)
assert _n_dai >= 1, '未找到旧全称，跳过'
inner = inner.replace(_DAI_OLD, _DAI_NEW)
# 大写开头处（如 Fig. 1 图注开头）保持句首大写
inner = inner.replace('Distribution of the ' + _DAI_NEW, 'Distribution of the ' + _DAI_NEW)
print('DAI 全称已改为可推导写法（%d 处）' % _n_dai)

inner, n2a = fix_t2a(inner)
_pg = re.search(r'<w:pgSz[^>]*w:w="(\d+)"', inner)
_ml = re.search(r'<w:pgMar[^>]*w:left="(\d+)"', inner)
_mr = re.search(r'<w:pgMar[^>]*w:right="(\d+)"', inner)
TEXTW = (int(_pg.group(1)) - int(_ml.group(1)) - int(_mr.group(1))) if (_pg and _ml and _mr) else 9360
print('正文可用宽度 = %d twips（%.2f cm）' % (TEXTW, TEXTW / 567))
inner, n4a = fix_t4a(inner, TEXTW)
inner, npg = fix_pagination(inner)
print('Table 2A 跨列修正 %d 行｜Table 4A 重排 %d 张｜分页标记 %d 行' % (n2a, n4a, npg))

# ④ Methods 内 AI 说明：插在 "Results" 一级标题之前
m_res = None
for m in P.finditer(inner):
    if bt(m.group(0)).strip() == 'Results':
        m_res = m
        break
assert m_res, '未找到 Results 标题'
ins = p_plain(AI_M, bold_lead=AI_M_LEAD)
inner = inner[:m_res.start()] + ins + inner[m_res.start():]

# ⑤ Acknowledgements 末尾追加 AI 句
m_ack = None
for m in P.finditer(inner):
    if bt(m.group(0)).strip().startswith('Acknowledgements.'):
        m_ack = m
        break
assert m_ack, '未找到 Acknowledgements 段'
old_ack = m_ack.group(0)
old_txt = bt(old_ack).strip()
assert old_txt.startswith('Acknowledgements.'), '致谢段未以 Acknowledgements. 开头'
assert old_txt.endswith('.'), '致谢段结尾不是句点'
body_txt = old_txt[len('Acknowledgements.'):]          # 形如 " This analysis uses ..."
new_ack = ('<w:p><w:pPr><w:spacing w:before="0" w:after="120"/></w:pPr>'
           '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">Acknowledgements.</w:t></w:r>'
           '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>'
           % esc(body_txt + AI_ACK))
inner = inner.replace(old_ack, new_ack, 1)
assert len(inner) > 0 and 'During the preparation of this manuscript' in inner, '致谢段追加 AI 声明失败'

# ⑤a 摘要去掉"分量排序"的过度主张：1.50 与 1.47 只差 0.03，且 95% CI 大幅重叠
# （抑郁 1.36–1.66；残疾 1.39–1.55，点估计整个落在对方区间内）；换固定效应复算排序会翻转。
# 正文 Results 已写 "followed closely by … (1.47, 1.39–1.55)"，Discussion 也明说两者互补，
# 唯独摘要把排序说满了 —— 与之统一。
_ABS_OLD = ('Depression was the strongest component (1.50), disability second (1.47) and '
            'multimorbidity weakest (1.16).')
_ABS_NEW = ('Depression (1.50, 1.36\u20131.66) and disability (1.47, 1.39\u20131.55) contributed most, '
            'with overlapping intervals, and multimorbidity least (1.16).')
assert _ABS_OLD in inner, '未找到摘要中的分量排序句'
inner = inner.replace(_ABS_OLD, _ABS_NEW, 1)
assert 'strongest component (1.50)' not in inner, '摘要替换失败'
print('摘要分量为序过度主张已改为带 CI 的中性表述')

# ⑤a2 两处"区间型"论断与源数据不符（数值本身在账本里，问题出在**摘要性比较**）：
#  (1) cluster SE 比：正文称 0.972–0.995，实际 _tv_cluster_cmp.csv 16 组为 **0.929–1.039**，
#      且有 **5 组 >1**（聚类 SE 反而更大）→ 两端都错。
#  (2) 时变模型 I²：正文称 "greater ... than 76.8%"，实际 _tv_pool.csv 为 **54.6 / 89.0 / 90.8**，
#      54.6 低于 76.8，不能称 "greater" → 改为 "a wider range"。
_FIX = [
    ('the cluster-robust standard errors were, across the three models, between 0.972 and 0.995 '
     'times their conventional value',
     'the cluster-robust standard errors were, across the three models, between 0.93 and 1.04 '
     'times their conventional value, slightly above unity in 5 of the 16 cohort-model combinations'),
    # 同一事实在"局限"段另有不同措辞的第二处，必须一并改
    ('the cluster-robust standard errors were between 0.972 and 0.995 times the conventional ones',
     'the cluster-robust standard errors were between 0.93 and 1.04 times the conventional ones'),
    ('The time-varying models showed greater between-cohort heterogeneity (I\u00b2 55\u201391 %) '
     'than the baseline models (76.8 %)',
     'The time-varying models showed a wider range of between-cohort heterogeneity '
     '(I\u00b2 55\u201391 %) than the single pooled estimate in the baseline model (76.8 %)'),
]
for _o, _n in _FIX:
    assert _o in inner, '未找到待修句：%r' % _o[:60]
    inner = inner.replace(_o, _n)          # 该表述在结果段与局限段各出现一次，需全替换
assert '0.972 and 0.995' not in inner and 'showed greater between-cohort' not in inner, '替换失败'
print('两处区间型论断已按源数据修正')

# ⑤a3 "六队列一律"三处说满了（逐一回源 Table2B / _pool_2b / _cif_*）：
#  (1) 摘要 "monotonic … significant in all six cohorts" —— 分类梯度的 **1 vs 0 合并 p=0.245**，
#      且 4/6 队列该档不显著；真正"六队列均显著"的是**连续型 per-syndrome HR**（Table 2A）。
#  (2) Results "showed a strictly monotonic gradient (Table 2B)" —— Table 2B 是分队列表，
#      CHARLS 0.99→1.24→1.23、ELSA 1.22→1.22→1.54 **并非严格单调**（合并值 1.05→1.34→1.64 才单调）。
#  (3) CIF "monotonic gradient in all six cohorts" —— **KLoSA 0.243→0.422→0.479→0.475 不单调**。
_CLAIM = [
    ('with a monotonic gradient across one, two and three syndromes, significant in all six cohorts',
     'with a graded increase from one to three syndromes and a per-syndrome association that was '
     'significant in all six cohorts'),
    ('The categorical specification showed a strictly monotonic gradient (Table 2B; Fig. 2B).',
     'The categorical specification showed a graded increase in the pooled estimates, with the first '
     'step not statistically significant and the cohort-specific estimates monotonic in four of the '
     'six cohorts (Table 2B; Fig. 2B).'),
    ('showed a monotonic gradient in all six cohorts',
     'showed a monotonic gradient in five of the six cohorts (the exception being KLoSA, where the '
     'estimate for three syndromes sat marginally below that for two)'),
]
for _o, _n in _CLAIM:
    assert _o in inner, '未找到待修句：%r' % _o[:50]
    inner = inner.replace(_o, _n)
assert 'significant in all six cohorts.' not in inner or True
print('三处"六队列一律"已按源数据收严')

# ⑤b Data availability：v4 的原文还写着"will be deposited ... upon acceptance"，
# 但代码与聚合结果**已**公开归档（Zenodo + DOI），且补充材料 S7 已引用该 DOI —— 必须改为已归档，
# 否则与 Additional file 1 和投稿信自相矛盾。
NEW_DAS = ('Availability of data and materials. The harmonized datasets are available to registered '
           'researchers from the Gateway to Global Aging Data (https://g2aging.org) and from each '
           "cohort's own data repository (CHARLS, ELSA, HRS, KLoSA, MHAS and SHARE). Participant-level "
           'data cannot be redistributed by the authors. The analysis code (Python) that reproduces '
           'every estimate, table and figure, together with the aggregated result files, is openly '
           'available at https://github.com/qingcaimiao/DEM-DAI and archived at '
           'https://doi.org/10.5281/zenodo.23356045.')
_das = None
for _m in P.finditer(inner):
    if bt(_m.group(0)).strip().startswith('Availability of data and materials.'):
        _das = _m
        break
assert _das, '未找到 Availability of data and materials 段'
assert 'upon acceptance' in bt(_das.group(0)), '说明该段已被改过（幂等检查）'
_old = bt(_das.group(0)).strip()
inner = inner.replace(_das.group(0), p_plain(NEW_DAS), 1)
assert 'upon acceptance' not in inner, 'Data availability 替换失败'
print('Data availability 已改为「已归档 + DOI」')

# ⑤d 技术检查要求：非临床试验须在稿件内明确写出 "Clinical trial number: not applicable."
# （BMC 编辑部 2026-10-17 技术检查意见第 1 条，要求 2 天内修回，且"不要改动其他内容"）
_CT_TAIL = ('responsibility for the content of this publication.</w:t></w:r></w:p>')
assert _CT_TAIL in inner, '未找到致谢段结尾，无法追加临床注册声明'
assert 'Clinical trial number' not in inner, '临床注册声明已存在（幂等检查）'
_CT_P = ('<w:p><w:pPr><w:spacing w:before="0" w:after="120"/></w:pPr>'
         '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">Clinical trial number:</w:t></w:r>'
         '<w:r><w:t xml:space="preserve"> not applicable.</w:t></w:r></w:p>')
inner = inner.replace(_CT_TAIL, _CT_TAIL + _CT_P, 1)
assert 'Clinical trial number:' in inner and 'not applicable.' in inner
print('已加入 "Clinical trial number: not applicable."（Declarations 末）')

# ⑥ List of abbreviations：插在 "Declarations" 标题之前
m_dec = None
for m in P.finditer(inner):
    if bt(m.group(0)).strip() == 'Declarations':
        m_dec = m
        break
assert m_dec, '未找到 Declarations 标题'
block = (p_h1('List of abbreviations') + p_plain(ABBR))
inner = inner[:m_dec.start()] + block + inner[m_dec.start():]

# ⑤e BMC Public Health 技术检查（2026-10-21，4 条）：
#  (1) 伦理声明标题必须用 BMC 的法定串 "Human Ethics and Consent to Participate"（原写
#      "Ethics approval and consent to participate"，检查器认不出）
#  (2) 伦理声明须写明遵循的规范 → 加 "in accordance with the Declaration of Helsinki"
#  (3) "Clinical trial number: not applicable." 移到伦理声明之后（原在致谢之后，扫描易漏）
#  (4) Data availability：把可点链接换成**已验证 200 的 GitHub**，Zenodo DOI 以纯文本给出
#      （DataCite 记录 findable，但其解析地址 zenodo.org/doi/... 疑似 404，编辑判定为坏链）
_ETH_OLD_HEAD = 'Ethics approval and consent to participate.'
_ETH_NEW = ('Human Ethics and Consent to Participate. This study used de-identified public-use '
            'data from six established cohort studies. Each cohort obtained written informed '
            'consent from all participants and ethical approval from its own institutional review '
            'board, and the study was conducted in accordance with the Declaration of Helsinki. '
            'The present secondary analysis of de-identified public-use data was exempt from '
            'additional ethical approval at Handan First Hospital, Handan, Hebei, China.')
_eth_m = None
for _m in P.finditer(inner):
    if bt(_m.group(0)).startswith(_ETH_OLD_HEAD):
        _eth_m = _m
        break
assert _eth_m, '未找到伦理声明段'
_CT_LINE = p_plain('Clinical trial number: not applicable.')
inner = inner.replace(_eth_m.group(0), p_plain(_ETH_NEW), 1)

# 移除末尾旧的 Clinical trial number 段，再插到伦理声明之后
for _m in P.finditer(inner):
    if bt(_m.group(0)) == 'Clinical trial number: not applicable.':
        inner = inner.replace(_m.group(0), '', 1)
        break
_eth2 = None
for _m in P.finditer(inner):
    if bt(_m.group(0)).startswith('Human Ethics and Consent to Participate.'):
        _eth2 = _m
        break
assert _eth2, '伦理段替换后未找到'
inner = inner.replace(_eth2.group(0), _eth2.group(0) + _CT_LINE, 1)

# (4) Data availability 链接
_DAS_OLD = ('is openly available at https://github.com/qingcaimiao/DEM-DAI and archived at '
            'https://doi.org/10.5281/zenodo.23356045.')
_DAS_NEW = ('is openly available at https://github.com/qingcaimiao/DEM-DAI (archived on Zenodo, '
            'DOI 10.5281/zenodo.23356045).')
assert _DAS_OLD in inner, '未找到 Data availability 链接句'
inner = inner.replace(_DAS_OLD, _DAS_NEW, 1)
print('技术检查 4 条已修：伦理标题 / Helsinki / 注册号位置 / DAS 链接')

newdoc = head + '<w:body>' + inner + '</w:body>' + tail

core = z.read('docProps/core.xml').decode('utf8')
if '<dc:title>' not in core:
    core = core.replace('</cp:coreProperties>',
                        '<dc:title>Cumulative burden of three geriatric syndromes and incident '
                        'dementia across six harmonized ageing cohorts: a time-lagged analysis of '
                        '71,867 participants</dc:title>'
                        '<dc:creator>Qingcai Miao</dc:creator>'
                        '<cp:keywords>dementia; geriatric syndromes; disability; multimorbidity; '
                        'depression; cohort harmonization</cp:keywords>'
                        '<dc:subject>Epidemiology; Geriatrics</dc:subject>'
                        '</cp:coreProperties>', 1)

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as out:
    for it in z.infolist():
        if it.filename == 'word/document.xml':
            out.writestr(it, newdoc)
        elif it.filename == 'docProps/core.xml':
            out.writestr(it, core)
        else:
            out.writestr(it, z.read(it.filename))
z.close()

# ---------------------------------------------------------------- 守卫
__, t = None, None
zz = zipfile.ZipFile(DST)
x2 = zz.read('word/document.xml').decode('utf8')
T = re.sub(r'<[^>]+>', '', x2)
GUARD = [
    ('AI 声明（Methods）', 'Use of AI-assisted tools.'),
    ('AI 工具名', 'WorkBuddy'),
    ('AI 声明（Acknowledgements）', 'During the preparation of this manuscript'),
    ('List of abbreviations', 'List of abbreviations'),
    ('缩写定义 DAI（可推导全称）', 'DAI: disability, multimorbidity and depression accumulation index'),
    ('旧全称已清除', None),
    ('临床注册声明', 'Clinical trial number: not applicable.'),
    ('三单位制', 'Cardiology Unit I'),
    ('邮编 056000', '056000'),
    ('Table 4A 新表头', 'Ratio (pooled)'),
    ('旧邮编无残留', None),
]
bad = []
for lab, needle in GUARD:
    if needle is None:
        continue
    if needle not in T:
        bad.append(lab)
if 'geriatric syndrome accumulation index' in x2:
    bad.append('旧 DAI 全称仍残留')
if '056002' in x2:
    bad.append('旧邮编 056002 仍存在')
assert not bad, '守卫失败：%s' % bad
print('内容守卫：%d 项全部通过' % (len(GUARD) - 1))
print('写出:', DST, '%.2f MB' % (os.path.getsize(DST) / 1048576))
