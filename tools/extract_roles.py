#!/usr/bin/env python3
"""
extract_roles.py — 원본 변형에서 역할별 스타일 선언을 전사한다.

구조가 아니라 **텍스트 내용**으로 역할을 판별하므로, 변형마다 DOM 이 달라도 매칭된다.
"""
import json, re, sys, pathlib
from html.parser import HTMLParser

# 역할 판별용 텍스트 지문 (원본 콘텐츠 기준)
FINGERPRINTS = [
    ("name",          lambda t: t.strip() == "Taemin Kang"),
    ("headline",      lambda t: t.strip().lower().rstrip(" ·|") in
                                ("data engineering","data engineer","curriculum vitae")),
    ("contact",       lambda t: "taemin.kang@gmail.com" in t),
    ("section-label", lambda t: t.strip() in ("Summary","Education","Experience","Projects",
                                              "Research","Skills","Honors","Curriculum vitae",
                                              "Research Experience","Professional Experience",
                                              "Selected Projects","Technical Skills","Honors & Awards")),
    ("title",         lambda t: t.strip().startswith("Solo Developer")),
    ("org",           lambda t: "Artemis" in t and "Career Platform" in t),
    ("dates",         lambda t: t.strip().startswith("Mar 2026")),
    ("summary",       lambda t: "Data engineer who builds" in t),
    ("bullet",        lambda t: "Engineered a Postgres" in t),
    ("kicker",        lambda t: t.strip().rstrip(":").lower() in ("coursework","languages","data","pipelines")),
    ("sub",           lambda t: t.strip().startswith("B.S. Computational")),
    ("awards",        lambda t: t.strip().startswith("Sung and Fumi")),
]

class Walker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []          # [(tag, style)]
        self.found = {}          # role -> [(tag, own_style, ancestor_styles)]
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        self.stack.append((tag, d.get("style", ""), d.get("class", "")))
        if tag in ("br","img","hr"): self.stack.pop()
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
    def handle_data(self, data):
        t = data.strip()
        if not t: return
        for role, test in FINGERPRINTS:
            if role in self.found: continue
            try:
                if test(t):
                    own = self.stack[-1] if self.stack else ("", "", "")
                    parent = self.stack[-2] if len(self.stack) > 1 else ("", "", "")
                    gp = self.stack[-3] if len(self.stack) > 2 else ("", "", "")
                    self.found[role] = {
                        "tag": own[0], "style": own[1],
                        "parent_tag": parent[0], "parent_style": parent[1],
                        "gp_tag": gp[0], "gp_style": gp[1],
                    }
            except Exception:
                pass

def extract(label, frag):
    w = Walker(); w.feed(frag)
    return w.found

if __name__ == "__main__":
    V = json.loads(pathlib.Path("variants.json").read_text())
    targets = sys.argv[1:] or list(V)
    out = {}
    for label in targets:
        if label not in V:
            match = [k for k in V if label.lower() in k.lower()]
            if not match: print(f"(없음) {label}"); continue
            label = match[0]
        roles = extract(label, V[label])
        out[label] = roles
        print(f"\n=== {label} — {len(roles)}개 역할 매칭 ===")
        for role in ("name","headline","contact","section-label","title","org","dates",
                     "summary","bullet","kicker","sub","awards"):
            r = roles.get(role)
            if not r: print(f"  {role:14s} (매칭 실패)"); continue
            print(f"  {role:14s} <{r['tag']}> {r['style'][:118]}")
            if r["parent_style"]:
                print(f"  {'':14s}   ↳부모<{r['parent_tag']}> {r['parent_style'][:104]}")
    pathlib.Path("roles.json").write_text(json.dumps(out, indent=1))
