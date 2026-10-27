# -*- coding: utf-8 -*-
"""p23_insert_tables.py —— 把 p22 生成的表格作为真实 Word 表格对象插入文稿

输入：D:/桌面/AIzuopin/痴呆/稿件正文_修订版_20261013.docx
      out/_tables.json
输出：D:/桌面/AIzuopin/痴呆/稿件正文_修订稿_v4_20261013.docx
规则：
- 按正文首次引用位置，在该段之后插入 caption 段 + 表格 + 注释段
- Table 4A 已是真实表格对象，仅在其前补 caption 段
- 不动其他任何部件
"""
import os
import re
import json
import shutil
import zipfile

# Paths are parameterised: override with environment variables if needed.
_BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('DEM_OUT', os.path.join(_BASE, 'out'))
SRC = os.environ.get('DEM_SRC_DOCX', os.path.join(_BASE, 'manuscript_revised.docx'))
DST = os.environ.get('DEM_DST_DOCX', os.path.join(_BASE, 'manuscript_v4.docx'))
FONT = ('<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" '
        'w:eastAsia="Times New Roman" w:cs="Times New Roman"/>')
BORD = ('<w:tblBorders><w:top w:val="single" w:color="CBCDD1" w:sz="6" w:space="0"/>'
        '<w:left w:val="single" w:color="CBCDD1" w:sz="6" w:space="0"/>'
        '<w:bottom w:val="single" w:color="CBCDD1" w:sz="6" w:space="0"/>'
        '<w:right w:val="single" w:color="CBCDD1" w:sz="6" w:space="0"/>'
        '<w:insideH w:val="single" w:color="CBCDD1" w:sz="6" w:space="0"/>'
        '<w:insideV w:val="single" w:color="CBCDD1" w:sz="6" w:space="0"/></w:tblBorders>')


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def para(text, bold=False, italic=False, size=20, before=120, after=120, keep_next=False):
    rpr = '<w:rPr>%s%s%s<w:sz w:val="%d"/></w:rPr>' % (
        FONT, '<w:b w:val="1"/>' if bold else '', '<w:i w:val="1"/>' if italic else '', size)
    ppr = ('<w:pPr><w:spacing w:before="%d" w:after="%d" w:line="240" w:lineRule="auto"/>'
           '%s</w:pPr>' % (before, after, '<w:keepNext/>' if keep_next else ''))
    return '<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (ppr, rpr, esc(text))


def caption(label, rest):
    rpr_b = '<w:rPr>%s<w:b w:val="1"/><w:sz w:val="20"/></w:rPr>' % FONT
    rpr_n = '<w:rPr>%s<w:sz w:val="20"/></w:rPr>' % FONT
    ppr = ('<w:pPr><w:spacing w:before="240" w:after="80" w:line="240" w:lineRule="auto"/>'
           '<w:keepNext/></w:pPr>')
    return ('<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>'
            '<w:r>%s<w:t xml:space="preserve"> %s</w:t></w:r></w:p>'
            % (ppr, rpr_b, esc(label), rpr_n, esc(rest)))


def tc(text, bold=False, span=1, w=1200, shade=None):
    tcpr = ('<w:tcPr><w:tcW w:w="%d" w:type="dxa"/>%s%s<w:vAlign w:val="center"/></w:tcPr>'
            % (w, '<w:gridSpan w:val="%d"/>' % span if span > 1 else '',
               '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade if shade else ''))
    rpr = '<w:rPr>%s%s<w:sz w:val="16"/></w:rPr>' % (
        FONT, '<w:b w:val="1"/>' if bold else '')
    ppr = ('<w:pPr><w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/>'
           '<w:jc w:val="%s"/></w:pPr>' % ('left' if span > 1 else 'center'))
    return ('<w:tc>%s<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p></w:tc>'
            % (tcpr, ppr, rpr, esc(text)))


def table_xml(rows, colw=None, ncol=None):
    n = ncol or max(len(r) for r in rows)
    if colw is None:
        colw = [int(9000 / n)] * n
    grid = ''.join('<w:gridCol w:w="%d"/>' % w for w in colw)
    trs = []
    for i, r in enumerate(rows):
        filled = [c for c in r if str(c).strip() != '']
        is_panel = (len(filled) == 1 and len(r) > 1 and str(r[0]).strip() != '')
        if is_panel:
            trs.append('<w:tr>%s</w:tr>' % tc(str(r[0]), bold=True, span=n, w=sum(colw),
                                              shade='F2F4F7'))
            continue
        tcs = []
        for j, c in enumerate(r):
            bold = (i == 0) and not is_panel
            tcs.append(tc(c, bold=bold, w=colw[j] if j < len(colw) else 1200))
        trs.append('<w:tr>%s</w:tr>' % ''.join(tcs))
    pr = ('<w:tblPr><w:tblW w:w="5000" w:type="pct"/>%s<w:tblLayout w:type="autofit"/>'
          '<w:tblCellMar><w:top w:w="15" w:type="dxa"/><w:left w:w="15" w:type="dxa"/>'
          '<w:bottom w:w="15" w:type="dxa"/><w:right w:w="15" w:type="dxa"/></w:tblCellMar>'
          '</w:tblPr>' % BORD)
    return '<w:tbl>%s<w:tblGrid>%s</w:tblGrid>%s</w:tbl>' % (pr, grid, ''.join(trs))


TABLES = json.load(open(os.path.join(OUT, '_tables.json'), encoding='utf8'))
z = zipfile.ZipFile(SRC)
doc = z.read('word/document.xml').decode('utf8')
head, body, tail = doc.split('<w:body>')[0], doc.split('<w:body>')[1].split('</w:body>')[0], \
    '</w:body>' + doc.split('</w:body>')[1]

BLOCK_RE = re.compile(r'<w:tbl>.*?</w:tbl>|<w:p\b.*?</w:p>|<w:p\b[^>]*/>', re.S)
blocks = list(BLOCK_RE.finditer(body))
print('正文块数:', len(blocks))


def txt(b):
    return ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', b))


# 校验锚点：按"引用段特征串"在运行时定位
# （2026-10-13：原先用固定块索引，题头/Declarations 增删段落即错位，故改为文本定位）
def resolve(anchor_text):
    hits = [i for i, b in enumerate(blocks) if anchor_text in txt(b.group(0))]
    assert len(hits) == 1, '锚点 %r 命中 %d 次（应恰好 1 次）: %s' % (anchor_text, len(hits), hits)
    return hits[0]


for t in TABLES:
    assert 'anchor_text' in t, '表 %s 缺少 anchor_text' % t['key']
    t['anchor'] = resolve(t['anchor_text'])
    b = blocks[t['anchor']]
    s = txt(b.group(0))
    assert len(s) > 40, '锚点 %d 文本过短: %s' % (t['anchor'], s)
    print('%-4s anchor=%-4d %-44s | %s' % (t['key'], t['anchor'], t['anchor_text'][:44], s[:56]))

# 逆序插入
ins = sorted(TABLES, key=lambda t: -t['anchor'])
for t in ins:
    if t.get('cap_only'):
        frag = caption(*re.match(r'^(\S+ \S+)\s+(.*)$', t['cap']).groups())
        pos = blocks[t['anchor']].end()
        body = body[:pos] + frag + body[pos:]
        print('插入 %s caption（既有表格对象前置）' % t['key'])
        continue
    frag = caption(*re.match(r'^(\S+ \S+)\s+(.*)$', t['cap']).groups())
    rows_all = ([t['header']] if t.get('header') else []) + list(t['rows'])
    frag += table_xml(rows_all, colw=t.get('colw'))
    if t.get('note'):
        frag += para('Note. ' + t['note'], italic=True, size=16, before=60, after=240)
    pos = blocks[t['anchor']].end()
    body = body[:pos] + frag + body[pos:]
    print('插入 %s（%d 行 × %d 列）%s' % (t['key'], len(rows_all), max(len(r) for r in rows_all),
                                    '［含表头行］' if t.get('header') else ''))

# 2026-10-13：Table 4A 列名更精确（原为 "Ratio of pooled effects"），并保持反斜杠校验
body = body.replace('Ratio of pooled effects', 'Ratio of pooled coefficients')
# 2026-10-14：这两个表头过长、把列宽顶满（渲染后看似出格）→ 精简措辞，注中仍保留完整解释
body = body.replace('Mediated proportion (95 % CI)', 'Mediated % (95 % CI)')
body = body.replace('Ratio of pooled coefficients', 'Ratio (pooled)')
body = body.replace('The ratio of pooled effects, 1', 'The ratio of pooled coefficients, 1')
newdoc = head + '<w:body>' + body + tail
assert newdoc.count('\\') == 0, '出现反斜杠'

zo = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
for it in z.infolist():
    if it.filename == 'word/document.xml':
        zo.writestr(it, newdoc.encode('utf8'))
    else:
        zo.writestr(it, z.read(it.filename))
zo.close()
z.close()
print('\n已写出:', DST)

# 复核
z2 = zipfile.ZipFile(DST)
x2 = z2.read('word/document.xml').decode('utf8')
print('tbl=%d  blip=%d  反斜杠=%d  段落=%d'
      % (x2.count('<w:tbl>'), x2.count('<a:blip'), x2.count('\\'),
         x2.count('<w:p ') + x2.count('<w:p>')))
