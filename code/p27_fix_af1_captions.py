# -*- coding: utf-8 -*-
"""p27_fix_af1_captions.py —— 让正文里 Additional file 1 的表目说明与实际的补充表一一对应"""
import os
import re
import zipfile

DOCX = r'D:/桌面/AIzuopin/痴呆/稿件正文_修订稿_v4_20261013.docx'
MAP = [
    ('<w:t xml:space="preserve"> Baseline characteristics of the six cohorts.</w:t>',
     '<w:t xml:space="preserve"> Cohort overview, data sources and baseline sample of the six '
     'cohorts.</w:t>'),
    ('<w:t xml:space="preserve"> Pre-screening decisions for candidate index components (S3a) and '
     'formal comparison of candidate accumulation indices (S3b).</w:t>',
     '<w:t xml:space="preserve"> Pre-screening decisions for candidate index components (S3a), '
     'formal comparison of candidate index specifications (S3b) and discrimination of the count '
     'index against its three components (S3c).</w:t>'),
    ('<w:t xml:space="preserve"> Detailed cohort harmonization, exposure construction, outcome '
     'ascertainment and statistical procedures.</w:t>',
     '<w:t xml:space="preserve"> Detailed cohort harmonization, exposure construction, outcome '
     'ascertainment and statistical procedures (provided as a separate file).</w:t>'),
]
z = zipfile.ZipFile(DOCX)
doc = z.read('word/document.xml').decode('utf8')
n = 0
for old, new in MAP:
    if old not in doc:
        print('  跳过（上游规则已完成或文案已变）：%s' % old[:60])
        continue
    doc = doc.replace(old, new, 1)
    n += 1
tmp = DOCX + '.tmp'
zo = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
for it in z.infolist():
    zo.writestr(it, doc.encode('utf8') if it.filename == 'word/document.xml'
                else z.read(it.filename))
zo.close()
z.close()
os.replace(tmp, DOCX)
print('已修订 %d 条表目说明' % n)
