# -*- coding: utf-8 -*-
"""p20_figures.py —— 按重建数字重绘 Fig 1–4（Arial, 400 dpi, 英文标注）
所有数值由脚本从 out/*.csv 读取或经 DerSimonian–Laird 现算，无手工转录。
输出：out/fig/Fig1.png … Fig4.png（尺寸与 docx 内原图宽高比一致，便于原位替换）
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import dem_lib as L

OUT = L.OUT
# 2026-10-14：输出目录与 DPI 可由环境变量覆盖（投稿用 600 dpi 单图，不影响 docx 内嵌 400 dpi 图）
FIG = os.environ.get('DEM_FIGDIR', os.path.join(OUT, 'fig'))
DPI = int(os.environ.get('DEM_FIGDPI', '400'))
# 输出文件名前缀：正文内嵌链用 Fig（p21_replace_figs 依赖 FigN.png），
# 投稿包槽位要求 FigureN.png。2026-10-14 因二者不一致，投稿包 Figures/ 长期停留在旧图。
FIGPRE = os.environ.get('DEM_FIGPREFIX', 'Fig')
MS = pd.read_csv(os.path.join(OUT, '_ms_numbers.csv'))
MS['key'] = MS['key'].astype(str).str.replace('^\ufeff', '', regex=True)
MS['value'] = pd.to_numeric(MS['value'], errors='coerce')
V = dict(zip(MS['key'], MS['value']))
os.makedirs(FIG, exist_ok=True)

# ================================================================ 图内字号整体放大
# 2026-10-14（由 PDF 渲染发现的缺陷）：图在 docx 中按 15.88 cm 放置，而画布宽 11.0–11.5 英寸，
# 缩放比约 0.55–0.65 → 7.2 pt 的标注在最终尺寸下只剩约 4.3 pt，印出来不可读。
# 解决：生成后统一把所有 Text 对象的字号 ×FONT_SCALE（只放大字号，不动几何与线宽），
# 使最终有效字号达到约 7 pt。几何不变，故不会改变面板布局，但需目视确认无重叠。
FONT_SCALE = 1.35


def scale_fonts(fig, k=FONT_SCALE):
    n = 0
    for o in fig.findobj(match=lambda x: hasattr(x, 'get_fontsize') and hasattr(x, 'set_fontsize')):
        try:
            o.set_fontsize(float(o.get_fontsize()) * k)
            n += 1
        except Exception:
            pass
    print('      [font] 已放大 %d 个文本对象的字号 ×%.2f' % (n, k))
    return n

plt.rcParams.update({
    'font.family': 'Arial', 'font.size': 9, 'axes.linewidth': 0.8,
    'axes.edgecolor': '#333333', 'axes.labelcolor': '#111111',
    'text.color': '#111111', 'xtick.color': '#333333', 'ytick.color': '#333333',
    'figure.facecolor': 'white', 'axes.facecolor': 'white',
    'savefig.facecolor': 'white', 'savefig.dpi': DPI, 'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.02,
})

BLUE, TEAL, ORANGE, RED, GREEN, GREY = '#2c6fbb', '#3a9ab5', '#e08b2e', '#c0392b', '#4b8b3b', '#9aa5b1'
CO = L.COHORTS
CN = {'CHARLS': 'CHARLS\n(China)', 'ELSA': 'ELSA\n(England)', 'HRS': 'HRS\n(USA)',
      'KLoSA': 'KLoSA\n(Korea)', 'MHAS': 'MHAS\n(Mexico)', 'SHARE': 'SHARE\n(Europe)'}
CN1 = {'CHARLS': 'CHARLS (China)', 'ELSA': 'ELSA (England)', 'HRS': 'HRS (USA)',
       'KLoSA': 'KLoSA (Korea)', 'MHAS': 'MHAS (Mexico)', 'SHARE': 'SHARE (Europe)'}


def ci(hr, se):
    return float(hr) * np.exp(-1.96 * se), float(hr) * np.exp(1.96 * se)


def forest(ax, labels, hrs, los, his, colors, xlabel, xlim, title=None,
           marker='o', msize=5, lw=1.2, ref=1.0):
    """横向森林图：labels 自上而下。"""
    y = np.arange(len(labels))[::-1]
    for i, (h, lo, hi) in enumerate(zip(hrs, los, his)):
        ax.plot([lo, hi], [y[i], y[i]], color=colors[i], lw=lw, solid_capstyle='butt', zorder=2)
        ax.plot([h], [y[i]], marker=marker, ms=msize, color=colors[i], zorder=3,
                markeredgecolor='white', markeredgewidth=0.4)
    if ref is not None:
        ax.axvline(ref, color='#555555', lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8.2)
    ax.set_ylim(-0.8, len(labels) - 0.2)
    ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel, fontsize=8.5)
    ax.tick_params(axis='x', labelsize=8)
    ax.grid(axis='x', color='#e8e8e8', lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    for s in ('top', 'right', 'left'):
        ax.spines[s].set_visible(False)
    if title:
        ax.set_title(title, fontsize=9.5, loc='left', fontweight='bold', pad=6)
    return y


class FP(object):
    """森林图行收集器：add(...) 后 drop_blank() 再 forest()。

    7 个并行列表（rows/hrs/los/his/cols/pool/mk）必须始终等长；
    每次 add/gap 后立即自检，避免行标签与系数错位（用户硬性要求）。
    """

    def __init__(self):
        self.rows, self.hrs, self.los, self.his = [], [], [], []
        self.cols, self.pool, self.mk = [], [], []

    def _check(self):
        L.pa(rows=self.rows, hrs=self.hrs, los=self.los, his=self.his,
             cols=self.cols, pool=self.pool, mk=self.mk)

    def add(self, label, hr, lo, hi, color, pooled=False, marker='o'):
        self.rows.append(label); self.hrs.append(hr); self.los.append(lo); self.his.append(hi)
        self.cols.append(color); self.pool.append(pooled); self.mk.append(marker)
        self._check()

    def gap(self):
        self.rows.append(''); self.hrs.append(np.nan); self.los.append(np.nan)
        self.his.append(np.nan); self.cols.append('white'); self.pool.append(False); self.mk.append(None)
        self._check()

    def drop_blank(self):
        idx = [i for i, h in enumerate(self.hrs) if np.isfinite(h)]
        self.rows = [self.rows[i] for i in idx]; self.hrs = [self.hrs[i] for i in idx]
        self.los = [self.los[i] for i in idx]; self.his = [self.his[i] for i in idx]
        self.cols = [self.cols[i] for i in idx]; self.pool = [self.pool[i] for i in idx]
        self.mk = [self.mk[i] for i in idx]
        self._check()

    def dump(self, tag):
        """打印「变量名 + 系数」，供人工核对行标签是否与系数对上。"""
        print('      [FP:%s] k=%d' % (tag, len(self.rows)))
        for i, r in enumerate(self.rows):
            print('        %-42s HR=%.4f (%.4f-%.4f) pooled=%s'
                  % (r[:42], self.hrs[i], self.los[i], self.his[i], self.pool[i]))

    def draw(self, ax, xlabel, xlim, title=None, ref=1.0, marker='o', msize=5):
        y = forest(ax, self.rows, self.hrs, self.los, self.his, self.cols, xlabel, xlim,
                   title=title, ref=ref, marker=marker, msize=msize)
        for i in range(len(self.rows)):
            if self.pool[i]:
                ax.plot([self.hrs[i]], [y[i]], marker='D', ms=5.6, color=RED, zorder=4,
                        markeredgecolor='white', markeredgewidth=0.4)
            elif self.mk[i] not in (None, marker):
                ax.plot([self.hrs[i]], [y[i]], marker=self.mk[i], ms=5.2, color=self.cols[i],
                        zorder=4, markeredgecolor='white', markeredgewidth=0.4)
        return y


def assert_inside_boxes(fig, pairs, tag):
    """布局断言：每个文字对象的包围盒必须落在其所属盒子内（含 0.5 px 容差）。

    pairs: [(FancyBboxPatch, [Text, ...]), ...]
    2026-10-14 新增：此前 Figure 1 面板 A 的文字多次越框（标签被放大后装不下、
    注释被画到框外），肉眼看一次只能抓一次，故改为脚本断言，改图时立即报错。
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    bad = []
    for pat, texts in pairs:
        pb = pat.get_window_extent(r)
        for t in texts:
            tb = t.get_window_extent(r)
            if (tb.x0 < pb.x0 - 0.5 or tb.x1 > pb.x1 + 0.5
                    or tb.y0 < pb.y0 - 0.5 or tb.y1 > pb.y1 + 0.5):
                bad.append('%r 文字(%.1f,%.1f)-(%.1f,%.1f) 越出盒子(%.1f,%.1f)-(%.1f,%.1f)'
                           % (t.get_text()[:28], tb.x0, tb.y0, tb.x1, tb.y1,
                              pb.x0, pb.y0, pb.x1, pb.y1))
    if bad:
        raise AssertionError('[%s] 共 %d 处文字越框：\n  - %s' % (tag, len(bad), '\n  - '.join(bad)))
    print('      [layout] %s：%d 个文字对象全部在框内 ✓' % (tag, sum(len(v) for _, v in pairs)))


def annot(ax, x, y, txt, color='#111111', size=7.6, ha='left', va='center'):
    ax.annotate(txt, (x, y), fontsize=size, color=color, ha=ha, va=va,
                xycoords=('axes fraction', 'data'), annotation_clip=False)


# =============================================================== Fig 1
FL = pd.read_csv(os.path.join(OUT, '_flow.csv'))
T1 = pd.read_csv(os.path.join(OUT, 'Table1.csv'))

fig = plt.figure(figsize=(11.5, 11.1))
gs = fig.add_gridspec(1, 2, width_ratios=[1.0, 1.35], wspace=0.16)
axA = fig.add_subplot(gs[0, 0])
axA.set_xlim(0, 1); axA.set_ylim(0, 1); axA.axis('off')

STEP_COL = [BLUE, BLUE, BLUE, BLUE, BLUE, RED]
_flow_pairs = []
ys = np.linspace(0.930, 0.160, 6)   # 底部留出 0–0.11 的空白带放注释
h = 0.098
for i, r in FL.iterrows():
    y0 = ys[i] - h / 2
    face = '#eaf1fa' if i < 5 else '#fdecea'
    edge = '#2c6fbb' if i < 5 else '#c0392b'
    box = FancyBboxPatch((0.01, y0), 0.70, h, boxstyle='round,pad=0.005,rounding_size=0.010',
                         linewidth=1.0, edgecolor=edge, facecolor=face, zorder=3)
    axA.add_patch(box)
    lab = (r['label'].replace('Survived to and assessed during follow-up',
                             'Survived and assessed at follow-up')
           .replace('Baseline cognitive assessment available',
                    'Cognitive assessment available'))
    _t_lab = axA.text(0.022, y0 + h * 0.70, lab, fontsize=6.2, va='center', color='#111111')
    _t_n = axA.text(0.022, y0 + h * 0.27, 'N = %s' % format(int(r['n']), ','), fontsize=8.8,
                    va='center', color=edge, fontweight='bold')
    _flow_pairs.append((box, [_t_lab, _t_n]))
    if i:
        axA.annotate('', xy=(0.36, y0 + h + 0.010), xytext=(0.36, ys[i - 1] - h - 0.010),
                     arrowprops=dict(arrowstyle='-|>', color='#666666', lw=1.0,
                                     shrinkA=0, shrinkB=0), zorder=2)
        axA.text(0.745, (ys[i - 1] - h + y0) / 2, '− %s' % format(int(r['excluded']), ','),
                 fontsize=7.4, va='center', ha='left', color=RED, fontweight='bold')
axA.text(0.5, 1.035, 'A  Participant flow and sample selection', fontsize=10.5,
         fontweight='bold', ha='center', va='top')
tot = int(T1.groupby('cohort')['events'].sum().sum())
py = T1.groupby('cohort')['py'].sum().sum()
axA.text(0.022, 0.100, '%s cases · %s person-years\nmedian follow-up 9 years'
         % (format(tot, ','), format(int(round(py)), ',')), fontsize=6.6,
         color='#333333', va='top')

axB = fig.add_subplot(gs[0, 1])
order = ['CHARLS', 'ELSA', 'HRS', 'KLoSA', 'MHAS', 'SHARE']
cols = ['#8fb8de', '#5b93cf', '#e8b96a', '#d98b3a']
y = np.arange(len(order))[::-1]
for i, co in enumerate(order):
    s = T1[T1['cohort'].str.startswith(co)]
    tot_n = s['n'].sum()
    left = 0.0
    for lv in range(4):
        v = float(s[s['dai'] == lv]['n'].iloc[0])
        pct = 100 * v / tot_n
        axB.barh(y[i], pct, left=left, height=0.62, color=cols[lv],
                 edgecolor='white', linewidth=0.8)
        if pct > 4:
            axB.text(left + pct / 2, y[i], '%.0f' % pct, ha='center', va='center',
                     fontsize=7.6, color='#1a1a1a')
        left += pct
    evc = int(s['events'].sum())
    axB.text(101.5, y[i], 'n = %s\n%s events' % (format(int(tot_n), ','), format(evc, ',')),
             fontsize=7.6, va='center', ha='left', color='#333333')
axB.set_yticks(y)
axB.set_yticklabels([CN[c] for c in order], fontsize=8.4)
axB.set_xlim(0, 100); axB.set_ylim(-0.7, len(order) - 0.3)
axB.set_xlabel('Proportion of participants (%)', fontsize=8.6)
axB.set_title('B  Distribution of the DAI by cohort', fontsize=10.5, loc='left',
              fontweight='bold', pad=8)
handles = [Rectangle((0, 0), 1, 1, color=cols[i]) for i in range(4)]
axB.legend(handles, ['DAI = 0', 'DAI = 1', 'DAI = 2', 'DAI = 3'], ncol=4, fontsize=8,
           frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.085))
for s in ('top', 'right', 'left'):
    axB.spines[s].set_visible(False)
scale_fonts(fig)
assert_inside_boxes(fig, _flow_pairs, 'Fig1 面板A 流程盒')
fig.savefig(os.path.join(FIG, FIGPRE + '1.png'))
plt.close(fig)

# =============================================================== Fig 2
M = pd.read_csv(os.path.join(OUT, '_m1234.csv'))
POOL = pd.read_csv(os.path.join(OUT, '_pool.csv'))
T2B = pd.read_csv(os.path.join(OUT, 'Table2B.csv'))
P2B = pd.read_csv(os.path.join(OUT, '_pool_2b.csv'))
T3C = pd.read_csv(os.path.join(OUT, 'Table3C.csv'))
P3C = pd.read_csv(os.path.join(OUT, '_pool_3c.csv'))
MP = pd.read_csv(os.path.join(OUT, '_med_pool.csv'))
MS_ = pd.read_csv(os.path.join(OUT, '_med_sens_pool.csv'))

fig = plt.figure(figsize=(11.5, 12.2))
gs = fig.add_gridspec(2, 2, hspace=0.62, wspace=0.46)

# ---- A: per-cohort M2 + pooled M1-M4
axA = fig.add_subplot(gs[0, 0])
f = FP()
for co in CO:
    r = M[(M['model'] == 'M2') & (M['cohort'] == co)].iloc[0]
    lo, hi = ci(r['hr'], r['se'])
    f.add(CN1[co], r['hr'], lo, hi, BLUE)
f.gap()
MODCOL = {'M1': '#9dc3e6', 'M2': BLUE, 'M3': '#1f4e79', 'M4': TEAL}
for m in ['M1', 'M2', 'M3', 'M4']:
    p = POOL[POOL['label'] == m].iloc[0]
    f.add('Pooled %s' % m, p['hr'], p['lo'], p['hi'], RED, pooled=True)
f.drop_blank()
y = f.dump('Fig2A')
f.draw(axA, 'Hazard ratio (95 % CI, log scale)', (0.9, 2.2),
           title='A  Main analysis: DAI per additional syndrome')
axA.text(0.0, -0.165, 'Cohort-specific M2 (upper block); pooled M1–M4 (lower block).\n'
                      'M1 unadjusted; M2 covariate-adjusted; M3 further adjusted for urban–rural residence;\n'
                      'M4 further adjusted for grip strength and physical activity',
         transform=axA.transAxes, fontsize=7.2, color='#555555', va='top')

# ---- B: categorical gradient
axB = fig.add_subplot(gs[0, 1])
f = FP()
for co in CO:
    r = T2B[(T2B['level'] == '3 vs 0') & (T2B['cohort'].str.startswith(co))].iloc[0]
    lo, hi = ci(r['hr'], r['se'])
    f.add(CN1[co], r['hr'], lo, hi, '#4a80b8')
f.gap()
LVCOL = {'1 vs 0': '#9dc3e6', '2 vs 0': '#4a80b8', '3 vs 0': '#1f4e79'}
for lv in ['1 vs 0', '2 vs 0', '3 vs 0']:
    p = P2B[P2B['level'] == lv].iloc[0]
    f.add('Pooled: %s syndrome%s' % (lv[0], '' if lv[0] == '1' else 's'), p['hr'], p['lo'], p['hi'],
          RED, pooled=True)
f.drop_blank()
f.dump('Fig2B')
y = f.draw(axB, 'Hazard ratio (95 % CI, log scale)', (0.8, 3.2),
           title='B  Categorical gradient by number of syndromes')
for i, r in enumerate(f.rows):
    if r.startswith('Pooled'):
        lv = '3 vs 0' if '3 syndrome' in r else ('2 vs 0' if '2 syndrome' in r else '1 vs 0')
        axB.text(2.72, y[i] + 0.30, 'I² = %.0f %%' % float(P2B[P2B['level'] == lv]['I2'].iloc[0]),
                 fontsize=7.4, va='bottom', color='#555555')
axB.text(0.0, -0.165, 'Upper block: cohort-specific 3 vs 0 syndromes; lower block: pooled contrasts.',
         transform=axB.transAxes, fontsize=7.2, color='#555555', va='top')

# ---- C: eight categories (pooled)
axC = fig.add_subplot(gs[1, 0])
CAT_ORDER = ['All three', 'Disability+Depression', 'Multimorbidity+Depression',
             'Depression only', 'Disability only', 'Disability+Multimorbidity',
             'Multimorbidity only']
CATLAB = {'All three': 'All three syndromes', 'Disability+Depression': 'Disability + depression',
          'Multimorbidity+Depression': 'Multimorbidity + depression',
          'Depression only': 'Depression only', 'Disability only': 'Disability only',
          'Disability+Multimorbidity': 'Disability + multimorbidity',
          'Multimorbidity only': 'Multimorbidity only'}
f = FP()
for cat in CAT_ORDER:
    p = P3C[P3C['category'] == cat].iloc[0]
    f.add(CATLAB[cat], p['hr'], p['lo'], p['hi'], RED, pooled=True)
f.add('None of the three (reference)', 1.0, 1.0, 1.0, '#444444')
f.drop_blank()
y = f.dump('Fig2C')
f.draw(axC, 'Hazard ratio (95 % CI, log scale)', (0.6, 2.2),
           title='C  Joint distribution of the three syndromes')
axC.text(0.0, -0.130, 'Pooled cohort-specific estimates, random effects. I² is reported in Table 3C.',
         transform=axC.transAxes, fontsize=7.2, color='#555555', va='top')

# ---- D: mediation
axD = fig.add_subplot(gs[1, 1])
f = FP()
fw = MP[MP['estimand'] == 'mediated %']
FWLAB = {'cross-sectional': 'Cross-sectional difference', 'temporal': 'Temporally ordered difference',
         'counterfactual': 'Counterfactual g-formula'}
for _, r in fw.iterrows():
    lo = r['lo'] if pd.notna(r['lo']) else r['value']
    hi = r['hi'] if pd.notna(r['hi']) else r['value']
    f.add(FWLAB[r['framework']], r['value'], lo, hi, BLUE, pooled=True, marker='D')
f.gap()
SPECS = [('two-wave washout', 'Two-wave washout (from w2)'),
         ('incident depression', 'Mediator: incident depression'),
         ('with interaction', 'With exposure-by-mediator interaction'),
         ('multimorbidity only', 'Exposure: multimorbidity only')]
for key, lab in SPECS:
    r = MS_[MS_['spec'] == key].iloc[0]
    f.add('    ' + lab, r['pct'], r['lo'], r['hi'], '#7fa8d0', marker='o')
f.drop_blank()
f.dump('Fig2D')
y = f.draw(axD, 'Proportion mediated by depression (%)', (0, 45), ref=None, marker=None,
           title='D  Proportion mediated by depression')
for i, mk in enumerate(f.mk):
    axD.plot([f.hrs[i]], [y[i]], marker=mk, ms=6.0 if mk == 'D' else 5.2, color=f.cols[i],
             zorder=4, markeredgecolor='white', markeredgewidth=0.4)
band_lo = float(V['med_pct_min']); band_hi = float(V['med_pct_max'])
assert band_lo < band_hi, '收敛带上下限顺序错误: %.2f %.2f' % (band_lo, band_hi)
axD.axvspan(band_lo, band_hi, color='#f2c14e', alpha=0.22, zorder=0)
axD.text((band_lo + band_hi) / 2, len(f.rows) - 0.4,
         'Convergence band %.1f\u2013%.1f %%' % (band_lo, band_hi), fontsize=7.6,
         ha='center', color='#8a6d1f', va='bottom')
axD.text(0.0, -0.135, 'Diamonds: pooled cohort-specific proportions under three identification frameworks.\n'
                      'Circles: four further specifications. I² = %s %% for the temporally ordered framework.'
                      % ('%.1f' % float(V['med_tp_pct_I2'])),
         transform=axD.transAxes, fontsize=7.2, color='#555555', va='top')
scale_fonts(fig)
fig.savefig(os.path.join(FIG, FIGPRE + '2.png'))
plt.close(fig)

# =============================================================== Fig 3
TV = pd.read_csv(os.path.join(OUT, '_tv_pool.csv'))
TVc = pd.read_csv(os.path.join(OUT, '_tv.csv'))
DP = pd.read_csv(os.path.join(OUT, '_traj_dist_pool_summary.csv'))
TP = pd.read_csv(os.path.join(OUT, '_traj_pool.csv'))
TR = pd.read_csv(os.path.join(OUT, '_traj.csv'))
LP = pd.read_csv(os.path.join(OUT, '_level_pool.csv'))

fig = plt.figure(figsize=(11.5, 14.3))
gs = fig.add_gridspec(2, 2, hspace=0.36, wspace=0.30)

# ---- A: time-varying
axA = fig.add_subplot(gs[0, 0])
f = FP()
VCOL = {'time-varying (1 wave)': '#2c6fbb', 'lagged (2 waves)': '#3a9ab5',
        'cumulative mean': '#4b8b3b'}
VP = {'time-varying (1 wave)': 'time-varying (1 wave)', 'lagged (2 waves)': 'lagged (2 waves)',
      'cumulative mean': 'cumulative mean'}
for v in ['time-varying (1 wave)', 'lagged (2 waves)', 'cumulative mean']:
    for co in CO:
        r = TVc[(TVc['variant'] == v) & (TVc['cohort'] == co)]
        if len(r):
            r = r.iloc[0]
            lo, hi = ci(r['hr'], r['se'])
            f.add('    %s' % CN1[co], r['hr'], lo, hi, VCOL[v])
    p = TV[TV['variant'] == v].iloc[0]
    f.add('Pooled: %s' % v, p['hr'], p['lo'], p['hi'], RED, pooled=True)
f.drop_blank()
f.dump('Fig3A')
f.draw(axA, 'Hazard ratio per additional syndrome', (0.9, 2.2),
       title='A  Time-varying exposure and the exposure–outcome gap')

# ---- B: pooled density by trajectory
axB = fig.add_subplot(gs[0, 1])
TRAJ = ['persistently low', 'remitted', 'incident', 'persistently affected']
TLAB = ['Persistently low\n(0→0)', 'Remitted\n(1→0)', 'Incident\n(0→1)',
        'Persistently affected\n(1→1)']
TCOL = [GREEN, TEAL, ORANGE, RED]
dens = [float(DP[DP['traj'] == t]['density'].iloc[0]) for t in TRAJ]
ns = [int(DP[DP['traj'] == t]['n'].iloc[0]) for t in TRAJ]
evs = [int(DP[DP['traj'] == t]['ev'].iloc[0]) for t in TRAJ]
L.pa(dens=dens, ns=ns, evs=evs)
print('      [Fig3B] ' + '; '.join('%s 密度=%.1f (n=%d, 事件=%d)' % (t, d, nn, e)
                              for t, d, nn, e in zip(TRAJ, dens, ns, evs)))
bars = axB.bar(np.arange(4), dens, color=TCOL, width=0.62, edgecolor='white', linewidth=0.8)
for i, (d, n, e) in enumerate(zip(dens, ns, evs)):
    axB.text(i, d + 0.5, '%.1f' % d, ha='center', fontsize=8.6, fontweight='bold')
    # 字号放大后横排会溢出窄柱体，改为竖排（rotation=90）彻底消除横向溢出
    axB.text(i, 0.030 * max(dens), 'n = %s\n%s events' % (format(n, ','), format(e, ',')),
             ha='center', fontsize=6.6, color='white', va='bottom', rotation=90)
axB.set_xticks(np.arange(4)); axB.set_xticklabels(TLAB, fontsize=7.8)
axB.set_ylabel('Dementia incidence density (per 1,000 person-years)', fontsize=8.4)
axB.set_ylim(0, max(dens) * 1.18)
axB.set_title('B  Dementia incidence density by exposure trajectory', fontsize=9.5,
              loc='left', fontweight='bold', pad=6)
axB.grid(axis='y', color='#ececec', lw=0.6); axB.set_axisbelow(True)
for s in ('top', 'right'):
    axB.spines[s].set_visible(False)
axB.tick_params(axis='x', length=0, pad=4)

# ---- C: trajectory HR
axC = fig.add_subplot(gs[1, 0])
f = FP()
TORD = ['incident', 'remitted', 'persistently affected']
TNAME = {'incident': 'Incident 0→1', 'remitted': 'Remitted 1→0',
         'persistently affected': 'Persistently affected 1→1'}
for t in TORD:
    for co in CO:
        r = TR[(TR['traj'] == t) & (TR['cohort'] == co)]
        if len(r):
            r = r.iloc[0]
            lo, hi = ci(r['hr'], r['se'])
            f.add('    %s' % CN1[co], r['hr'], lo, hi, GREY)
    p = TP[TP['traj'] == t].iloc[0]
    f.add('Pooled: %s' % TNAME[t], p['hr'], p['lo'], p['hi'], RED, pooled=True)
    if t != 'persistently affected':
        f.gap()
f.add('Persistently low 0→0 (reference)', 1.0, 1.0, 1.0, '#444444')
f.drop_blank()
f.dump('Fig3C')
f.draw(axC, 'Hazard ratio relative to persistently low', (0.9, 3.0),
       title='C  Trajectory classes (red diamond = pooled)')
axC.text(0.0, -0.115, 'Upper block: cohort-specific estimates; lower block: pooled estimates.',
         transform=axC.transAxes, fontsize=7.2, color='#555555', va='top')

# ---- D: level vs change
axD = fig.add_subplot(gs[1, 1])
ORD = [('baseline level', 'd0', 'Baseline level (alone)', BLUE),
       ('follow-up level', 'd1', 'Follow-up level (alone)', TEAL),
       ('change', 'dchg', 'Change, Δ (alone)', GREY),
       ('baseline+follow-up', 'd0', 'Baseline level (mutually adjusted)', BLUE),
       ('baseline+follow-up', 'd1', 'Follow-up level (mutually adjusted)', TEAL)]
f = FP()
for mod, term, lab, c in ORD:
    r = LP[(LP['model'] == mod) & (LP['term'] == term)].iloc[0]
    f.add(lab, r['hr'], r['lo'], r['hi'], c)
f.drop_blank()
f.dump('Fig3D')
y = f.draw(axD, 'Hazard ratio per additional syndrome', (0.9, 1.7),
           title='D  Risk tracks current level, not rate of change')
for i, (mod, term, lab, c) in enumerate(ORD):
    r = LP[(LP['model'] == mod) & (LP['term'] == term)].iloc[0]
    axD.text(1.72, y[i], 'I² = %.0f %%' % r['I2'], fontsize=7.4, va='center', color='#555555')
axD.text(0.0, -0.135, 'Δ cannot be entered jointly with the follow-up level, with which it is collinear.',
         transform=axD.transAxes, fontsize=7.2, color='#555555', va='top')
scale_fonts(fig)
fig.savefig(os.path.join(FIG, FIGPRE + '3.png'))
plt.close(fig)

# =============================================================== Fig 4
SUB = pd.read_csv(os.path.join(OUT, '_sub.csv'))
INT = pd.read_csv(os.path.join(OUT, '_int.csv'))
MODS = [('Age group', ['<65', '65-74', '>=75'], ['< 65', '65–74', '≥ 75']),
        ('Sex', ['0.0', '1.0'], ['Women', 'Men']),
        ('Education', ['1.0', '2.0', '3.0'], ['Low', 'Medium', 'High']),
        ('Baseline cognition', ['low', 'high'], ['Below median', 'Above median']),
        ('Marital status', ['0.0', '1.0'], ['Not partnered', 'Partnered']),
        ('BMI', ['<25', '25-29.9', '>=30'], ['< 25', '25–29.9', '≥ 30'])]
fig, axes = plt.subplots(2, 3, figsize=(11.0, 11.3))
fig.subplots_adjust(hspace=0.42, wspace=0.58, left=0.06, right=0.985, top=0.92, bottom=0.07)
for ax, (mod, keys, labs) in zip(axes.ravel(), MODS):
    iv = INT[INT['modifier'] == mod].iloc[0]
    rows, hrs, los, his, cols_, ann = [], [], [], [], [], []
    for k, lab in zip(keys, labs):
        r = SUB[(SUB['modifier'] == mod) & (SUB['stratum'].astype(str) == k)]
        if len(r):
            r = r.iloc[0]
            lo, hi = float(r['lo']), float(r['hi'])
            rows.append(lab); hrs.append(r['hr']); los.append(lo); his.append(hi)
            cols_.append(BLUE)
            ann.append('HR %.2f (%.2f–%.2f)\nn = %s  ·  events = %s'
                       % (r['hr'], lo, hi, format(int(r['n']), ','), format(int(r['ev']), ',')))
    L.pa(rows=rows, hrs=hrs, los=los, his=his, cols_=cols_, ann=ann)
    L.print_coef(rows, hrs, 'Fig4/%s HR' % mod)
    y = forest(ax, rows, hrs, los, his, cols_, 'Hazard ratio (per additional syndrome)',
               (0.9, 3.15))
    ptxt = '< 0.001' if iv['p_int'] < 0.001 else '= %.3f' % iv['p_int']
    ax.set_title('%s    ·    P interaction %s' % (mod, ptxt), fontsize=9.2,
                 loc='left', fontweight='bold', pad=6)
    for i in range(len(rows)):
        ax.text(1.78, y[i], ann[i], fontsize=7.0, va='center', color='#333333')
fig.suptitle('Subgroup and interaction analyses', fontsize=11, fontweight='bold', x=0.02, ha='left')
fig.text(0.02, 0.012, 'Pooled HR within each stratum by random effects; the covariate set of the stratifying '
                      'variable itself was removed from that stratum. Dashed line: HR = 1.',
         fontsize=7.4, color='#555555')
scale_fonts(fig)
fig.savefig(os.path.join(FIG, FIGPRE + '4.png'))
plt.close(fig)

for f in sorted(os.listdir(FIG)):
    if f.endswith('.png'):
        from PIL import Image
        im = Image.open(os.path.join(FIG, f))
        print(f, im.size, 'aspect=%.3f' % (im.size[0] / im.size[1]))
print('done')
