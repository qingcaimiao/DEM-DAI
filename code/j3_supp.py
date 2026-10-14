# -*- coding: utf-8 -*-
"""j3_supp.py —— 补充材料 JCM/MDPI 化 + 修正过期编号 → 投稿包

1) Additional file 1 → Supplementary_Materials_1_Methods_and_Tables.docx
   "Additional file 1" → "Supplementary Materials"
2) Additional file 2 → Supplementary_Materials_2_STROBE_Checklist.docx
   "Additional file 1/2" 术语 → Supplementary Materials；并修正过期编号：
   Tables S1–S7 → S1–S17；nine main tables → ten；4A–4C → 4A–4D；seven supplementary → seventeen
   "Methods, " → "Materials and Methods, "（与 JCM 章名一致）
"""
import os
import re
import shutil
import zipfile

D = r'D:/桌面/AIzuopin/痴呆'
PKG = os.path.join(D, '投稿包_JCM_20261014')
os.makedirs(PKG, exist_ok=True)

SRC1 = os.path.join(D, '附加材料_Additional_file_1_20261013.docx')
SRC2 = os.path.join(D, '附加材料_Additional_file_2_STROBE_20261013.docx')
DST1 = os.path.join(PKG, 'Supplementary_Materials_1_Methods_and_Tables.docx')
DST2 = os.path.join(PKG, 'Supplementary_Materials_2_STROBE_Checklist.docx')

RULES1 = [
    ('Additional file 1', 'Supplementary Materials', 1),
]
RULES2 = [
    # 过期编号（真实缺陷）：主表已 10 张、补充表已 17 张
    ('Tables S1\u2013S7 (seven supplementary tables)',
     'Tables S1\u2013S17 (seventeen supplementary tables)', 1),
    ('Tables 1, 2A\u20132B, 3A\u20133C and 4A\u20134C (nine main tables)',
     'Tables 1, 2A\u20132B, 3A\u20133C and 4A\u20134D (ten main tables)', 1),
    ('Additional file 1 contains the Supplementary Methods and Tables S1\u2013S7.',
     'The Supplementary Materials also contain the Supplementary Methods and Tables S1\u2013S17.', 1),
    # 术语
    ('prepared for submission as Additional file 2',
     'submitted as part of the Supplementary Materials', 1),
    ('Additional file 1 \u00a7', 'Supplementary Materials, Section ', 8),
    ('Additional file 1 Table S', 'Table S', 5),
    ('Additional file 1 (Supplementary Methods)', 'the Supplementary Materials', 1),
    ('Additional file 1 (supplementary methods)', 'the Supplementary Materials', 1),
    # 章名与 JCM 一致
    ('Methods, *', 'Materials and Methods, Section *', 13),
]


def apply(path, rules, dst):
    x = zipfile.ZipFile(path).read('word/document.xml').decode('utf8')
    for old, new, exp in rules:
        n = x.count(old)
        if n != exp:
            # 允许该规则在个别稿中出现次数不同；打印但用实际次数替换
            print('  ! 规则命中 %d 次（预期 %d）: %r' % (n, exp, old[:60]))
        x = x.replace(old, new)
    # 兜底：剩余 "Additional file N" 一律改称
    x = re.sub(r'Additional file \d', 'Supplementary Materials', x)
    x = x.replace('Supplementary Materials \u00a7', 'Supplementary Materials, Section ')
    x = x.replace('Supplementary Materials Table S', 'Table S')
    x = x.replace('Supplementary Materials 1', 'Supplementary Materials').replace(
        'Supplementary Materials 2', 'Supplementary Materials')
    # 反斜杠校验
    assert x.count('\\') == 0, '出现反斜杠'
    shutil.copy(path, dst)
    z = zipfile.ZipFile(dst, 'a')
    z.writestr('word/document.xml', x.encode('utf8'))
    z.close()
    # 清空并重写 zip（避免重复条目）
    zin = zipfile.ZipFile(dst)
    items = [(i, zin.read(i.filename)) for i in zin.infolist()]
    zin.close()
    seen = set()
    zo = zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED)
    for i, data in items:
        if i.filename in seen:
            continue
        seen.add(i.filename)
        zo.writestr(i, x.encode('utf8') if i.filename == 'word/document.xml' else data)
    zo.close()
    t = re.sub(r'<[^>]+>', '', x)
    print('  %s → 段落 %d 表 %d | Additional file 残留 %d | 反斜杠 %d'
          % (os.path.basename(dst), x.count('<w:p '), x.count('<w:tbl>'),
             t.count('Additional file'), x.count('\\')))
    return t


print('=== AF1 ===')
t1 = apply(SRC1, RULES1, DST1)
assert t1.count('Additional file') == 0
print('=== AF2 ===')
t2 = apply(SRC2, RULES2, DST2)
assert t2.count('Additional file') == 0
assert 'Tables S1\u2013S17' in t2 and 'ten main tables' in t2
print()
print('补充材料已规范化并写入投稿包。')
