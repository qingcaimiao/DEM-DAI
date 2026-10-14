# -*- coding: utf-8 -*-
"""p26_audit_docx_numbers.py —— 终稿（含表格）数字溯源审计

逐表检查 docx 中每个数值 token 是否能在「本脚本从 out/*.csv 汇总的数值集合」中找到，
或落入白名单（年份、百分比符号、量表量程、分类编号、参考值 1.00 等）。
输出：out/_audit_tables.txt、out/_audit_tables_unmatched.csv
"""
import os
import re
import csv
import sys
import numpy as np
import pandas as pd
import docx

OUT = r'D:/workbuddygongzuokongjian/2026-10-12-21-32-15/dem_pipeline/out'
DOCX = os.environ.get('DEM_DOCX', r'D:/桌面/AIzuopin/痴呆/稿件正文_修订稿_v4_20261013.docx')

# ---------------------------------------------------------------- 数值集合
vals = set()
for fn in os.listdir(OUT):
    if not fn.lower().endswith('.csv'):
        continue
    try:
        df = pd.read_csv(os.path.join(OUT, fn))
    except Exception:
        continue
    for c in df.columns:
        col = pd.to_numeric(df[c], errors='coerce').dropna()
        for x in col.astype(float).tolist():
            if not np.isfinite(x):
                continue
            for d in range(0, 5):
                vals.add(('%.' + str(d) + 'f') % x)
            if abs(x - round(x)) < 1e-9 and abs(x) < 1e7:
                vals.add(format(int(round(x)), ','))
                vals.add(str(int(round(x))))
                vals.add('%.1f' % (100 * x) if abs(x) <= 1 else '%.1f' % x)
            vals.add(format(x, ',.0f'))
            vals.add(format(x, ',.1f'))
            vals.add(format(x, ',.2f'))
# 由数值现算派生量（HR×exp(±1.96 se) 之类）——把常见派生式也登记
for fn, cols in [('_m1234.csv', ('hr', 'se')), ('Table2B.csv', ('hr', 'se')),
                 ('Table3A.csv', ('hr', 'se')), ('Table3B.csv', ('hr', 'se')),
                 ('Table3C.csv', ('hr', 'se')), ('_tv.csv', ('hr', 'se')),
                 ('_traj.csv', ('hr', 'se'))]:
    p = os.path.join(OUT, fn)
    if not os.path.exists(p):
        continue
    df = pd.read_csv(p)
    for _, r in df.iterrows():
        try:
            hr, se = float(r['hr']), float(r['se'])
        except Exception:
            continue
        for v in (hr, hr * np.exp(-1.96 * se), hr * np.exp(1.96 * se)):
            vals.add('%.2f' % v)
            vals.add('%.1f' % v)

WHITE = set()
for y in range(1990, 2031):
    WHITE.add(str(y))
for a in range(0, 12):
    for b in range(0, 12):
        WHITE.add('%d\u2013%d' % (a, b))
WHITE |= {'1.00', '0.00', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '12', '14',
          '16', '18', '20', '24', '25', '30', '50', '60', '65', '74', '75', '29.9', '0.001',
          '0.05', '0.01', '0.5', '95', '105', '1,000', '20 26'}
TOK = re.compile(r'\d[\d,\.]*')


def toks(s):
    out = []
    for m in TOK.finditer(s):
        t = m.group(0).rstrip('.,')
        if t:
            out.append(t)
    return out


d = docx.Document(DOCX)
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
blocks = list(d.element.body.iterchildren())
ti = 0
rep = []
bad = []
for blk in blocks:
    if blk.tag.split('}')[-1] != 'tbl':
        continue
    ti += 1
    rows = blk.findall('.//' + W + 'tr')
    caps = []
    texts = []
    for r in rows:
        for c in r.findall('.//' + W + 'tc'):
            t = ''.join(n.text or '' for n in c.iter() if n.tag.endswith('}t'))
            texts.append(t)
    n_tok = 0
    un = []
    for t in texts:
        for x in toks(t):
            n_tok += 1
            if x in vals or x in WHITE or x.replace(',', '') in vals:
                continue
            un.append((x, t[:70]))
    rep.append('表 %d：单元格文本块 %d，数值 token %d，未匹配 %d' % (ti, len(texts), n_tok, len(un)))
    for x, c in un:
        rep.append('    UNMATCHED %-12s | %s' % (x, c))
        bad.append((ti, x, c))

# ---------------------------------------------------------------- 表注逐句复核
# 用户要求：每次改表后必须重新逐句复核表注；表注里的数值同样必须脚本可算。
note_rep = []
note_bad = []
W2 = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
for i, blk in enumerate(blocks):
    tag = blk.tag.split('}')[-1]
    if tag != 'p':
        continue
    t = ''.join(nn.text or '' for nn in blk.iter() if nn.tag.endswith('}t'))
    if not t.startswith('Note.'):
        continue
    sent = [x.strip() for x in re.split(r'(?<=[.;])\s+', t) if x.strip()]
    note_rep.append('表注（第 %d 个文档块）共 %d 句' % (i, len(sent)))
    for s_ in sent:
        miss = [x for x in toks(s_) if not (x in vals or x in WHITE or x.replace(',', '') in vals)]
        note_rep.append('    %s | %s' % ('OK ' if not miss else 'MISS %s' % miss, s_[:150]))
        for x in miss:
            note_bad.append((i, x, s_[:120]))
open(os.path.join(OUT, '_audit_tables_notes.txt'), 'w', encoding='utf8').write('\n'.join(note_rep))
print('\n'.join(note_rep))
print('\n表注未匹配数值：%d' % len(note_bad))
bad.extend(note_bad)

open(os.path.join(OUT, '_audit_tables.txt'), 'w', encoding='utf8').write('\n'.join(rep))
with open(os.path.join(OUT, '_audit_tables_unmatched.csv'), 'w', encoding='utf-8-sig',
          newline='') as f:
    w = csv.writer(f)
    w.writerow(['table', 'token', 'context'])
    w.writerows(bad)
print('\n'.join(rep))
print('\n未匹配合计：%d' % len(bad))
sys.exit(1 if bad else 0)
