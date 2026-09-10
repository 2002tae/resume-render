#!/usr/bin/env python3
"""
visual_check.py — 시각 회귀. 테마별 렌더를 참조 스냅샷과 픽셀 비교한다.

ATS 스위트는 텍스트가 온전하면 통과시키므로 배치가 깨져도 못 잡는다(실측: 소속이 날짜 옆으로 밀림,
잉크 필드 소실, 요약이 이름에 겹침 — 전부 눈으로만 잡혔다). 이 도구가 그 공백을 메운다.

  python3 tools/visual_check.py --update      # 지금 렌더를 참조로 저장 (의도한 변경 후)
  python3 tools/visual_check.py               # 참조와 비교. 차이율이 임계 초과면 FAIL + diff 이미지
"""
import sys, json, pathlib, subprocess, tempfile
from PIL import Image, ImageChops
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from render_theme import render
from ats_check import to_pdf

REF = ROOT / "tools" / "visual-ref"
THRESH = 0.2   # 실측: 소속 밀림 회귀 = 0.53%, 안티앨리어싱 노이즈 = 0.00% — 0.2 면 둘을 가른다

def snapshot(theme, ir, density):
    with tempfile.TemporaryDirectory() as td:
        pdf = pathlib.Path(td) / "x.pdf"
        to_pdf(render(ir, theme, density)["html"], theme, pdf)
        subprocess.run(["pdftoppm", "-jpeg", "-r", "60", "-f", "1", "-l", "1", str(pdf), str(pathlib.Path(td)/"s")], check=True)
        return Image.open(pathlib.Path(td) / "s-1.jpg").convert("L").copy()

def main():
    update = "--update" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    ir = json.loads((ROOT / "fixtures/dense.json").read_text())
    params = json.loads((ROOT / "tools/visual-ref/params.json").read_text()) if (REF / "params.json").exists() else {}
    themes = sorted(d.name for d in (ROOT / "themes").iterdir() if d.is_dir())
    import weasyprint
    if not update and params.get("_weasyprint") and params["_weasyprint"] != weasyprint.__version__:
        print(f"  ! baseline was made with WeasyPrint {params['_weasyprint']}, this is {weasyprint.__version__} — line-height rounding differs between versions; expect drift. Re-baseline with --update after confirming visually.")
    if only: themes = [t for t in themes if t in only]
    REF.mkdir(exist_ok=True)
    fails = 0
    for t in themes:
        d = params.get(t, 1.0)
        img = snapshot(t, ir, d)
        ref = REF / f"{t}.png"
        if update or not ref.exists():
            img.save(ref); params[t] = d
            print(f"  {t:12s} baseline saved (density {d})")
            continue
        base = Image.open(ref).convert("L")
        if base.size != img.size:
            print(f"  {t:12s} FAIL size {base.size} → {img.size}"); fails += 1; continue
        diff = ImageChops.difference(base, img).point(lambda p: 255 if p > 40 else 0)
        changed = sum(1 for p in diff.getdata() if p) / (diff.size[0] * diff.size[1]) * 100
        ok = changed <= THRESH
        if not ok:
            fails += 1
            diff.save(REF / f"{t}.diff.png")
        print(f"  {t:12s} {'ok  ' if ok else 'FAIL'} changed={changed:5.2f}%  {'' if ok else '→ ' + str(REF / f'{t}.diff.png')}")
    if update:
        import weasyprint as _w; params["_weasyprint"] = _w.__version__   # 기준선을 만든 버전만 기록 — 검사 때 덮어쓰면 가드가 자기를 끈다(Artemis 지적)
    (REF / "params.json").write_text(json.dumps(params, indent=1))
    print("PASS" if not fails else f"FAIL — {fails} theme(s) changed beyond {THRESH}%")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
