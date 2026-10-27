# -*- coding: utf-8 -*-
"""j5_coverletter.py —— 生成 JCM 投稿信（Markdown 留档 + PDF 提交件）"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

PKG = r'D:/桌面/AIzuopin/痴呆/投稿包_JCM_20261014'
os.makedirs(PKG, exist_ok=True)

DATE = '14 October 2026'
JOURNAL = 'Journal of Clinical Medicine'
TITLE = ('Cumulative burden of three geriatric syndromes and incident dementia across six '
         'harmonized ageing cohorts: a time-lagged analysis of 71,867 participants')

BODY = [
    ('To', 'The Editorial Office, %s (MDPI)' % JOURNAL),
    ('Date', DATE),
    ('Manuscript type', 'Article (original research)'),
    ('Title', TITLE),
    ('Corresponding author', 'Renjie Zhang, MD (zhangrenjie725@sina.com)'),
    ('Authors', 'Qingcai Miao; Jianhong Cen; Lu Chen; Runzhi Lu; Renjie Zhang'),
    ('', ''),
    ('salutation', 'Dear Editors,'),

    ('p', 'We submit for your consideration a multicohort study of 71,867 older adults in which the '
          'cumulative burden of three named geriatric syndromes \u2014 disability, multimorbidity and '
          'depression \u2014 counted as a single unweighted index (0\u20133) predicted incident dementia '
          '(pooled HR 1.27, 95 % CI 1.21\u20131.33 per additional syndrome; I\u00b2 = 76.8 %) across six '
          'harmonized population-based cohorts on three continents (CHARLS, ELSA, HRS, KLoSA, MHAS and '
          'SHARE; 11,185 incident cases over 694,305 person-years).'),

    ('h', 'What the study adds'),
    ('p', 'The three syndromes are individually established risk factors, and joint '
          'physical\u2013psychological exposures have been reported in two and in three cohorts. The '
          'contribution here is not first description but scale, construct and temporal design. First, '
          'the exposure is a minimal, computable count of three items that every harmonized ageing '
          'survey already collects in its core instrument, rather than a deficit-accumulation frailty '
          'index of 30 or more items or a five-domain composite; the minimal index loses no '
          'discrimination relative to a full multivariate specification of the same components '
          '(\u0394C = \u22120.0016, and \u22120.0009 (95 % CI \u22120.0018 to \u22120.0001) in the pooled '
          'paired-bootstrap comparison, inside a non-inferiority margin of 0.01), so the information is '
          'in the construct rather than in a weighted score. Second, the association survives a '
          'deliberately adversarial sequence of reverse-causation designs: excluding the first 2 to 12 '
          'years of follow-up leaves the estimate essentially unchanged (no trend with increasing '
          'latency, P = 0.128), and measuring exposure four to six years before outcome ascertainment '
          'reproduces the baseline estimate. Third, the effect of non-depressive burden is decomposed '
          'under three independent identification frameworks, which converge on a depression-mediated '
          'fraction that is modest and bounded (12.7\u201317.4 % when cohort-specific proportions are '
          'pooled).'),

    ('p', 'Two findings that qualify the headline association are reported as such, because we think '
          'they matter more than a large effect size: multimorbidity carries little independent signal '
          'once disability and depression are accounted for, and risk tracks the current level of '
          'burden rather than its rate of change. The practical implication is that a three-item '
          'assessment \u2014 of which the two most informative items are functional limitation and '
          'depressive symptoms \u2014 captures most of the gradient.'),

    ('h', 'Why it suits your readership'),
    ('p', 'The index requires no laboratory measurement, no grip strength and no gait speed, items that '
          'are missing in most of the world\u2019s ageing cohorts. Two of the six cohorts are from '
          'middle-income settings, and the analysis includes Korean and Mexican populations that are '
          'under-represented in this literature.'),

    ('h', 'Rigour and transparency'),
    ('p', 'Between-cohort heterogeneity in the primary model is substantial and we do not hide it '
          '(I\u00b2 = 76.8 %); we report E-values, competing-risk models, leave-one-out estimates, four '
          'alternative outcome definitions, multiple-imputation analyses, a pre-specified '
          'Benjamini\u2013Hochberg correction for the interaction analyses, and the full cohort-level '
          'detail in the Supplementary Materials. Every number, table and figure in the manuscript is '
          'produced by a single versioned analysis pipeline. The completed STROBE checklist is provided '
          'in the Supplementary Materials.'),

    ('h', 'Declarations'),
    ('p', 'This work is original, is not under consideration elsewhere, and has not been published '
          'previously in whole or in part. All authors have read and approved the submission and agree '
          'to its content. The authors declare no conflicts of interest. The study used de-identified '
          'public-use data from established cohort studies that obtained their own ethical approval and '
          'participant consent; no additional ethical approval was required. Consistent with the '
          'disclosure in the manuscript, the generative AI tool WorkBuddy (an AI coding and writing '
          'assistant powered by the DeepSeek-V4.1-Flash large language model) was used for code '
          'generation, statistical analysis support and language editing; all analyses were designed, '
          'verified and interpreted by the authors, and the authors take full responsibility for the '
          'content.'),

    ('h', 'Data and code availability'),
    ('p', 'The harmonized data are available to registered researchers from the Gateway to Global Aging '
          'Data and from each cohort\u2019s own repository. The analysis code that reproduces every '
          'number, table and figure is openly available at https://github.com/qingcaimiao/DEM-DAI and '
          'archived on Zenodo at https://doi.org/10.5281/zenodo.23356045.'),

    ('p', 'Suggested reviewers, if you wish to use them, are listed in the submission form. We confirm '
          'that none is affiliated with Handan First Hospital or Hebei North University and that none '
          'has been a co-author within the past five years.'),

    ('p', 'Thank you for considering our work.'),

    ('p', 'Yours sincerely,'),
    ('p', 'Renjie Zhang, MD'),
    ('p', 'Department of Cardiology (Cardiology Unit I), Handan First Hospital, No. 25 Congtai '
          'Road, Handan 056000, Hebei, China'),
    ('p', 'E-mail: zhangrenjie725@sina.com | ORCID: 0009-0009-4026-2068'),
    ('p', 'on behalf of all authors'),
]

# ---------------------------------------------------------------- Markdown 留档
md = ['# Cover letter', '']
for k, v in BODY:
    if k == '':
        md.append('')
    elif k in ('salutation', 'p'):
        md.append(v)
        md.append('')
    elif k == 'h':
        md.append('**%s.**' % v)
        md.append('')
    else:
        md.append('**%s:** %s' % (k, v))
        md.append('')
md_path = os.path.join(PKG, '_核对报告', 'Cover_Letter_JCM.md')   # 与审计脚本读取路径一致
open(md_path, 'w', encoding='utf-8').write('\n'.join(md))
print('写出', md_path)

# ---------------------------------------------------------------- PDF
from fpdf import FPDF

FONT_DIR = r'C:/Windows/Fonts'
pdf = FPDF(format='A4', unit='mm')
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_font('AR', '', os.path.join(FONT_DIR, 'arial.ttf'))
pdf.add_font('AR', 'B', os.path.join(FONT_DIR, 'arialbd.ttf'))
pdf.add_font('AR', 'I', os.path.join(FONT_DIR, 'ariali.ttf'))
pdf.add_page()
pdf.set_margins(22, 18, 22)

for k, v in BODY:
    if k == '':
        pdf.ln(3)
        continue
    if k == 'salutation':
        pdf.set_font('AR', '', 10.5)
        pdf.multi_cell(0, 5.2, v)
        pdf.ln(1.5)
        continue
    if k == 'h':
        pdf.set_font('AR', 'B', 10.5)
        pdf.ln(2)
        pdf.multi_cell(0, 5.2, v + '.')
        pdf.ln(0.5)
        continue
    if k == 'p':
        pdf.set_font('AR', '', 10.5)
        pdf.multi_cell(0, 5.2, v)
        pdf.ln(1.5)
        continue
    if k == 'Title':
        pdf.set_font('AR', 'B', 10.5)
        pdf.multi_cell(0, 5.2, v)
        pdf.ln(1)
        continue
    pdf.set_font('AR', 'B', 10.5)
    pdf.write(5.2, k + ': ')
    pdf.set_font('AR', '', 10.5)
    pdf.multi_cell(0, 5.2, str(v))
    pdf.ln(0.6)

pdf_path = os.path.join(PKG, 'Cover_Letter_JCM.pdf')
pdf.output(pdf_path)
print('写出 %s (%d B)' % (pdf_path, os.path.getsize(pdf_path)))
