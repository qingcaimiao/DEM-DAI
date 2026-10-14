# -*- coding: utf-8 -*-
import io
p = 'p20_figures.py'
s = io.open(p, encoding='utf8').read()
n = 0

o = "bars = axB.bar(np.arange(4), dens, color=TCOL, width=0.62, edgecolor='white', linewidth=0.8)"
add = ("L.pa(dens=dens, ns=ns, evs=evs)\n"
       "print('      [Fig3B] ' + '; '.join('%s 密度=%.1f (n=%d, 事件=%d)' % (t, d, nn, e)\n"
       "                              for t, d, nn, e in zip(TRAJ, dens, ns, evs)))\n")
if 'L.pa(dens=dens' not in s:
    assert o in s
    s = s.replace(o, add + o, 1); n += 1

o2 = ("    y = forest(ax, rows, hrs, los, his, cols_, 'Hazard ratio (per additional syndrome)',\n"
      "               (0.9, 3.15))")
if 'L.pa(rows=rows, hrs=hrs, los=los, his=his, cols_=cols_, ann=ann)' not in s:
    assert o2 in s
    s = s.replace(o2,
                  "    L.pa(rows=rows, hrs=hrs, los=los, his=his, cols_=cols_, ann=ann)\n"
                  "    L.print_coef(rows, hrs, 'Fig4/%s HR' % mod)\n" + o2, 1); n += 1

for tag, anchor in [
    ('Fig2A', "f.draw(axA, 'Hazard ratio (95 % CI, log scale)', (0.9, 2.2),"),
    ('Fig2B', "y = f.draw(axB, 'Hazard ratio (95 % CI, log scale)', (0.8, 3.2),"),
    ('Fig2C', "f.draw(axC, 'Hazard ratio (95 % CI, log scale)', (0.6, 2.2),"),
    ('Fig2D', "y = f.draw(axD, 'Proportion mediated by depression (%)', (0, 45), ref=None, marker=None,"),
    ('Fig3A', "f.draw(axA, 'Hazard ratio per additional syndrome', (0.9, 2.2),"),
    ('Fig3C', "f.draw(axC, 'Hazard ratio relative to persistently low', (0.9, 3.0),"),
    ('Fig3D', "y = f.draw(axD, 'Hazard ratio per additional syndrome', (0.9, 1.7),"),
]:
    if ("f.dump('%s')" % tag) in s:
        continue
    assert anchor in s, anchor[:60]
    s = s.replace(anchor, "f.dump('%s')\n" % tag + anchor, 1); n += 1

io.open(p, 'w', encoding='utf8').write(s)
print('p20 加固完成，新增 %d 处' % n)
