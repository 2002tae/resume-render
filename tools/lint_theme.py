#!/usr/bin/env python3
"""
lint_theme.py — 테마 CSS 규칙 검사

규칙은 전부 실측된 파손에서 도출됐다. 근거는 각 규칙의 docstring 참조.
usage: python3 lint_theme.py themes/*.css
"""
import re, sys, pathlib
import tinycss2

# letter-spacing 이 허용되는 선택자 — 디스플레이 크기라 글자 분리가 관측되지 않음
LETTERSPACING_OK = {".rz-name", ".rz-section-label"}

# 그리드 컨테이너 → 그 안에 오는 자식 선택자 (정규 HTML 기준)
GRID_CHILDREN = {
    ".rz-basics":     [".rz-name", ".rz-headline", ".rz-contacts"],
    ".rz-section":    [".rz-section-label", ".rz-entries"],
    ".rz-entry-head": [".rz-title", ".rz-org", ".rz-dates"],
    ".rz-skill":      [".rz-kicker", ".rz-skill-items"],
}
GRID_CONTAINERS = set(GRID_CHILDREN)


def decls(content):
    out = []
    for d in tinycss2.parse_blocks_contents(content):
        if d.type == "declaration":
            val = tinycss2.serialize(d.value).strip()
            out.append((d.lower_name, val))
    return out


def lint(path):
    css = pathlib.Path(path).read_text()
    rules = tinycss2.parse_stylesheet(css, skip_whitespace=True, skip_comments=True)
    problems = []
    seen_grid_cols = {}      # selector -> track list
    has_grid_column = set()  # selectors that declare grid-column
    contact_nowrap = False
    all_selectors = []

    def err(code, msg, sel=""):  problems.append(("ERROR", code, msg, sel))
    def warn(code, msg, sel=""): problems.append(("WARN",  code, msg, sel))

    for rule in rules:
        if rule.type == "at-rule":
            if rule.lower_at_keyword == "import":
                err("R5-IMPORT",
                    "@import 는 인라인 <style> 에서 해석되지 않는다. 빌드가 명시적으로 연결할 것")
            continue
        if rule.type != "qualified-rule":
            continue
        sel = tinycss2.serialize(rule.prelude).strip()
        all_selectors.append(sel)
        ds = dict(decls(rule.content))

        # ── R4: 본문급 요소의 letter-spacing → 추출기가 글자를 분리 (3회 재발)
        if "letter-spacing" in ds:
            _ls = ds["letter-spacing"].strip()
            # 음수 자간은 글자를 벌리지 않고 좁히므로 분리 위험이 없다
            _neg = _ls.startswith("-")
            base = re.findall(r"\.rz[\w-]*", sel)
            # 실측: .006em/.012em 은 통과, .08em/.14em 은 글자 분리. 0·음수는 무해.
            _m = re.match(r"([\d.]+)\s*em", _ls)
            _small = _ls in ("0","normal") or (_m and float(_m.group(1)) < 0.03)
            if _neg:
                warn("R4-LETTERSPACING-NEG",
                     f"음수 자간은 추출엔 안전하나 WeasyPrint 가 intrinsic 폭을 실제보다 작게 계산해 "
                     f"flex 아이템(제목 등)이 조기 줄바꿈된다(실측) ({_ls})", sel)
            elif _small:
                if _m and float(_m.group(1)) > 0:
                    warn("R4-LETTERSPACING-TIGHT",
                         f"작은 양수 자간 — 실측상 안전하나 ATS 스위트로 확인할 것 ({_ls})", sel)
            elif _m and float(_m.group(1)) > 0.08:
                # 실측(4 엔진): 0.08em 까지 안전, 0.1em 부터 poppler·pdfminer 가 'E D U C A T I O N' 으로 분리.
                # 섹션 라벨 예외는 없다 — 일반 ATS 헤딩 매처가 그 문자열을 못 읽는다.
                err("R4-LETTERSPACING-CAP",
                    f"자간 {_ls} > 0.08em — 헤딩이 글자 단위로 분리되어 섹션 식별 실패 (실측)", sel)
            elif not base or not set(base) & LETTERSPACING_OK:
                err("R4-LETTERSPACING",
                    f"본문급 요소의 letter-spacing 은 'C O U R S E W O R K' 분리를 유발한다 "
                    f"({ds['letter-spacing']})", sel)
            else:
                warn("R4-LETTERSPACING-DISPLAY",
                     f"디스플레이 요소의 letter-spacing — 추출 확인 권장 ({ds['letter-spacing']})", sel)

        # ── R3a: overflow-wrap:anywhere → 이메일을 토큰 중간에서 절단
        if ds.get("overflow-wrap", "").lower() == "anywhere" or ds.get("word-break", "").lower() == "break-all":
            err("R3-ANYWHERE",
                "overflow-wrap:anywhere / word-break:break-all 은 이메일·URL 을 중간에서 끊는다. "
                "break-word 를 쓸 것", sel)

        # ── R3b: 연락처는 원자 단위
        if ".rz-contact" in sel and ds.get("white-space", "").lower().startswith("nowrap"):
            contact_nowrap = True

        # ── R6: 읽기 순서를 시각 순서와 어긋나게 하는 속성
        if "order" in ds and ds["order"].strip().lstrip("-").isdigit():
            err("R6-ORDER", "order 는 DOM 순서와 시각 순서를 어긋나게 한다", sel)
        if ds.get("position", "").lower() == "absolute" and re.search(r"\.rz-(section|entry|bullet)\b", sel):
            if not re.search(r"::(before|after)", sel):
                err("R6-ABSOLUTE", "콘텐츠 블록의 absolute 배치는 읽기 순서를 깨뜨린다", sel)

        # ── R10: 불릿 마커가 텍스트 글리프면 stream 추출에서 줄바꿈 지점에 삽입된다(실측)
        if ".rz-bullet::before" in sel or ".rz-bullet::after" in sel:
            c = ds.get("content", "").strip().strip('"').strip("'")
            # 실측 결함은 절대배치 마커(top 오프셋)가 다른 줄에 걸려 삽입된 것. 인라인 흐름 글리프는
            # 텍스트 앞에 순서대로 읽힌다(plain 테마, ATS 통과) — 절대배치일 때만 오류
            if c and not c.startswith("counter(") and ds.get("position", "").strip() == "absolute":
                err("R10-GLYPH-MARKER",
                    f"불릿 마커 '{c}' 는 추출되는 텍스트다. content:\"\" + 박스(width/height/background)로 그릴 것", sel)

        # ── R9: display:contents 는 WeasyPrint 에서 미지원 — 래퍼가 그리드 아이템이 된다(실측)
        if ds.get("display", "").strip().lower() == "contents":
            err("R9-DISPLAY-CONTENTS",
                "display:contents 는 WeasyPrint 에서 무시되어 자식이 한 셀에 뭉친다", sel)

        # ── R8: grid-column: 1/-1 은 WeasyPrint 69 에서 폭이 거터값으로 계산된다(실측)
        gc = ds.get("grid-column", "")
        if re.search(r"/\s*-1", gc):
            err("R8-SPAN-MINUS1",
                "grid-column 의 -1 라인은 WeasyPrint 에서 폭이 거터값으로 잘못 계산된다. "
                "명시적 라인 번호나 span N 을 쓸 것", sel)

        # ── R7: 다단 조판
        if "column-count" in ds or ("columns" in ds and "px" in ds.get("columns", "")):
            err("R7-MULTICOL", "다단 조판은 추출 읽기 순서를 깨뜨린다", sel)

        # ── R1/R2: 그리드 트랙
        gtc = ds.get("grid-template-columns")
        if gtc:
            tracks = [t for t in re.split(r"\s+(?![^(]*\))", gtc) if t]
            if len(tracks) >= 2:
                seen_grid_cols[sel] = tracks
                # R2: minmax 없는 고정폭 트랙
                for t in tracks:
                    if re.fullmatch(r"\d+(\.\d+)?(px|pt|em|rem)", t):
                        warn("R2-FIXEDTRACK",
                             f"고정폭 트랙 '{t}' 은 내용이 길면 깨진다. minmax(0,…) 권장", sel)
        if "grid-column" in ds:
            has_grid_column.add(sel)

    # ── R1: 2트랙 이상 그리드인데 자식 배치가 명시되지 않음
    for sel, tracks in seen_grid_cols.items():
        base = next((b for b in GRID_CONTAINERS if b in sel), None)
        if not base:
            continue
        kids = GRID_CHILDREN[base]
        placed = [s for s in has_grid_column
                  if any(k in s for k in kids) or (base in s and s != sel)]
        if len(placed) < 2:
            err("R1-IMPLICIT-PLACEMENT",
                f"{len(tracks)}트랙 그리드인데 자식 grid-column 이 {len(placed)}개만 명시됨. "
                f"필드가 빠진 엔트리에서 자식이 트랙1로 떨어진다", sel)

    # ── R3b 최종
    if any(".rz-contact" in s for s in all_selectors) and not contact_nowrap:
        warn("R3-CONTACT-ATOMIC",
             ".rz-contact 에 white-space:nowrap 이 없다. _shared.css 가 제공하면 무시 가능")

    return problems


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    shared_ok = "--shared" in sys.argv or pathlib.Path("themes/_shared.css").exists() or pathlib.Path(__file__).resolve().parent.parent.joinpath("themes/_shared.css").exists()
    paths = args or sorted(pathlib.Path("themes").glob("*.css"))
    total_err = 0
    for p in paths:
        probs = lint(p)
        probs = [x for x in probs if not (x[1] == "R3-CONTACT-ATOMIC" and shared_ok)]
        errs = [x for x in probs if x[0] == "ERROR"]
        total_err += len(errs)
        status = "FAIL" if errs else ("WARN" if probs else "PASS")
        print(f"[{status}] {pathlib.Path(p).name}")
        for lvl, code, msg, sel in probs:
            if code == "R3-CONTACT-ATOMIC" and shared_ok:
                continue
            mark = "✗" if lvl == "ERROR" else "!"
            print(f"    {mark} {code:26s} {msg}")
            if sel: print(f"      선택자: {sel[:80]}")
    sys.exit(1 if total_err else 0)
