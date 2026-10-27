# -*- coding: utf-8 -*-
"""j47b_refs_titlecheck.py —— 无 DOI 条目的标题级核验

对无 DOI 的参考文献，用 Crossref 的 bibliographic 检索取最佳匹配，
再检查「返回标题的长词是否出现在稿件文献串中」+ 年份，以发现错引/虚构。
"""
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

sys.stdout.reconfigure(encoding='utf-8')
MS = r'D:/桌面/AIzuopin/痴呆/投稿包_BMC_Geriatrics_20261017/Manuscript_BMC_Geriatrics_20261017.docx'
UA = {'User-Agent': 'DEM-DAI/1.0 (mailto:15511075821@163.com)'}

x = zipfile.ZipFile(MS).read('word/document.xml').decode('utf8')
body = x.split('<w:body>')[1].split('</w:body>')[0]
P = re.compile(r'<w:p\b[^>]*>.*?</w:p>', re.S)
TXT = re.compile(r'<w:t[^>]*>([^<]*)</w:t>')
ps = [html.unescape(''.join(TXT.findall(m.group(0)))) for m in P.finditer(body)]
ri, fi = ps.index('References'), ps.index('Figure legends')
refs = [p.strip() for p in ps[ri + 1:fi] if p.strip()]


def longwords(s):
    return {w for w in re.findall(r'[a-z]{5,}', (s or '').lower())
            if w not in {'study', 'cohort', 'among', 'using', 'their', 'these', 'which',
                         'prospective', 'longitudinal', 'analysis', 'findings', 'evidence'}}


ok_n, bad, svc = 0, [], []
for i, r in enumerate(refs, 1):
    if re.search(r'(10\.\d{4,9}/[^\s,;)\]]+)', r):
        continue                       # 有 DOI 的上一脚本已核
    q = urllib.parse.urlencode({'query.bibliographic': r, 'rows': '1',
                                'select': 'title,issued,DOI,container-title'})
    try:
        u = 'https://api.crossref.org/works?' + q
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as f:
            items = json.load(f)['message']['items']
    except Exception as e:
        svc.append((i, str(e)[:50]))
        continue
    if not items:
        bad.append((i, 'Crossref 无匹配', r[:100]))
        continue
    it = items[0]
    t = (it.get('title') or [''])[0]
    tw = longwords(t)
    rw = longwords(r)
    cover = (len(tw & rw) / len(tw)) if tw else 0
    ry = re.search(r'(19|20)\d{2}', r)
    cy = None
    if it.get('issued', {}).get('date-parts'):
        cy = it['issued']['date-parts'][0][0]
    if cover >= 0.7 and (not ry or not cy or abs(int(ry.group(0)) - cy) <= 1):
        ok_n += 1
    else:
        bad.append((i, '词覆盖 %.2f ｜ 年份 稿件%s vs Crossref%s ｜ DOI=%s'
                    % (cover, ry.group(0) if ry else '?', cy, it.get('DOI')),
                    'MS=%s || T=%s' % (r[:85], t[:85])))
    time.sleep(0.2)

print('无 DOI 条目核验完成')
print('  通过: %d ｜ 需人工确认: %d ｜ 服务不可用: %d' % (ok_n, len(bad), len(svc)))
if bad:
    print('\n★ 需人工确认：')
    for i, why, ctx in bad:
        print('  [%d] %s' % (i, why))
        print('      %s' % ctx)
if svc:
    print('\n★ 服务不可用（不判为有误）：')
    for i, why in svc:
        print('  [%d] %s' % (i, why))
