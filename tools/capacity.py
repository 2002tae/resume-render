#!/usr/bin/env python3
"""
capacity.py — "본문 X pt 로 1페이지에 bullet 몇 개까지 들어가나" 를 테마별로 실측한다.

fit.py 는 밀도를 찾지만, 리뷰어 요구(≥10pt)는 밀도를 고정하고 내용을 묻는 질문이다.
priority 오름차순(1 이 먼저)·원문 순서로 상위 N 개만 남기며 N 을 줄여 1페이지가 되는 최대 N 을 찾는다.

usage: capacity.py <ir.json> --pt 10 [--themes a b] [--opts '{...}']
"""
import argparse, json, sys, pathlib, tempfile, subprocess
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"tools"))
from render_theme import render
from ats_check import to_pdf
from fit import pages_of, last_text

PX2PT = 0.75

def keep_top(ir, n):
    """priority 순으로 상위 n 개 bullet 만 남긴 IR (원문 순서 유지)."""
    ir = json.loads(json.dumps(ir))
    items = []
    for sec in ("experiences", "projects", "research"):
        for i, x in enumerate(ir.get(sec, [])):
            for j, b in enumerate(x.get("bullets", [])):
                items.append(((b.get("priority", 99) if isinstance(b, dict) else 99), sec, i, j))
    keep = set((s, i, j) for _, s, i, j in sorted(items)[:n])
    for sec in ("experiences", "projects", "research"):
        for i, x in enumerate(ir.get(sec, [])):
            x["bullets"] = [b for j, b in enumerate(x.get("bullets", [])) if (sec, i, j) in keep]
    return ir

def fits(ir, theme, density, opts, td):
    out = pathlib.Path(td)/"x.pdf"
    to_pdf(render(ir, theme, density, None, opts)["html"], theme, out)
    if pages_of(out) > 1: return False
    lt = last_text(ir)
    if lt:
        txt = " ".join(subprocess.run(["pdftotext", str(out), "-"], capture_output=True, text=True).stdout.split()).lower()
        if lt.lower().replace("**", "") not in txt: return False
    return True

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ir"); ap.add_argument("--pt", type=float, default=10)
    ap.add_argument("--themes", nargs="*"); ap.add_argument("--opts", default="{}")
    a = ap.parse_args()
    ir = json.loads(pathlib.Path(a.ir).read_text()); opts = json.loads(a.opts)
    total = sum(len(x.get("bullets", [])) for s in ("experiences","projects","research") for x in ir.get(s, []))
    themes = a.themes or sorted(d.name for d in (ROOT/"themes").iterdir() if d.is_dir())
    print(f"본문 {a.pt}pt 고정 · 1페이지 · 전체 {total} bullet · opts={a.opts}")
    print(f"{'theme':12s} {'bodyscale':>9s} {'max bullets':>11s}")
    with tempfile.TemporaryDirectory() as td:
        for t in themes:
            man = json.loads((ROOT/"themes"/t/"manifest.json").read_text())
            bs = a.pt / ((man.get("baseBodyPx") or 11) * PX2PT)     # 본문만 이 배율로
            o2 = {**opts, "vars": {**opts.get("vars", {}), "--body-scale": f"{bs:.3f}"}}
            d = 1.0
            lo, hi = 0, total          # lo 는 들어감(0 은 항상), hi 는 후보
            if fits(ir, t, d, o2, td): lo = total
            else:
                while hi - lo > 1:
                    mid = (lo + hi) // 2
                    if fits(keep_top(ir, mid), t, d, o2, td): lo = mid
                    else: hi = mid
            print(f"{t:12s} {bs:7.3f} {lo:6d}/{total}")

if __name__ == "__main__":
    main()
