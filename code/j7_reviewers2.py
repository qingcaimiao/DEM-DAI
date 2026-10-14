# -*- coding: utf-8 -*-
"""j7_reviewers2.py —— 按"参考文献内 + 大同行 + 国籍分散"重选审稿人，并核实单位"""
import json
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')


def epmc(q, n=3):
    u = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urllib.parse.urlencode(
        {'query': q, 'format': 'json', 'resultType': 'core', 'pageSize': str(n),
         'sort': 'P_PDATE_D desc'})
    return json.load(urllib.request.urlopen(u, timeout=40)).get('resultList', {}).get('result', [])


Q = [
    ('Prince MJ (KCL)', 'AUTH:"Prince, Martin J" AND AFF:"King\'s College London"'),
    ('Prince MJ 痴呆近作', 'AUTH:"Prince MJ" AND TITLE:"dementia"'),
    ('Beekman ATF', 'AUTH:"Beekman ATF" AND AFF:"Amsterdam"'),
    ('Zhao Y (CHARLS/PKU)', 'AUTH:"Zhao Y" AND AFF:"Peking University" AND TITLE:"CHARLS"'),
    ('Wong R (MHAS)', 'AUTH:"Wong R" AND TITLE:"Mexican Health and Aging"'),
]
for lab, q in Q:
    print('###', lab)
    try:
        for x in epmc(q):
            ji = x.get('journalInfo', {})
            print('   -', (x.get('title') or '')[:80], '|',
                  ji.get('journal', {}).get('title'), x.get('pubYear'))
            for a in (x.get('authorList', {}).get('author', []) or [])[:3]:
                aff = ((a.get('authorAffiliationDetailsList', {}) or {})
                       .get('authorAffiliation', [{}]) or [{}])[0].get('affiliation', '')
                print('       ', a.get('fullName'), '|', aff[:150])
    except Exception as e:
        print('   ERR', e)
    print()
