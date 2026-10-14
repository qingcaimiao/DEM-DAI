# -*- coding: utf-8 -*-
"""p7_mediation.py —— 抑郁的效应分解（Table 4A/4B 的数据源）
X = 非抑郁负担 dm2 = 失能 + 多病（0–2）；M = 抑郁超阈；Y = 新发痴呆
① 截面差分法：M、X 同测于基线波
② 时序差分法：X@w0 → M@w1 → 结局自 w1 起（暴露严格早于中介一个波）
③ 反事实 g-formula：加性风险尺度上的四向分解（X 取二分「有无非抑郁负担」）
每队列 bootstrap 求比例 SE → 原始尺度 DL 合并（比例不可取对数）
输出：out/_med_cs.csv、_med_tv.csv、_gf.csv、_med_pool.csv、_patha.csv
"""
import os, sys
import numpy as np
import pandas as pd
import dem_lib as L

OUT = L.OUT
CO = L.COHORTS
NAME = {c: c for c in CO}
NB = 200   # 自助抽样次数，2026-10-13 起固定为 200（早期一次运行曾用 150，
          # 会使中介比例的自助 SE 与合并权重出现蒙特卡洛差异）


def dcols(df, drop=()):
    return L.design_frame(df, drop=drop)


def cox_beta(d, dur, ev, cols):
    r = L.cox(d, dur, ev, cols, penalizer=1e-4, return_frame=True)
    if r is None:
        return None
    s = r[5]
    return {c: (float(s.loc[c, 'coef']), float(s.loc[c, 'se(coef)']), float(s.loc[c, 'p']))
            for c in cols if c in s.index}


def prep(co):
    """构造 dm2（非抑郁负担 0–2）并合并到生存数据。"""
    surv = pd.read_parquet(os.path.join(OUT, '_surv_%s.parquet' % co))
    dai = pd.read_parquet(os.path.join(OUT, '_dai_%s.parquet' % co))
    dai['pid'] = dai['pid'].astype(str); surv['pid'] = surv['pid'].astype(str)
    b = L.BASE_WAVE[co]
    da = dai[dai['wave'] == b][['pid', 'disab', 'multi', 'dep']].set_index('pid')
    s = surv.set_index('pid').join(da, how='inner', rsuffix='_b')
    ok = s['disab'].notna() & s['multi'].notna() & s['dep'].notna()
    s = s[ok].copy()
    s['dm2'] = (s['disab'] + s['multi']).astype(float)
    s['Xbin'] = ((s['dm2'] > 0).astype(float))
    return s.reset_index(), dai, b


def best_fit(d0, dur, ev, cols):
    """四级稳健拟合：pen 1e-4 → 与 1e-2 一致性 → 去 age2。
    返回 (coef, se, p) 或 None。"""
    def one(d, c, pen):
        r = L.cox(d, dur, ev, c, penalizer=pen, return_frame=True)
        if r is None:
            return None
        s = r[5]
        if 'dm2' not in s.index:
            return None
        return {k: (float(s.loc[k, 'coef']), float(s.loc[k, 'se(coef)']), float(s.loc[k, 'p']))
                for k in c if k in s.index}

    def ok(res):
        if not res or 'dm2' not in res:
            return False
        b, se, _ = res['dm2']
        return np.isfinite(b) and np.isfinite(se) and abs(b) < 3 and se < 2 and se > 0

    plans = [(cols, 1e-4), (cols, 1e-2),
             ([c for c in cols if c != 'age2'], 1e-4)]
    for cc, pen in plans:
        r = one(d0, cc, pen)
        if ok(r):
            return r, cc
    return None, None


def med_diff(s, dur='T', ev='E', medcol='dep', boot=NB, seed=7):
    """① 截面/时序差分法：总效应 vs 调中介的直接效应（两者共用同一协变量集）。

    2026-10-13 修复：原先无论截面还是时序都硬取 `dep`（基线波抑郁），
    导致"时序差分法"实际上并未把中介放到暴露之后一个波——文档字符串声称的
    X@w0 → M@w1 → 结局自 w1 起 并未实现。现由 medcol 显式指定中介列：
    截面用 'dep'（基线），时序用 'dep1'（第 w1 波）。
    """
    Xc = dcols(s)
    d = pd.concat([s[[dur, ev, 'dm2', medcol]], Xc], axis=1).dropna()
    d = d.rename(columns={medcol: '_M'})
    if len(d) < 300 or d[ev].sum() < 40:
        return None
    base = list(Xc.columns)
    cols = ['dm2', '_M'] + base
    _, usecols = best_fit(d, dur, ev, cols)
    if usecols is None:
        return None
    use = [c for c in usecols if c != '_M']
    tot_res, _ = best_fit(d, dur, ev, use)
    dir_res, _ = best_fit(d, dur, ev, usecols)
    if not (tot_res and dir_res):
        return None
    bt, bt_se = tot_res['dm2'][0], tot_res['dm2'][1]
    bd, bd_se = dir_res['dm2'][0], dir_res['dm2'][1]
    if abs(bt) < 0.03:
        return dict(flag='unstable', n=len(d), ev=int(d[ev].sum()))
    prop = (bt - bd) / bt

    def one(dd):
        tr, _ = best_fit(dd, dur, ev, use)
        dr, _ = best_fit(dd, dur, ev, usecols)
        if not (tr and dr):
            return np.nan, np.nan
        a, c = tr['dm2'][0], dr['dm2'][0]
        return (np.nan if abs(a) < 1e-6 else (a - c) / a), a - c
    rng = np.random.default_rng(seed)
    bs, bs_ind = [], []
    for _ in range(boot):
        p_, i_ = one(d.iloc[rng.integers(0, len(d), len(d))])
        bs.append(p_); bs_ind.append(i_)
    bs = np.array([x for x in bs if np.isfinite(x)])
    bs_ind = np.array([x for x in bs_ind if np.isfinite(x)])
    assert len(bs) == len(bs_ind), ('bootstrap 并行列表长度不一致: %d vs %d'
                                    % (len(bs), len(bs_ind)))
    se = bs.std(ddof=1) if len(bs) > 20 else np.nan
    ind_se = bs_ind.std(ddof=1) if len(bs_ind) > 20 else np.nan
    print('      [med_diff] dur=%s medcol=%s  n=%d ev=%d  β_total=%.4f β_direct=%.4f '
          'β_indirect=%.4f prop=%.4f' % (dur, medcol, len(d), int(d[ev].sum()),
                                         bt, bd, bt - bd, prop))
    return dict(flag='ok', n=len(d), ev=int(d[ev].sum()),
                tot_hr=np.exp(bt), tot_se=bt_se,
                dir_hr=np.exp(bd), dir_se=bd_se,
                ind_hr=np.exp(bt - bd), ind_se=ind_se,
                prop=prop, prop_se=se,
                dep_hr=np.exp(dir_res['_M'][0]) if '_M' in dir_res else np.nan,
                med_col=medcol, dur=dur,
                boot_ok=int(len(bs)))


rows = []
gf_rows = []
patha = []
patha_tv = []
for co in CO:
    print('=' * 70); print('#', co)
    s, dai, b = prep(co)
    print('  基线 n=%d 事件=%d dm2均值=%.2f 抑郁=%.1f%%'
          % (len(s), s['E'].sum(), s['dm2'].mean(), 100 * s['dep'].mean()))
    # ① 截面
    r = med_diff(s)
    if r:
        r.update(cohort=NAME[co])
        rows.append(r)
        print('  ① 截面: tot=%.3f dir=%.3f ind=%.3f prop=%.3f (se %.3f)'
              % (r.get('tot_hr', np.nan), r.get('dir_hr', np.nan), r.get('ind_hr', np.nan),
                 r.get('prop', np.nan), r.get('prop_se', np.nan)))

    # 路径 a（截面）：dm2 → dep logistic
    try:
        import statsmodels.api as sm
        Xa = pd.concat([s[['dm2']], dcols(s)], axis=1).astype(float)
        y = s['dep'].astype(float)
        m = (y.notna()) & Xa.notna().all(axis=1)
        Xa2 = Xa[m]; y2 = y[m]
        Xa2 = Xa2.loc[:, Xa2.nunique() > 1]
        res = sm.Logit(y2, Xa2).fit(disp=0)
        patha.append(dict(cohort=co, or_=float(np.exp(res.params['dm2'])),
                          se=float(res.bse['dm2']), lo=float(np.exp(res.params['dm2'] - 1.96 * res.bse['dm2'])),
                          hi=float(np.exp(res.params['dm2'] + 1.96 * res.bse['dm2'])), n=int(m.sum())))
    except Exception as e:
        print('   路径a 失败:', e)

    # ② 时序：X@w0 → M@w1 → 结局自 w1（中介为**第 w1 波**抑郁 dep1）
    ws = [w for w in L.WAVES[co] if w > b]
    if ws:
        w1 = ws[0]
        nxt = dai[dai['wave'] == w1][['pid', 'dep']].rename(columns={'dep': 'dep1'}).set_index('pid')
        t1 = L.WAVE_YEAR[co][w1] - L.WAVE_YEAR[co][b]
        st = s.set_index('pid').join(nxt, how='inner')
        st = st[(st['T'] > t1)]
        st['T1'] = st['T'] - t1
        assert st['dep1'].notna().sum() > 0, '%s: 时序中介 dep1 全缺' % co
        r2 = med_diff(st, dur='T1', ev='E', medcol='dep1')
        if r2:
            r2.update(cohort=NAME[co])
            print('  ② 时序(w%d): tot=%.3f dir=%.3f ind=%.3f prop=%.3f (中介=dep1)'
                  % (w1, r2.get('tot_hr', np.nan), r2.get('dir_hr', np.nan),
                     r2.get('ind_hr', np.nan), r2.get('prop', np.nan)))
            r2['variant'] = 'temporal'
        else:
            r2 = None
        # 路径 a（时序口径）：w0 的 dm2 → w1 的抑郁
        try:
            import statsmodels.api as sm
            Xa = pd.concat([st[['dm2']], dcols(st)], axis=1).astype(float)
            y = st['dep1'].astype(float)
            m = (y.notna()) & Xa.notna().all(axis=1)
            Xa2, y2 = Xa[m], y[m]
            Xa2 = Xa2.loc[:, Xa2.nunique() > 1]
            res = sm.Logit(y2, Xa2).fit(disp=0)
            patha_tv.append(dict(cohort=co, or_=float(np.exp(res.params['dm2'])),
                                 se=float(res.bse['dm2']),
                                 lo=float(np.exp(res.params['dm2'] - 1.96 * res.bse['dm2'])),
                                 hi=float(np.exp(res.params['dm2'] + 1.96 * res.bse['dm2'])),
                                 n=int(m.sum())))
        except Exception as e:
            print('   路径a(时序) 失败:', e)
    else:
        r2 = None

    # ③ 反事实 g-formula（X 二分），5 年风险
    try:
        from lifelines import CoxPHFitter
        import statsmodels.api as sm
        Xc = dcols(s)
        d = pd.concat([s[['T', 'E', 'Xbin', 'dep']], Xc], axis=1).dropna()
        if len(d) >= 300 and d['E'].sum() >= 40:
            base = list(Xc.columns)
            cph = CoxPHFitter(penalizer=1e-4)
            cph.fit(d[['T', 'E', 'Xbin', 'dep'] + base], duration_col='T', event_col='E')
            Xl = pd.concat([d[['Xbin']], d[base]], axis=1)
            Xl = Xl.loc[:, Xl.nunique() > 1]
            lg = sm.Logit(d['dep'].astype(float), Xl).fit(disp=0)

            def risk(xv, mv):
                z = Xl.copy(); z['Xbin'] = xv; z['dep'] = mv
                S = cph.predict_survival_function(z, times=[5.0])
                return 1 - S.iloc[0].values
            # 中介概率 P(M=1|x',C)
            zx0 = Xl.copy(); zx0['Xbin'] = 0.0
            zx1 = Xl.copy(); zx1['Xbin'] = 1.0
            pM0 = np.asarray(lg.predict(zx0)).ravel()
            pM1 = np.asarray(lg.predict(zx1)).ravel()
            # 并行列表长度自检（每次个体风险向量必须等长）
            assert len(pM0) == len(pM1) == len(Xl), \
                '中介概率与设计矩阵长度不一致: pM0=%d pM1=%d Xl=%d' % (len(pM0), len(pM1), len(Xl))
            R00, R01 = risk(0.0, 0.0), risk(0.0, 1.0)
            R10, R11 = risk(1.0, 0.0), risk(1.0, 1.0)
            for _nm, _v in [('R00', R00), ('R01', R01), ('R10', R10), ('R11', R11),
                            ('pM0', pM0), ('pM1', pM1)]:
                assert len(_v) == len(Xl), '%s 长度 %d ≠ 设计矩阵 %d' % (_nm, len(_v), len(Xl))
            Y00 = R00
            Y11 = pM1 * R11 + (1 - pM1) * R10
            Y10 = pM0 * R11 + (1 - pM0) * R10          # Y(x=1, M(0))
            Y01 = pM1 * R01 + (1 - pM1) * R00          # Y(x=0, M(1))
            TE = Y11 - Y00
            NDE = Y10 - Y00
            NIE = Y11 - Y10
            den = np.where(np.abs(TE) > 1e-6, TE, np.nan)
            PM = NIE / den
            print('      [g-formula] Y00=%.5f Y01=%.5f Y10=%.5f Y11=%.5f | TE=%.5f '
                  'NDE=%.5f NIE=%.5f PM=%.4f (n=%d)' % (
                      np.mean(Y00), np.mean(Y01), np.mean(Y10), np.mean(Y11),
                      np.mean(TE), np.mean(NDE), np.mean(NIE), np.nanmean(PM), len(d)))
            gf_rows.append(dict(cohort=co, n=len(d), ev=int(d['E'].sum()),
                                Y00=float(np.mean(Y00)), Y10=float(np.mean(Y10)),
                                Y01=float(np.mean(Y01)), Y11=float(np.mean(Y11)),
                                TE=float(np.mean(TE)), NDE=float(np.mean(NDE)),
                                NIE=float(np.mean(NIE)), PM=float(np.nanmean(PM))))
            print('  ③ g-formula: Y(0,0)=%.4f Y(1,1)=%.4f TE=%.4f NDE=%.4f NIE=%.4f PM=%.3f'
                  % (np.mean(Y00), np.mean(Y11), np.mean(TE), np.mean(NDE), np.mean(NIE),
                     np.nanmean(PM)))
    except Exception as e:
        print('  ③ g-formula 失败:', type(e).__name__, e)
    if r2:
        rows.append(r2)

M = pd.DataFrame(rows)
M.to_csv(os.path.join(OUT, '_med_cs.csv'), index=False, encoding='utf-8-sig')
pd.DataFrame(gf_rows).to_csv(os.path.join(OUT, '_gf.csv'), index=False, encoding='utf-8-sig')
pd.DataFrame(patha).to_csv(os.path.join(OUT, '_patha.csv'), index=False, encoding='utf-8-sig')
pd.DataFrame(patha_tv).to_csv(os.path.join(OUT, '_patha_tv.csv'), index=False, encoding='utf-8-sig')
# 时序框架单独落盘（可追溯：中介列 = dep1）
MTV = M[M['variant'].fillna('') == 'temporal']
MTV.to_csv(os.path.join(OUT, '_med_tv.csv'), index=False, encoding='utf-8-sig')
# 并行列表长度自检
assert len(M) == len(rows), '中介结果行数与收集列表不一致'
assert set(M[M['variant'].fillna('') == 'temporal']['med_col'].dropna()) <= {'dep1'}, \
    '时序框架的中介列必须是 dep1'

# ---------------- 合并（对数尺度用 DL；中介比例用原始尺度）
print('\n' + '=' * 70)
print('# 合并：总效应 / 直接效应 / 间接效应 与 中介比例')
pool = []
M['variant'] = M.get('variant', pd.Series(index=M.index, dtype=object)).fillna('cross-sectional')
for tag in ['cross-sectional', 'temporal']:
    sub = M[(M['flag'] == 'ok') & (M['variant'] == tag)]
    if len(sub) < 2:
        print('  %s: k=%d 不足，不可合并' % (tag, len(sub))); continue
    # 并行列表自检 + 逐队列系数打印（变量名:系数）
    assert len(sub['cohort']) == len(sub['tot_hr']) == len(sub['tot_se']) == \
        len(sub['dir_hr']) == len(sub['dir_se']) == len(sub['ind_hr']) == len(sub['prop']), \
        '合并输入列长度不一致 (%s)' % tag
    print('  [pool] %s k=%d  逐队列系数（log 尺度）:' % (tag, len(sub)))
    for _c, _th, _dh in zip(sub['cohort'], sub['tot_hr'], sub['dir_hr']):
        print('        %-8s β_total=%.4f  β_direct=%.4f  β_indirect=%.4f'
              % (_c, np.log(_th), np.log(_dh), np.log(_th) - np.log(_dh)))
    pt = L.dl_meta(np.log(sub['tot_hr']), sub['tot_se'], tag + ' total')
    pd_ = L.dl_meta(np.log(sub['dir_hr']), sub['dir_se'], tag + ' direct')
    pi = L.dl_meta(np.log(sub['ind_hr']), sub['ind_se'], tag + ' indirect')
    pp = L.dl_meta_raw(sub['prop'], sub['prop_se'], tag + ' proportion')
    for nm, x in [('total HR', pt), ('direct HR', pd_), ('indirect HR', pi)]:
        print('  %-16s %-13s k=%d %.3f (%.3f-%.3f) I2=%.1f%%'
              % (tag, nm, x['k'], x['hr'], x['lo'], x['hi'], x['I2']))
        pool.append(dict(framework=tag, estimand=nm, k=x['k'], value=x['hr'], lo=x['lo'],
                         hi=x['hi'], I2=x['I2']))
    if pp:
        print('  %-16s %-13s k=%d %.1f%% (%.1f-%.1f) I2=%.1f%%'
              % (tag, 'mediated %', pp['k'], 100 * pp['est'], 100 * pp['lo'], 100 * pp['hi'], pp['I2']))
        pool.append(dict(framework=tag, estimand='mediated %', k=pp['k'], value=100 * pp['est'],
                         lo=100 * pp['lo'], hi=100 * pp['hi'], I2=pp['I2']))
    pool.append(dict(framework=tag, estimand='ratio of pooled (indirect/total)',
                     k=pt['k'], value=100 * (1 - pd_['loghr'] / pt['loghr']),
                     lo=np.nan, hi=np.nan, I2=np.nan))
GF = pd.DataFrame(gf_rows)
if len(GF) >= 2:
    print('  %-16s %-13s k=%d %.1f%%' % ('counterfactual', 'mediated %', len(GF), 100 * GF['PM'].mean()))
    pool.append(dict(framework='counterfactual', estimand='mediated %', k=len(GF),
                     value=100 * GF['PM'].mean(), lo=np.nan, hi=np.nan, I2=np.nan))
pd.DataFrame(pool).to_csv(os.path.join(OUT, '_med_pool.csv'), index=False, encoding='utf-8-sig')
print('\nDONE')
