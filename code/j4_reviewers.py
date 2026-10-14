# -*- coding: utf-8 -*-
"""j4_reviewers.py —— 从近邻文献作者群中取候选审稿人及其单位（Europe PMC 权威索引）"""
import json
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')


def epmc(titles):
    u = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urllib.parse.urlencode(
        {'query': ' OR '.join('TITLE:"%s"' % t for t in titles),
         'format': 'json', 'resultType': 'core', 'pageSize': '10'})
    return json.load(urllib.request.urlopen(u, timeout=40))


TITLES = [
    'Frailty trajectories preceding dementia in the US and UK',
    'The lifetime accumulation of multimorbidity and its influence on dementia risk',
    'Effects of physical and psychological multimorbidity on the risk of dementia',
    'Geriatric syndromes and mortality among hospitalized older adults',
    'Longitudinal dynamics in frailty and incident all-cause dementia',
    'Dynamic frailty exposure and cognitive aging trajectories',
]
r = epmc(TITLES)
for x in r.get('resultList', {}).get('result', []):
    print('###', x.get('title', '')[:95])
    ji = x.get('journalInfo', {})
    print('    %s %s  %s' % (ji.get('journal', {}).get('title'), x.get('pubYear'),
                             ji.get('volume') or ''))
    print('    DOI:', x.get('doi'))
    for a in (x.get('authorList', {}).get('author', []) or [])[:5]:
        aff = ((a.get('authorAffiliationDetailsList', {}) or {})
               .get('authorAffiliation', [{}]) or [{}])[0].get('affiliation', '')
        print('     -', a.get('fullName'), '|', aff[:150])
    print()
