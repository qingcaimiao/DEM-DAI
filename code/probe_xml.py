# -*- coding: utf-8 -*-
import zipfile, re, os
P = r'D:/桌面/AIzuopin/痴呆/稿件正文_修订版_20261012.docx'
z = zipfile.ZipFile(P)
x = z.read('word/document.xml').decode('utf8')
body = x.split('<w:body>')[1].split('</w:body>')[0]
blocks = re.findall(r'<w:tbl>.*?</w:tbl>|<w:p\b.*?</w:p>|<w:p\b[^>]*/>', body, re.S)
out = []
out.append('=== body para 61 ===')
out.append(blocks[61][:700])
out.append('=== legend para 100 ===')
out.append(blocks[100][:500])
out.append('=== para 82 ===')
out.append(blocks[82][:400])
out.append('=== tbl 83 pr ===')
out.append(blocks[83][:1400])
out.append('=== styles TableGrid? ===')
s = z.read('word/styles.xml').decode('utf8')
out.append('TableGrid present: %s' % ('TableGrid' in s))
out.append('docDefaults:')
m = re.search(r'<w:docDefaults>.*?</w:docDefaults>', s, re.S)
out.append(m.group(0)[:900] if m else 'none')
os.makedirs(r'D:/workbuddygongzuokongjian/2026-10-12-21-32-15/dem_pipeline/out', exist_ok=True)
open(r'D:/workbuddygongzuokongjian/2026-10-12-21-32-15/dem_pipeline/out/_probe_xml.txt', 'w',
     encoding='utf8').write('\n'.join(out))
print('ok')
