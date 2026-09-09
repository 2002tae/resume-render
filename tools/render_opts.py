#!/usr/bin/env python3
"""render_opts.py — 매니페스트 defaults 위에 호출자 옵션(JSON)을 얹어 렌더. Artemis 가 부를 방식 그대로.
usage: render_opts.py <ir.json> <theme> <out.pdf> '<options json>' [--density 0.9]"""
import json, sys, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"tools")); from ats_check import to_pdf
ir_p, theme, out, opts_json = sys.argv[1:5]
density = float(sys.argv[sys.argv.index("--density")+1]) if "--density" in sys.argv else 1.0
man=json.loads((ROOT/"themes"/theme/"manifest.json").read_text()); d=man.get("defaults",{}); o=json.loads(opts_json)
opts={**d,**o,"sections":{**d.get("sections",{}),**o.get("sections",{})},"layout":{**d.get("layout",{}),**o.get("layout",{})},
      "vars":{**d.get("vars",{}),**o.get("vars",{}),"--density":f"{density:.3f}"}}
js=f"""import {{ render }} from '{ROOT/"dist/index.js"}';
process.stdout.write(JSON.stringify(render(JSON.parse(process.argv[1]), JSON.parse(process.argv[2]))));"""
r=json.loads(subprocess.run(["node","--input-type=module","-e",js,json.dumps(json.loads(pathlib.Path(ir_p).read_text())),json.dumps(opts)],capture_output=True,text=True,check=True).stdout)
to_pdf(r["html"],theme,pathlib.Path(out))
info=subprocess.run(["pdfinfo",out],capture_output=True,text=True).stdout
print(theme,[l.split()[1] for l in info.splitlines() if l.startswith("Pages")][0]+"p","warnings:",r["warnings"])
