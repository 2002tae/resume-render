// plan() with a stub measurer — no browser. `npm run build && node --test tools/`
//
// The stub reads the density plan() rendered at (the --density var) and the number of bullets left, and reports a
// height that overflows one letter page at density 1 and fits at about 0.92. That is the shape of a real résumé a
// little too long for its theme, which is exactly the case the phantom 10pt floor broke: before the fix,
// {compact, trim:"none"} came back infeasible, and {compact, trim:"ask"} trimmed bullets at density > 1.
import { test } from "node:test"
import assert from "node:assert/strict"
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { plan } from "../dist/browser.js"

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..")
const ir = JSON.parse(fs.readFileSync(path.join(ROOT, "fixtures/typical.json"), "utf8"))
const bulletsIn = (x) => (["experiences", "projects", "research"]).reduce((n, k) => n + (x[k] ?? []).reduce((m, e) => m + (e.bullets ?? []).length, 0), 0)
const TOTAL = bulletsIn(ir)
const PAGE_H = 1056 // letter portrait, CSS px

const assetsFor = (theme) => ({
  sharedCss: fs.readFileSync(path.join(ROOT, "themes/_shared.css"), "utf8"),
  themeCss: fs.readFileSync(path.join(ROOT, `themes/${theme}/theme.css`), "utf8"),
  manifest: JSON.parse(fs.readFileSync(path.join(ROOT, `themes/${theme}/manifest.json`), "utf8")),
})

// height = 1.08 pages × density, scaled down as bullets are removed (bullets are half the page)
const measure = async (html) => {
  const d = Number(/style="[^"]*--density:([0-9.]+)/.exec(html)?.[1] ?? "1")
  const li = (html.match(/<li\b/g) ?? []).length
  const share = TOTAL ? Math.min(1, li / TOTAL) : 1
  return PAGE_H * 1.08 * d * (0.5 + 0.5 * share)
}

const densities = (p) => p.options.filter((o) => "density" in o).map((o) => o.density)

for (const theme of ["classic", "broadsheet", "minimal"]) {
  test(`${theme}: an overflowing résumé shrinks under {compact, trim:"none"}`, async () => {
    assert.ok(TOTAL > 0, "fixture has bullets")
    const p = await plan(ir, assetsFor(theme), { mode: "compact", pages: 1, trim: "none" }, measure)
    assert.equal(p.feasible, true, JSON.stringify(p.options))
    assert.equal(p.options[0].kind, "shrink")
    assert.ok(p.best.density < 1 && p.best.density >= 0.82, `density ${p.best.density}`)
    assert.deepEqual(p.best.removed, [])
  })

  test(`${theme}: {compact, trim:"ask"} shrinks before it trims, and never enlarges`, async () => {
    const p = await plan(ir, assetsFor(theme), { mode: "compact", pages: 1, trim: "ask" }, measure)
    assert.equal(p.options[0].kind, "shrink", JSON.stringify(p.options))
    for (const d of densities(p)) assert.ok(d <= 1, `an option at density ${d} > 1`)
  })
}

test("a policy WITH minBodyPt still takes the body-lock path (unchanged)", async () => {
  const p = await plan(ir, assetsFor("classic"), { mode: "compact", pages: 1, minBodyPt: 10, trim: "ask" }, measure)
  for (const o of p.options) if ("bodyPt" in o && o.kind !== "overflow") assert.equal(o.bodyPt, 10)
})
