# -*- coding: utf-8 -*-
"""j47_refs_verify.py —— 逐条双源核验参考文献（Crossref 为准，区分"查不到"与"服务不可用"）

对每条：抽 DOI → Crossref 取回 metadata → 比对标题相似度与年份。
无 DOI 的条目单独列出，需人工核。
"""
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding='utf-8')
MS = r'D:/桌面/AIzuopin/痴呆/投稿包_BMC_Geriatrics_20261017/Manuscript_BMC_Geriatrics_20261017.docx'
UA = {'User-Agent': 'DEM-DAI/1.0 (mailto:15511075821@163.com)'}

x = zipfile.ZipFile(MS).read('word/document.xml').decode('utf8')
body = x.split('<w:body>')[1].split('</w:body>')[0]
P = re.compile(r'<w:p\b[^>]*>.*?</w:p>', re.S)
TXT = re.compile(r'<w:t[^>]*>([^<]*)</w:t>')
ps = [html.unescape(''.join(TXT.findall(m.group(0)))) for m in P.finditer(body)]
ri = ps.index('References')
fi = ps.index('Figure legends')
refs = [p.strip() for p in ps[ri + 1:fi] if p.strip()]
print('参考文献 %d 条\n' % len(refs))


def norm(s):
    return re.sub(r'[^a-z0-9 ]', ' ', (s or '').lower()).split()


def sim(a, b):
    return SequenceMatcher(None, ' '.join(norm(a)), ' '.join(norm(b))).ratio()


bad, nodoi, svc = [], [], []
for i, r in enumerate(refs, 1):
    m = re.search(r'(10\.\d{4,9}/[^\s,;)\]]+)', r)
    if not m:
        nodoi.append((i, r[:110]))
        continue
    doi = m.group(1).rstrip('.').rstrip(')')
    try:
        u = 'https://api.crossref.org/works/' + urllib.parse.quote(doi)
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40) as f:
            d = json.load(f)['message']
    except urllib.error.HTTPError as e:
        if e.code == 404:
            bad.append((i, doi, 'DOI 在 Crossref 不存在（404）', r[:90]))
        else:
            svc.append((i, doi, 'HTTP %d' % e.code))
        continue
    except Exception as e:
        svc.append((i, doi, str(e)[:60]))
        continue
    t_true = (d.get('title') or [''])[0]
    yr = None
    for k in ('published-print', 'published-online', 'issued'):
        if d.get(k, {}).get('date-parts'):
            yr = d[k]['date-parts'][0][0]
            break
    s = sim(t_true, r)
    refyr = re.search(r'\.?\s(19|20)\d{2}[;:]', r)
    ry = int(refyr.group(0).strip(' .;:')) if refyr else None
    flag = []
    if s < 0.72:
        flag.append('标题相似度 %.2f' % s)
    if ry and yr and abs(ry - yr) > 1:
        flag.append('年份 稿件%d vs Crossref%d' % (ry, yr))
    if flag:
        bad.append((i, doi, '; '.join(flag), 'TRUETITLE=%s || MS=%s' % (t_true[:80], r[:70])))
    time.sleep(0.15)

print('=== 有 DOI 的条目核验结果 ===')
print('  通过: %d ｜ 有问题: %d ｜ 无 DOI: %d ｜ 服务不可用: %d'
      % (len(refs) - len(bad) - len(nodoi) - len(svc), len(bad), len(nodoi), len(svc)))
if bad:
    print('\n★ 需人工确认：')
    for i, doi, why, ctx in bad:
        print('  [%d] %s  ← %s' % (i, doi, why))
        print('      %s' % ctx)
if svc:
    print('\n★ 服务不可用（不能判为文献有误）：')
    for i, doi, why in svc:
        print('  [%d] %s  %s' % (i, doi, why))
if nodoi:
    print('\n★ 无 DOI（需人工核）：')
    for i, t in nodoi:
        print('  [%d] %s' % (i, t))
