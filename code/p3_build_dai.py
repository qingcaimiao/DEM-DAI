# -*- coding: utf-8 -*-
"""p3_build_dai.py —— DAI 暴露与协调化协变量（重建）
DAI = 失能(ADL∨IADL≥1) + 多病(7病集≥2) + 抑郁(队列特异阈值)，三组分全非缺失才计分。
协变量：年龄/年龄²、性别、教育、婚姻、吸烟3类、当前饮酒、BMI(ELSA 邻近波补)、城乡、握力、体力活动。
输出：out/_dai_<队列>.parquet
"""
import os, json
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS

# 失能：汇总分（>0）或项目法（≥60% 非缺失且任一为 1）
DIS = {
 'CHARLS': dict(adl_sum=['adlab_c'], iadl_sum=['iadl'], adl=[], iadl=[]),
 'ELSA':   dict(adl_sum=['adltot6'], iadl_sum=[], adl=[],
                iadl=['mapa', 'phonea', 'medsa', 'shopa', 'mealsa', 'housewka', 'dangera', 'communa', 'moneya']),
 'HRS':    dict(adl_sum=['adl6a'], iadl_sum=['iadl5a'], adl=[], iadl=[]),
 'KLoSA':  dict(adl_sum=[], iadl_sum=[],
                adl=['dressb', 'bathb', 'eatb', 'toiltb', 'bedb_k', 'brushb'],
                iadl=['mealsb', 'shopb', 'medsb', 'moneyb', 'phoneb', 'transb', 'gooutb', 'laundryb', 'housewkb', 'groomb']),
 'MHAS':   dict(adl_sum=['adltot6'], iadl_sum=['iadlfour'], adl=[], iadl=[]),
 'SHARE':  dict(adl_sum=[], iadl_sum=[],
                adl=['walkra', 'dressa', 'batha', 'eata', 'beda', 'toilta'],
                iadl=['phonea', 'medsa', 'moneya', 'shopa', 'mealsa', 'mapa', 'housewka']),
}
CHRON = {'CHARLS': ['hibpe', 'diabe', 'cancre', 'lunge', 'hearte', 'stroke', 'arthre'],
         'ELSA':   ['hibpe', 'diabe', 'cancre', 'lunge', 'hearte', 'stroke', 'arthre'],
         'HRS':    ['hibpe', 'diabe', 'cancre', 'lunge', 'hearte', 'stroke', 'arthre'],
         'KLoSA':  ['hibpe', 'diabe', 'cancre', 'lunge', 'hearte', 'stroke', 'arthre'],
         'MHAS':   ['hibpe', 'diabe', 'cancre', 'respe', 'hrtatte', 'stroke', 'arthre'],
         'SHARE':  ['hibpe', 'diabe', 'cancre', 'lunge', 'hearte', 'stroke', 'arthre']}
DEP = {'CHARLS': ('cesd10', 10), 'ELSA': ('cesd', 4), 'HRS': ('cesd', 4),
       'KLoSA': ('CESD10K', 10), 'MHAS': ('cesd_m', 5), 'SHARE': ('eurod', 4)}
COV = {
 'CHARLS': dict(sex='ragender', edu='raeducl', mar='marry', smoke=['smokev', 'smoken'],
                drink='drinkl', bmi='bmi', urban='hrural', grip=['gripsum'], act='vgactx_c'),
 'ELSA':   dict(sex='ragender', edu='raeducl', mar='mstath', smoke=['smokev', 'smoken'],
                drink='drink', bmi='mbmi', urban=None, grip=['lgrip'], act='vgactx_e'),
 'HRS':    dict(sex='ragender', edu='raeducl', mar='mstath', smoke=['smokev', 'smoken'],
                drink='drink', bmi='bmi', urban='rural', grip=['lgrip'], act='vgactx'),
 'KLoSA':  dict(sex='ragender', edu='raeducl', mar='mstath', smoke=['smokev', 'smoken'],
                drink='drink', bmi='bmi', urban='rural', grip=['lgrip'], act='vigact'),
 'MHAS':   dict(sex='ragender', edu='raeducl', mar='mstath', smoke=['smokev', 'smoken'],
                drink='drink', bmi='bmi', urban='rural', grip=['lgrip'], act='vigact'),
 'SHARE':  dict(sex='ragender', edu='raeducl', mar='mstath', smoke=['smokev', 'smoken'],
                drink='drink3m', bmi='bmi', urban='rural', grip=['lgrip', 'rgrip'], act='vgactx'),
}
# 当前饮酒的兜底列（按优先级）
DRINK_ALT = {'SHARE': ['drink3m', 'drinkxw']}
# 体力活动量程需反转的队列（以握力为锚点校正，见 Stage2 修正 1）
ACT_REVERSED = ('ELSA', 'SHARE')


def items_or_any(df, items, need_frac=0.6, min_need=2):
    sub = df[[c for c in items if c in df.columns]]
    if sub.shape[1] == 0:
        return pd.Series(np.nan, index=df.index)
    avail = sub.notna().sum(axis=1)
    need = max(min_need, int(np.ceil(need_frac * sub.shape[1])))
    anypos = (sub.fillna(0) > 0).any(axis=1).astype(float)
    return anypos.where(avail >= need)


def build(co):
    d = DIS[co]; cov = COV[co]
    w2 = ['wave', L.ID[co], 'radyear', 'agey', 'rabyear']
    want = list(dict.fromkeys(
        w2 + cov['smoke'] + CHRON[co] + d['adl_sum'] + d['iadl_sum'] + d['adl'] + d['iadl']
        + [c for c in [cov['sex'], cov['edu'], cov['mar'], cov['drink'], cov['bmi'], cov['urban'], cov['act']] if c]
        + DRINK_ALT.get(co, [])
        + cov['grip'] + ['lgrip1', 'lgrip2', 'rgrip1', 'rgrip2', 'gripsum',
                         'drinkd', 'drinkev', 'cesd10', 'cesd', 'cesd10a', 'cesd10b',
                         'cesd_m', 'eurod', 'iwstat', 'ragender', 'raeducl']))
    df = L.load(co, want)
    df = df[df['wave'].isin(L.WAVES[co])].copy()
    df['year'] = df['wave'].map(L.WAVE_YEAR[co])
    df['age'] = df['agey'] if 'agey' in df.columns else np.nan
    if 'rabyear' in df.columns:
        df['age'] = df['age'].where(df['age'].notna(), df['year'] - df['rabyear'])

    # ---- 失能
    if d['adl_sum'] and d['adl_sum'][0] in df.columns:
        a = (df[d['adl_sum'][0]] > 0).astype(float).where(df[d['adl_sum'][0]].notna())
    else:
        a = items_or_any(df, d['adl'])
    if d['iadl_sum'] and d['iadl_sum'][0] in df.columns:
        i = (df[d['iadl_sum'][0]] > 0).astype(float).where(df[d['iadl_sum'][0]].notna())
    else:
        i = items_or_any(df, d['iadl'])
    df['disab'] = ((a == 1) | (i == 1)).astype(float).where(a.notna() & i.notna())
    df['disab_adl'] = a
    df['disab_iadl'] = i

    # ---- 多病（允许 1 项缺失）
    cc = df[[c for c in CHRON[co] if c in df.columns]]
    df['nchron'] = cc.fillna(0).sum(axis=1)
    df['multi'] = (df['nchron'] >= 2).astype(float).where(cc.notna().sum(axis=1) >= len(cc.columns) - 1)

    # ---- 抑郁（KLoSA: cesd10a 覆盖 w3-4、cesd10b 覆盖 w5-8，无重叠，直接拼接）
    sc, cut = DEP[co]
    if co == 'KLoSA':
        a = df['cesd10a'] if 'cesd10a' in df.columns else pd.Series(np.nan, index=df.index)
        b = df['cesd10b'] if 'cesd10b' in df.columns else pd.Series(np.nan, index=df.index)
        raw = a.where(a.notna(), b)
    else:
        raw = df[sc] if sc in df.columns else pd.Series(np.nan, index=df.index)
    df['dep_raw'] = raw
    df['dep'] = (raw >= cut).astype(float).where(raw.notna())

    # ---- DAI
    ok = df['disab'].notna() & df['multi'].notna() & df['dep'].notna()
    df['dai3'] = (df['disab'].fillna(0) + df['multi'].fillna(0) + df['dep'].fillna(0)).where(ok)

    # ---- 协变量
    df['male'] = (df[cov['sex']] == 1).astype(float).where(df[cov['sex']].notna())
    df['edu'] = df[cov['edu']]
    m = df[cov['mar']] if cov['mar'] in df.columns else pd.Series(np.nan, index=df.index)
    df['partnered'] = m.isin([1, 2, 3]).astype(float).where(m.notna())
    if all(c in df.columns for c in cov['smoke']):
        sv, sn = df[cov['smoke'][0]], df[cov['smoke'][1]]
        sm = pd.Series(np.nan, index=df.index)
        sm[(sv == 0)] = 0
        sm[(sv == 1) & (sn == 0)] = 1
        sm[(sn == 1)] = 2
        df['smoke3'] = sm.where(sv.notna() & sn.notna())
    else:
        df['smoke3'] = np.nan
    # 当前饮酒：主列 + 兜底列
    dk = pd.Series(np.nan, index=df.index)
    for c in [cov['drink']] + DRINK_ALT.get(co, []):
        if c in df.columns:
            vv = df[c].where(df[c].isin([0, 1]))
            dk = dk.where(dk.notna(), vv)
    df['drink_now'] = dk
    df['bmi'] = df[cov['bmi']] if cov['bmi'] in df.columns else np.nan
    df['bmi'] = df['bmi'].where((df['bmi'] >= 10) & (df['bmi'] <= 70))
    # ELSA 奇数波不测 BMI → 个体内最近波长补（先向后、再向前）
    if co == 'ELSA':
        df = df.sort_values(['pid' if 'pid' in df.columns else L.ID[co], 'wave'])
        key = 'pid' if 'pid' in df.columns else L.ID[co]
        b = df.groupby(key)['bmi'].transform(lambda s: s.ffill().bfill())
        df['bmi'] = b
    if cov['urban'] and cov['urban'] in df.columns:
        u = df[cov['urban']]
        if cov['urban'] in ('rural', 'hrural'):
            df['urban'] = (1 - u).where(u.isin([0, 1]))      # rural=1 → urban=0
        else:
            df['urban'] = u.where(u.notna())
    else:
        df['urban'] = np.nan
    # 握力：候选列取最大（最佳手）；<1kg 视为未测
    g = pd.Series(np.nan, index=df.index)
    for c in cov['grip']:
        if c in df.columns:
            g = g.where(g.notna(), df[c]) if g.notna().any() else df[c]
    if len(cov['grip']) > 1 and all(c in df.columns for c in cov['grip']):
        g = df[cov['grip']].max(axis=1)
    df['grip'] = g.where(g >= 1)
    act = df[cov['act']] if cov['act'] in df.columns else pd.Series(np.nan, index=df.index)
    df['act_raw'] = act
    if co in ACT_REVERSED:
        df['act'] = act.where(~act.isin([2, 3, 4, 5]), 7 - act)   # 2=最活跃 → 反转
    else:
        df['act'] = act

    keep = [L.ID[co], 'wave', 'year', 'age', 'male', 'edu', 'partnered', 'smoke3', 'drink_now',
            'bmi', 'urban', 'grip', 'act', 'act_raw', 'disab', 'disab_adl', 'disab_iadl',
            'nchron', 'multi', 'dep_raw', 'dep', 'dai3', 'radyear']
    keep = [c for c in keep if c in df.columns]
    out = df[keep].rename(columns={L.ID[co]: 'pid'})
    out['pid'] = out['pid'].astype(str)
    return out


meta = {}
for co in CO:
    print('=' * 70); print('#', co, ' cov=', COV[co]['drink'], COV[co]['bmi'], COV[co]['act'])
    o = build(co)
    o.to_parquet(os.path.join(OUT, '_dai_%s.parquet' % co), index=False)
    b = o[o['wave'] == L.BASE_WAVE[co]]
    print('  基线波 %s: n=%d  失能%.1f%% 多病%.1f%% 抑郁%.1f%%  三组分齐%d (%.1f%%)'
          % (L.BASE_WAVE[co], len(b), 100 * b['disab'].mean(), 100 * b['multi'].mean(),
             100 * b['dep'].mean(), b['dai3'].notna().sum(), 100 * b['dai3'].notna().mean()))
    print('  DAI 分布:', {int(k): round(100 * v, 1) for k, v in b['dai3'].value_counts(normalize=True).items()})
    print('  协变量缺失率%%: ' + ' '.join('%s=%.1f' % (c, 100 * b[c].isna().mean())
          for c in ['age', 'male', 'edu', 'partnered', 'smoke3', 'drink_now', 'bmi', 'urban', 'grip', 'act']))
    meta[co] = dict(n_base=int(len(b)), dai_complete=int(b['dai3'].notna().sum()))
json.dump(meta, open(os.path.join(OUT, '_dai_meta.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('\nDONE')
