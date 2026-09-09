#!/usr/bin/env python3
"""mutate.py — 식별성 검사용 IR 변이. usage: mutate.py <ir.json> <outdir>"""
import json, sys, pathlib
ir=json.loads(pathlib.Path(sys.argv[1]).read_text()); out=pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
def w(name, m, expect): (out/f"{name}.json").write_text(json.dumps(m)); (out/f"{name}.expect.json").write_text(json.dumps(expect))
base_exp=dict(name="Taemin Kang", contacts=5, sections=["experience","education","projects","research","skills","honors"], exp_entries=2)
# 1 짧은 이름 + 연락처 3개
m=json.loads(json.dumps(ir)); m["basics"]["name"]="Li Wu"; m["basics"]["contacts"]=m["basics"]["contacts"][:3]
w("short-name", m, {**base_exp, "name":"Li Wu", "contacts":3})
# 2 연구·수상 없음 (전형적 학부생)
m=json.loads(json.dumps(ir)); m.pop("research"); m.pop("awards")
w("no-research-honors", m, {**base_exp, "sections":["experience","education","projects","skills"]})
# 3 경력 1개, 요약 없음
m=json.loads(json.dumps(ir)); m["experiences"]=m["experiences"][:1]; m.pop("summary")
w("one-job-no-summary", m, {**base_exp, "exp_entries":1})
# 4 스킬이 평면 문자열 (라벨 없음)
m=json.loads(json.dumps(ir)); m["skills"]=[x for g in m["skills"] for x in g["items"]][:14]
w("flat-skills", m, base_exp)
print("변이 4종 →", out)
