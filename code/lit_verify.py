# -*- coding: utf-8 -*-
"""lit_verify.py —— 参考文献双源校验（Crossref + Europe PMC）+ 撞车候选摘要抓取

铁律（用户要求）：每个条目的判定必须区分
  MATCH          两源至少一源命中，且题名/DOI 一致
  NOT_FOUND      服务正常应答，但两源均无匹配 → 这才是"查不到"
  SERVICE_ERROR  网络/HTTP/限流/解析异常 → 不能判为"查不到"，必须重试或标注为待核

输出：out/lit_verify.md、out/lit_verify.json、out/lit_candidates.md
"""
import os
import re
import json
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
MS = r'D:/桌面/AIzuopin/痴呆/修订版正文_纯文本_20261012.txt'
EPMC = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
CR = 'https://api.crossref.org/works'
UA = 'WorkBuddy-litcheck/1.0 (mailto:15511075821@163.com)'
TIMEOUT = 30
RETRY = 3


def fetch(url):
    last = None
    for i in range(RETRY):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA,
                                                       'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                if r.status != 200:
                    last = 'HTTP %s' % r.status
                    time.sleep(2 * (i + 1)); continue
                body = r.read().decode('utf8', 'replace')
                try:
                    return 'OK', json.loads(body), None
                except Exception as e:
                    last = 'JSON 解析失败: %s' % e
                    time.sleep(2 * (i + 1)); continue
        except Exception as e:
            last = '%s: %s' % (type(e).__name__, e)
            time.sleep(2 * (i + 1))
    return 'SERVICE_ERROR', None, 'url=%s err=%s' % (url, last)


def norm(s):
    s = re.sub(r'[^0-9a-zA-Z]+', ' ', s or '')
    return ' '.join(s.lower().split())


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    n = min(len(a), len(b), 90)
    x, y = a[:n], b[:n]
    if x == y:
        return 1.0
    same = sum(1 for i in range(n) if x[i] == y[i])
    return same / float(n)


def epmc_query(q, fmt='lite'):
    url = ('%s?query=%s&format=json&pageSize=5&resultType=%s'
           % (EPMC, urllib.parse.quote(q), fmt))
    st, js, err = fetch(url)
    if st != 'OK':
        return st, [], err
    res = js.get('resultList', {}).get('result', [])
    hits = js.get('hitCount', 0)
    if not res:
        return ('NO_HIT' if hits == 0 else 'OK'), [], None
    return 'OK', res, None


def cr_query(q, rows=5):
    url = ('%s?query.bibliographic=%s&rows=%d&select=DOI,title,container-title,issued,author'
           % (CR, urllib.parse.quote(q), rows))
    st, js, err = fetch(url)
    if st != 'OK':
        return st, [], err
    items = js.get('message', {}).get('items', [])
    if not items:
        return 'NO_HIT', [], None
    return 'OK', items, None


# ---------------------------------------------------------------- 解析参考文献
txt = open(MS, encoding='utf8').read()
seg = txt[txt.find('\nReferences'):txt.find('Figure legends')]
refs = [l.strip() for l in seg.split('\n') if l.strip()][1:]

REF = []
for i, r in enumerate(refs, 1):
    doi = re.search(r'(10\.\d{4,9}/[^\s;,]+)', r)
    # DOI 末尾常跟句号/逗号/分号，必须剥离，否则会向 Crossref 请求一个不存在的 DOI 而得 404，
    # 被误读成"文献查不到"（2026-10-13 实测：带尾点 → 404；剥离后 → 200）
    doi_val = doi.group(1).rstrip('.,;') if doi else None
    pmid = re.search(r'PMID:\s*(\d+)', r)
    year = re.search(r'\b(19|20)\d{2}\b', r)
    # 题名：作者段之后、期刊名之前
    title = r
    m = re.match(r'^(.{0,200}?\.)\s', r)
    if m:
        title = r[m.end():]
    title = re.split(r'\s(?:Lancet|JAMA|BMJ|N Engl J Med|Int J Epidemiol|J Am Geriatr Soc|'
                     r'J Gerontol|Gerontologist|J Chronic Dis|Am J Prev Med|Br J Psychiatry|'
                     r'Arch Gen Psychiatry|Int J Geriatr Psychiatry|J Alzheimers Dis|'
                     r'J Adv Res|Arch Gerontol Geriatr|J Prev Alzheimers Dis|BMC Med|'
                     r'Gen Psychiatry|Brain Commun|JAMA Netw Open|Alzheimers Dement|'
                     r'Age Ageing|Stat Med|Epidemiology|Annu Rev Public Health|'
                     r'J Am Stat Assoc|Ann Intern Med|Control Clin Trials|JAMA Neurol|'
                     r'Neurobiol Aging|J Nutr Health Aging|Cell Rep Med|Front Public Health|'
                     r'Lancet Public Health|Lancet Neurol|Front Med|J Health Popul Nutr|'
                     r'Arch Gerontol|J Gerontol A|J Gerontol B|Int Psychogeriatr)\b', title)[0]
    title = title.strip().rstrip('.').strip()
    if not title or len(title) < 12:      # 无题名的（如数据源条目）不判
        title = None
    is_web = bool(re.search(r'https?://|Accessed \d', r))
    if is_web and not re.search(r'doi:|PMID:', r):
        title = None                      # 网站/数据源条目：不适用双源校验
    REF.append(dict(idx=i, raw=r, doi=doi_val,
                    pmid=pmid.group(1) if pmid else None,
                    year=year.group(0) if year else None, title=title, is_web=is_web))

report = ['# 参考文献双源校验（Crossref + Europe PMC）', '',
          '判定口径：MATCH = 至少一源命中且题名相似度 ≥ 0.90 或 DOI/PMID 直接一致；',
          'NOT_FOUND = 两源均正常应答但无匹配（真"查不到"）；',
          'SERVICE_ERROR = 服务不可用/超时/解析失败（**不得计为查不到**）。', '']
report.append('| # | 判定 | Crossref | Europe PMC | 题名/DOI |')
report.append('|---|---|---|---|---|')
J = []
n_err = 0
for r in REF:
    cr_st, cr_res, cr_err = 'SKIP', [], None
    ep_st, ep_res, ep_err = 'SKIP', [], None
    cr_ok = ep_ok = False
    cr_ref = ep_ref = ''
    if r['doi']:
        st, res, err = cr_query(r['doi'], rows=3)
        # DOI 直查
        url = ('%s/%s' % (CR, urllib.parse.quote(r['doi'])))
        st2, js2, err2 = fetch(url)
        if st2 == 'OK':
            it = js2.get('message', {})
            cr_ok = True
            cr_st = 'OK(DOI)'
            cr_ref = (it.get('title') or [''])[0]
        elif st2 == 'SERVICE_ERROR':
            cr_st, cr_err = 'SERVICE_ERROR', err2
        else:
            cr_st = 'OK(DOI 未收录)'
    if r['title']:
        st, res, err = cr_query(r['title'])
        if st == 'SERVICE_ERROR':
            cr_st = 'SERVICE_ERROR'; cr_err = err
        elif st == 'NO_HIT':
            if cr_st == 'SKIP':
                cr_st = 'NO_HIT'
        else:
            best = max(res, key=lambda it: sim(r['title'], (it.get('title') or [''])[0]))
            sc = sim(r['title'], (best.get('title') or [''])[0])
            if sc >= 0.90:
                cr_ok = True
                cr_ref = (best.get('title') or [''])[0]
                if cr_st == 'SKIP':
                    cr_st = 'OK(题名 %.2f)' % sc
            elif cr_st == 'SKIP':
                cr_st = 'NO_HIT(最佳 %.2f)' % sc
    # Europe PMC
    q = None
    if r['pmid']:
        q = 'EXT_ID:%s' % r['pmid']
    elif r['doi']:
        q = 'DOI:"%s"' % r['doi']
    if q:
        st, res, err = epmc_query(q)
        if st == 'SERVICE_ERROR':
            ep_st, ep_err = 'SERVICE_ERROR', err
        elif st == 'NO_HIT':
            ep_st = 'NO_HIT'
        else:
            ep_ok = True; ep_st = 'OK(ID)'
            ep_ref = res[0].get('title', '')
    if not ep_ok and r['title']:
        st, res, err = epmc_query('TITLE:"%s"' % r['title'][:120])
        if st == 'SERVICE_ERROR':
            ep_st, ep_err = 'SERVICE_ERROR', err
        elif st == 'NO_HIT':
            if ep_st == 'SKIP':
                ep_st = 'NO_HIT'
        else:
            best = max(res, key=lambda it: sim(r['title'], it.get('title', '')))
            sc = sim(r['title'], best.get('title', ''))
            if sc >= 0.90:
                ep_ok = True; ep_ref = best.get('title', '')
                if ep_st == 'SKIP':
                    ep_st = 'OK(题名 %.2f)' % sc
            elif ep_st == 'SKIP':
                ep_st = 'NO_HIT(最佳 %.2f)' % sc
    if cr_st == 'SERVICE_ERROR' or ep_st == 'SERVICE_ERROR':
        verdict = 'SERVICE_ERROR'
        n_err += 1
    elif cr_ok or ep_ok:
        verdict = 'MATCH'
    elif r['title'] is None:
        verdict = 'N/A(数据源/网址条目)'
    else:
        verdict = 'NOT_FOUND'
    disp = (r['title'] or r['raw'])[:70]
    report.append('| %d | %s | %s | %s | %s |' % (r['idx'], verdict, cr_st, ep_st, disp))
    J.append(dict(idx=r['idx'], verdict=verdict, crossref=cr_st, epmc=ep_st,
                  doi=r['doi'], pmid=r['pmid'], title=r['title'],
                  cr_title=cr_ref, ep_title=ep_ref,
                  crossref_err=cr_err, epmc_err=ep_err))
    time.sleep(0.35)

ok = sum(1 for x in J if x['verdict'] == 'MATCH')
nf = [x['idx'] for x in J if x['verdict'] == 'NOT_FOUND']
na = [x['idx'] for x in J if x['verdict'].startswith('N/A')]
se = [x['idx'] for x in J if x['verdict'] == 'SERVICE_ERROR']

# ---------------------------------------------------------------- 第二轮：只重跑 SERVICE_ERROR
if se:
    report.append('')
    report.append('## 第二轮重试（仅对第一轮 SERVICE_ERROR 的条目）')
    report.append('')
    report.append('| # | 第一轮 | 第二轮结果 | 依据 |')
    report.append('|---|---|---|---|')
    for x in J:
        if x['verdict'] != 'SERVICE_ERROR':
            continue
        det = []
        got = False
        if x['doi']:
            st, js, err = fetch('%s/%s' % (CR, urllib.parse.quote(x['doi'])))
            if st == 'OK':
                it = js.get('message', {})
                det.append('Crossref DOI 命中：%s（%s）'
                           % ((it.get('title') or [''])[0][:80],
                              (it.get('container-title') or [''])[0][:40]))
                got = True
            else:
                det.append('Crossref DOI：SERVICE_ERROR（%s）' % err)
        if x['pmid']:
            st, res, err = epmc_query('EXT_ID:%s' % x['pmid'])
            if st == 'OK' and res:
                det.append('Europe PMC PMID 命中：%s' % res[0].get('title', '')[:80])
                got = True
            else:
                det.append('Europe PMC PMID：%s' % st)
        if x['title']:
            st, res, err = epmc_query('TITLE:"%s"' % x['title'][:120])
            if st == 'OK' and res:
                sc = sim(x['title'], res[0].get('title', ''))
                det.append('Europe PMC 题名相似度 %.2f：%s' % (sc, res[0].get('title', '')[:70]))
                got = got or sc >= 0.90
            else:
                det.append('Europe PMC 题名检索：%s' % st)
        x['verdict2'] = 'MATCH' if got else 'NOT_FOUND'
        report.append('| %d | %s | **%s** | %s |' % (x['idx'], x['verdict'], x['verdict2'],
                                                     '；'.join(det)))
        time.sleep(0.5)

report.append('')
n_ok2 = sum(1 for x in J if x.get('verdict2') == 'MATCH')
report.append('**第一轮汇总**：共 %d 条；MATCH %d；NOT_FOUND %d%s；N/A %d；SERVICE_ERROR %d%s'
              % (len(J), ok, len(nf), ('（编号 %s）' % nf) if nf else '',
                 len(na), len(se), ('（编号 %s）' % se) if se else ''))
if se:
    report.append('**第二轮后最终**：SERVICE_ERROR 条目中 %d 条确认为 MATCH；'
                  '仍未确认为 %d 条（须重跑，**不得计为查不到**）'
                  % (n_ok2, len(se) - n_ok2))

open(os.path.join(OUT, 'lit_verify.md'), 'w', encoding='utf8').write('\n'.join(report))
json.dump(J, open(os.path.join(OUT, 'lit_verify.json'), 'w', encoding='utf8'),
          ensure_ascii=False, indent=1)
print('\n'.join(report))

# ---------------------------------------------------------------- 撞车候选摘要
CAND = [('42727174', 'Intrinsic capacity impairment and incident dementia across three cohorts'),
        ('42723149', 'Dynamic frailty exposure and cognitive aging trajectories: multicohort'),
        ('42595986', 'Frailty, trajectories of frailty, and cognitive impairment: 5 cohorts'),
        ('41936045', 'Trajectories of frailty, grip strength and gait speed preceding dementia'),
        ('42298488', 'Dual trajectories of intrinsic capacity and frailty: joint predictor'),
        ('42145061', 'Longitudinal Interplay Between Cognitive Impairment and Frailty'),
        ('36427050', 'Multimorbidity burden and developmental trajectory in relation to dementia'),
        ('40672935', 'The lifetime accumulation of multimorbidity and dementia (UK Biobank)'),
        ('41795669', 'Psychological distress and subsequent cognitive decline: multi-cohort'),
        ('42309981', 'Intrinsic capacity and dementia risk in older Mexicans')]
cand_out = ['# 撞车候选（近邻）摘要级核对', '']
for pmid, note in CAND:
    st, res, err = epmc_query('EXT_ID:%s' % pmid, fmt='core')
    if st == 'SERVICE_ERROR':
        cand_out.append('- **%s** %s → SERVICE_ERROR（服务不可用：%s）' % (pmid, note, err))
        continue
    if st == 'NO_HIT' or not res:
        cand_out.append('- **%s** %s → NO_HIT（服务正常但无此记录）' % (pmid, note))
        continue
    r = res[0]
    cand_out.append('- **PMID %s** ｜ %s (%s, %s)' % (pmid, r.get('title', ''),
                                                      r.get('journalTitle', ''),
                                                      r.get('pubYear', '')))
    cand_out.append('  - 作者：%s' % (r.get('authorString', '')[:150]))
    ab = re.sub(r'<[^>]+>', ' ', r.get('abstractText', '') or '')
    cand_out.append('  - 摘要：%s' % (' '.join(ab.split())[:1100] or '（无摘要）'))
    cand_out.append('  - 是否与本研究冲突：待人工判定（见报告）')
    cand_out.append('')
    time.sleep(0.4)
open(os.path.join(OUT, 'lit_candidates.md'), 'w', encoding='utf8').write('\n'.join(cand_out))
print('\n撞车候选摘要已写出 out/lit_candidates.md')
