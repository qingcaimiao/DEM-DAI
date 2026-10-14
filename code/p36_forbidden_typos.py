# -*- coding: utf-8 -*-
"""p36_forbidden_typos.py —— 禁用串 / 占位符 / 残留转义 全量扫描

用途：外部审稿意见反复出现"参考文献 7 写 multicolour""DOI 写成 azl""出现 timevarying"
这类**拼写级**指控。这类指控在 docx 上是可穷举验证的，故固化为机器检查：

  1. 禁用串（FORBID）：任何成品文件里出现即报警（错拼、旧 DOI、过时写法）；
  2. 正确形（EXPECT）：同时报告正确写法的出现次数，便于直接引用回函；
  3. 模板残留：`%s` / `%d` / 字面 `\\uXXXX` / 孤立反斜杠 / `(nan)`；
  4. 覆盖范围：正文终稿 + Additional file 1 + Additional file 2 + 补充方法 md。

输出：out/_forbidden_scan.txt（退出码非 0 表示命中禁用串）
"""
import os
import re
import sys
import zipfile

BASE = r'D:/桌面/AIzuopin/痴呆'
TARGETS = [
    ('正文终稿', os.environ.get('DEM_DOCX', os.path.join(BASE, '稿件正文_修订稿_v4_20261013.docx'))),
    ('Additional file 1', os.path.join(BASE, '附加材料_Additional_file_1_20261013.docx')),
    ('Additional file 2', os.path.join(BASE, '附加材料_Additional_file_2_STROBE_20261013.docx')),
    ('Supplementary Methods (md)', os.path.join(BASE, 'SupplementaryMethods_修订_20261013.md')),
]

# 禁用串：外部意见点名过或同类风险写法
FORBID = [
    'multicolour', 'multicolor', 'multicolort', 'multicoloure',
    'multichort', 'multichohort', 'multicohot',
    'timevarying', 'timevaring', 'timevary', 'timelagged', 'landmarkanalysis',
    'azl.71821', 'alz.71281', 'jnh.2026', 'j.jnh.',
    'fca422', 'fcaF222', 'fcaf2222',
    'at no cost', 'cost-free', 'collectable at no cost',
    'not corrected for multiple testing',
    'reasonsable request',
    'DerSimonian-Laird',          # 应为 en dash
    'KLoSA/KLoSa', 'KLoSa', 'KLOSA',
]

# 模板 / 转义残留
PATTERNS = [
    (r'%[sd]\b', '未替换的格式占位符 %s / %d'),
    (r'\\u[0-9a-fA-F]{4}', '字面 Unicode 转义（应为真实字符）'),
    (r'\\\*', '字面 markdown 转义 \\*'),
    (r'\(nan\)', '数值缺失被写成 (nan)'),
    (r'\bnan\b', '数值缺失被写成 nan'),
    (r'\bNaN\b', '数值缺失被写成 NaN'),
    (r'\bNone\b(?! of the)', '占位 None 残留（排除 “None of the …” 这一正常措辞）'),
]

# 正确形：报告出现次数，供回函引用
EXPECT = ['multicohort', 'time-varying', 'time-lagged', 'fcaf222',
          'j.jnha.2026.100983', 'alz.71821', 'Benjamini', 'DerSimonian\u2013Laird']


def docx_text(path):
    z = zipfile.ZipFile(path)
    x = z.read('word/document.xml').decode('utf8')
    # 段落以换行分隔，便于按段落报告；保留原始实体后反转义
    x = x.replace('</w:p>', '</w:p>\n')
    t = re.sub(r'<[^>]+>', '', x)
    import html
    return html.unescape(t)


def md_text(path):
    return open(path, encoding='utf8').read()


rep, bad = [], 0
rep.append('禁用串 / 占位符 / 残留转义 全量扫描（p36）')
rep.append('=' * 74)
rep.append('检查文件：%d 个' % len(TARGETS))

for label, path in TARGETS:
    if not os.path.exists(path):
        rep.append('%s：文件不存在，跳过（%s）' % (label, path))
        continue
    text = md_text(path) if path.lower().endswith('.md') else docx_text(path)
    rep.append('')
    rep.append('-' * 74)
    rep.append('%s  (%s 字符)' % (label, format(len(text), ',')))

    for s_ in FORBID:
        c = text.count(s_)
        if c:
            bad += 1
            rep.append('  [X] 禁用串命中 %-34s x%d' % (repr(s_), c))
            for m in list(re.finditer(re.escape(s_), text))[:3]:
                seg = re.sub(r'\s+', ' ', text[max(0, m.start() - 70):m.start() + 70])
                rep.append('         …%s…' % seg)
    for pat, desc in PATTERNS:
        hits = list(re.finditer(pat, text))
        if hits:
            bad += 1
            rep.append('  [X] %-34s x%d' % (desc, len(hits)))
            for m in hits[:3]:
                seg = re.sub(r'\s+', ' ', text[max(0, m.start() - 70):m.start() + 70])
                rep.append('         …%s…' % seg)
    rep.append('  正确形计数：' + '；'.join(
        '%s=%d' % (e, text.count(e)) for e in EXPECT))

rep.append('')
rep.append('=' * 74)
rep.append('命中禁用串 / 占位符的次数：%d' % bad)
rep.append('结论：%s' % ('全部干净（禁用串 0、占位符 0）' if bad == 0 else '存在需要处理的项目'))

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', '_forbidden_scan.txt')
open(out, 'w', encoding='utf8').write('\n'.join(rep))
print('\n'.join(rep))
sys.exit(0 if bad == 0 else 1)
