# -*- coding: utf-8 -*-
"""p19_fig_data.py —— 图表与 Word 表格所需的补充聚合（全部由脚本从源数据/中间产物计算）

① 纳入流程（Fig 1A）：逐级排除数 = _surv_flow.csv 相邻列差
② 轨迹发病密度（Fig 3B / Table S7）：复刻 p13 的轨迹构造，补存人年与合并密度
③ 分类梯度 / 三组分 / 八类联合（Fig 2B/2C, Table 2B/3A/3B/3C 合并行）：
   由逐队列 CSV 经 DerSimonian–Laird 合并
④ 水平 vs 变化（Fig 3D）：_level.csv 逐项 DL 合并
输出：out/_flow.csv、out/_traj_dist_pool.csv、out/_pool_2b.csv、out/_pool_3a.csv、
      out/_pool_3b.csv、out/_pool_3c.csv、out/_level_pool.csv、out/_pool_check.txt
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
NAME = {'CHARLS': 'CHARLS (China)', 'ELSA': 'ELSA (England)', 'HRS': 'HRS (USA)',
        'KLoSA': 'KLoSA (Korea)', 'MHAS': 'MHAS (Mexico)', 'SHARE': 'SHARE (Europe)'}
CHK = []


def chk(name, got, exp, src):
    """与稿件已用数值（_ms_numbers.csv）逐项对撞，不一致即报错。"""
    ok = abs(float(got) - float(exp)) <= max(0.005, 0.005 * abs(float(exp)))
    CHK.append('%s: got=%.4f  ms=%.4f  %s  (%s)' % (name, got, exp, 'OK' if ok else 'MISMATCH', src))
    assert ok, '%s 不一致: %.6f vs %.6f' % (name, got, exp)


# ------------------------------------------------------------------ ① 纳入流程
F = pd.read_csv(os.path.join(OUT, '_surv_flow.csv'))
STEPS = [('baseline_respondents', 'Baseline respondents'),
         ('cog_available', 'Baseline cognitive assessment available'),
         ('free_of_dementia', 'Dementia-free at baseline'),
         ('age_50_105', 'Aged 50-105 years'),
         ('has_followup_cog', 'Survived to and assessed during follow-up')]
flow = []
for i, (col, lab) in enumerate(STEPS):
    n = int(F[col].sum())
    prev = int(F[STEPS[i - 1][0]].sum()) if i else None
    flow.append(dict(step=i + 1, label=lab, n=n,
                     excluded=(prev - n) if prev is not None else 0))
final_n = int(F['N'].sum())
flow.append(dict(step=len(STEPS) + 1, label='Final analytic sample',
                 n=final_n, excluded=flow[-1]['n'] - final_n))
FL = pd.DataFrame(flow)
FL.to_csv(os.path.join(OUT, '_flow.csv'), index=False, encoding='utf-8-sig')

# ------------------------------------------------------------------ ② 轨迹人年
panel = {}
for co in CO:
    dai = pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % co))
    cog = pd.read_parquet(os.path.join(OUT, '_cog2_%s.parquet' % co))
    for x in (dai, cog):
        x['pid'] = x['pid'].astype(str)
    p = dai.merge(cog[['pid', 'wave', 'dem_alg_edu']], on=['pid', 'wave'], how='inner')
    p['year'] = p['wave'].map(L.WAVE_YEAR[co])
    p = p[p['dai3'].notna() & p['dem_alg_edu'].notna()]
    p = p.sort_values(['pid', 'year'])
    panel[co] = p

dist = []
for co in CO:
    p = panel[co]
    base = L.BASE_WAVE[co]
    ws = [w for w in L.WAVES[co] if w in p['wave'].unique()]
    if len(ws) < 2:
        continue
    w0, w1 = ws[0], ws[1]
    b = p[p['wave'] == w0][['pid', 'dai3', 'dem_alg_edu', 'year']].rename(
        columns={'dai3': 'd0', 'year': 'y0', 'dem_alg_edu': 'dem0'})
    f = p[p['wave'] == w1][['pid', 'dai3', 'dem_alg_edu', 'year']].rename(
        columns={'dai3': 'd1', 'year': 'y1', 'dem_alg_edu': 'dem1'})
    m = b.merge(f, on='pid')
    m = m[(m['dem0'] != 1) & (m['dem1'] != 1)]
    m['grp'] = np.where(m['d0'] > 0, 'P', 'L') + np.where(m['d1'] > 0, 'P', 'L')
    m['traj'] = m['grp'].map({'LL': 'persistently low', 'PL': 'remitted',
                              'LP': 'incident', 'PP': 'persistently affected'})
    after = p[p['wave'].isin([w for w in L.WAVES[co] if w > w1])]
    ev = after[after['dem_alg_edu'] == 1].groupby('pid')['year'].min()
    last = after.groupby('pid')['year'].max()
    m = m.merge(pd.DataFrame({'yr_event': ev, 'yr_last': last}), left_on='pid',
                right_index=True, how='left')
    m = m[m['yr_last'].notna()].copy()
    m['E'] = m['yr_event'].notna().astype(int)
    m['exit'] = np.where(m['E'] == 1, m['yr_event'] - m['y1'], m['yr_last'] - m['y1']).astype(float)
    m = m[m['exit'] > 0]
    for t in ['persistently low', 'remitted', 'incident', 'persistently affected']:
        s = m[m['traj'] == t]
        if len(s) < 100:
            continue
        dist.append(dict(cohort=co, traj=t, n=len(s), ev=int(s['E'].sum()),
                         py=float(s['exit'].sum()),
                         density=1000 * s['E'].sum() / max(s['exit'].sum(), 1)))
D = pd.DataFrame(dist)
D.to_csv(os.path.join(OUT, '_traj_dist_pool.csv'), index=False, encoding='utf-8-sig')
ORDER = ['persistently low', 'remitted', 'incident', 'persistently affected']
rows = []
for t in ORDER:
    s = D[D['traj'] == t]
    rows.append(dict(traj=t, n=int(s['n'].sum()), ev=int(s['ev'].sum()),
                     py=float(s['py'].sum()),
                     density=1000 * s['ev'].sum() / s['py'].sum(),
                     cohorts=len(s)))
DP = pd.DataFrame(rows)
DP.to_csv(os.path.join(OUT, '_traj_dist_pool_summary.csv'), index=False, encoding='utf-8-sig')

# ------------------------------------------------------------------ ③④ DL 合并
def pool_by(csv, keycol):
    T = pd.read_csv(os.path.join(OUT, csv))
    out = []
    for lv, g in T.groupby(keycol):
        p = L.dl_meta(np.log(g['hr'].astype(float)), g['se'].astype(float))
        if p:
            out.append({keycol: lv, 'k': p['k'], 'hr': p['hr'], 'lo': p['lo'], 'hi': p['hi'],
                        'I2': p['I2'], 'p': p['p']})
    return pd.DataFrame(out)


P2B = pool_by('Table2B.csv', 'level')
P3A = pool_by('Table3A.csv', 'component')
P3B = pool_by('Table3B.csv', 'component')
P3C = pool_by('Table3C.csv', 'category')
P2B.to_csv(os.path.join(OUT, '_pool_2b.csv'), index=False, encoding='utf-8-sig')
P3A.to_csv(os.path.join(OUT, '_pool_3a.csv'), index=False, encoding='utf-8-sig')
P3B.to_csv(os.path.join(OUT, '_pool_3b.csv'), index=False, encoding='utf-8-sig')
P3C.to_csv(os.path.join(OUT, '_pool_3c.csv'), index=False, encoding='utf-8-sig')

LV = pd.read_csv(os.path.join(OUT, '_level.csv'))
rows = []
for (mod, term), g in LV.groupby(['model', 'term']):
    p = L.dl_meta(np.log(g['hr'].astype(float)), g['se'].astype(float))
    if p:
        rows.append(dict(model=mod, term=term, k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'],
                         I2=p['I2'], p=p['p']))
LP = pd.DataFrame(rows)
LP.to_csv(os.path.join(OUT, '_level_pool.csv'), index=False, encoding='utf-8-sig')

# ------------------------------------------------------------------ 对撞
MS = pd.read_csv(os.path.join(OUT, '_ms_numbers.csv'))
MS['key'] = MS['key'].astype(str).str.replace('^\ufeff', '', regex=True)
MS['value'] = pd.to_numeric(MS['value'], errors='coerce')
V = dict(zip(MS['key'], MS['value']))

chk('flow_baseline', FL['n'].iloc[0], V['baseline_resp'], '_flow vs baseline_resp')
chk('flow_final', FL['n'].iloc[-1], V['n_analytic'], '_flow vs n_analytic')
for _, r in P2B.iterrows():
    lv = int(r['level'][0])
    chk('grad%d_hr' % lv, r['hr'], V['grad%d_hr' % lv], '_pool_2b vs grad%d' % lv)
for _, r in P3A.iterrows():
    k = r['component']
    chk('t3A_%s_hr' % k, r['hr'], V['t3A_%s_hr' % k], '_pool_3a vs ms')
for _, r in P3B.iterrows():
    k = r['component']
    chk('t3B_%s_hr' % k, r['hr'], V['t3B_%s_hr' % k], '_pool_3b vs ms')
for _, r in P3C.iterrows():
    k = r['category'].replace(' ', '_')
    chk('t3C_%s_hr' % k, r['hr'], V['t3C_%s_hr' % k], '_pool_3c vs ms')
for _, r in LP[LP['model'] == 'change'].iterrows():
    chk('lvl_change_hr', r['hr'], V['lvl_chg_hr'], '_level_pool vs ms')
for _, r in LP[LP['model'] == 'baseline level'].iterrows():
    chk('lvl_base_hr', r['hr'], V['lvl_base_hr'], '_level_pool vs ms')
for _, r in LP[LP['model'] == 'follow-up level'].iterrows():
    chk('lvl_fu_hr', r['hr'], V['lvl_fu_hr'], '_level_pool vs ms')

# 轨迹密度与逐队列表对撞
DOLD = pd.read_csv(os.path.join(OUT, '_traj_dist.csv'))
mg = D.merge(DOLD, on=['cohort', 'traj'], suffixes=('', '_old'))
assert len(mg) == len(DOLD), '轨迹表行数不一致'
assert np.allclose(mg['density'], mg['density_old'], atol=1e-6), '轨迹密度与 p13 输出不一致'
CHK.append('traj_dist 与 p13 输出逐行一致 (n=%d)' % len(mg))

# ------------------------------------------------------------------ 报告
rep = ['# p19 图表/表格聚合数据', '']
rep += ['## 纳入流程'] + ['', '| step | 阶段 | N | 排除 |', '|---|---|---|---|']
for _, r in FL.iterrows():
    rep.append('| %d | %s | %s | %s |' % (r['step'], r['label'], format(r['n'], ','),
                                           format(r['excluded'], ',')))
rep += ['', '## 轨迹发病密度（合并）', '',
        '| trajectory | n | events | person-years | density (/1000 py) | cohorts |',
        '|---|---|---|---|---|---|']
for _, r in DP.iterrows():
    rep.append('| %s | %s | %s | %s | %.1f | %d |' % (
        r['traj'], format(r['n'], ','), format(r['ev'], ','), format(r['py'], ','),
        r['density'], r['cohorts']))
rep += ['', '## 对撞结果', '']
rep += ['- ' + c for c in CHK]
open(os.path.join(OUT, '_pool_check.txt'), 'w', encoding='utf8').write('\n'.join(rep))
print('\n'.join(rep))
print('\n全部对撞通过：%d 项' % len(CHK))
