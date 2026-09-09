#!/usr/bin/env python3
"""sync_manifests.py — CSS 에서 파생되는 매니페스트 필드를 다시 계산한다 (baseBodyPx, fonts, page).
손으로 두면 낡는다(실측: broadsheet baseBodyPx 10.8 vs CSS 10 → body-lock 이 9.3pt 로 빗나감). npm run check 의 첫 단계."""
import json, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
GENERIC = {"Helvetica Neue","Georgia","Didot","Times New Roman","Arial","Menlo","ui-monospace","monospace","serif","sans-serif","Helvetica"}
changed = []
for d in sorted((ROOT/"themes").iterdir()):
    if not d.is_dir(): continue
    css = re.sub(r"/\*.*?\*/", "", (d/"theme.css").read_text(), flags=re.S)
    mp = d/"manifest.json"; m = json.loads(mp.read_text()); before = json.dumps(m, sort_keys=True)
    fs = re.search(r"--fs:calc\(([\d.]+)px", css) or re.search(r"\.rz\{[^}]*font-size:([\d.]+)px", css)
    if fs: m["baseBodyPx"] = float(fs.group(1))
    fams = set(re.findall(r"(?:font-family|--mono|--serif|--sans):[^;]*?'([^']+)'", css)) - GENERIC
    fmap = json.loads((ROOT/"fonts/map.json").read_text())["families"] if (ROOT/"fonts/map.json").exists() else {}
    m["fonts"] = [{"family": f, "license": "OFL", "files": fmap.get(f, [])} for f in sorted(fams)]
    m.setdefault("page", {})["orientation"] = "landscape" if "size:11in 8.5in" in css else "portrait"
    if json.dumps(m, sort_keys=True) != before:
        mp.write_text(json.dumps(m, indent=2) + "\n"); changed.append(d.name)
print("synced:", ", ".join(changed) or "(no change)")
