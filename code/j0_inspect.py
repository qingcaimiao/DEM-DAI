# -*- coding: utf-8 -*-
"""读取 v4 段落结构，定位 MDPI 改体例所需的全部锚点"""
import re
import sys
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
P = r'D:/桌面/AIzuopin/痴呆/稿件正文_修订稿_v4_20261013.docx'
x = zipfile.ZipFile(P).read('word/document.xml').decode('utf8')
body = x.split('<w:body>')[1].split('</w:body>')[0]
BLOCK = re.compile(r'<w:tbl>.*?</w:tbl>|<w:p\b.*?</w:p>|<w:p\b[^>]*/>', re.S)
paras = [''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', b.group(0)))
         for b in BLOCK.finditer(body)]

print('总块数 =', len(paras))
print()
print('=== 前 40 块（题头/摘要/关键词/引言开头）===')
for i in range(min(40, len(paras))):
    t = paras[i].strip()
    if t:
        print('[%3d] %s' % (i, t[:210]))
print()
print('=== 章节标题候选（短段落）===')
for i, t in enumerate(paras):
    s = t.strip()
    if s and len(s) < 60 and not s.endswith('.') and not s.endswith(','):
        print('[%3d] %s' % (i, s))
print()
print('=== 含 "Additional file" 的块 ===')
for i, t in enumerate(paras):
    if 'Additional file' in t:
        print('[%3d] %s' % (i, t[:230]))
