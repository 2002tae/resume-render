# Claude Design 에 붙여넣을 프롬프트

첨부: `design-brief.html`

---

## 프롬프트 (그대로 복사)

```
Attached is `design-brief.html` — a résumé with REAL, FULL-LENGTH content already
marked up in a fixed semantic structure. Design stylesheets for it.

## The one rule that matters

Style it with CSS ONLY. Do not change the HTML — no adding, removing, reordering,
or rewrapping elements, and no inline style attributes. Every design must be
achievable purely by writing rules against the existing classes and data-attributes.
This is a hard constraint: these stylesheets get applied to other people's résumés
with different content, so the markup has to stay fixed.

## Do not touch the `.page` rules at the top of the file

`min-height` (not height), `overflow: visible`, and the dashed "page 1 ends" line
are there so I can SEE when content overflows. A design that looks clean only
because content is being clipped is a broken design. If your layout pushes past
the dashed line, that is real information — tighten the design rather than hiding it.

## Structure you are styling

.rz                     the document
.rz-basics              header block
  .rz-name              h1
  .rz-headline          one-line role
  .rz-contacts          ul > li.rz-contact[data-kind="email|phone|linkedin|github|website"]
.rz-section[data-section="summary|education|experiences|projects|research|skills|awards"]
  .rz-section-label     h2 — the section name
  .rz-entries           wrapper
    .rz-entry           one job / project / degree
      .rz-entry-head    > .rz-title, .rz-org, .rz-dates
      .rz-sub           degree line
      .rz-coursework    > .rz-kicker + text
      .rz-bullets       ul > li.rz-bullet[data-priority="1..5"]
  .rz-summary  .rz-skill > .rz-kicker + .rz-skill-items  .rz-awards

`data-section` lets you style or place sections individually.
`data-priority` marks how important each bullet is (1 = most).

## Constraints — these come from measured ATS failures, not taste

- Single-column content flow. No sidebars, no multi-column text, no layout tables.
- Real text only. No icons, no images, no text inside SVG.
- Do not reorder content visually away from DOM order (no `order`, no absolute
  repositioning that changes reading sequence).
- `.rz-contact` must never break mid-token — an email split across lines is
  unreadable to résumé parsers.
- No `letter-spacing` on body-level text. It makes extractors split words into
  single characters. Section labels at display sizes are fine.
- Place grid children explicitly with `grid-column`. Never rely on source order
  to land in the right track — some entries are missing fields, and a lone child
  silently falls into track 1.
- Avoid fixed-width columns. Use `minmax(0, …)` and `min-width: 0`.
- US Letter, 816 × 1056px at 96dpi.

## Expose everything as CSS custom properties

Colors, type sizes, spacing, and rule weights should all be variables on `.rz`,
so density and accent can be adjusted without touching the rules:

  --ink --mid --faint --accent --rule --paper
  --fs --lh --fs-name --fs-sec --fs-entry --fs-meta
  --sp-sec --sp-item --sp-bul --rw

Where a size is a scaled value, write it as calc(N * var(--density, 1)) so one
variable can compress the whole document to fit a page.

## What to produce

Six distinct stylesheets, each a self-contained `<style>` block I can drop in.
Make them genuinely different in typographic strategy, not just recolored:

1. Conservative serif — banking / consulting convention, quiet
2. Swiss grid — strict baseline rhythm, rules doing the work, one accent
3. Technical — mono section labels in a left column, dense, engineering feel
4. High-contrast minimal — near-zero ornament, typography carries everything
5. Editorial — magazine-like display typography, generous leading
6. Your own direction, same constraints

Use only OFL/open-licensed typefaces (EB Garamond, Newsreader, Source Serif 4,
Libre Franklin, Archivo, Instrument Serif, IBM Plex Sans/Mono, Bodoni Moda are
all fine) and name the exact families you use.

For each: render it, and tell me honestly whether the content fits above the
dashed page line or overflows.
```

---

## 왜 이렇게 바꿨나

| 이전 | 이번 | 이유 |
|---|---|---|
| 내용 적은 샘플 | **실제 전체 분량** (906단어, 무압축) | 넘침이 디자인 시점에 드러남 |
| `height:1056px` + `overflow:hidden` | `min-height` + `overflow:visible` + 점선 경계 | 잘림을 **숨기지 않음** |
| 인라인 style 1107개 | **CSS만, 클래스 대상** | 변환 작업 불필요 — 바로 테마 |
| 제약 없음 | ATS 실측 규칙 6개 | 만들고 나서 버리는 일 방지 |

**첨부 파일 하나만 주면 돼**: `design-brief.html`

---

## 결과 받으면

`<style>` 블록만 잘라서 나한테 주면 (또는 완성 HTML 그대로 줘도 됨):
1. `themes/<id>.css` 로 앉히고
2. fixture 3종(minimal · ragged · dense) × ATS 스위트 돌리고
3. 통과분을 매니페스트와 함께 레포에 커밋

지금 있는 12종 중 무손실 5종(`2a Classic` · `1d Minimal` · `1e Ledger` · `3e Numerals` · `3b Standfirst`)은
이 형식이 아니어도 내가 변환할 수 있어. 새로 뽑는 것만 이 프롬프트로 하면 돼.
