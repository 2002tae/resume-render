#!/usr/bin/env python3
"""test_manifest_write.py — the manifest writers must not erase each other's fields.

ats_check.py --write rebuilt the whole `ats` object and dropped `ats.generic`, which ats_generic.py writes and consumers
show as the tier badge. That is how 270efce shipped every manifest without a tier. This runs the REAL ats_check.py
--write for one theme against a copy of the repo and asserts `generic` survives.

  python3 tools/test_manifest_write.py            (needs weasyprint + poppler, like ats_check.py itself)
"""
import json, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
THEME = "marginalia"

with tempfile.TemporaryDirectory() as tmp:
    copy = pathlib.Path(tmp) / "rr"
    shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns("node_modules", "out", ".git", "tools/visual-ref"))
    mp = copy / "themes" / THEME / "manifest.json"
    m = json.loads(mp.read_text())
    marker = {"cases": {"base": "A"}, "grade": "A", "tier": "ats-safe", "method": "test marker"}
    m.setdefault("ats", {})["generic"] = marker
    mp.write_text(json.dumps(m, indent=2) + "\n")
    r = subprocess.run([sys.executable, str(copy / "tools" / "ats_check.py"), THEME, "--write"], capture_output=True, text=True, cwd=copy)
    after = json.loads(mp.read_text())
    ok = after.get("ats", {}).get("generic") == marker and "verified" in after.get("ats", {})
    print(("PASS" if ok else "FAIL") + f" — ats_check.py --write kept ats.generic for {THEME} (exit {r.returncode})")
    if not ok:
        print("ats after write:", json.dumps(after.get("ats"), indent=1)[:800])
        print(r.stdout[-800:], r.stderr[-800:])
    sys.exit(0 if ok else 1)
