# -*- coding: utf-8 -*-
"""把各脚本里各自实现的 dcols/design/design_cols/design_X 统一改为调用 dem_lib.design_frame，
确保全流程只有一处设计矩阵实现（并修掉"缺失被编码成参照组"的缺陷）。"""
import re, os

BASE = os.path.dirname(os.path.abspath(__file__))
TARGETS = {
 'p4_surv_cox.py':   ('def design(df, extra=())', 'design'),
 'p5_tables.py':     ('def design_cols(df, drop=())', 'design_cols'),
 'p6_lag_hetero.py': ('def dcols(df, drop=())', 'dcols'),
 'p7_mediation.py':  ('def dcols(df, drop=())', 'dcols'),
 'p9_subgroup.py':   ('def dcols(df, drop=())', 'dcols'),
 'p10_mice.py':      ('def design_X(d)', 'design_X'),
 'p12_outcomes.py':  ('def dcols(df)', 'dcols'),
 'p13_timevar.py':   ('def dcols(df)', 'dcols'),
 'p14_cindex.py':    ('def dcols(df)', 'dcols'),
}
NEW = {
 'p4_surv_cox.py':   'def design(df, extra=()):\n    return L.design_frame(df, extra=extra)\n\n\n',
 'p5_tables.py':     'def design_cols(df, drop=()):\n    return L.design_frame(df, drop=drop)\n\n\n',
 'p6_lag_hetero.py': 'def dcols(df, drop=()):\n    return L.design_frame(df, drop=drop)\n\n\n',
 'p7_mediation.py':  'def dcols(df, drop=()):\n    return L.design_frame(df, drop=drop)\n\n\n',
 'p9_subgroup.py':   'def dcols(df, drop=()):\n    return L.design_frame(df, drop=drop)\n\n\n',
 'p10_mice.py':      'def design_X(d):\n    return L.design_frame(d)\n\n\n',
 'p12_outcomes.py':  'def dcols(df, drop=()):\n    return L.design_frame(df, drop=drop)\n\n\n',
 'p13_timevar.py':   'def dcols(df, drop=()):\n    return L.design_frame(df, drop=drop)\n\n\n',
 'p14_cindex.py':    'def dcols(df, drop=()):\n    return L.design_frame(df, drop=drop)\n\n\n',
}
for fn, (anchor, name) in TARGETS.items():
    p = os.path.join(BASE, fn)
    s = open(p, encoding='utf8').read()
    i = s.find(anchor)
    if i < 0:
        print('SKIP (anchor not found):', fn); continue
    j = s.find('\ndef ', i + 1)
    if j < 0:
        j = len(s)
    old = s[i:j]
    s2 = s[:i] + NEW[fn] + s[j + 1:] if j < len(s) else s[:i] + NEW[fn]
    open(p, 'w', encoding='utf8').write(s2)
    print('patched %-20s  (%d -> %d chars)' % (fn, len(old), len(NEW[fn])))
