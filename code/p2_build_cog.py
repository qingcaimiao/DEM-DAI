# -*- coding: utf-8 -*-
"""p2_build_cog.py —— 认知协调化与四套痴呆结局（重建）
四域：记忆(0-20) / 执行(0-5) / 定向(0-4) / 语言
  记忆重标定：KLoSA (imrc3+dlrc3)*20/6；MHAS (imrc8+dlrc8)*20/16 —— 与留痕一致
  定向重标定：MHAS orient_m*4/3
每个域 z 化：参考分布 = 该库**最早一个年龄50-69岁观测数≥500 的波**，跨波固定
  - global_z      : 非分层 z 的域均值
  - global_z_edu  : 教育分层 z（在参考分布内按 raeducl 分层）的域均值
  - 全局分要求 ≥2 个域可得
结局：dem_alg_edu = global_z_edu ≤ −1.5；dem_alg = global_z ≤ −1.5
      dem_alg25 / dem_pub（HRS/ELSA/KLoSA 预置分类）作替代
代理访谈（HRS/MHAS proxy==1）认知置缺失
输出：out/_cog_<队列>.parquet（人-波）
"""
import os, sys, json
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS

# ---------------------------------------------------------------- 域规格
SPEC = {
 'CHARLS': dict(
    mem_sum=['imrc', 'dlrc'], mem_scale=1.0,
    exe=['ser7'], exe_alt=[],
    ori='orient', ori_scale=1.0,
    lang=[], lang_scale=1.0),
 'ELSA': dict(
    mem_sum=['imrc', 'dlrc'], mem_scale=1.0,
    exe=['ser7'], exe_alt=['bwc20'],
    ori='orient', ori_scale=1.0,
    lang=['verbf'], lang_scale=1.0),
 'HRS': dict(
    mem_sum=['imrc', 'dlrc'], mem_scale=1.0,
    exe=['ser7'], exe_alt=[],
    ori='orient', ori_scale=1.0,
    lang=['verbf'], lang_scale=1.0),
 'KLoSA': dict(
    mem_sum=['imrc3', 'dlrc3'], mem_scale=20.0 / 6.0,
    exe=['ser7'], exe_alt=[],
    ori=None, ori_scale=1.0,
    lang=['object1', 'object2', 'rpsnt'], lang_scale=1.0),
 'MHAS': dict(
    mem_sum=['imrc8', 'dlrc8'], mem_scale=20.0 / 16.0,
    exe=['ser7'], exe_alt=['bwc20'],
    ori='orient_m', ori_scale=4.0 / 3.0,
    lang=['verbf'], lang_scale=1.0),
 'SHARE': dict(
    mem_sum=['imrc', 'dlrc'], mem_scale=1.0,
    exe=['ser7'], exe_alt=[],
    ori='orient', ori_scale=1.0,
    lang=['verbf'], lang_scale=1.0),
}
# HRS w14/w15 认知改名的替代列（原列优先，p 次之，w 兜底）
HRS_ALT = {'imrc': ['imrcp', 'imrcw'], 'dlrc': ['dlrcp', 'dlrcw'],
           'ser7': ['ser7p', 'ser7w'], 'bwc20': ['bwc20p', 'bwc20w'], 'orient': []}


def hcols(n):
    """HRS 专用：原列 + 替代列，按优先级合并。"""
    return [n] + HRS_ALT.get(n, [])
EDU_OK = ('raeducl',)

# 锁定域集：只保留"基线波已测、且全波由同一仪器测量"的域，保证复合分跨波可比。
#   ELSA/SHARE 执行域（ser7）仅中后段可得、HRS 语言域（verbf）仅 w10+、MHAS 执行域
#   在 w3 用 bwc20、w4/5 用 ser7（仪器不同）→ 均不适合进入锁定域集。
LOCK = {
 'CHARLS': ['mem', 'exe', 'ori'],
 'ELSA':   ['mem', 'ori', 'lang'],
 'HRS':    ['mem', 'exe', 'ori'],
 'KLoSA':  ['mem', 'exe', 'lang'],
 'MHAS':   ['mem', 'ori', 'lang'],
 'SHARE':  ['mem', 'ori', 'lang'],
}

AGEBAND = (50, 69)
MIN_REF = 500


def needed_cols(spec):
    s = set()
    for k in ('mem_sum', 'exe', 'exe_alt', 'lang'):
        s.update(spec[k])
    if spec['ori']:
        s.add(spec['ori'])
    return s


def build(co):
    spec = SPEC[co]
    base = L.BASE_WAVE[co]
    want = ['wave', L.ID[co], 'radyear', 'iwstat', 'raeducl', 'rabyear', 'proxy', 'agey'] + sorted(needed_cols(spec))
    if co == 'HRS':
        want += [c for v in HRS_ALT.values() for c in v]
    df = L.load(co, list(dict.fromkeys(want)))
    df = df[df['wave'].isin(L.WAVES[co])].copy()

    df['year'] = df['wave'].map(L.WAVE_YEAR[co])
    # 年龄：优先 agey，缺则 年 − 出生年
    if 'agey' in df.columns:
        df['age'] = df['agey']
    else:
        df['age'] = np.nan
    df['age'] = df['age'].where(df['age'].notna(), df['year'] - df['rabyear'])

    # ---------------- 域构造
    def col(*names):
        """按优先级返回第一个存在的列（合并 HRS 的 p/w 两套）。"""
        for n in names:
            if n in df.columns:
                return df[n]
        return pd.Series(np.nan, index=df.index)

    def merge_cols(names):
        """多个候选列取首个非缺失（HRS w14/15: p 优先，w 兜底）。"""
        out = pd.Series(np.nan, index=df.index)
        for n in names:
            if n in df.columns:
                out = out.where(out.notna(), df[n])
        return out

    mem = None
    if spec['mem_sum']:
        parts = []
        ok = pd.Series(True, index=df.index)
        for n in spec['mem_sum']:
            v = merge_cols(hcols(n)) if co == 'HRS' else col(n)
            parts.append(v)
            ok &= v.notna()
        mem = (sum(p.fillna(0) for p in parts) * spec['mem_scale']).where(ok)
    exe = None
    if spec['exe']:
        v = merge_cols(hcols(spec['exe'][0])) if co == 'HRS' else col(spec['exe'][0])
        for alt in spec['exe_alt']:
            va = merge_cols(hcols(alt)) if co == 'HRS' else col(alt)
            v = v.where(v.notna(), va * 2.5)
        exe = v
    ori = None
    if spec['ori']:
        v = merge_cols(hcols(spec['ori'])) if co == 'HRS' else col(spec['ori'])
        ori = v * spec['ori_scale']
    lang = None
    if spec['lang']:
        if co == 'HRS':
            cols = [merge_cols(hcols(spec['lang'][0]))]
        else:
            cols = [col(n) for n in spec['lang'] if n in df.columns]
        if cols:
            s = sum(c.fillna(0) for c in cols)
            okk = pd.concat(cols, axis=1).notna().any(axis=1)
            lang = (s * spec['lang_scale']).where(okk)

    for nm, ser in [('mem', mem), ('exe', exe), ('ori', ori), ('lang', lang)]:
        df['raw_' + nm] = ser

    # 代理访谈：认知置缺失
    if co in ('HRS', 'MHAS') and 'proxy' in df.columns:
        pr = df['proxy'] == 1
        for nm in ('mem', 'exe', 'ori', 'lang'):
            df.loc[pr, 'raw_' + nm] = np.nan

    # ---------------- 参考分布：**单库单一参考波**，跨波固定
    # 规则：优先取该库基线波（域最全且与主分析基线一致）；基线波该域不足 500 时
    #       取该域最早的 ≥500 观测波。所有域尽量共用同一参考波，避免复合分跨波漂移。
    domains = [d for d in LOCK[co] if df['raw_' + d].notna().any()]
    inband = df['age'].between(*AGEBAND)
    base_w = L.BASE_WAVE[co]
    ref_ref = {}
    for d in domains:
        m = inband & (df['wave'] == base_w) & df['raw_' + d].notna()
        if m.sum() >= MIN_REF:
            ref_ref[d] = base_w
        else:
            chosen = None
            for w in L.WAVES[co]:
                mm = inband & (df['wave'] == w) & df['raw_' + d].notna()
                if mm.sum() >= MIN_REF:
                    chosen = w
                    break
            ref_ref[d] = chosen
    print('  参考波:', ref_ref)

    # ---------------- z 化（非分层 + 教育分层），参考分布跨波固定
    for d in domains:
        w = ref_ref[d]
        m = inband & (df['wave'] == w) & df['raw_' + d].notna()
        mu, sd = df.loc[m, 'raw_' + d].mean(), df.loc[m, 'raw_' + d].std()
        df['z_' + d] = (df['raw_' + d] - mu) / sd
        # 教育分层
        zs = pd.Series(np.nan, index=df.index)
        for ed in sorted(df.loc[m, 'raeducl'].dropna().unique()):
            mm = m & (df['raeducl'] == ed)
            if mm.sum() < 50:
                mm = m
            m2, s2 = df.loc[mm, 'raw_' + d].mean(), df.loc[mm, 'raw_' + d].std()
            sel = (df['raeducl'] == ed)
            zs.loc[sel] = (df.loc[sel, 'raw_' + d] - m2) / s2
        # 教育缺失者用非分层 z 兜底
        zs = zs.where(zs.notna(), df['z_' + d])
        df['ze_' + d] = zs

    zc = ['z_' + d for d in domains]
    ze = ['ze_' + d for d in domains]
    df['n_dom'] = df[zc].notna().sum(axis=1)
    df['global_z'] = df[zc].mean(axis=1).where(df['n_dom'] >= 2)
    df['global_z_edu'] = df[ze].mean(axis=1).where(df['n_dom'] >= 2)

    df['dem_alg'] = (df['global_z'] <= -1.5).astype(float).where(df['global_z'].notna())
    df['dem_alg_edu'] = (df['global_z_edu'] <= -1.5).astype(float).where(df['global_z_edu'].notna())

    keep = [L.ID[co], 'wave', 'year', 'age', 'radyear', 'iwstat', 'raeducl',
            'n_dom', 'global_z', 'global_z_edu', 'dem_alg', 'dem_alg_edu'] + \
           ['raw_' + d for d in ('mem', 'exe', 'ori', 'lang')] + \
           ['z_' + d for d in domains] + ['ze_' + d for d in domains]
    keep = [c for c in keep if c in df.columns]
    out = df[keep].rename(columns={L.ID[co]: 'pid'})
    n_wave = out.groupby('wave')['global_z_edu'].apply(lambda s: int(s.notna().sum()))
    print('  各波可用全局分:', dict(n_wave))
    print('  N 行=%d  人=%d' % (len(out), out['pid'].nunique()))
    out.to_parquet(os.path.join(OUT, '_cog_%s.parquet' % co), index=False)
    return dict(cohort=co, rows=int(len(out)), persons=int(out['pid'].nunique()),
                domains=domains, ref_wave={k: (int(v) if v is not None else None) for k, v in ref_ref.items()},
                cov={w: int(v) for w, v in n_wave.items()})


meta = {}
for co in CO:
    print('=' * 70); print('#', co)
    try:
        meta[co] = build(co)
    except Exception as e:
        import traceback; traceback.print_exc()
        print('  FAILED', co, e)
json.dump(meta, open(os.path.join(OUT, '_cog_meta.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
print('\nDONE')
