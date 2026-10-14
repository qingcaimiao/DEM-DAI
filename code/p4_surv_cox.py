# -*- coding: utf-8 -*-
"""p4_build_surv.py —— 生存数据集与主分析（Cox + DerSimonian-Laird 合并）
纳入链（与 StageR §2.2 对齐）：基线受访者 → 认知可得 → 排除基线痴呆 → 年龄50-105
→ 排除基线前死亡 / 无随访认知评估 → 排除 DAI 三组分缺失 → 分析样本
结局：首次 dem_alg_edu==1 的波；T 主版本延伸至死亡年，T_sens 保守截尾至末次认知评估
模型：M1 粗 / M2 核心 / M3 +城乡 / M4 +握力+体力活动
输出：out/_surv_<队列>.parquet、out/_surv_flow.csv、out/_m1234.csv、out/_pool.csv
"""
import os, json
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS

# 结局判定可用的波：HRS w14/w15 已无协调化认知条目（imrc/dlrc/ser7/orient 全缺），
# 结局判定止于 w13(2016)；但**随访时间仍延伸至死亡年**（HRS 死亡登记至 2021 ⇒ 最长 21 年）。
OUTCOME_WAVES = {'HRS': list(range(5, 14))}


def build(co):
    cg = pd.read_parquet(os.path.join(OUT, '_cog_%s.parquet' % co))
    da = pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % co))
    cg['pid'] = cg['pid'].astype(str); da['pid'] = da['pid'].astype(str)
    df = cg.merge(da, on=['pid', 'wave'], how='inner', suffixes=('', '_d'))
    base = L.BASE_WAVE[co]
    ybase = L.WAVE_YEAR[co][base]
    owaves = OUTCOME_WAVES.get(co, L.WAVES[co])
    flow = {}
    n0 = df.loc[df['wave'] == base, 'pid'].nunique()
    flow['baseline_respondents'] = int(n0)
    b = df[df['wave'] == base].copy()
    b = b[b['global_z_edu'].notna()]                                   # 基线认知可得
    flow['cog_available'] = int(len(b))
    b = b[b['dem_alg_edu'] != 1]                                       # 排除基线痴呆
    flow['free_of_dementia'] = int(len(b))
    b = b[b['age'].between(50, 105)]                                   # 年龄窗
    flow['age_50_105'] = int(len(b))

    # 随访：同一人基线后的认知波（结局判定波受限，但末次认知评估不受限 → 用于保守截尾）
    keep_id = set(b['pid'])
    fw = df[df['pid'].isin(keep_id) & (df['wave'] != base)].copy()
    fw = fw[fw['global_z_edu'].notna() & (fw['year'] > ybase)]
    fu = fw[fw['wave'].isin(owaves)]
    fu = fu.sort_values(['pid', 'year'])
    first_ev = fu[fu['dem_alg_edu'] == 1].groupby('pid')['year'].min()
    last_cog = fw.groupby('pid')['year'].max()
    b = b.set_index('pid')
    b['yr_event'] = first_ev
    b['yr_lastcog'] = last_cog
    b['has_fu'] = b['yr_lastcog'].notna()
    flow['has_followup_cog'] = int(b['has_fu'].sum())
    b['died_yr'] = b['radyear']
    b = b[~((b['died_yr'].notna()) & (b['died_yr'] <= ybase))]
    flow['alive_at_baseline'] = int(len(b))
    b2 = b[b['dai3'].notna()]
    flow['exposure_complete'] = int(len(b2))
    b = b2

    b['E'] = b['yr_event'].notna().astype(int)
    b['T_sens'] = np.where(b['E'] == 1, b['yr_event'] - ybase, b['yr_lastcog'] - ybase)
    ext = np.where(b['died_yr'].notna() & (b['died_yr'] > b['yr_lastcog']),
                   b['died_yr'] - ybase, b['T_sens'])
    b['T'] = np.maximum(b['T_sens'], ext)
    b['T'] = b['T'].astype(float)
    b['died'] = b['died_yr'].notna().astype(int)
    b = b[b['T'] > 0]
    flow['T_gt_0'] = int(len(b))
    b = b.reset_index()
    return b, flow


def design(df, extra=()):
    return L.design_frame(df, extra=extra)


def _one(d, dur, event, x, dai_col, method, penalizer=1e-4):
    """method: 'lifelines' | 'phreg'"""
    if method == 'lifelines':
        r = L.cox(d, dur, event, [dai_col] + list(x.columns), penalizer=penalizer)
        if r is None:
            return None
        return float(r[0][dai_col]), float(r[1][dai_col]), float(r[2][dai_col])
    # statsmodels PHReg（无惩罚）
    from statsmodels.duration.hazard_regression import PHReg
    try:
        cols = [dai_col] + list(x.columns)
        m = PHReg(d[dur].values, d[cols].values, status=d[event].values).fit(disp=0)
        return float(np.exp(m.params[0])), float(m.bse[0]), float(m.pvalues[0])
    except Exception:
        return None


def fit(df, dai_col, extra=(), Tcol='T'):
    """稳健拟合：lifelines(1e-4) → 双惩罚一致性检查 → PHReg 无惩罚 → 去 age²。"""
    X = design(df, extra)
    d = pd.concat([df[[Tcol, 'E', dai_col]], X], axis=1).dropna()
    if len(d) < 100 or d['E'].sum() < 20:
        return None
    n, ev = len(d), int(d['E'].sum())

    def guard(v):
        if v is None:
            return None
        hr, se, p = v
        if not np.isfinite(hr) or not np.isfinite(se) or se <= 0 or abs(np.log(hr)) > 3 or se > 2:
            return None
        return v

    # 1) lifelines 1e-4
    v1 = guard(_one(d, Tcol, 'E', X, dai_col, 'lifelines', 1e-4))
    # 2) 双惩罚一致性
    v2 = guard(_one(d, Tcol, 'E', X, dai_col, 'lifelines', 1e-2))
    method = 'lifelines1e-4'
    if v1 is not None and v2 is not None and abs(np.log(v1[0]) - np.log(v2[0])) <= 0.10:
        out = v1
    else:
        # 3) 无惩罚 PHReg
        v3 = guard(_one(d, Tcol, 'E', X, dai_col, 'phreg'))
        if v3 is not None:
            out, method = v3, 'phreg'
        elif v1 is not None:
            out, method = v1, 'lifelines1e-4*'
        else:
            # 4) 去 age² 兜底
            X2 = X.drop(columns=[c for c in ['age2'] if c in X.columns])
            d2 = pd.concat([df[[Tcol, 'E', dai_col]], X2], axis=1).dropna()
            v4 = guard(_one(d2, Tcol, 'E', X2, dai_col, 'lifelines', 1e-4))
            if v4 is None:
                return None
            out, method = v4, 'no-age2'
    hr, se, p = out
    return dict(hr=hr, se=se, p=p, n=n, ev=ev, method=method)


rows = []
flows = []
data = {}
for co in CO:
    print('=' * 72); print('#', co)
    d, flow = build(co)
    d.to_parquet(os.path.join(OUT, '_surv_%s.parquet' % co), index=False)
    ev, py = int(d['E'].sum()), float(d['T'].sum())
    print('  N=%d 事件=%d 人年=%.0f 中位随访=%.0f 最长=%.0f 死亡=%.1f%% 疼痛占比 NA'
          % (len(d), ev, py, d['T'].median(), d['T'].max(), 100 * d['died'].mean()))
    print('  纳入链:', flow)
    flows.append(dict(cohort=co, **flow, N=int(len(d)), events=ev, person_years=py,
                      median_fu=float(d['T'].median()), max_fu=float(d['T'].max()),
                      dai_mean=float(d['dai3'].mean())))
    data[co] = d
    for tag, extra in [('M1', ()), ('M2', ()), ('M3', ['urban']), ('M4', ['grip', 'act'])]:
        if tag == 'M1':
            X = pd.DataFrame({'dai3': d['dai3'].astype(float)})
            dd = pd.concat([d[['T', 'E', 'dai3']]], axis=1).dropna()
            r = L.cox(dd, 'T', 'E', ['dai3'], penalizer=1e-4)
            res = None if r is None else dict(hr=float(r[0]['dai3']), se=float(r[1]['dai3']),
                                              p=float(r[2]['dai3']), n=len(dd), ev=int(dd['E'].sum()))
        else:
            res = fit(d, 'dai3', extra)
        if res is None:
            print('   %s: 不可估' % tag); continue
        print('   %-3s HR=%.3f (%.3f-%.3f) p=%.2e n=%d ev=%d [%s]'
              % (tag, res['hr'], res['hr'] * np.exp(-1.96 * res['se']), res['hr'] * np.exp(1.96 * res['se']),
                 res['p'], res['n'], res['ev'], res.get('method', 'lifelines1e-4')))
        rows.append(dict(cohort=co, model=tag, **res))

R = pd.DataFrame(rows)
R.to_csv(os.path.join(OUT, '_m1234.csv'), index=False)
pd.DataFrame(flows).to_csv(os.path.join(OUT, '_surv_flow.csv'), index=False)

print('\n' + '=' * 72)
print('# DerSimonian-Laird 合并')
pools = []
for tag in ['M1', 'M2', 'M3', 'M4']:
    s = R[R['model'] == tag]
    if len(s) == 0:
        continue
    p = L.dl_meta(np.log(s['hr']), s['se'], tag)
    print('  %-3s k=%d HR=%.3f (%.3f-%.3f) I2=%.1f%% Qp=%.3f'
          % (tag, p['k'], p['hr'], p['lo'], p['hi'], p['I2'], p['Qp']))
    pools.append(p)
pd.DataFrame(pools).to_csv(os.path.join(OUT, '_pool.csv'), index=False)

# 合计
tot = pd.DataFrame(flows)[['N', 'events', 'person_years']].sum()
print('\n合计: N=%d 事件=%d 人年=%.0f' % (tot['N'], tot['events'], tot['person_years']))
print('回归测试目标: 基线 103444 / 分析 74501 / 事件 10848 / M2 = 1.230 (1.187-1.276) I2=60.6%')
print('DONE')
