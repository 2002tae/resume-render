#!/bin/bash
# 테마 목록을 받아 기본 + 변이 4종을 렌더하고 ats_generic 으로 판정. 결과는 out/gen/<theme>.txt
cd "$(dirname "$0")/.."
for t in "$@"; do
  d=$(python3 -c "import json;print(json.load(open('tools/visual-ref/params.json')).get('$t',1.0))")
  mkdir -p out/gen/$t; : > out/gen/$t.txt
  python3 tools/render_theme.py fixtures/dense.json $t out/gen/$t/base.pdf --density $d >/dev/null 2>&1
  python3 tools/ats_generic.py out/gen/$t/base.pdf --theme $t >> out/gen/$t.txt 2>&1
  for m in short-name no-research-honors one-job-no-summary flat-skills; do
    python3 tools/render_theme.py out/mut/$m.json $t out/gen/$t/$m.pdf --density $d >/dev/null 2>&1
    python3 tools/ats_generic.py out/gen/$t/$m.pdf --expect "$(cat out/mut/$m.expect.json)" --theme $t >> out/gen/$t.txt 2>&1
  done
  echo "== $t =="; cat out/gen/$t.txt
done
