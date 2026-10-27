# -*- coding: utf-8 -*-
"""revise_apply.py —— 把 revise_ms.py 里的规则应用到 docx

- 逐 run 做字符串替换（已验证稿件的数字没有被拆散到多个 run）
- 局限段（P147）按主题重构为 3 段
- 应用后自动统计摘要/正文字数并回填题头
输出：稿件正文_修订版_20261013.docx、_revised_text.txt
"""
import os
import re
import html
import shutil
import zipfile

from revise_ms import RULES, PIDX, DST, SRC, WORK, V, n

_MS = os.path.join(WORK, '_ms')
if not os.path.isdir(_MS):          # 首次运行时从源稿解包（不改变任何替换逻辑）
    import zipfile as _zf
    with _zf.ZipFile(SRC) as _z:
        _z.extractall(_MS)
XML = open(os.path.join(_MS, 'word', 'document.xml'), encoding='utf-8').read()
used = {}


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def apply(text):
    for old, new, tag in RULES:
        if old in text:
            text = text.replace(old, new)
            used[tag] = used.get(tag, 0) + 1
    return text


para_pat = re.compile(r'<w:p[ >].*?</w:p>', re.S)
paras = para_pat.findall(XML)


def para_text(p):
    return html.unescape(''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S)))


def rewrite_runs(p, only=None):
    """only 非空时只应用指定的 (old,new,tag) 一条规则（用于段落定向替换）。"""
    def one(m):
        head, inner = m.group(1), m.group(2)
        t = html.unescape(inner)
        if only is None:
            new_t = apply(t)
        else:
            old, new, tag = only
            if old in t:
                new_t = t.replace(old, new)
                used[tag] = used.get(tag, 0) + 1
            else:
                new_t = t
        space = ' xml:space="preserve"' if (new_t != new_t.strip()) else ''
        head2 = re.sub(r'\s*xml:space="[^"]*"', '', head) + space
        return '<w:t%s>%s</w:t>' % (head2, esc(new_t))
    return re.sub(r'<w:t([^>]*)>(.*?)</w:t>', one, p, flags=re.S)


# ------------------------------------------------ 局限段重构文本
lim1 = ("Several limitations must be acknowledged. **Outcome ascertainment.** The outcome was an algorithmic "
        "classification of probable dementia rather than a clinical diagnosis. Agreement between our derived "
        "criterion and the classifications distributed with the harmonized files was moderate (Cohen \u03ba "
        "%s\u2013%s across ELSA, HRS and KLoSA) [30,31], and alternative outcome definitions gave estimates "
        "from %s to %s, all concordant with the primary result. **Exposure measurement.** Exposure "
        "components are self-reported: multimorbidity reflects physician diagnosis reported by the participant, "
        "and depression is a scale threshold rather than a clinical diagnosis. Such misclassification is "
        "generally expected to bias estimates towards the null, so the true associations may be somewhat "
        "stronger. The components are equally weighted without external validation of the weights, although a "
        "first-principal-component weighted index gave a similar estimate with near-equal loadings, supporting "
        "that choice. **Measurement comparability.** The harmonized cognitive instruments differ "
        "between cohorts \u2014 a 27-point battery, a 25-point battery or item-level scores "
        "depending on the survey \u2014 and the criterion is a within-cohort education-stratified "
        "z-score threshold in the tradition of the Langa\u2013Weir approach rather than a fixed "
        "cut-off on a shared scale. We did not test measurement invariance formally, so the "
        "criterion should be read as comparable in construction but not strictly equivalent "
        "across cohorts; that is also why event rates exceed those reported from clinically "
        "ascertained cohorts, since the criterion also captures milder impairment."
        % (n('kappa_min'), n('kappa_max'), n('alt_min'), n('alt_max')))

lim2 = ("**Design and confounding.** Residual confounding cannot be excluded in an observational design; the "
        "E-value of %s for the lower confidence limit quantifies how strong such confounding would need to "
        "be. Follow-up length varies considerably (MHAS %s years, CHARLS %s years, HRS %s years), which reduces "
        "precision in the longest-lag strata. The time-varying models showed greater between-cohort "
        "heterogeneity (I\u00b2 55\u201391 %%) than the baseline models (%s %%), and were further restricted by "
        "covariate completeness; they should be treated as exploratory, with the baseline models providing the "
        "primary effect estimates. Standard errors in the time-varying models were clustered by participant, "
        "which accounts for the correlation between the successive intervals contributed by one person; the "
        "cluster-robust standard errors were between %s and %s times the conventional ones and the point "
        "estimates were unchanged. The "
        "counterfactual mediation analysis rests on two untestable assumptions \u2014 sequential ignorability and "
        "the absence of exposure-induced confounding \u2014 and its risks are extrapolated from parametric Cox "
        "and logistic models; it is presented as a cross-validation of the mediated proportion under a "
        "different scale and framework, not as causal evidence. The mediated proportion was poolable in all "
        "six cohorts under every framework, so no specification lost a cohort, but its value depends on the "
        "pooling estimand: pooling cohort-specific proportions gives %s\u2013%s %% "
        "whereas taking the ratio of the pooled coefficients gives %s\u2013%s %%. Both are reported, and under "
        "either depression remains a quantitatively modest mediator. **Age range.** The index required "
        "an age of 50 years or over because the three syndromes are uncommon earlier in life; as a "
        "result few events arise in the youngest stratum, and the estimates for that group rest on "
        "far fewer outcomes than the older strata, so the age interaction should be read with that "
        "in mind."
        % (n('evalue_M2_ci'), n('cohort_fu_MHAS', 0), n('cohort_fu_CHARLS', 0), n('cohort_fu_HRS', 0),
           n('pool_M2_I2', 1), n('seratio_med_min', 3), n('seratio_med_max', 3),
           n('med_pct_min', 1), n('med_pct_max', 1),
           n('med_ratio_min', 1), n('med_ratio_max', 1)))

lim3 = ("**Generalisability and multiplicity.** The joint association of physical and psychological burden with "
        "dementia has already been reported in two and in three cohorts [14,15]; the contribution of the "
        "present analysis therefore lies in scale, geographic breadth, temporal design and mechanism rather "
        "than in first description. The Indian cohort (LASI) could not be included because it has only a "
        "single wave, so coverage of low- and middle-income settings rests on CHARLS and MHAS. Subgroup and "
        "interaction analyses were corrected for multiplicity across the six prespecified modifiers by the "
        "Benjamini\u2013Hochberg procedure, and age and marital status remained significant after that "
        "correction; the interaction estimates were "
        "themselves heterogeneous across cohorts. All 15 stratum-specific estimates nevertheless remained "
        "above unity, so the qualitative conclusion does not depend on the subgroup results. Finally, %s %% of "
        "participants with a complete exposure lacked at least one covariate and were older and more often "
        "disabled; multiple imputation analyses that recovered them reproduced the primary estimate to within "
        "%s. **Coverage and heterogeneity.** Coverage is uneven in two respects: Europe is "
        "represented only by Western Europe (SHARE), and the only East Asian cohorts are CHARLS "
        "and KLoSA, so these estimates should not be generalised to South Asia, Africa, or Latin "
        "American settings other than Mexico. Between-cohort heterogeneity in the primary model "
        "was substantial (I\u00b2 = %s %%; \u03c4\u00b2 = %s on the log-hazard scale), which "
        "reflects genuine differences in cohort composition, exposure prevalence and outcome "
        "ascertainment rather than sampling error alone; the point estimate was nevertheless "
        "insensitive to the choice of heterogeneity estimator and to leave-one-cohort-out "
        "analysis."
        % (n('miss_pct', 1), n('mice_maxdiff', 4), n('pool_M2_I2', 1), n('pool_M2_tau2', 4)))

LIM_NEW = [lim1, lim2, lim3]

new_paras = []

# ------------------------------------------------ 2026-10-13 投稿前：整段替换
# 这些占位段的文本被拆进多个 <w:t> run，逐 run 替换无法命中，故按"整段文本 == 原串"重建该段。
PARA_REPL = [
    ('\\* Corresponding author: [Name], [Postal address], [City, Country]. E-mail: [e-mail]',
     ['* Corresponding author: Renjie Zhang, Department of Cardiology (Cardiology Unit I), Handan First Hospital, No. 25 Congtai Road, Handan 056000, Hebei, China. E-mail: zhangrenjie725@sina.com. ORCID: 0009-0009-4026-2068.',
      'ORCID: Qingcai Miao 0009-0006-1479-6726; Renjie Zhang 0009-0009-4026-2068.']),
    ('Tables: 4 main, 6 supplementary. Figures: 4 main.',
     'Tables: 10 main (Tables 1, 2A, 2B, 3A, 3B, 3C, 4A, 4B, 4C, 4D); 17 supplementary '
     '(Tables S1\u2013S17). Figures: 4 main.'),
    ('Funding. [To be completed.]',
     'Funding. This research received no specific grant from any funding agency in the public, '
     'commercial or not-for-profit sectors.'),
    ("Authors' contributions. [To be completed.] All authors read and approved the final manuscript.",
     "Authors' contributions. QM and RZ conceived and designed the study. QM performed the "
     "statistical analysis and wrote the first draft. JC and LC contributed to the harmonization "
     "of the six cohorts and to the construction of the exposure and outcome variables. RL "
     "designed and checked the sensitivity, time-lag, trajectory and mediation analyses. RZ "
     "supervised the study, independently verified the analytical code and critically revised the "
     "manuscript. All authors read and approved the final manuscript."),
    ('Acknowledgements. [To be completed.] This analysis uses data from the Gateway to Global Aging Data and the underlying cohorts.',
     'Acknowledgements. This analysis uses data from the Gateway to Global Aging Data and from '
     'CHARLS, ELSA, HRS, KLoSA, MHAS and SHARE. The authors thank the study teams and the '
     'respondents of these cohorts, and the Gateway to Global Aging Data for its harmonization '
     'documentation.'),
]
for _old, _new in PARA_REPL:
    for _p in paras:
        if para_text(_p).strip() == _old:
            _ppr = re.search(r'<w:pPr>.*?</w:pPr>', _p, re.S)
            _ppr = _ppr.group(0) if _ppr else ''
            _rpr = re.search(r'<w:rPr>.*?</w:rPr>', _p, re.S)
            _rpr = _rpr.group(0) if _rpr else ''
            _lines = _new if isinstance(_new, (list, tuple)) else [_new]
            _frag = ''.join('<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>'
                            % (_ppr, _rpr, esc(_l)) for _l in _lines)
            XML = XML.replace(_p, _frag, 1)
            used['投稿前整段替换：%s' % _old[:22]] = 1
            print('整段已替换：', (_new if isinstance(_new, str) else _new[0])[:70])
            break
    else:
        raise SystemExit('!! 未找到整段锚点：%s' % _old[:70])

for idx, p in enumerate(paras):
    txt = para_text(p)
    if txt.strip().startswith('Several limitations must be acknowledged.'):
        ppr = re.search(r'<w:pPr>.*?</w:pPr>', p, re.S)
        ppr = ppr.group(0) if ppr else ''
        rpr = re.search(r'<w:rPr>.*?</w:rPr>', p, re.S)
        rpr = rpr.group(0) if rpr else ''
        frag = []
        for blk in LIM_NEW:
            runs = []
            for part in re.split(r'(\*\*[^*]+\*\*)', blk):
                if not part:
                    continue
                if part.startswith('**') and part.endswith('**'):
                    runs.append('<w:r><w:rPr><w:b w:val="1"/></w:rPr>'
                                '<w:t xml:space="preserve">%s</w:t></w:r>' % esc(part[2:-2]))
                else:
                    runs.append('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, esc(part)))
            frag.append('<w:p>%s%s</w:p>' % (ppr, ''.join(runs)))
        new_paras.append(''.join(frag))
        used['局限段重构为 3 段'] = 1
    elif idx in PIDX:
        new_paras.append(rewrite_runs(p, only=PIDX[idx]))
    else:
        new_paras.append(rewrite_runs(p))

for p, np_ in zip(paras, new_paras):
    XML = XML.replace(p, np_, 1)

# ------------------------------------------------ 2026-10-13：补引参考文献 39–41（追加在 ref 38 之后）
REF_NEW = [
    'Zhou Y, Guo Y. Intrinsic capacity impairment and incident dementia across three population-based cohorts: '
    'a harmonized individual participant data analysis. J Nutr Health Aging. 2026;30(11):100983. '
    'doi:10.1016/j.jnha.2026.100983. PMID: 42727174.',
    'Wang X, Hao H, Jiang T, Yao X, Duan Y, Xia J, Wang C, Liang J. Dynamic frailty exposure and cognitive aging '
    'trajectories: a multicohort study. Alzheimers Dement. 2026;22(9):e71821. doi:10.1002/alz.71821. '
    'PMID: 42723149.',
    'Peng L, Chen Z, Li L, Zhang S. Frailty, trajectories of frailty, and cognitive impairment: evidence from five '
    'longitudinal cohort studies. BMC Public Health. 2026;26(1):2349. doi:10.1186/s12889-026-28715-0. '
    'PMID: 42595986.',    'Fang J, Cheng W, Li H, Ho K, Yang C, Zhang Y, et al. Frailty transitions, depressive symptoms, and incident '
    'dementia: findings from four longitudinal studies. J Affect Disord. 2026;414:122381. '
    'doi:10.1016/j.jad.2026.122381. PMID: 42600788.',
    'Hou Z, Ming Y, Lu K, Ma Y, Jia R, Lai G, et al. Cumulative and variable depression symptom exposure and '
    'incident dementia: Panel data analysis of four longitudinal cohort studies. Alzheimers Dement. '
    '2025;21(11):e70950. doi:10.1002/alz.70950. PMID: 41313677.',
]

_anchor = 'White IR, Royston P. Imputing missing covariate values for the Cox model.'
for _i, _p in enumerate(paras):
    if _anchor in para_text(_p):
        _ppr = re.search(r'<w:pPr>.*?</w:pPr>', _p, re.S)
        _ppr = _ppr.group(0) if _ppr else ''
        _rpr = re.search(r'<w:rPr>.*?</w:rPr>', _p, re.S)
        _rpr = _rpr.group(0) if _rpr else ''
        _frag = ''.join('<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>'
                        % (_ppr, _rpr, esc(_r)) for _r in REF_NEW)
        XML = XML.replace(_p, _p + _frag, 1)
        used['参考文献补引 39-43'] = 1
        print('已在 ref 38 之后追加 3 条参考文献（39-41）')
        break
else:
    raise SystemExit('!! 未找到 ref 38 段落，参考文献未追加')

# ------------------------------------------------ 2026-10-13：题头补 ORCID 段 + 附表目录拆分 S7
# S6/S7 表题在原文中本就是两段，无需插入；此列表保留为空，便于日后扩展。
_INS = [
    # ① 轨迹分类的两分性质与密度/HR 的主次
    ('We classified participants by their exposure at the baseline and immediately subsequent waves',
     ['The trajectory contrast is deliberately dichotomous \u2014 any burden (index \u2265 1) versus none \u2014 '
      'which prioritises the interpretability of reversal over dose resolution; the continuous and categorical '
      'models retain the full 0\u20133 granularity, and the trajectory analysis should be read as a complement to '
      'them. Incidence density within a trajectory is reported per unit of person-time at risk in that group; '
      'because the groups differ in follow-up length and in mortality, the corresponding hazard ratios, not the '
      'densities, are the primary quantity, and the densities are descriptive.']),
    # ② 预注册状态
    ('Six effect modifiers were prespecified',
     ['The six modifiers and the four nested main models were fixed before any interaction model was fitted. The '
      'analysis was not registered in a public trials or analysis registry, so the time-lag, trajectory, '
      'competing-risk and mediation components should be described as pre-specified within this project\u2019s own '
      'analysis plan rather than as prospectively registered. Interaction P values were additionally corrected '
      'for multiplicity across the six modifiers by the Benjamini\u2013Hochberg procedure, and the subgroup '
      'results are presented as exploratory throughout.']),
    # ③ ADL 条目与 Katz 原版的差异
    ('Disability \u2014 self-reported difficulty with at least one basic activity of daily living',
     ['Following the harmonized files, the Katz items are reproduced as bathing, dressing, eating, transferring '
      'from bed, toileting and walking; the harmonized instrument therefore substitutes walking for the '
      'continence item of the original Katz index, and walking was retained because it is the item measured '
      'consistently in every cohort.']),
    # ⑥ 单位 3（河北北方学院）：插在单位 2 之后（2026-10-14 按作者更正为三单位制）
    ('\u00b2 Handan Key Laboratory of Cardiac Precision Medicine',
     ['\u00b3 Hebei North University, No. 11 Diamond South Road, Zhangjiakou Economic Development Zone, Zhangjiakou 075000, Hebei, China']),
    # ⑤ Additional file 1 目录：补齐 S7–S13
    ('Table S6 Cohort-specific total, direct and indirect effects',
     ['Table S7 Exposure trajectory-specific incidence densities by cohort.',
      'Table S8 Association after adjustment for baseline cognitive performance.',
      'Table S9 Hazard of death by exposure category (cause-specific, death as the event).',
      'Table S10 Equivalence of the lag-specific estimates to the no-lag estimate.',
      'Table S11 Effect modification: multiplicative interaction with Benjamini\u2013Hochberg correction.',
      'Table S12 Characteristics of the sample contributing to each lag-specific estimate.',
      'Table S13 Cluster-robust standard errors for the interval (time-varying) models.',
      'Table S14 Subdistribution hazard ratios by exposure category (Fine\u2013Gray).',
      'Table S15 Sensitivity of the pooled estimate to the random-effects estimator, and meta-regression on candidate sources of heterogeneity.',
      'Table S16 Sensitivity analysis requiring the outcome criterion to be met at two consecutive assessments.',
      'Table S17 Calibration of the primary model by cohort (observed/expected ratio and calibration slope).']),
    # ④ 七种慢病的取舍
    ('Multimorbidity \u2014 two or more self-reported, physician-diagnosed chronic conditions',
     ['Depression and cognitive impairment are deliberately excluded from these seven conditions: depression is '
      'a separate component of the index, and cognitive impairment is the outcome construct, so including either '
      'would build the exposure out of the outcome domain. The number was fixed at seven because these are the '
      'conditions ascertained identically across all six cohorts.']),
]
# 2026-10-14 修复（严重）：锚点必须在**规则应用之后**的 XML 上重新扫描。
# 原实现在「规则前的段落快照」上匹配锚点、却在「规则已改写的 XML」上做 replace：
# 一旦某条规则改动了锚点所在段（例如给 ADL/IADL 补缩写定义），replace 静默失配，
# 被追加的段落整段丢失且不计入「未命中规则数」——曾导致 Katz 说明段凭空消失。
for _key, _lines in _INS:
    _hit = None
    for _p in para_pat.findall(XML.split('<w:body>')[1]):
        if _key in para_text(_p):
            _hit = _p
            break
    if _hit is None:
        raise SystemExit('!! 未找到插入锚点：%s' % _key[:60])
    _ppr = re.search(r'<w:pPr>.*?</w:pPr>', _hit, re.S)
    _ppr = _ppr.group(0) if _ppr else ''
    _rpr = re.search(r'<w:rPr>.*?</w:rPr>', _hit, re.S)
    _rpr = _rpr.group(0) if _rpr else ''
    _frag = ''.join('<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>'
                    % (_ppr, _rpr, esc(_l)) for _l in _lines)
    _n0 = len(XML)
    XML = XML.replace(_hit, _hit + _frag, 1)
    assert len(XML) > _n0, '插入未生效（锚点串在替换时未命中）：%s' % _key[:60]
    used['投稿前插入段落：%s' % _key[:26]] = 1
    print('已插入段落：', _lines[0][:64])

# ------------------------------------------------ 字数回填
body = XML.split('<w:body>')[1]
ps = para_pat.findall(body)


def ptext(p):
    return html.unescape(''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', p, re.S)))


W = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\u2019\-]*")
abs_txt, main_txt = '', ''
in_abs = False
for p in ps:
    t = ptext(p).strip()
    if t == 'Abstract':
        in_abs = True
        continue
    if in_abs and t == 'Background':
        in_abs = False
    if in_abs:
        abs_txt += ' ' + t
in_main = False
for p in ps:
    t = ptext(p).strip()
    if t == 'Background' and not in_main:
        in_main = True
        continue
    if t == 'Declarations':
        in_main = False
    if in_main:
        main_txt += ' ' + t
n_abs = len(W.findall(re.sub(r'(\d)\s+%', r'\1%', abs_txt)))
n_main = len(W.findall(re.sub(r'(\d)\s+%', r'\1%', main_txt)))
print('摘要词数 = %d   正文词数 = %d' % (n_abs, n_main))

old_wc = 'Abstract 350 (limit 350); main text 7,494'
new_wc = 'Abstract %d; main text %s' % (n_abs, format(n_main, ','))
if old_wc in XML:
    XML = XML.replace(old_wc, new_wc, 1)
else:
    print('!! 未命中字数串')

# ------------------------------------------------ 写盘
if not XML.lstrip().startswith('<?xml'):
    XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + XML

outdir = os.path.join(WORK, '_ms_new')
if os.path.exists(outdir):
    # 2026-10-13：不删除既有目录（沙箱 rmtree 会失败且删除不可逆），改为改名留痕
    import time as _t
    _bak = outdir + '_bak%d' % int(_t.time())
    os.rename(outdir, _bak)
    print('原 _ms_new 已改名留痕：', _bak)
shutil.copytree(os.path.join(WORK, '_ms'), outdir)
open(os.path.join(outdir, 'word', 'document.xml'), 'w', encoding='utf-8').write(XML)

if os.path.exists(DST):
    os.remove(DST)
zf = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
for root, dirs, files in os.walk(outdir):
    for f in files:
        fp = os.path.join(root, f)
        zf.write(fp, os.path.relpath(fp, outdir).replace('\\', '/'))
zf.close()
print('写出', DST)

txt_lines = [ptext(p) for p in para_pat.findall(XML.split('<w:body>')[1])]
open(os.path.join(WORK, '_revised_text.txt'), 'w', encoding='utf-8').write('\n'.join(txt_lines))
print('写出 _revised_text.txt，段落 %d' % len(txt_lines))

print('\n---- 规则命中统计 ----')
miss = 0
for old, new, tag in RULES:
    c = used.get(tag, 0)
    if c == 0:
        miss += 1
        print('  X 未命中: %-30s | %s' % (tag, old[:70]))
    else:
        print('  v %-30s x%d' % (tag, c))
for i, (old, new, tag) in PIDX.items():
    c = used.get(tag, 0)
    if c == 0:
        miss += 1
        print('  X 未命中(段%s): %-26s | %s' % (i, tag, old[:60]))
    else:
        print('  v %-30s x%d' % (tag, c))
print('\n未命中规则数 =', miss)
