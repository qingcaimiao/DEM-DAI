# -*- coding: utf-8 -*-
"""P1: 认知条目取值域探针 —— 逐库逐波 min/max/分位/非缺失数。
同时把各库列名全量转储，便于定位 KLoSA 定向题、MHAS 量程等。"""
import re, json, sys
import numpy as np
import pandas as pd

ROOT = 'D:/shujuku/'
FILES = {'CHARLS': 'Charls/charls.csv', 'ELSA': 'Elsa/elsa.csv', 'HRS': 'HRS/hrs.csv',
         'KLoSA': 'KLOSA/klosa.csv', 'LASI': 'LASI/lasi.csv', 'SHARE': 'SHARE/share.csv',
         'MHAS': 'mhas/mhas.csv'}
COGV = re.compile(r'^(r1)?(imrc|dlrc|recall|ser7|bwc20|orient|verbf|cogtot|cog27|word|cog_total|total_cognition)'
                  r'[a-z_0-9]*$', re.I)

allcols = {}
for co, f in FILES.items():
    p = ROOT + f
    h = open(p, encoding='utf8', errors='replace').readline().rstrip('\r\n')
    cols = [c.strip().strip('"') for c in h.split('","')]
    nms = [re.sub(r'\s*\(.*\)$', '', c).strip() for c in cols]
    allcols[co] = dict(zip(nms, cols))
json.dump({k: {n: c for n, c in v.items()} for k, v in allcols.items()},
          open('out/_columns.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)

print('#' * 90)
print('# 各库全部列名中含 orient / word / memor / 认知 的条目')
for co, m in allcols.items():
    hits = [(n, c) for n, c in m.items() if re.search(r'orient|word|memor|cognit|recall|fluen|verbf|ser7|calc|count|题', c, re.I)]
    print('== %s (%d 命中)' % (co, len(hits)))
    for n, c in hits[:40]:
        print('   %-22s %s' % (n, c[:70]))
print()

for co, f in FILES.items():
    p = ROOT + f
    m = allcols[co]
    want = ['wave'] + [n for n in m if COGV.match(n)]
    want = list(dict.fromkeys(want))
    h = open(p, encoding='utf8', errors='replace').readline().rstrip('\r\n')
    cols = [c.strip().strip('"') for c in h.split('","')]
    nms = [re.sub(r'\s*\(.*\)$', '', c).strip() for c in cols]
    idx, nam = [], []
    for i, n in enumerate(nms):
        if n in want:
            idx.append(i); nam.append(n)
    df = pd.read_csv(p, usecols=idx, dtype=str, low_memory=False,
                     encoding='utf-8', encoding_errors='replace')
    df.columns = nam
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    if 'wave' not in df.columns:
        df['wave'] = 1
    print('=' * 90)
    print('== %s ==' % co)
    for w in sorted(pd.unique(df['wave'].dropna())):
        s = df[df['wave'] == w]
        if len(s) < 30:
            continue
        parts = []
        for c in nam:
            if c == 'wave':
                continue
            v = s[c].dropna()
            if len(v) < 50:
                continue
            parts.append('%s[%d] %g-%g %s' % (c, len(v), v.min(), v.max(),
                          np.round(v.quantile([.25, .5, .75]).values, 1)))
        if parts:
            print('  w=%-3s n=%-6d' % (w, len(s)))
            for x in parts:
                print('      ', x)
