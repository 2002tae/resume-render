# resume-render

Structured résumé → canonical HTML → your choice of PDF backend.
**Templates are CSS only. Every theme is measured against real text extraction.**

```
IR (JSON)  ──render()──▶  canonical HTML  ──+ theme.css──▶  PDF
                                            (browser print · WeasyPrint · Playwright)
```

## Why this exists

Most résumé tools give you a template and hope it parses. This one:

- **Separates content from presentation completely.** The renderer emits one semantic HTML
  structure; a template is a single `theme.css`. A template cannot add, remove, or reorder text —
  so it cannot fabricate anything, and user-supplied templates are safe to accept.
- **Measures instead of promising.** Every theme is rendered against four fixtures (a sparse
  first-year résumé, a pathological one with missing fields and 60-character emails, a typical
  one-page résumé, and a dense real one) and run through `pdftotext` in two modes. The results are in each theme's
  `manifest.json`. The rules in `tools/lint_theme.py` all come from observed failures — there is
  no rule in there that didn't first break something.
- **Auto-fit is a real problem here, not an afterthought.** Every bullet carries a `priority`;
  every theme exposes a `--density` variable. Fitting to N pages is a search over those, not a
  font-size hack.

## Honest scope

- Two ATS checks, neither a claim about any specific vendor's parser.
  - `ats_check.py` knows the markup and verifies **text-layer integrity**: every string survives
    extraction, in order, with section labels and contacts intact. It catches what actually goes
    wrong: letter-spacing splitting words into characters, emails breaking mid-token, right-aligned
    dates landing inside wrapped titles, marginal labels being injected into paragraphs.
  - `ats_generic.py` does not know the markup. It grades what a generic heading-lexicon parser would
    identify across three extractors (poppler, pdfminer, pypdf), on the base résumé and four mutations
    of it; the grade is `ats.generic` in each manifest. It found a letter-spacing problem the first
    check had been rationalising.
- Two-column themes are marked `expressive`. Their text is complete in every extraction mode,
  but reading order is **not** preserved when a parser reads by visual position — sections from
  the two columns interleave. Each manifest's `ats.orderPreserved` says exactly which modes hold.
- The renderer does **not** produce PDF. It returns HTML. PDF is the consumer's choice:
  the browser's print dialog, WeasyPrint, Playwright. This keeps the library dependency-free and
  identical in Node and the browser.

## Layout

```
src/            TypeScript core — ir.ts (contract), render.ts (IR → HTML),
                browser.ts (adapter: buildDocument · mount · plan · print)
adapters/       python/resume_ir.py — Pydantic mirror of ir.ts for backends (schema, validation, loose input)
themes/         one directory per theme: theme.css + manifest.json
  _shared.css   structural defaults every theme inherits (page margin convention,
                UA neutralisation, robustness rules derived from fixtures)
fixtures/       minimal · ragged · typical · dense
tools/          lint_theme.py    static rules (R1–R11), each traceable to a measured failure
                ats_check.py     render every theme × fixture with manifest defaults, extract, verify
                fit.py           search density, then priority trimming, until the page target holds
                                 (also detects multicolumn overflow, which does not add pages)
                render_theme.py  render one theme with its manifest defaults
                capacity.py      max bullets per theme at a fixed body size ("how many at 10pt?")
                ats_generic.py   structure-blind check: 3 extractors × heading lexicon × mutations
                mutate.py        IR mutations for ats_generic (short name, no research, one job, flat skills)
                compare.py       side-by-side against the original Claude Design capture
                extract_roles.py transcribe a design's declarations by matching text, not DOM
                margin_check.py  no text in the paper's top/bottom margin on any page (1-page fit and a forced page 2)
                regression/      known-bad.css — every past defect, for the linter to catch
                plan.test.mjs    unit tests for the browser fitter (npm test)
docs/           ir.md · template-contract.md · design-prompt.md
examples/       design-brief.html — hand this to a designer; page frame makes overflow visible
```

## Install

Not on npm yet. Depend on the repo directly — `prepare` builds `dist/` on install:

```
npm install github:2002tae/resume-render
```

## Use

```ts
import { render } from "resume-render";

const { html, warnings } = render(ir, {
  sections: { order: ["summary", "experiences", "education", "skills"] },
  filter:   { maxBulletsPerEntry: 4, minPriority: 2 },
  vars:     { "--density": "0.92", "--accent": "#41556B" },
});
// wrap with themes/_shared.css + themes/<id>/theme.css, then print or convert.
```

`warnings` is never empty when something was dropped. If a section was omitted, an entry had
no bullets, or a field couldn't be rendered, it says so with a path.

## Themes

13 themes. Twelve are transcribed from a Claude Design original and checked against it side by side
(`tools/compare.py`); `plain` is a deliberately bare theme for unattended rendering. `profile` is the design axis; `ats.verified` is measured by `tools/ats_check.py`
— **with each theme's manifest `defaults` applied**, so the verified configuration is the shipped one.

| id | profile | pages | notes |
|---|---|---|---|
| classic · academic · minimal · ledger · numerals · masthead · standfirst · marginalia · colorfield · folio | safe | 1–2 | single column |
| plain | safe | 1–2 | engine `plain` for unattended fitz.Story rendering — **not yet verified in fitz** |
| broadsheet | expressive | **1 only** | two-column body, balanced; capacity ≈ 13 bullets (`capacity` in manifest) |
| spread | expressive | **1 only** | landscape open-book across a gutter |

Manifest `defaults` carry each design's own section order, label overrides and layout flags:

- `layout.summaryInHeader` — summary as an unlabeled lede inside the header (folio, marginalia, colorfield, spread)
- `layout.orgFirst` — CV convention: institution as the headline, role beneath (academic)
- `layout.skillsGrid` — aligned label column for skills; default is the originals' inline `Label  items` (minimal)

Fonts are OFL: EB Garamond, Newsreader, Source Serif 4, Instrument Serif, Bodoni Moda, Libre Franklin,
Archivo, Space Grotesk, IBM Plex Mono — upright **and italic** files, plus `ArchivoCond` / `ArchivoSemiCond`
instanced from Archivo's `wdth` axis because WeasyPrint ignores `font-stretch`.

## Verify

```
npm install && npm run build
pip install -r requirements.txt          # verification tools only; needs poppler-utils on PATH
npm test                                 # type-check + unit tests
npm run check                            # syncs manifests, then runs the four checks below (ats_check without --write)
python3 tools/lint_theme.py themes/*/theme.css
python3 tools/visual_check.py         # pixel diff against tools/visual-ref — catches layout breaks ATS can't
python3 tools/margin_check.py         # no text in the top/bottom page margin, on page 1 and a forced page 2
python3 tools/ats_check.py --write    # ~2 min, needs weasyprint + poppler; writes ats.* into manifests
```

## Writing a theme

Open `examples/design-brief.html`. It is real, full-length content in the canonical structure
with a visible page boundary. Style `.rz` and its descendants — nothing else. Then run the two
checks above. The linter will tell you if you used `letter-spacing` on body text, relied on
source order in a grid, or reached for `display:contents` (WeasyPrint ignores it). The ATS check
will tell you if a real name breaks mid-word at your display size.

`docs/template-contract.md` has the full rules and the measurements behind each one.

## License

MIT for the code. Themes are MIT. Fonts carry their own OFL licenses in `fonts/`.
