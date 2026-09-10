#!/usr/bin/env python3
"""
ats_generic.py — 우리 HTML 구조를 **모르는** 파서로 식별성을 잰다.

ats_check.py 는 IR 을 알고 rz-* 를 안다 → 편향. 이 도구는 일반 ATS 가 하는 것만 한다:
  * 텍스트를 3개 엔진(poppler pdftotext · pdfminer.six · pypdf)으로 뽑고
  * 이메일/전화/URL 정규식, 헤딩 사전, 날짜 정규식으로 **구조를 추측**한다.
  * 기대값은 IR 이 아니라 "이력서라면 있어야 하는 것" 수준으로만 쓴다 (연락처 수, 섹션 존재, 경력 항목 수).

등급
  A  3개 엔진 모두: 이름이 첫 줄, 연락처 전부, 섹션 전부 식별, 경력 항목 수 일치
  B  2개 엔진 이상 A 조건 / 나머지는 순서·항목 수 차이만
  C  섹션 헤딩을 사전으로 못 찾거나 연락처가 합쳐짐 (구조 식별 실패)
  D  텍스트 유실
"""
import re, sys, json, subprocess, pathlib, tempfile, argparse
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/"tools"))

# ── 일반 ATS 헤딩 사전 (Workday/Greenhouse/Lever 류 파서가 쓰는 수준) ──
HEADINGS = {
  "experience": ["experience","work experience","professional experience","employment","work history"],
  "education":  ["education","academic background"],
  "projects":   ["projects","selected projects","personal projects","technical projects"],
  "research":   ["research","research experience","publications"],
  "skills":     ["skills","technical skills","core competencies","technologies"],
  "honors":     ["honors","awards","honors & awards","honors and awards","achievements"],
  "summary":    ["summary","profile","objective","about"],
}
DATE = re.compile(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{4}|\b(?:19|20)\d{2}\b|present|current|expected|incoming", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
URL   = re.compile(r"\b(?:linkedin\.com|github\.com|[\w-]+\.(?:com|io|dev|me|org))\S*", re.I)

def extract_all(pdf):
    out = {}
    out["poppler"] = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    try:
        from pdfminer.high_level import extract_text
        out["pdfminer"] = extract_text(str(pdf))
    except Exception as e: out["pdfminer"] = ""
    try:
        from pypdf import PdfReader
        out["pypdf"] = "\n".join(p.extract_text() or "" for p in PdfReader(str(pdf)).pages)
    except Exception as e: out["pypdf"] = ""
    return out

def is_heading(line):
    t = re.sub(r"[^a-z& ]", " ", line.lower()).strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"^\d+\s+", "", t)             # "01 summary" 같은 번호 접두
    for key, names in HEADINGS.items():
        if t in names: return key
    # 추출기가 공백 하나를 끼운 경우("honors & a wards")만 허용 — 글자 단위 분리("e d u c a t i o n")는 불허
    sq = t.replace(" ", "")
    for key, names in HEADINGS.items():
        for n in names:
            if sq == n.replace(" ", "") and t.count(" ") <= n.count(" ") + 1: return key
    return None

def parse(text):
    """구조를 모르는 채로 이력서를 읽는다."""
    lines = [l.rstrip() for l in text.splitlines()]
    nonblank = [l for l in lines if l.strip()]
    name = nonblank[0].strip() if nonblank else ""
    emails = set(EMAIL.findall(text)); phones = set(p.strip() for p in PHONE.findall(text) if sum(c.isdigit() for c in p) >= 10)
    urls = set(u.rstrip(".,;·|") for u in URL.findall(text) if "@" not in u)
    sections, cur = {}, None
    for l in lines:
        s = l.strip()
        if not s: continue
        # 우측 정렬/여백이 큰 레이아웃에서는 헤딩이 한 줄 안에 다른 내용과 같이 올 수 있다 — 단어 수 5 이하만 헤딩 후보
        if len(s.split()) <= 5:
            h = is_heading(s)
            if h and h not in sections: sections[h] = []; cur = h; continue
        if cur: sections[cur].append(s)
    # 경력 항목 수: experience 섹션에서 날짜 범위가 있는 줄 수
    # 경력 항목 수 = 섹션 텍스트 안의 날짜 '범위' 수 (우측정렬 날짜가 별도 박스로 떨어져도 세어진다)
    RANGE = re.compile(r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}\s*[–-]\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}|present|current)", re.I)
    exp_entries = len(RANGE.findall(" ".join(sections.get("experience", []))))
    dates = len(DATE.findall(text))
    return dict(name=name, emails=len(emails), phones=len(phones), urls=len(urls),
                sections=sorted(sections), exp_entries=exp_entries, dates=dates, chars=len(text))

def grade(results, expect):
    """expect: dict(name, contacts=5, sections=[...], exp_entries=2)"""
    engines_ok = 0; notes = []
    for eng, r in results.items():
        if r["chars"] < 500: notes.append(f"{eng}: 텍스트 유실"); continue
        ok = True
        if not r["name"].lower().replace(" ","").startswith(expect["name"].lower().replace(" ","")[:6]): ok = False; notes.append(f"{eng}: 이름이 첫 줄 아님 ('{r['name'][:30]}')")
        if r["emails"] + r["phones"] + r["urls"] < expect["contacts"]: ok = False; notes.append(f"{eng}: 연락처 {r['emails']+r['phones']+r['urls']}/{expect['contacts']}")
        miss = [s for s in expect["sections"] if s not in r["sections"]]
        if miss: ok = False; notes.append(f"{eng}: 섹션 미식별 {miss}")
        if r["exp_entries"] != expect["exp_entries"]: notes.append(f"{eng}: 경력 항목 {r['exp_entries']}≠{expect['exp_entries']}"); ok = ok and False
        engines_ok += ok
    if any("유실" in n for n in notes): return "D", notes
    if engines_ok == len(results): return "A", notes
    if any("미식별" in n or "연락처" in n for n in notes) and engines_ok == 0: return "C", notes
    if engines_ok >= 2: return "B", notes
    return "C", notes

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("pdfs", nargs="+"); ap.add_argument("--json"); ap.add_argument("--expect")
    ap.add_argument("--theme", help="이 테마의 매니페스트 ats.generic 에 결과를 누적 기록")
    a = ap.parse_args()
    expect = json.loads(a.expect) if a.expect else dict(name="Taemin Kang", contacts=5, sections=["experience","education","projects","research","skills","honors"], exp_entries=2)
    report = {}
    for pdf in a.pdfs:
        res = {e: parse(t) for e, t in extract_all(pdf).items()}
        g, notes = grade(res, expect)
        report[pathlib.Path(pdf).stem] = dict(grade=g, notes=notes, engines=res)
        print(f"{pathlib.Path(pdf).stem:40s} {g}   " + (" | ".join(notes[:3]) if notes else "clean"))
    if a.json: pathlib.Path(a.json).write_text(json.dumps(report, indent=1, ensure_ascii=False))
    if a.theme:
        mp = ROOT/"themes"/a.theme/"manifest.json"; m = json.loads(mp.read_text())
        g = m.setdefault("ats", {}).setdefault("generic", {"cases": {}})
        for k, v in report.items(): g["cases"][k] = v["grade"]
        order = {"A": 0, "B": 1, "C": 2, "D": 3}
        worst = max(g["cases"].values(), key=lambda x: order[x])
        g["grade"] = worst
        g["tier"] = "ats-safe" if worst == "A" else ("distinctive" if worst in ("B",) else "distinctive-limited")
        g["method"] = "tools/ats_generic.py — structure-blind heading lexicon over poppler/pdfminer/pypdf, base + 4 mutations (tools/mutate.py)"
        mp.write_text(json.dumps(m, indent=2) + "\n")

if __name__ == "__main__":
    main()
