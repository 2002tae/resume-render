#!/usr/bin/env python3
"""render_theme.py — 매니페스트 defaults(layout·sections)를 적용해 한 테마를 렌더한다.
usage: python3 tools/render_theme.py fixtures/dense.json <theme> <out.pdf> [--density 0.9] [--min-priority 2]
"""
import json, sys, pathlib, subprocess, argparse
ROOT=pathlib.Path(__file__).resolve().parent.parent
if not (ROOT/"dist/index.js").exists():
    raise SystemExit("dist/index.js not found — run `npm install && npm run build` first (the tools render through the compiled library)")
sys.path.insert(0,str(ROOT/"tools")); from ats_check import to_pdf

def render(ir, theme, density=1.0, min_priority=None, extra=None):
    man=json.loads((ROOT/"themes"/theme/"manifest.json").read_text())
    d=man.get("defaults",{}); e=extra or {}
    opts={**d,**e,"sections":{**d.get("sections",{}),**e.get("sections",{})},"layout":{**d.get("layout",{}),**e.get("layout",{})},"vars":{**d.get("vars",{}),**e.get("vars",{})}}
    opts.setdefault("vars",{})["--density"]=f"{density:.3f}"
    if min_priority: opts.setdefault("filter",{})["minPriority"]=min_priority
    js=f"""import {{ render }} from '{ROOT/"dist/index.js"}';
    const r=render(JSON.parse(process.argv[1]), JSON.parse(process.argv[2]));
    process.stdout.write(JSON.stringify(r));"""
    out=subprocess.run(["node","--input-type=module","-e",js,json.dumps(ir),json.dumps(opts)],
                       capture_output=True,text=True,check=True).stdout
    return json.loads(out)

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("ir"); ap.add_argument("theme"); ap.add_argument("out")
    ap.add_argument("--density",type=float,default=1.0); ap.add_argument("--min-priority",type=int)
    a=ap.parse_args()
    ir=json.loads(pathlib.Path(a.ir).read_text())
    r=render(ir,a.theme,a.density,a.min_priority)
    to_pdf(r["html"],a.theme,pathlib.Path(a.out))
    info=subprocess.run(["pdfinfo",a.out],capture_output=True,text=True).stdout
    print(a.theme, [l.split()[1] for l in info.splitlines() if l.startswith("Pages")][0]+"p", "warnings:",len(r["warnings"]))
