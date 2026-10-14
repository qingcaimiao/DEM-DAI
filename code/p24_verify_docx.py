# -*- coding: utf-8 -*-
"""p24_verify_docx.py —— 终检：按文档流顺序导出段落与表格，核对表格位置与内容完整性"""
import os
import docx

P = os.environ.get('DEM_DOCX', r'D:/桌面/AIzuopin/痴呆/稿件正文_修订稿_v4_20261013.docx')
OUT = r'D:/workbuddygongzuokongjian/2026-10-12-21-32-15/dem_pipeline/out/_verify_docx.txt'
d = docx.Document(P)
lines = []
ntbl = 0
for blk in d.element.body.iterchildren():
    tag = blk.tag.split('}')[-1]
    if tag == 'p':
        t = ''.join(n.text or '' for n in blk.iter() if n.tag.endswith('}t'))
        lines.append('[P] ' + t)
    elif tag == 'tbl':
        ntbl += 1
        rows = blk.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr')
        lines.append('[TBL %d] rows=%d' % (ntbl, len(rows)))
        for r in rows:
            cells = r.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc')
            vals = [''.join(n.text or '' for n in c.iter()
                             if n.tag.endswith('}t')) for c in cells]
            lines.append('    | ' + ' | '.join(vals))
lines.append('')
lines.append('总段数=%d 表格数=%d' % (sum(1 for l in lines if l.startswith('[P] ')), ntbl))
open(OUT, 'w', encoding='utf8').write('\n'.join(lines))
print('总段数=%d 表格数=%d' % (sum(1 for l in lines if l.startswith('[P] ')), ntbl))
print('输出:', OUT)
# 表名与位置
import re
prev = ''
for l in lines:
    if l.startswith('[TBL'):
        print('  ', prev[:110], '-->', l)
    if not l.startswith('    |') and l.strip():
        prev = l
