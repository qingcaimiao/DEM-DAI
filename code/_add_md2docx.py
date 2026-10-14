# -*- coding: utf-8 -*-
import io
p = 'docxtbl.py'
s = io.open(p, encoding='utf8').read()
if 'def md_to_parts' not in s:
    s += '''

# ---------------------------------------------------------------- Markdown → docx 片段
import re as _re


def _inline(t):
    """去掉 markdown 强调标记（表格/正文内的 ** 与 ` ）。"""
    t = _re.sub(r'\\*\\*(.+?)\\*\\*', r'\\1', t)
    t = t.replace('`', '')
    return t.strip()


def md_to_parts(md, h1=28, h2=24, h3=22):
    """把简单 Markdown 转成 Word 片段序列（标题 / 段落 / 项目符号 / 管道表）。"""
    parts, lines, i = [], md.split('\\n'), 0
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
        elif _re.match(r'^\\s*[-\\d]+\\.\\s', ln) or ln.lstrip().startswith('- '):
            parts.append(para('\\u2022 ' + _inline(_re.sub(r'^\\s*(?:[-\\d]+\\.)\\s*', '', ln)),
                              size=20, before=40, after=40))
        else:
            parts.append(para(_inline(ln), size=20, before=60, after=60))
        i += 1
    return parts
'''
    io.open(p, 'w', encoding='utf8').write(s)
    print('docxtbl.py：已加 md_to_parts()')
else:
    print('已存在，跳过')
