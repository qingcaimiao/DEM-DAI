# -*- coding: utf-8 -*-
"""p21_replace_figs.py —— 把重绘的 Fig1–4 原位替换进 docx，并按新宽高比重算显示尺寸

- 只替换 word/media/imageN.png（N=1..4 对应 Fig1..Fig4，逐一核对 r:embed → rels）
- wp:extent / a:ext 的 cx 保持不变，cy = cx * (h/w) 以保证不被拉伸
- 不动其他任何部件；反斜杠计数核验
"""
import os
import re
import shutil
import struct
import zipfile

# Paths are parameterised: override with environment variables if needed.
_BASE = os.path.dirname(os.path.abspath(__file__))
DOCX = os.environ.get('DEM_DST_DOCX', os.path.join(_BASE, 'manuscript_v4.docx'))
FIG = os.environ.get('DEM_FIGDIR', os.path.join(_BASE, 'out', 'fig'))
SRC = [os.path.join(FIG, 'Fig%d.png' % i) for i in (1, 2, 3, 4)]


def png_size(p):
    b = open(p, 'rb').read(33)
    w, h = struct.unpack('>II', b[16:24])
    return w, h


z = zipfile.ZipFile(DOCX)
doc = z.read('word/document.xml').decode('utf8')
rels = z.read('word/_rels/document.xml.rels').decode('utf8')
rmap = dict(re.findall(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rels))
order = [rmap[b] for b in re.findall(r'<a:blip[^>]*r:embed="([^"]+)"', doc)]
assert order == ['media/image%d.png' % i for i in (1, 2, 3, 4)], order
print('图片顺序核对通过:', order)

# 新高度
new = {}
for i, p in enumerate(SRC, 1):
    w, h = png_size(p)
    new['image%d.png' % i] = (w, h)
    print('Fig%d.png %dx%d aspect=%.4f size=%.1f KB' % (i, w, h, w / h, os.path.getsize(p) / 1024))

# 重算 extent：按出现顺序
pat = re.compile(r'<wp:extent cx="(\d+)" cy="(\d+)"/>')
seq = [m for m in pat.finditer(doc)]
assert len(seq) == 4, len(seq)


def fix(m, kind):
    cx = int(m.group(1))
    return cx


out = doc
for i, m in enumerate(seq):
    cx = int(m.group(1))
    w, h = new['image%d.png' % (i + 1)]
    cy = int(round(cx * h / w))
    old_block = m.group(0)
    new_block = '<wp:extent cx="%d" cy="%d"/>' % (cx, cy)
    out = out.replace(old_block, new_block, 1)
    # 同步 a:ext（每个图一个）
    a_old = '<a:ext cx="%d" cy="%d"/>' % (cx, int(m.group(2)))
    a_new = '<a:ext cx="%d" cy="%d"/>' % (cx, cy)
    assert a_old in out, 'a:ext 未找到: %s' % a_old
    out = out.replace(a_old, a_new, 1)
    print('Fig%d 显示高度 %d -> %d (aspect %.4f)' % (i + 1, int(m.group(2)), cy, cx / cy))

assert out.count('\\') == 0, 'document.xml 中出现反斜杠'

tmp = DOCX + '.tmp'
zo = zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED)
for it in z.infolist():
    if it.filename == 'word/document.xml':
        zo.writestr(it, out.encode('utf8'))
    elif it.filename in ['word/media/image%d.png' % i for i in (1, 2, 3, 4)]:
        n = os.path.basename(it.filename)
        zo.write(SRC[int(n.replace('image', '').replace('.png', '')) - 1], it.filename)
    else:
        zo.writestr(it, z.read(it.filename))
zo.close()
z.close()
shutil.move(tmp, DOCX)

# 复核
z2 = zipfile.ZipFile(DOCX)
x2 = z2.read('word/document.xml').decode('utf8')
print('\n复核：tbl=%d  blip=%d  反斜杠=%d  段落=%d'
      % (x2.count('<w:tbl>'), x2.count('<a:blip'), x2.count('\\'),
         x2.count('<w:p ') + x2.count('<w:p>')))
for f in ['word/media/image%d.png' % i for i in (1, 2, 3, 4)]:
    print(f, len(z2.read(f)) // 1024, 'KB')
