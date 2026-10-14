# -*- coding: utf-8 -*-
"""p32_codepoint_scan.py —— 投稿前"非常规码点"扫描（用户硬性检查项）

背景：曾出现把作者上标分隔符写成 U+1427（加拿大原住民音节字符）的事故；
投稿前必须做一次**非常规码点扫描**，非白名单字符逐个人工判定。

白名单：ASCII 可打印 / en-em dash / 弯引号 / ± × ° 上标 / ≥ ≤ − χ² Δ κ → /
        Greek 区（β κ χ Δ）/ 段落符 ¶ / § / 数学符号 ∈ ′ / CJK 及其标点 / 全角
输出：out/_codepoint_scan.txt（非白名单字符逐条列出，含文件与上下文）
"""
import os
import re
import sys
import zipfile
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')
D = r'D:/桌面/AIzuopin/痴呆'
TARGETS = [
    os.environ.get('DEM_DOCX', os.path.join(D, '稿件正文_修订稿_v4_20261013.docx')),
    os.path.join(D, '附加材料_Additional_file_1_20261013.docx'),
    os.path.join(D, '附加材料_Additional_file_2_STROBE_20261013.docx'),
    os.path.join(D, 'SupplementaryMethods_修订_20261013.md'),
    os.path.join(D, 'STROBE_checklist_修订_20261013.md'),
]

RANGES = [
    (0x0020, 0x007E),   # ASCII 可打印
    (0x00A7, 0x00A7),   # §
    (0x00B0, 0x00B1),   # ° ±
    (0x00B6, 0x00B7),   # ¶ ·
    (0x00B9, 0x00B9),
    (0x00B2, 0x00B3),   # ² ³
    (0x00D7, 0x00D7),   # ×
    (0x0370, 0x03FF),   # Greek（β κ χ Δ μ）
    (0x2010, 0x2014),   # ‐ ‑ ‒ – —
    (0x2018, 0x2019),   # ‘ ’
    (0x201C, 0x201D),   # “ ”
    (0x2020, 0x2026),   # † ‡ … （省略号）
    (0x2032, 0x2033),   # ′ ″（M(x′)）
    (0x2039, 0x203A),
    (0x2070, 0x207F),   # 上标（10⁻⁴ 的 ⁻）
    (0x2080, 0x208E),   # 下标
    (0x2190, 0x2192),   # ← → （含制表符）
    (0x2208, 0x2208),   # ∈
    (0x2212, 0x2212),   # −
    (0x2264, 0x2265),   # ≤ ≥
    (0x25A0, 0x25FF),   # 几何/方块符号（项目符号 ▪ ● 等）
    (0x3000, 0x303F),   # CJK 标点
    (0x4E00, 0x9FFF),   # CJK 统一表意
    (0xFF00, 0xFFEF),   # 全角
    (0x00C0, 0x00D6),   # 拉丁字母变音符（Østbye / Börsch-Supan 等作者名）
    (0x00D8, 0x00F6),   # 同上（跳过 0x00D7 ×）
    (0x00F8, 0x024F),   # 同上（跳过 0x00F7 ÷）
    (0x0009, 0x000A),
]
OK = set()
for a, b in RANGES:
    OK |= set(range(a, b + 1))


def texts(path):
    if path.lower().endswith('.docx'):
        z = zipfile.ZipFile(path)
        for n in z.namelist():
            if n.startswith('word/') and n.endswith('.xml'):
                raw = z.read(n).decode('utf8', 'replace')
                for t in re.findall(r'<w:t[^>]*>(.*?)</w:t>', raw, re.S):
                    yield n, t
    else:
        yield 'md', open(path, encoding='utf8').read()


bad = []
total = 0
for p in TARGETS:
    if not os.path.exists(p):
        bad.append(('文件缺失', p, ''))
        continue
    for part, t in texts(p):
        total += len(t)
        for i, ch in enumerate(t):
            cp = ord(ch)
            if cp in OK:
                continue
            ctx = t[max(0, i - 40):i + 40].replace('\n', ' ')
            bad.append((os.path.basename(p) + ':' + part, 'U+%04X %s' % (cp, ch),
                        unicodedata.name(ch, '?') + ' ‖ ' + ctx))

rep = ['投稿前非常规码点扫描', '=' * 70,
       '扫描文件: %d' % len(TARGETS), '字符总数: %s' % format(total, ','),
       '非白名单码点: %d' % len(bad), '']
for a, b, c in bad:
    rep.append('  %-46s %-14s %s' % (a, b, c))
open(os.path.join(OUT, '_codepoint_scan.txt'), 'w', encoding='utf8').write('\n'.join(rep))
print('\n'.join(rep))
sys.exit(1 if bad else 0)
