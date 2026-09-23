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
STEPS = 5   # browser plan() 과 동일 — fit.py 가 기준
PX2PT = 0.75   # CSS px → PDF pt (실측: 12px → 9.0pt)           # 이분탐색 반복 — 0.18 범위를 ~0.003 정밀도로

EXTRA_OPTS = {}   # --opts '<json>' 로 주입 (예: {"sections":{"exclude":["summary"]}})

BODY_LOCK = None   # (base_px, min_pt) — 설정되면 density 가 줄어도 본문은 min_pt 로 고정

def render_opts(ir, density, min_priority, theme=None):
    if theme:
        from render_theme import render as _r
        extra = EXTRA_OPTS
        if BODY_LOCK:
            base, minpt = BODY_LOCK
            bs = minpt / (base * PX2PT * density)
            extra = {**EXTRA_OPTS, "vars": {**EXTRA_OPTS.get("vars", {}), "--body-scale": f"{bs:.4f}"}}
        return _r(ir, theme, density, min_priority, extra)
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

def fit(ir, theme, target, out, log, min_body_pt=None):
    """returns dict(density, minPriority, pages, fitted, warnings, bodyPt)"""
    man = json.loads((ROOT/"themes"/theme/"manifest.json").read_text())
    base = man.get("baseBodyPx") or 11
    global BODY_LOCK
    if min_body_pt:
        # 본문 고정 모드: density 는 여백·이름·간격만 줄이고 body-scale 이 본문을 min_pt 로 붙든다
        BODY_LOCK = (base, min_body_pt); floor = FLOOR; top = 1.0
        pt = lambda d: float(min_body_pt)
    else:
        BODY_LOCK = None; floor = FLOOR; top = 1.0
        pt = lambda d: round(base * d * PX2PT, 1)
    if min_body_pt:
        # 본문 고정 모드에서는 density 가 여백·간격만 바꾼다 — 글자 크기는 그대로이므로 "많이 넣기"가 항상 낫다.
        # priority 티어는 들어가는 순간 멈춰 남은 공간을 버린다(실측: 11개 들어갈 자리에 6개). 그래서 여기서는
        # 가장 조밀한 여백(FLOOR)에서 들어가는 최대 N 을 찾고, 그 N 에서 여백을 최대한 되돌린다.
        from capacity import keep_top
        total = sum(len(x.get("bullets", [])) for s_ in ("experiences","projects","research") for x in ir.get(s_, []))
        lo, hi = 0, total + 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if try_render(keep_top(ir, mid), theme, floor, None, out)[0] <= target: lo = mid
            else: hi = mid
        if lo == 0 and total:
            p, w = try_render(keep_top(ir, 0), theme, floor, None, out)
            return dict(density=round(floor,3), minPriority=None, topN=0, pages=p, fitted=False, bodyPt=pt(floor), warnings=w + [
                {"code":"FIT_FAILED","message":f"still {p} pages at density {floor:.3f} with no bullets"}])
        kept = keep_top(ir, lo)
        d_lo, d_hi = floor, 1.0
        if try_render(kept, theme, 1.0, None, out)[0] <= target: d_lo = 1.0
        else:
            for _ in range(STEPS):
                m = (d_lo + d_hi) / 2
                if try_render(kept, theme, m, None, out)[0] <= target: d_lo = m
                else: d_hi = m
        p, w = try_render(kept, theme, d_lo, None, out)
        log(f"  body-lock: top-{lo}/{total}  density={d_lo:.3f} → {p}p  ✓")
        return dict(density=round(d_lo,3), minPriority=None, topN=(lo if lo < total else None), pages=p, fitted=True, bodyPt=pt(d_lo), warnings=w)
    trimmed = 0
    for min_priority in (None, 5, 4, 3, 2, 1):
        # density 이분탐색: lo 는 들어감(있으면), hi 는 안 들어감
        start = max(1.0, floor)
        p, w = try_render(ir, theme, start, min_priority, out)
        log(f"  prio≤{min_priority or '∞'}  density={start:.3f} → {p}p")
        if p <= target:
            # 들어가면 더 키울 여지 탐색 (top 까지)
            lo, hi = start, top
            for _ in range(STEPS):
                mid = (lo + hi) / 2
                p2, _ = try_render(ir, theme, mid, min_priority, out)
                if p2 <= target: lo = mid
                else: hi = mid
            p, w = try_render(ir, theme, lo, min_priority, out)
            return dict(density=round(lo,3), minPriority=min_priority, pages=p, fitted=True, warnings=w, bodyPt=pt(lo))
        p, w = try_render(ir, theme, floor, min_priority, out)
        log(f"  prio≤{min_priority or '∞'}  density={floor:.3f} → {p}p")
        if p > target:
            continue                      # floor 에서도 안 들어감 → 절삭 단계로
        lo, hi = floor, start             # lo 는 들어감, hi 는 안 들어감
        for _ in range(STEPS):
            mid = (lo + hi) / 2
            p, w = try_render(ir, theme, mid, min_priority, out)
            if p <= target: lo = mid
            else: hi = mid
        p, w = try_render(ir, theme, lo, min_priority, out)
        log(f"  prio≤{min_priority or '∞'}  density={lo:.3f} → {p}p  ✓")
        return dict(density=round(lo,3), minPriority=min_priority, pages=p, fitted=True, warnings=w, bodyPt=pt(lo))
    # 마지막 단계: priority 티어가 거칠어 실패하면 top-N(priority 순·원문 순) 이분탐색 — 정확한 N 을 찾는다
    from capacity import keep_top
    total = sum(len(x.get("bullets", [])) for sec in ("experiences","projects","research") for x in ir.get(sec, []))
    lo, hi = 0, total
    while hi - lo > 1:
        mid = (lo + hi) // 2
        p, _ = try_render(keep_top(ir, mid), theme, floor, None, out)
        if p <= target: lo = mid
        else: hi = mid
    if lo > 0:
        # 찾은 N 에서 density 를 다시 최대한 키운다
        d_lo, d_hi = floor, 1.0
        for _ in range(STEPS):
            m = (d_lo + d_hi) / 2
            p2, _ = try_render(keep_top(ir, lo), theme, m, None, out)
            if p2 <= target: d_lo = m
            else: d_hi = m
        p, w = try_render(keep_top(ir, lo), theme, d_lo, None, out)
        log(f"  top-{lo} bullets  density={d_lo:.3f} → {p}p  ✓")
        return dict(density=round(d_lo,3), minPriority=None, topN=lo, pages=p, fitted=True, bodyPt=pt(d_lo), warnings=w)
    p, w = try_render(ir, theme, floor, 1, out)
    return dict(density=round(floor,3), minPriority=1, pages=p, fitted=False, bodyPt=pt(floor), warnings=w + [
        {"code":"FIT_FAILED","message":f"still {p} pages at density {floor:.3f} even with 1 bullet"}])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ir"); ap.add_argument("--theme"); ap.add_argument("--all", action="store_true")
    ap.add_argument("--pages", type=int, default=1); ap.add_argument("--out"); ap.add_argument("--outdir")
    ap.add_argument("-q", action="store_true"); ap.add_argument("--opts", default="{}")
    ap.add_argument("--min-body-pt", type=float, default=None)
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
        r = fit(ir, t, a.pages, out, log, a.min_body_pt)
        results[t] = r
        tag = "✓" if r["fitted"] else "✗ FIT_FAILED"
        trim = f"top-{r['topN']}" if r.get("topN") else f"prio≤{r['minPriority'] or '∞'}"
        print(f"{t:18s} density={r['density']:.3f} {trim:7s} body={r['bodyPt']:4.1f}pt → {r['pages']}p {tag}")
    (outdir / "fit-report.json").write_text(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
