#!/usr/bin/env python3
"""
margin_check.py — no text in the paper's top or bottom margin, on any page.

Page margins are .rz padding, not @page margin (_shared.css). Without box-decoration-break:clone, WeasyPrint kept that
padding only at the very top and very bottom of the article: a full page 1 ended at the paper's edge, page 2 began at
it, and fit() reported 'fits on one page' for résumés whose last lines sat in the bottom margin (measured: last line
783–791pt on a 792pt sheet in 9 of 13 themes; page 2 starting 2–12pt from the top). The visual check missed it for
a month because the reference images were taken with the same defect. This checks the PDF text itself.

  python3 tools/margin_check.py            # all themes
  python3 tools/margin_check.py classic    # some
"""
import sys, json, pathlib, tempfile
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextLine
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from render_theme import render
from ats_check import to_pdf

FLOOR_PT = 20   # theme paddings are 27–40pt at fitted densities; the defect put text 0–12pt from the edge


def lines(pdf):
    out = []
    for pno, page in enumerate(extract_pages(str(pdf))):
        def walk(o):
            if isinstance(o, LTTextLine):
                out.append((pno, page.height - o.y1, page.height - o.y0, page.height, o.get_text().strip()[:40]))
            elif hasattr(o, "__iter__"):
                for c in o: walk(c)
        walk(page)
    return out


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    ir = json.loads((ROOT / "fixtures/dense.json").read_text())
    params = json.loads((ROOT / "tools/visual-ref/params.json").read_text())
    themes = sorted(d.name for d in (ROOT / "themes").iterdir() if d.is_dir())
    if only: themes = [t for t in themes if t in only]
    fails = 0
    for t in themes:
        bad = []; pages = []
        # the visual-check density (dense fixture, usually 1 full page + a spill) and 1.1 (forces a page break)
        for d in sorted({params.get(t, 1.0), 1.1}):
            with tempfile.TemporaryDirectory() as td:
                pdf = pathlib.Path(td) / "x.pdf"
                to_pdf(render(ir, t, d)["html"], t, pdf)
                ls = lines(pdf)
            pages.append(f"{d}:{max(l[0] for l in ls) + 1}p")
            for pno in sorted({l[0] for l in ls}):
                on = [l for l in ls if l[0] == pno]
                top = min(l[1] for l in on); bottom = max(l[2] for l in on); h = on[0][3]
                if top < FLOOR_PT:
                    bad.append(f"d={d} page {pno + 1}: first line {top:.1f}pt from the top ('{min(on, key=lambda l: l[1])[4]}')")
                if h - bottom < FLOOR_PT:
                    bad.append(f"d={d} page {pno + 1}: last line {h - bottom:.1f}pt from the bottom ('{max(on, key=lambda l: l[2])[4]}')")
        fails += bool(bad)
        print(f"  {t:12s} {'FAIL' if bad else 'ok  '} ({', '.join(pages)})")
        for b in bad: print(f"      {b}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
