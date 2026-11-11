// render() sections that are easy to break silently. `npm test` builds first.
import { test } from "node:test"
import assert from "node:assert/strict"
import { render } from "../dist/index.js"

const base = { version: "1.0", basics: { name: "A B" } }

test("publications render as entries (title + date head, authors · venue · note sub line)", () => {
  const ir = { ...base, publications: [
    { title: "A Poster Title", venue: "Some Exhibition", note: "An award", date: { year: 2026, month: 10 } },
    { title: "A Manuscript", authors: ["A B", "C D"], venue: "Manuscript in preparation", date: { year: 2026 } },
  ] }
  const { html, warnings } = render(ir, { sections: { order: ["publications"], labels: { publications: "Presentations" } } })
  assert.equal(warnings.filter((w) => w.code === "UNKNOWN_SECTION").length, 0)
  assert.match(html, /data-section="publications"/)
  assert.match(html, /<h2 class="rz-section-label">Presentations<\/h2>/)
  assert.equal((html.match(/class="rz-entry"/g) ?? []).length, 2)
  assert.match(html, /<span class="rz-title">A Poster Title<\/span>/)
  assert.match(html, /data-raw="Oct 2026"/)
  assert.match(html, /<p class="rz-sub">Some Exhibition · An award<\/p>/)
  assert.match(html, /<p class="rz-sub">A B, C D · Manuscript in preparation<\/p>/)
  assert.match(html, /data-raw="2026"/)
})

test("an empty publications list renders nothing", () => {
  const { html } = render({ ...base, publications: [] }, { sections: { order: ["publications"] } })
  assert.doesNotMatch(html, /data-section="publications"/)
})
