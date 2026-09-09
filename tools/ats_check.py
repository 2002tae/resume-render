#!/usr/bin/env python3
"""
ats_check.py — 실제 TS 렌더러 출력을 모든 테마 × fixture 에 대해 검사한다.

  render(ir) → HTML  (node, dist/index.js)
  + _shared.css + theme.css  → PDF (WeasyPrint)
  → pdftotext (-layout / stream 두 모드)
  → 텍스트 무결성 · 읽기 순서 · 섹션 라벨 · 연락처 검증

판정 등급:
  missing      텍스트가 없음                    → 실패
  mangled      문자 사이 공백 삽입(자간)         → 실패
  interleaved  섹션 라벨/날짜가 문단에 삽입      → 경고
  hyphenBreaks 줄끝 하이픈 소실 (추출기 공통)    → 경고

이것은 "진짜 Workday 가 파싱한다"는 증명이 아니라 텍스트 레이어 무결성 검증이다.
"""
import json, re, subprocess, sys, pathlib, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
if not (ROOT/"dist/index.js").exists():
    raise SystemExit("dist/index.js not found — run `npm install && npm run build` first (the tools render through the compiled library)")
LABELS = {"summary":"Summary","education":"Education","experiences":"Experience","projects":"Projects",
          "research":"Research","skills":"Skills","awards":"Honors","languages":"Languages"}

def render_ts(ir: dict) -> str:
    js = f"""
    import {{ render }} from '{ROOT/"dist/index.js"}';
    const ir = JSON.parse(process.argv[1]);
    process.stdout.write(render(ir).html);"""
    return subprocess.run(["node","--input-type=module","-e",js,json.dumps(ir)],
                          capture_output=True, text=True, check=True).stdout

def to_pdf(html: str, theme: str, out: pathlib.Path):
    from weasyprint import HTML
    css = (ROOT/"themes/_shared.css").read_text() + "\n" + (ROOT/"themes"/theme/"theme.css").read_text()
    HTML(string=f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{html}</body></html>').write_pdf(str(out))

DEFAULT_ORDER = ["summary","education","experiences","projects","research","skills","awards"]

def expected_strings(ir, order=None, summary_in_header=False):
    """렌더 순서대로의 기대 문자열. 매니페스트 defaults 의 섹션 순서를 따라야 순서 검사가 의미 있다."""
    b = ir.get("basics") or {}
    s = [b.get("name")]
    if b.get("headline"): s.append(b["headline"])
    summ = (ir.get("summary") or {}).get("text")
    if summary_in_header and summ: s.append(summ)
    for sec in (order or DEFAULT_ORDER):
        if sec == "summary" and summ and not summary_in_header: s.append(summ)
        elif sec == "education":
            for e in ir.get("education", []): s.append(e["school"])
        elif sec in ("experiences","projects","research"):
            for x in ir.get(sec, []):
                s.append(x.get("title") or x.get("name") or x.get("org"))
                for bl in x.get("bullets", []): s.append(bl["text"] if isinstance(bl, dict) else bl)
    return [x for x in s if x]

def clean(t):   return t.replace("**", "")       # IR 의 인라인 강조 마커는 렌더 텍스트에 없다
def norm(t):    # 하이픈·엔대시·엠대시 뒤 줄바꿈은 붙인다 (추출기가 그 지점에서 공백을 삽입함)
    # "1996–\n2026" 처럼 앞뒤가 붙은 대시만 잇는다. "May –\nJul" 처럼 띄운 대시는 공백을 유지.
    return re.sub(r"\s+"," ", re.sub(r"(\S[-–—])\n\s*",r"\1",clean(t))).strip().lower()
def squeeze(t): return re.sub(r"\s+","",clean(t)).lower()
def dehyph(t):  return re.sub(r"[-–—]","",squeeze(t))

def check(raw, ir, labels_override=None, order=None, summary_in_header=False):
    flat, sq, dh = norm(raw), squeeze(raw), dehyph(raw)
    strip = flat
    # 헤드 행에서 제목 옆에 오는 것들 — 제목이 줄바꿈되면 이들이 제목 중간에 삽입된다
    side = []
    for sec in ("education","experiences","projects","research"):
        for x in ir.get(sec, []):
            d = x.get("dates");  side.append(d.get("raw", d) if isinstance(d, dict) else d)
            for k in ("org","location","institution","department","role","subtitle"): side.append(x.get(k))
    # 헤더에서 요약 옆에 오는 연락처도 삽입물이 될 수 있다 (folio: 요약 좌 / 연락처 우)
    for c in (ir.get("basics") or {}).get("contacts", []): side.append(c["value"] if isinstance(c, dict) else c)
    # 짧은 토큰("solo")은 다른 문자열 안에서도 매칭되어 오히려 본문을 지운다 — 8자 이상만 제거
    # 긴 토큰부터 제거 — 짧은 라벨("Research")이 먼저 빠지면 그걸 포함한 긴 기관명이 깨져 매칭에 실패한다
    for tok in sorted(list(LABELS.values()) + [t for t in side if t and len(str(t)) >= 8], key=lambda x: -len(str(x))):
        strip = re.sub(r"\s*"+re.escape(norm(str(tok)))+r"\s*", " ", strip)
    # 삽입물을 뺀 자리에 구두점만 남을 수 있으므로 (institution, department → ", ") interleave 비교는 구두점 무시
    strip = re.sub(r"\s+"," ",re.sub(r"[,;:·|]"," ",strip))
    strip = re.sub(r"-\s+","-",strip)                 # 삽입물을 뺀 자리의 하이픈 뒤 공백
    res = {"missing":[],"mangled":[],"hyphen":[],"interleaved":[]}; pos = []
    for t in expected_strings(ir, order, summary_in_header):
        n = norm(t); i = flat.find(n)
        # 너무 짧은 문자열은 다른 곳에 우연히 매칭되어 순서 판정을 오염시킨다 ("P" → 이메일 안의 p).
        # 존재 여부는 세되 순서 추적에서는 제외한다.
        if i >= 0:
            if len(n) >= 6: pos.append(i)
        elif squeeze(t) in sq: res["mangled"].append(n[:50])
        elif dehyph(t) in dh:  res["hyphen"].append(n[:50])
        elif re.sub(r"-\s+","-",re.sub(r"\s+"," ",re.sub(r"[,;:·|]"," ",n))) in strip: res["interleaved"].append(n[:50])
        else:                  res["missing"].append(n[:50])
    # Summary 는 산문이라 파서가 헤딩 없이도 읽는다 — 매거진형 테마는 리드 스타일로 라벨을 숨긴다. 필수 아님.
    present = [k for k in LABELS if ir.get(k) and k != "summary"]
    res["orderOk"] = pos == sorted(pos)
    lab = {**LABELS, **{k:v for k,v in (labels_override or {}).items()}}
    res["labelsLost"] = [lab[k] for k in present if lab[k].lower() not in flat and squeeze(lab[k]).lower() not in sq]
    contacts = [(c["value"] if isinstance(c, dict) else c) for c in (ir.get("basics") or {}).get("contacts", [])]
    res["contacts"] = f"{sum(1 for c in contacts if norm(c) in flat)}/{len(contacts)}"
    return res

def main():
    themes = sorted(p.name for p in (ROOT/"themes").iterdir() if p.is_dir())
    fixtures = sorted(p.stem for p in (ROOT/"fixtures").glob("*.json"))
    manifests = {t: json.loads((ROOT/"themes"/t/"manifest.json").read_text()) for t in themes}
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    write = "--write" in sys.argv
    if only: themes = [t for t in themes if t in only]
    fails = 0
    agg = {t: {"hard":0,"interleave":0,"orderLayout":True,"orderStream":True} for t in themes}
    print(f"{'theme':18s} {'fixture':8s} {'mode':7s} {'miss':>4s} {'mang':>4s} {'inter':>5s} {'hyph':>4s} {'order':>5s} {'labels':>6s} {'contacts':>8s}")
    print("-"*84)
    with tempfile.TemporaryDirectory() as td:
        for t in themes:
            for fx in fixtures:
                ir = json.loads((ROOT/"fixtures"/f"{fx}.json").read_text())
                # 매니페스트가 선언한 이름 길이 한계를 넘는 fixture 는 이름을 검사에서 뺀다 (한계는 문서화된 것)
                lim = (manifests[t].get("limits") or {}).get("nameMaxChars")
                nm = (ir.get("basics") or {}).get("name","")
                if lim and nm and max(len(w) for w in nm.replace("-"," ").split()) > lim:
                    ir = json.loads(json.dumps(ir)); ir["basics"]["name"] = ""
                # 매니페스트 defaults(섹션 순서·라벨·layout) 를 적용해 실제 배포 구성으로 검사한다
                from render_theme import render as render_with_defaults
                html = render_with_defaults(ir, t)["html"]
                pdf = pathlib.Path(td)/f"{t}_{fx}.pdf"; to_pdf(html, t, pdf)
                # -raw 는 WeasyPrint 의 페인트 순서(flex 를 나중에 그림)를 드러낼 뿐 테마 속성이 아니다 — 제외
                for mode, flag in (("layout",["-layout"]),("stream",[])):
                    raw = subprocess.run(["pdftotext"]+flag+[str(pdf),"-"],capture_output=True,text=True).stdout
                    dfl = manifests[t].get("defaults",{}) or {}
                    r = check(raw, ir, (dfl.get("sections") or {}).get("labels"),
                              (dfl.get("sections") or {}).get("order"), bool((dfl.get("layout") or {}).get("summaryInHeader")))
                    expressive = manifests[t]["profile"] == "expressive"
                    # expressive 다단은 layout 모드에서 컬럼이 섞여 문자열이 끊길 수 있다 — 문서화된 한계.
                    # stream 모드는 항상 온전해야 한다.
                    lenient = expressive and mode == "layout"
                    hard = bool(r["mangled"] or r["labelsLost"] or (r["missing"] and not lenient))
                    order_bad = not r["orderOk"] and not expressive
                    bad = hard or order_bad
                    fails += bad
                    a = agg[t]; a["hard"] += hard; a["interleave"] += len(r["interleaved"])
                    if not r["orderOk"]: a["orderLayout" if mode=="layout" else "orderStream"] = False
                    print(f"{t:18s} {fx:8s} {mode:7s} {len(r['missing']):4d} {len(r['mangled']):4d} {len(r['interleaved']):5d} "
                          f"{len(r['hyphen']):4d} {'ok' if r['orderOk'] else ('~' if expressive else 'X'):>5s} "
                          f"{'ok' if not r['labelsLost'] else 'LOST':>6s} {r['contacts']:>8s}  {'FAIL' if bad else ''}")
    print(f"\n{'FAIL' if fails else 'PASS'} — {fails} hard failure(s). (expressive 테마의 순서 흐트러짐은 '~' 로 표시, 실패 아님)")
    if write:
        import datetime
        for t, a in agg.items():
            mp = ROOT/"themes"/t/"manifest.json"; m = json.loads(mp.read_text())
            order = ("all" if a["orderLayout"] and a["orderStream"]
                     else "stream-only" if a["orderStream"] else "none")
            m["ats"] = {
                "verified": a["hard"] == 0 and order == "all" and a["interleave"] == 0,
                "textComplete": a["hard"] == 0,
                "orderPreserved": order,
                "interleaveWarnings": a["interleave"],
                "fixtures": fixtures, "extractors": ["pdftotext -layout", "pdftotext"],
                "checkedAt": datetime.date.today().isoformat(),
                "note": "Text-layer integrity, not a vendor guarantee. See docs/template-contract.md §5.",
            }
            mp.write_text(json.dumps(m, indent=2) + "\n")
        print(f"manifests updated: {len(agg)}")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
