#!/usr/bin/env python3
"""compare.py — 렌더 결과를 원본 디자인 캡처와 나란히 놓는다.

usage: python3 tools/compare.py <theme> <rendered.pdf> <original.png> <out.jpg>

원본 캡처는 레포에 포함되지 않는다(디자인 도구 출력물). 개발자가 자기 캡처를 넘긴다.
"""
import sys, subprocess, tempfile, pathlib
from PIL import Image, ImageDraw
if len(sys.argv) != 5:
    print(__doc__); sys.exit(2)
theme, pdf, original, out = sys.argv[1:5]
with tempfile.TemporaryDirectory() as td:
    subprocess.run(["pdftoppm", "-jpeg", "-r", "80", "-f", "1", "-l", "1", pdf, f"{td}/r"], check=True)
    r = Image.open(f"{td}/r-1.jpg").copy()
o = Image.open(original)
H = 900
fit = lambda im: im.resize((int(im.size[0] * H / im.size[1]), H))
o, r = fit(o), fit(r)
c = Image.new("RGB", (o.size[0] + r.size[0] + 20, H + 18), "#8a8a8a"); d = ImageDraw.Draw(c)
d.text((4, 2), f"{theme} — ORIGINAL", fill="#fff"); d.text((o.size[0] + 24, 2), f"{theme} — RENDERED", fill="#fff")
c.paste(o, (0, 16)); c.paste(r, (o.size[0] + 20, 16)); c.save(out, quality=86)
print(out)
