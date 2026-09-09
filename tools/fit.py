#!/usr/bin/env python3
"""
fit.py — 목표 페이지 수에 맞춘다. 렌더러는 측정을 못 하므로(순수 함수) 어댑터가 한다.

전략 (순서대로, 공개 API 만 사용):
  1. --density 를 1.0 → floor 까지 이분탐색     (render(ir, {vars:{"--density":d}}))
  2. 그래도 넘치면 priority 를 5→4→3 으로 절삭     (render(ir, {filter:{minPriority:p}}))
     절삭할 때마다 density 를 다시 1.0 부터 탐색 — 덜 줄이고도 들어갈 수 있으므로
  3. floor 에서도 안 들어가면 FIT_FAILED 보고, 마지막 시도 결과를 그대로 낸다

density floor 는 가독성 하한이다. 0.82 아래로 내려가면 본문이 9pt 미만이 되어
줄이는 것보다 자르는 게 낫다 — 그래서 절삭이 floor 뒤에 온다.

usage: python3 tools/fit.py fixtures/dense.json --theme classic --pages 1 --out out/x.pdf
       python3 tools/fit.py fixtures/dense.json --all --pages 1 --outdir out/fit
"""
import argparse, json, subprocess, sys, pathlib, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from ats_check import render_ts, to_pdf  # noqa

FLOOR = 0.82
STEPS = 4           # 이분탐색 반복 — 0.18 범위를 ~0.003 정밀도로

EXTRA_OPTS = {}   # --opts '<json>' 로 주입 (예: {"sections":{"exclude":["summary"]}})

def render_opts(ir, density, min_priority, theme=None):
    if theme:
        from render_theme import render as _r
        return _r(ir, theme, density, min_priority, EXTRA_OPTS)
    js = f"""
    import {{ render }} from '{ROOT/"dist/index.js"}';
    const ir = JSON.parse(process.argv[1]);
    const opts = {{ vars: {{ "--density": "{density:.3f}" }} }};
    if ({min_priority if min_priority else 'null'}) opts.filter = {{ minPriority: {min_priority or 0} }};
    const r = render(ir, opts);
    process.stdout.write(JSON.stringify(r));"""
    out = subprocess.run(["node","--input-type=module","-e",js,json.dumps(ir)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)

def pages_of(pdf):
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    return int([l.split()[1] for l in info.splitlines() if l.startswith("Pages")][0])

def last_text(ir):
    """마지막에 렌더되는 문자열 — 잘림 감지용 (awards → skills 마지막 항목 순)"""
    aw = ir.get("awards") or []
    if aw: return aw[-1]["title"]
    sk = ir.get("skills") or []
    if sk:
        g = sk[-1]; return (g["items"][-1] if isinstance(g, dict) else g)
    return None

def try_render(ir, theme, density, min_priority, out):
    r = render_opts(ir, density, min_priority, theme)
    to_pdf(r["html"], theme, out)
    p = pages_of(out)
    # 다단 테마는 넘쳐도 페이지가 늘지 않고 잘린다(실측) — 마지막 문자열이 추출되는지로 판정
    lt = last_text(ir)
    if lt:
        txt = subprocess.run(["pdftotext", str(out), "-"], capture_output=True, text=True).stdout
        if lt.lower().replace("**","") not in " ".join(txt.split()).lower():
            p = 99  # 잘림 = 안 들어감으로 취급
    return p, r["warnings"]

def fit(ir, theme, target, out, log):
    """returns dict(density, minPriority, pages, fitted, warnings)"""
    trimmed = 0
    for min_priority in (None, 5, 4, 3, 2, 1):
        # density 이분탐색: lo 는 들어감(있으면), hi 는 안 들어감
        p, w = try_render(ir, theme, 1.0, min_priority, out)
        log(f"  prio≤{min_priority or '∞'}  density=1.000 → {p}p")
        if p <= target:
            return dict(density=1.0, minPriority=min_priority, pages=p, fitted=True, warnings=w)
        p, w = try_render(ir, theme, FLOOR, min_priority, out)
        log(f"  prio≤{min_priority or '∞'}  density={FLOOR:.3f} → {p}p")
        if p > target:
            continue                      # floor 에서도 안 들어감 → 절삭 단계로
        lo, hi = FLOOR, 1.0               # lo 는 들어감, hi 는 안 들어감
        for _ in range(STEPS):
            mid = (lo + hi) / 2
            p, w = try_render(ir, theme, mid, min_priority, out)
            if p <= target: lo = mid
            else: hi = mid
        p, w = try_render(ir, theme, lo, min_priority, out)
        log(f"  prio≤{min_priority or '∞'}  density={lo:.3f} → {p}p  ✓")
        return dict(density=round(lo,3), minPriority=min_priority, pages=p, fitted=True, warnings=w)
    p, w = try_render(ir, theme, FLOOR, 2, out)
    return dict(density=FLOOR, minPriority=2, pages=p, fitted=False, warnings=w + [
        {"code":"FIT_FAILED","message":f"still {p} pages at density {FLOOR} with priority ≤2"}])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ir"); ap.add_argument("--theme"); ap.add_argument("--all", action="store_true")
    ap.add_argument("--pages", type=int, default=1); ap.add_argument("--out"); ap.add_argument("--outdir")
    ap.add_argument("-q", action="store_true"); ap.add_argument("--opts", default="{}")
    a = ap.parse_args()
    ir = json.loads(pathlib.Path(a.ir).read_text())
    global EXTRA_OPTS; EXTRA_OPTS = json.loads(a.opts)
    log = (lambda *x: None) if a.q else print
    themes = sorted(d.name for d in (ROOT/"themes").iterdir() if d.is_dir()) if a.all else [a.theme]
    outdir = pathlib.Path(a.outdir or "out/fit"); outdir.mkdir(parents=True, exist_ok=True)
    results = {}
    for t in themes:
        out = pathlib.Path(a.out) if (a.out and not a.all) else outdir / f"{t}.pdf"
        log(f"[{t}]")
        r = fit(ir, t, a.pages, out, log)
        results[t] = r
        tag = "✓" if r["fitted"] else "✗ FIT_FAILED"
        print(f"{t:18s} density={r['density']:.3f} prio≤{r['minPriority'] or '∞':<2} → {r['pages']}p {tag}")
    (outdir / "fit-report.json").write_text(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
