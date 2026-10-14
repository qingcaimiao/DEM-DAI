# -*- coding: utf-8 -*-
"""nov_search.py —— 三轨查新（概念级全字段 / 摘要级 / 标题级）

轨 1 Concept（全字段，Europe PMC 默认检索覆盖题名+摘要+全文+关键词）
轨 2 Abstract（ABSTRACT: 限定）
轨 3 Title（TITLE: 限定）
另加：Crossref 文献计量检索（补充非 PubMed 收录），以及中文库检索式（供人工在 CNKI/万方执行）

错误处理铁律（用户明确要求）：必须区分
  - NO_HIT       服务正常返回，但 0 命中  → 结论：该处未检索到
  - SERVICE_ERROR 网络/HTTP/解析异常      → 结论：无法判定，需重试，不得当作"没有"
输出：out/nov_search.json、out/nov_search.md
"""
import os
import json
import time
import urllib.parse
import urllib.request

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
EPMC = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
CR = 'https://api.crossref.org/works'
UA = 'WorkBuddy-novelty-check/1.0 (mailto:15511075821@163.com)'
TIMEOUT = 30
RETRY = 3


def fetch(url, what):
    """返回 (status, payload)。status ∈ {'OK','NO_HIT','SERVICE_ERROR'}"""
    last = None
    for i in range(RETRY):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA,
                                                       'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                if r.status != 200:
                    last = 'HTTP %s' % r.status
                    time.sleep(2 * (i + 1))
                    continue
                body = r.read().decode('utf8', 'replace')
                try:
                    return 'OK', json.loads(body)
                except Exception as e:
                    last = 'JSON 解析失败: %s' % e
                    time.sleep(2 * (i + 1))
                    continue
        except Exception as e:
            last = '%s: %s' % (type(e).__name__, e)
            time.sleep(2 * (i + 1))
    return 'SERVICE_ERROR', {'error': last, 'url': url, 'what': what}


def epmc(query, pagesize=100, sort=None):
    url = ('%s?query=%s&format=json&pageSize=%d&resultType=lite'
           % (EPMC, urllib.parse.quote(query), pagesize))
    if sort:
        url += '&sort=' + urllib.parse.quote(sort)
    st, js = fetch(url, query)
    if st != 'OK':
        return st, [], js.get('error')
    res = js.get('resultList', {}).get('result', [])
    hits = js.get('hitCount', 0)
    if hits == 0 or not res:
        return 'NO_HIT', [], None
    return 'OK', [dict(title=r.get('title', ''), journal=r.get('journalTitle', ''),
                       year=r.get('pubYear', ''), pmid=r.get('pmid', ''),
                       doi=r.get('doi', ''), cited=r.get('citedByCount', 0),
                       authors=r.get('authorString', '')[:120]) for r in res], hits


def crossref(query, rows=50):
    url = ('%s?query.bibliographic=%s&rows=%d&select=DOI,title,container-title,issued,'
           'is-referenced-by-count' % (CR, urllib.parse.quote(query), rows))
    st, js = fetch(url, query)
    if st != 'OK':
        return st, [], js.get('error')
    items = js.get('message', {}).get('items', [])
    if not items:
        return 'NO_HIT', [], 0
    out = []
    for it in items:
        t = (it.get('title') or [''])[0]
        j = (it.get('container-title') or [''])[0]
        yr = ''
        try:
            yr = str(it['issued']['date-parts'][0][0])
        except Exception:
            pass
        out.append(dict(title=t, journal=j, year=yr, doi=it.get('DOI', ''),
                        cited=it.get('is-referenced-by-count', 0), pmid='', authors=''))
    return 'OK', out, js.get('message', {}).get('total-results', 0)


# ---------------------------------------------------------------- 概念集合
# 每个概念对应本研究的一项具体贡献；用"相关性排序 + 近年窗口"来找直接撞车
YEAR = '(FIRST_PDATE:[2018-01-01 TO 2026-12-31])'
CONCEPTS = {
    'S1_three_syndrome_count': '(("geriatric syndrome" OR "geriatric syndromes") AND '
                               '("accumulation" OR "count" OR "burden") AND dementia AND '
                               '(cohort OR longitudinal)) AND ' + YEAR,
    'S2_dai_joint': '((disability OR "functional limitation") AND multimorbidity AND depression '
                    'AND dementia AND (joint OR combined OR "mutually exclusive" OR '
                    '"all eight" OR co-occurrence) AND cohort) AND ' + YEAR,
    'S3_harmonized_multi': '((CHARLS OR ELSA OR "Health and Retirement Study" OR HRS OR KLoSA OR '
                           'MHAS OR SHARE OR "Gateway to Global Aging") AND dementia AND '
                           '(frailty OR multimorbidity OR "geriatric syndrome" OR burden) AND '
                           '(harmonized OR "cross-cohort" OR "multi-cohort")) AND ' + YEAR,
    'S4_time_lagged': '(dementia AND (frailty OR multimorbidity OR disability OR "geriatric '
                      'syndrome") AND ("time-lagged" OR "lagged" OR "reverse causation" OR '
                      '"reverse causality" OR "latency" OR "time-varying") AND cohort) AND ' + YEAR,
    'S5_mediation_dep': '(dementia AND depression AND (mediation OR "mediated proportion" OR '
                        '"indirect effect" OR "four-way decomposition") AND (frailty OR '
                        'multimorbidity OR disability)) AND ' + YEAR,
    'S6_trajectory': '(dementia AND (frailty OR multimorbidity OR "geriatric syndrome") AND '
                     '(trajectory OR trajectories) AND (remitted OR reversal OR "persistently" OR '
                     '"changes in")) AND ' + YEAR,
    'S7_asia_latam': '(dementia AND (China OR Chinese OR Mexico OR Mexican OR Korea OR Korean) '
                     'AND (frailty OR multimorbidity OR disability) AND (cohort OR longitudinal '
                     'OR "nationally representative")) AND ' + YEAR,
    'S8_minimal_index_practical': '(dementia AND (frailty OR multimorbidity OR disability) AND '
                                  '(screening OR "risk stratification" OR "primary care" OR '
                                  '"routine assessment") AND "older adults") AND ' + YEAR,
}

# 标题级必须用短检索式，否则标题里不可能同时出现全部概念词（会假性 0 命中）
TITLE_QUERIES = {
    'T1_geriatric_syndrome_dementia': 'TITLE:("geriatric syndrome" OR "geriatric syndromes") '
                                      'AND TITLE:dementia',
    'T2_frailty_multi_dep_dementia': 'TITLE:(frailty AND multimorbidity AND depression) AND '
                                     'TITLE:dementia',
    'T3_disability_dep_dementia': 'TITLE:(disability AND depression AND dementia)',
    'T4_accumulation_index': 'TITLE:(frailty OR multimorbidity OR disability) AND '
                             'TITLE:(accumulation OR burden OR count) AND TITLE:dementia',
    'T5_harmonized_cohorts_dementia': 'TITLE:(harmonized OR multicohort OR "multi-cohort" OR '
                                      '"pooled analysis") AND TITLE:dementia AND TITLE:'
                                      '(cohort OR cohorts)',
    'T6_trajectory_dementia': 'TITLE:(frailty OR multimorbidity OR "geriatric syndrome") AND '
                              'TITLE:(trajectory OR trajectories) AND TITLE:(dementia OR cognitive)',
    'T7_mediation_depression_dementia': 'TITLE:(mediation OR mediator OR "indirect effect") AND '
                                        'TITLE:depression AND TITLE:(dementia OR cognitive)',
    'T8_geri_syndromes_mortality': 'TITLE:("geriatric syndrome" OR "geriatric syndromes")',
    'T9_CHARLS_dementia': 'TITLE:(CHARLS OR "China Health and Retirement") AND '
                          'TITLE:(dementia OR cognitive)',
    'T10_joint_combination': 'TITLE:(joint OR combined OR combination) AND '
                             'TITLE:(frailty OR multimorbidity OR disability) AND '
                             'TITLE:(depression OR dementia)',
}

TRACKS = [('concept', lambda q: q, CONCEPTS),                                   # 全字段
          ('abstract', lambda q: 'ABSTRACT:(' + q + ')', CONCEPTS),              # 摘要级
          ('title', lambda q: q, TITLE_QUERIES)]                                # 标题级（短式）

report = []
R = {'generated': time.strftime('%Y-%m-%d %H:%M:%S'), 'tracks': {}, 'crossref': {}}

for track, wrap, QS in TRACKS:
    report.append('\n' + '=' * 78)
    report.append('轨 %s —— Europe PMC（相关性排序）%s'
                  % (track, '' if track == 'title' else '，2018–2026 窗口'))
    report.append('=' * 78)
    R['tracks'][track] = {}
    for name, q in QS.items():
        query = wrap(q)
        st, hits, meta = epmc(query, pagesize=60, sort=None)
        R['tracks'][track][name] = dict(query=query, status=st, hitCount=meta,
                                        top=hits[:20])
        if st == 'SERVICE_ERROR':
            report.append('[%s] %s  →  SERVICE_ERROR（服务不可用，无法判定；%s）'
                          % (track, name, meta))
        elif st == 'NO_HIT':
            report.append('[%s] %s  →  NO_HIT（服务正常，0 命中）' % (track, name))
        else:
            report.append('[%s] %s  →  命中 %s 条' % (track, name, meta))
            for h in hits[:12]:
                report.append('      · %s｜%s (%s)｜PMID %s｜%s'
                              % (h['year'], h['title'][:120], h['journal'][:38],
                                 h['pmid'] or '-', h['authors'][:45]))
        time.sleep(0.5)

report.append('\n' + '=' * 78)
report.append('补充轨 —— Crossref（题录级，覆盖非 PubMed 收录）')
report.append('=' * 78)
for name, q in CONCEPTS.items():
    st, hits, total = crossref(q)
    R['crossref'][name] = dict(query=q, status=st, total=total, top=hits[:20])
    if st == 'SERVICE_ERROR':
        report.append('[%s] →  SERVICE_ERROR（服务不可用；%s）' % (name, total))
    elif st == 'NO_HIT':
        report.append('[%s] →  NO_HIT（服务正常，0 命中）' % name)
    else:
        report.append('[%s] →  约 %s 条' % (name, total))
        for h in hits[:6]:
            report.append('      · %s｜%s (%s)｜%s'
                          % (h['year'], h['title'][:120], h['journal'][:38], h['doi'][:45]))
    time.sleep(0.5)

report.append('\n' + '=' * 78)
report.append('中文库检索式（Europe PMC 对中文期刊覆盖有限，需在 CNKI / 万方 / 维普人工执行）')
report.append('=' * 78)
CN = ['(主题=老年综合征 OR 衰弱 OR 多病共存 OR 失能) AND (主题=痴呆 OR 认知障碍) AND (主题=队列 OR 随访)',
      '(主题=衰弱) AND (主题=痴呆) AND (主题=轨迹 OR 变化 OR 缓解 OR 逆转)',
      '(主题=抑郁) AND (主题=痴呆) AND (主题=中介 OR 间接效应) AND (主题=失能 OR 多病)',
      '(主题=CHARLS) AND (主题=痴呆 OR 认知) ',
      '(主题=多病共存) AND (主题=痴呆) AND (主题=交互 OR 联合作用)']
for c in CN:
    report.append('  · ' + c)

os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'nov_search.md'), 'w', encoding='utf8').write('\n'.join(report))
json.dump(R, open(os.path.join(OUT, 'nov_search.json'), 'w', encoding='utf8'),
          ensure_ascii=False, indent=1)
print('\n'.join(report))
