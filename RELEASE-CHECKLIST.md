# Release checklist

Run from a **fresh extract**, not the working tree. Every item below was checked for v0.1.0.

## Repo (public GitHub)
- [x] No personal contact data: phone masked in fixtures / examples / snapshots. Name and project
      content are deliberately real — this is a portfolio repo.
- [x] `npm install && npm run build` on a clean checkout (typescript is a devDependency).
- [x] `pip install -r requirements.txt` declares every tool import; poppler-utils noted as system dep.
- [x] Fonts: OFL text bundled per family (`fonts/licenses/`), derivative instances documented,
      no Reserved Font Name reused (IBM Plex ships unmodified).
- [x] No hardcoded environment paths in `tools/` (`compare.py` takes the capture as an argument).
- [x] README promises only what `src/index.ts` exports (`render`). `normalize()` / `plan()` are
      documented as contracts, not shipped code.
- [x] `npm run check` = lint (0 errors) + visual regression (12/12) + ATS (12/12, manifest defaults).
- [x] `package.json`: license, repository, author, engines, files.

## Shipped for integration (this release)
- `src/browser.ts` — `buildDocument` · `mount` · `plan` (DOM-measured, mirrors tools/fit.py) · `printCurrent`
- `adapters/python/resume_ir.py` — Pydantic IR (schema for structured output, validation, loose input)
- `themes/plain` — engine `plain` for fitz.Story; **unverified in fitz** (no PyMuPDF here), flagged in manifest

## Not in this release (documented, not hidden)
- `normalize()` in TS — backends use the Pydantic model instead.
- Markdown parser.
- Paged.js preview — `mount()` uses a plain iframe; the browser's own pagination is what prints.

## Artemis integration (separate track, not blocked by this release)
- `GET /resume-templates` from `themes/*/manifest.json` (wire format in docs/template-contract.md §6).
- Add `plain` engine template for the unattended fitz path.
- Web/extension import `dist/index.js`, render with manifest `defaults`, print via browser.
- `plan()` port to browser (measure `.rz` height in DOM).
