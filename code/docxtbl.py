# -*- coding: utf-8 -*-
"""docxtbl.py —— 生成 Word 表格 XML 的公共小工具（Times New Roman，边框 CBCDD1）"""
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
    rpr = '<w:rPr>%s%s<w:sz w:val="16"/></w:rPr>' % (FONT, '<w:b w:val="1"/>' if bold else '')
    ppr = ('<w:pPr><w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/>'
           '<w:jc w:val="%s"/></w:pPr>' % ('left' if span > 1 else 'center'))
    return ('<w:tc>%s<w:p>%s<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r></w:p></w:tc>'
            % (tcpr, ppr, rpr, esc(text)))


def table_xml(rows, colw=None, ncol=None, panel_shade='F2F4F7'):
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
                                              shade=panel_shade))
            continue
        tcs = []
        for j, c in enumerate(r):
            tcs.append(tc(c, bold=(i == 0), w=colw[j] if j < len(colw) else 1200))
        trs.append('<w:tr>%s</w:tr>' % ''.join(tcs))
    pr = ('<w:tblPr><w:tblW w:w="5000" w:type="pct"/>%s<w:tblLayout w:type="autofit"/>'
          '<w:tblCellMar><w:top w:w="15" w:type="dxa"/><w:left w:w="15" w:type="dxa"/>'
          '<w:bottom w:w="15" w:type="dxa"/><w:right w:w="15" w:type="dxa"/></w:tblCellMar>'
          '</w:tblPr>' % BORD)
    return '<w:tbl>%s<w:tblGrid>%s</w:tblGrid>%s</w:tbl>' % (pr, grid, ''.join(trs))


DOC_OPEN = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<w:body>')
DOC_CLOSE = '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>' \
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" ' \
            'w:header="708" w:footer="708" w:gutter="0"/></w:sectPr></w:body></w:document>'


def write_docx(path, parts):
    """把若干 XML 片段（段落/表格）打包成一个最小可用的 docx。"""
    import zipfile
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.'
          'relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.'
          'openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/docProps/core.xml" ContentType="application/vnd.'
          'openxmlformats-package.core-properties+xml"/>'
          '<Override PartName="/docProps/app.xml" ContentType="application/vnd.'
          'openxmlformats-officedocument.extended-properties+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
            'relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
            'officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/'
            'relationships/metadata/core-properties" Target="docProps/core.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships/extended-properties" Target="docProps/app.xml"/>'
            '</Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
             'relationships"></Relationships>')
    core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
            'metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">'
            '<dc:title>Additional file 1</dc:title></cp:coreProperties>')
    app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
           'extended-properties"/>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
              '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/'
              'main"><w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Times New Roman" '
              'w:hAnsi="Times New Roman" w:eastAsia="Times New Roman"/><w:sz w:val="24"/>'
              '</w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:before="0" w:after="0" '
              'w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
              '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
              '<w:name w:val="Normal"/></w:style></w:styles>')
    doc = DOC_OPEN + ''.join(parts) + DOC_CLOSE
    assert doc.count('\\') == 0, '反斜杠'
    z = zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml', ct)
    z.writestr('_rels/.rels', rels)
    z.writestr('word/document.xml', doc.encode('utf8'))
    z.writestr('word/_rels/document.xml.rels', drels)
    z.writestr('word/styles.xml', styles)
    z.writestr('docProps/core.xml', core)
    z.writestr('docProps/app.xml', app)
    z.close()
    return path


# ---------------------------------------------------------------- Markdown → docx 片段
import re as _re


def _inline(t):
    """去掉 markdown 强调标记（表格/正文内的 ** 与 ` ）。"""
    t = _re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    t = t.replace('`', '')
    return t.strip()


def md_to_parts(md, h1=28, h2=24, h3=22):
    """把简单 Markdown 转成 Word 片段序列（标题 / 段落 / 项目符号 / 管道表）。"""
    parts, lines, i = [], md.split('\n'), 0
    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue
        if ln.strip() in ('---', '***'):
            parts.append(para('', size=8, before=0, after=0))
            i += 1
            continue
        if ln.startswith('|') and i + 1 < len(lines) and set(lines[i + 1].strip()) <= set('|-: '):
            rows, j = [], i
            while j < len(lines) and lines[j].startswith('|'):
                if set(lines[j].strip()) <= set('|-: '):
                    j += 1
                    continue
                rows.append([_inline(c) for c in lines[j].strip().strip('|').split('|')])
                j += 1
            parts.append(table_xml(rows))
            parts.append(para('', size=10, before=0, after=0))
            i = j
            continue
        if ln.startswith('### '):
            parts.append(para(_inline(ln[4:]), bold=True, size=h3, before=200, after=80,
                              keep_next=True))
        elif ln.startswith('## '):
            parts.append(para(_inline(ln[3:]), bold=True, size=h2, before=240, after=100,
                              keep_next=True))
        elif ln.startswith('# '):
            parts.append(para(_inline(ln[2:]), bold=True, size=h1, before=0, after=160))
        elif _re.match(r'^\s*[-\d]+\.\s', ln) or ln.lstrip().startswith('- '):
            parts.append(para('\u2022 ' + _inline(_re.sub(r'^\s*(?:[-\d]+\.)\s*', '', ln)),
                              size=20, before=40, after=40))
        else:
            parts.append(para(_inline(ln), size=20, before=60, after=60))
        i += 1
    return parts
