# -*- coding: utf-8 -*-
"""p12_outcomes.py —— 替代结局与保守截尾（Table 4B / §8.2 的数据源）
① dem_alg      ：非教育分层 z ≤ −1.5（来自 p2）
② dem_alg25    ：25 分量表（记忆 0–20 + 连续减 7 0–5），教育分层参考，≤ −1.5
③ dem_pub      ：协调化文件预置已发表分类（dementia==1），并算与 dem_alg_edu 的 Cohen κ
④ T_sens       ：保守截尾（不向死亡年延伸）
对 ①②③④ 各跑一遍 M2 并 DL 合并
输出：out/_alt_outcomes.csv、out/_kappa.csv
"""
import os
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS


def dcols(df, drop=()):
    return L.design_frame(df, drop=drop)


def _phreg(d, dur, event, cols):
    """与 p4 一致的无惩罚 PHReg 兜底（statsmodels）。返回 None 表示不可用。"""
    from statsmodels.duration.hazard_regression import PHReg
    try:
        m = PHReg(d[dur].values, d[cols].values, status=d[event].values).fit(disp=0)
        # 返回 log 空间（与 one() 的 coef 口径一致），HR 由调用方取 exp
        return float(m.params[0]), float(m.bse[0])
    except Exception:
        return None


def _guard(v):
    """与 p4.guard 同一套有限性/稳定性守卫：拒绝非有限值、se<=0、|log HR|>3、se>2。

    2026-10-13：p4 一直有该守卫，p12 此前漏掉，致使 MHAS 的 dem_alg 在分离
    （separation）情形下把 NaN 当结果写出，并被合并脚本计入事件数而 k 不计，
    而 k 与事件数来自不同队列集合（自相矛盾）。
    """
    if v is None:
        return None
    cf, se = v                      # 注意：本函数收到的第一个元素是 log-HR（coef），不是 HR
    if not np.isfinite(cf) or not np.isfinite(se) or se <= 0:
        return None
    if abs(cf) > 3 or se > 2:
        return None
    return v


def fitM2(df, dur='T', expo='dai3'):
    X = dcols(df)
    d = pd.concat([df[[dur, 'E', expo]], X], axis=1).dropna()
    if len(d) < 200 or d['E'].sum() < 20:
        return None
    cols = [expo] + list(X.columns)

    def one(c, pen):
        r = L.cox(d, dur, 'E', c, penalizer=pen, return_frame=True)
        if r is None or expo not in r[5].index:
            return None
        s = r[5]
        return float(s.loc[expo, 'coef']), float(s.loc[expo, 'se(coef)'])
    # 与主分析 p4.fit 完全同一级联：lifelines(1e-4) → 双惩罚一致性 → 无惩罚 PHReg → 去 age²。
    # 2026-10-13 修正：此前本脚本在一致性检验失败时直接去 age²，与主分析（先试 PHReg）不同；
    # 经检验当两套级联跑在同一数据上时结果一致，故此处对齐以防未来漂移。
    v1, v2 = _guard(one(cols, 1e-4)), _guard(one(cols, 1e-2))
    method = 'lifelines1e-4'
    if v1 is not None and v2 is not None and abs(v1[0] - v2[0]) <= 0.10:
        v = v1
    else:
        v3 = _guard(_phreg(d, dur, 'E', cols))
        if v3 is not None:
            v, method = v3, 'phreg'
        elif v1 is not None:
            v, method = v1, 'lifelines1e-4*'
        else:
            c2 = [x for x in cols if x != 'age2']
            v = _guard(one(c2, 1e-4))
            method = 'no-age2'
            if v is None:
                return None
    return dict(coef=v[0], se=v[1], hr=np.exp(v[0]), n=len(d), ev=int(d['E'].sum()),
                method=method)


# ---------------------------------------------------------------- 构造替代结局
kappa_rows, prev_rows = [], []
for co in CO:
    c = pd.read_parquet(os.path.join(OUT, '_cog_%s.parquet' % co))
    c['pid'] = c['pid'].astype(str)
    # ① dem_alg 已在 p2；② dem_alg25：记忆(0-20) + 执行(0-5)
    mem, exe = c['raw_mem'], c['raw_exe']
    ok25 = mem.notna() & exe.notna()
    score25 = (mem.fillna(0) + exe.fillna(0)).where(ok25)
    bw = L.BASE_WAVE[co]
    inband = c['age'].between(50, 69)
    mref = inband & (c['wave'] == bw) & score25.notna()
    if mref.sum() < 500:
        mref = inband & score25.notna()
    z25 = pd.Series(np.nan, index=c.index)
    ed = c['raeducl']
    for e in sorted(ed[mref].dropna().unique()):
        mm = mref & (ed == e)
        if mm.sum() < 50:
            mm = mref
        mu, sd = score25[mm].mean(), score25[mm].std()
        sel = (ed == e)
        z25.loc[sel] = (score25[sel] - mu) / sd
    z25 = z25.where(z25.notna(), (score25 - score25[mref].mean()) / score25[mref].std())
    c['dem_alg25'] = (z25 <= -1.5).astype(float).where(z25.notna())
    # ③ dem_pub：预置已发表分类
    if co in ('HRS', 'KLoSA', 'ELSA'):
        d = L.load(co, ['wave', L.ID[co], 'dementia'])
        d['pid'] = d[L.ID[co]].astype(str)
        d['dem_pub'] = (d['dementia'] == 1).astype(float).where(d['dementia'].notna())
        c = c.merge(d[['pid', 'wave', 'dem_pub']], on=['pid', 'wave'], how='left')
        # κ（在 dem_alg_edu 与 dem_pub 同时可得的行上）
        sub = c[c['dem_alg_edu'].notna() & c['dem_pub'].notna()]
        if len(sub) > 100:
            a = sub['dem_alg_edu'].astype(int); b = sub['dem_pub'].astype(int)
            po = (a == b).mean()
            pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
            kappa_rows.append(dict(cohort=co, n=len(sub), kappa=(po - pe) / (1 - pe),
                                   agree=po, prev_alg=100 * a.mean(), prev_pub=100 * b.mean()))
    # 患病率对照
    prev_rows.append(dict(cohort=co, wave_agg='all',
                          dem_alg_edu=100 * c['dem_alg_edu'].mean(),
                          dem_alg=100 * c['dem_alg'].mean(),
                          dem_alg25=100 * c['dem_alg25'].mean(),
                          dem_pub=100 * c['dem_pub'].mean() if 'dem_pub' in c.columns else np.nan))
    c.to_parquet(os.path.join(OUT, '_cog2_%s.parquet' % co), index=False)

K = pd.DataFrame(kappa_rows)
K.to_csv(os.path.join(OUT, '_kappa.csv'), index=False, encoding='utf-8-sig')
print('Cohen κ（自制 dem_alg_edu vs 预置 dem_pub）:')
print(K.to_string(index=False) if len(K) else '  （无可比队列）')
print('\n患病率对照（%）:')
print(pd.DataFrame(prev_rows).round(1).to_string(index=False))

# ---------------------------------------------------------------- 替代结局的 M2
# 2026-10-13 重构（响应外部审稿意见）。
# 旧实现自行重建 E/T，且规则与主分析 p4.build **不同**：随访未向死亡年延伸、
# 末次认知评估限定在结局判定波内、且未套用 50–105 岁窗口。后果是**同一结局**
# （教育分层 z ≤ −1.5）在两处给出不同 HR（KLoSA 1.427 vs 1.468；SHARE 1.288 vs 1.317），
# 使 Table 2A 与 Table 4D 互相矛盾，且 Table 4D 的"保守截尾"行与"教育分层"行数值重合。
# 现改为与 p4.build 完全同规则：同一纳入链、同一结局判定波限制、同一随访定义
# （T 延伸至死亡年，T_sens 保守截尾），唯一变量是结局列名；
# 主结局行（dem_alg_edu）必须与主分析 M2 逐位一致，脚本内断言强制校验。
OUTCOME_WAVES = {'HRS': list(range(5, 14))}


def build_outcome(co, col):
    """按 p4.build 的规则构造某一结局的生存数据（仅结局列不同）。"""
    c2 = pd.read_parquet(os.path.join(OUT, '_cog2_%s.parquet' % co))
    da = pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % co))
    c2['pid'] = c2['pid'].astype(str)
    da['pid'] = da['pid'].astype(str)
    df = c2.merge(da, on=['pid', 'wave'], how='inner', suffixes=('', '_d'))
    base = L.BASE_WAVE[co]
    ybase = L.WAVE_YEAR[co][base]
    owaves = OUTCOME_WAVES.get(co, L.WAVES[co])

    b = df[df['wave'] == base].copy()
    b = b[b['global_z_edu'].notna()]              # 基线认知可得
    b = b[b['dem_alg_edu'] != 1]                  # 排除基线痴呆（一律用主结局判定，保证样本同一）
    b = b[b['age'].between(50, 105)]              # 年龄窗（旧实现漏掉）
    keep = set(b['pid'])

    fw = df[df['pid'].isin(keep) & (df['wave'] != base)].copy()
    fw = fw[fw['global_z_edu'].notna() & (fw['year'] > ybase)]   # 末次认知评估的来源（不受结局波限制）
    fu = fw[fw['wave'].isin(owaves) & fw[col].notna()]           # 结局判定波
    first_ev = fu[fu[col] == 1].groupby('pid')['year'].min()
    last_cog = fw.groupby('pid')['year'].max()

    b = b.set_index('pid')
    b['yr_event'] = first_ev
    b['yr_lastcog'] = last_cog
    b['died_yr'] = b['radyear']
    b = b[~((b['died_yr'].notna()) & (b['died_yr'] <= ybase))]   # 基线前死亡
    b = b[b['dai3'].notna()]                                     # 暴露完整

    b['E'] = b['yr_event'].notna().astype(int)
    b['T_sens'] = np.where(b['E'] == 1, b['yr_event'] - ybase, b['yr_lastcog'] - ybase)
    ext = np.where(b['died_yr'].notna() & (b['died_yr'] > b['yr_lastcog']),
                   b['died_yr'] - ybase, b['T_sens'])
    b['T'] = np.maximum(b['T_sens'], ext).astype(float)
    b = b[b['T'] > 0]
    return b.reset_index()


rows = []
MAIN = pd.read_csv(os.path.join(OUT, '_m1234.csv'))
for co in CO:
    c2 = pd.read_parquet(os.path.join(OUT, '_cog2_%s.parquet' % co))
    for tag, col in [('dem_alg_edu', 'dem_alg_edu'), ('dem_alg', 'dem_alg'),
                     ('dem_alg25', 'dem_alg25'), ('dem_pub', 'dem_pub')]:
        if col not in c2.columns or int(c2[col].notna().sum()) < 500:
            continue
        b = build_outcome(co, col)
        if b['E'].sum() < 20:
            continue
        r = fitM2(b)
        if r:
            rows.append(dict(cohort=co, outcome=tag, **r))
ALT = pd.DataFrame(rows)

# ------------------------------------------------ 不变量：主结局行 == 主分析 M2
_a = ALT[ALT['outcome'] == 'dem_alg_edu'].set_index('cohort')
_b = MAIN[MAIN['model'] == 'M2'].set_index('cohort')
_checked = 0
for co in _a.index:
    assert co in _b.index, '主分析缺 %s 的 M2' % co
    dh = abs(float(_a.loc[co, 'hr']) - float(_b.loc[co, 'hr']))
    dn = int(_a.loc[co, 'n']) - int(_b.loc[co, 'n'])
    assert dh < 1e-9 and dn == 0, '主结局管线仍不一致 %s: HR %.6f vs %.6f, n %d vs %d' \
        % (co, _a.loc[co, 'hr'], _b.loc[co, 'hr'], _a.loc[co, 'n'], _b.loc[co, 'n'])
    _checked += 1
print('不变量校验通过：dem_alg_edu 在 %d 个队列上与主分析 M2 的 HR 与 n 完全一致' % _checked)

ALT = pd.DataFrame(rows)
ALT.to_csv(os.path.join(OUT, '_alt_outcomes.csv'), index=False, encoding='utf-8-sig')
pool = []
for tag, s in ALT.groupby('outcome'):
    p = L.dl_meta(s['coef'], s['se'], tag)
    if p:
        _ok = s['coef'].notna() & s['se'].notna()
        pool.append(dict(outcome=tag, k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'], I2=p['I2'],
                         events=int(s.loc[_ok, 'ev'].sum()),
                         n=int(s.loc[_ok, 'n'].sum()),
                         cohorts=','.join(s.loc[_ok, 'cohort'])))
AP = pd.DataFrame(pool)
AP.to_csv(os.path.join(OUT, '_alt_pool.csv'), index=False, encoding='utf-8-sig')
print('替代结局 M2 合并:')
print(AP.to_string(index=False))

# ---------------------------------------------------------------- ④ 保守截尾
rows = []
for co in CO:
    d = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    r = fitM2(d, dur='T_sens')
    if r:
        rows.append(dict(cohort=co, **r))
TS = pd.DataFrame(rows)
p = L.dl_meta(TS['coef'], TS['se'], 'T_sens')
print('\n④ 保守截尾（末次认知评估，不向死亡年延伸）M2 合并: k=%d HR=%.3f (%.3f-%.3f) I2=%.1f%%'
      % (p['k'], p['hr'], p['lo'], p['hi'], p['I2']))
TS.to_csv(os.path.join(OUT, '_tsens.csv'), index=False, encoding='utf-8-sig')
pd.DataFrame([dict(k=p['k'], hr=p['hr'], lo=p['lo'], hi=p['hi'], I2=p['I2'])]).to_csv(
    os.path.join(OUT, '_tsens_pool.csv'), index=False, encoding='utf-8-sig')
print('\nDONE')
