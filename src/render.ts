import type {
  ResumeIR, RenderOptions, RenderResult, Warning, SectionKey,
  Bullet, LooseBullet, Contact, LooseContact, DateRange, SkillGroup,
} from "./ir.js";

/**
 * render(ir, options) → canonical semantic HTML.
 *
 * Pure. No I/O. Assumes a valid IR (run normalize() first for loose input).
 * Templates style this markup with CSS only — they never see or change it.
 */

const DEFAULT_ORDER: SectionKey[] = [
  "summary", "education", "experiences", "projects", "research",
  "skills", "awards", "publications", "certifications", "languages",
];

const DEFAULT_LABELS: Record<SectionKey, string> = {
  summary: "Summary", education: "Education", experiences: "Experience",
  projects: "Projects", research: "Research", skills: "Skills", awards: "Honors",
  publications: "Publications", certifications: "Certifications", languages: "Languages",
};

const esc = (s: unknown): string =>
  String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/**
 * vars go into a style attribute, so they are a CSS injection surface even with quotes escaped
 * (`;background:url(...)` would load an external resource). Only custom properties are accepted,
 * and values are restricted to a conservative charset — no `;`, `}`, `(`, `<`, `"`, `\`.
 */
const SAFE_VAR_KEY = /^--[a-z0-9-]+$/i;
const SAFE_VAR_VAL = /^[a-z0-9 .,%#+-]+$/i;
const safeVars = (vars: Record<string, string> | undefined, warn: (c: Warning["code"], m: string, p?: string) => void) =>
  Object.entries(vars ?? {}).filter(([k, v]) => {
    const ok = SAFE_VAR_KEY.test(k) && SAFE_VAR_VAL.test(v);
    if (!ok) warn("LOOSE_INPUT", `rejected unsafe css var ${k}`, `options.vars.${k}`);
    return ok;
  });

/** Only **bold** is honored. Everything else is escaped literally. */
const inline = (s: string): string =>
  esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

const dateRaw = (d?: DateRange | string): string =>
  typeof d === "string" ? d : d?.raw ?? "";

const asBullet = (b: LooseBullet): Bullet => (typeof b === "string" ? { text: b } : b);

const CONTACT_KIND = (v: string): Contact["kind"] => {
  if (v.includes("@")) return "email";
  if (/linkedin\.com/i.test(v)) return "linkedin";
  if (/github\.com/i.test(v)) return "github";
  if (/^\+?[\d\s().-]{5,}$/.test(v) && /\d{3}/.test(v)) return "phone";
  if (/\./.test(v)) return "website";
  return "other";
};
const asContact = (c: LooseContact): Contact =>
  typeof c === "string" ? { kind: CONTACT_KIND(c), value: c } : c;

export function render(ir: ResumeIR, opts: RenderOptions = {}): RenderResult {
  const warnings: Warning[] = [];
  const warn = (code: Warning["code"], message: string, path?: string) =>
    warnings.push({ code, message, path });

  const labels = { ...DEFAULT_LABELS, ...(opts.sections?.labels ?? {}) };
  let order = opts.sections?.order ?? DEFAULT_ORDER;
  if (opts.sections?.include) order = order.filter((k) => opts.sections!.include!.includes(k));
  if (opts.sections?.exclude) order = order.filter((k) => !opts.sections!.exclude!.includes(k));

  const filterBullets = (bs: LooseBullet[] | undefined, path: string): Bullet[] => {
    let out = (bs ?? []).map(asBullet);
    const f = opts.filter;
    if (f?.tags?.length) out = out.filter((b) => !b.tags || b.tags.some((t) => f.tags!.includes(t)));
    if (f?.minPriority != null) out = out.filter((b) => (b.priority ?? 99) <= f.minPriority!);
    if (f?.maxBulletsPerEntry != null) out = out.slice(0, f.maxBulletsPerEntry);
    if (bs && bs.length && !out.length) warn("ENTRY_NO_BULLETS", "all bullets filtered out", path);
    return out;
  };

  const bulletsHtml = (bs: Bullet[], path: string): string => {
    if (!bs.length) return "";
    return `<ul class="rz-bullets">` + bs.map((b) =>
      `<li class="rz-bullet"${b.priority != null ? ` data-priority="${b.priority}"` : ""}>${inline(b.text)}</li>`
    ).join("") + `</ul>`;
  };

  const headHtml = (title: string, org?: string, dates?: string, allowOrgFirst = false): string => {
    // CV 관례(orgFirst): 기관명이 표제, 직함은 그 다음. experiences·research 에만 — education 의 org 슬롯은
    // 위치, projects 의 org 슬롯은 role 이라 뒤집으면 뜻이 깨진다. DOM 순서를 바꾸므로 추출 순서도 같이 바뀐다.
    const t = `<span class="rz-title">${esc(title)}</span>`;
    const o = org ? `<span class="rz-org">${esc(org)}</span>` : "";
    const d = dates ? `<span class="rz-dates" data-raw="${esc(dates)}">${esc(dates)}</span>` : "";
    // orgFirst 는 org·dates·title 순: 날짜가 org 와 같은 줄 흐름에 있어야 pdfminer 류가 떼어내지 않는다(실측)
    const parts = allowOrgFirst && opts.layout?.orgFirst && o ? [o, d, t] : [t, ...(o ? [o] : []), d];
    return `<div class="rz-entry-head">${parts.join("")}</div>`;
  };

  const section = (key: SectionKey, inner: string): string =>
    `<section class="rz-section" data-section="${key}">` +
    `<h2 class="rz-section-label">${esc(labels[key])}</h2>` +
    `<div class="rz-entries">${inner}</div></section>`;

  // ── header
  const b = ir.basics ?? {};
  if (!b.name) warn("MISSING_NAME", "basics.name is missing; header name omitted", "basics.name");
  const contacts = (b.contacts ?? []).map(asContact)
    .map((c) => `<li class="rz-contact" data-kind="${esc(c.kind)}">${esc(c.value)}</li>`).join("");
  const summaryInHeader = !!opts.layout?.summaryInHeader && !!ir.summary?.text && order.includes("summary");
  const header =
    `<header class="rz-basics">` +
    (b.name ? `<h1 class="rz-name">${esc(b.name)}</h1>` : "") +
    (b.headline ? `<p class="rz-headline">${esc(b.headline)}</p>` : "") +
    (summaryInHeader ? `<p class="rz-summary rz-summary--header">${inline(ir.summary!.text!)}</p>` : "") +
    (contacts ? `<ul class="rz-contacts">${contacts}</ul>` : "") +
    `</header>`;
  if (summaryInHeader) order = order.filter((k) => k !== "summary");

  const out: string[] = [header];

  for (const key of order) {
    switch (key) {
      case "summary": {
        const s = ir.summary;
        if (!s) break;
        if (s.style === "bullets" && s.bullets?.length) {
          out.push(section(key, bulletsHtml(filterBullets(s.bullets, "summary"), "summary")));
        } else if (s.text) {
          out.push(section(key, `<p class="rz-summary">${inline(s.text)}</p>`));
        } else warn("SECTION_EMPTY", "summary has no text", "summary");
        break;
      }
      case "education": {
        const list = ir.education ?? [];
        if (!list.length) break;
        const inner = list.map((ed, i) => {
          const g = ed.gpa;
          const sub = [ed.degree, ed.minor ? `Minor in ${ed.minor}` : undefined,
            g ? `${g.label ?? "GPA"} ${g.value}${g.scale ? ` / ${g.scale}` : ""}` : undefined]
            .filter(Boolean).join(" · ");
          const bs = filterBullets(ed.details, `education[${i}]`);
          return `<div class="rz-entry">` +
            headHtml(ed.school, ed.location, dateRaw(ed.dates)) +
            (sub ? `<p class="rz-sub">${esc(sub)}</p>` : "") +
            (ed.coursework?.length ? `<p class="rz-coursework"><span class="rz-kicker">Coursework</span>${esc(ed.coursework.join(" · "))}</p>` : "") +
            bulletsHtml(bs, `education[${i}]`) + `</div>`;
        }).join("");
        out.push(section(key, inner));
        break;
      }
      case "experiences": {
        const list = ir.experiences ?? [];
        if (!list.length) break;
        out.push(section(key, list.map((x, i) => {
          const bs = filterBullets(x.bullets, `experiences[${i}]`);
          if (!x.bullets?.length) warn("ENTRY_NO_BULLETS", "entry has no bullets", `experiences[${i}]`);
          return `<div class="rz-entry">` + headHtml(x.title ?? x.org, x.title ? x.org : undefined, dateRaw(x.dates), true) +
            (x.summary ? `<p class="rz-sub">${inline(x.summary)}</p>` : "") +
            bulletsHtml(bs, `experiences[${i}]`) + `</div>`;
        }).join("")));
        break;
      }
      case "projects": {
        const list = ir.projects ?? [];
        if (!list.length) break;
        out.push(section(key, list.map((p, i) => {
          const bs = filterBullets(p.bullets, `projects[${i}]`);
          if (!p.bullets?.length) warn("ENTRY_NO_BULLETS", "entry has no bullets", `projects[${i}]`);
          const nm = p.subtitle ? `${p.name} — ${p.subtitle}` : p.name;
          return `<div class="rz-entry">` + headHtml(nm, p.role, dateRaw(p.dates)) +
            (p.summary ? `<p class="rz-sub">${inline(p.summary)}</p>` : "") +
            bulletsHtml(bs, `projects[${i}]`) + `</div>`;
        }).join("")));
        break;
      }
      case "research": {
        const list = ir.research ?? [];
        if (!list.length) break;
        out.push(section(key, list.map((r, i) => {
          const bs = filterBullets(r.bullets, `research[${i}]`);
          const t = r.role ? `${r.role} — ${r.title}` : r.title;
          const org = [r.institution, r.department].filter(Boolean).join(", ") || undefined;
          return `<div class="rz-entry">` + headHtml(t, org, dateRaw(r.dates), true) +
            (r.summary ? `<p class="rz-sub">${inline(r.summary)}</p>` : "") +
            bulletsHtml(bs, `research[${i}]`) + `</div>`;
        }).join("")));
        break;
      }
      case "skills": {
        const raw = ir.skills ?? [];
        if (!raw.length) break;
        const groups: SkillGroup[] = typeof raw[0] === "string"
          ? [{ items: raw as string[] }] : (raw as SkillGroup[]);
        // 스킬은 하나의 그리드로: 라벨 열이 가장 긴 라벨 폭으로 정렬된다 (docs/page-policy-contract.md §7)
        const inner = groups.map((g) =>
          `<span class="rz-kicker">${g.label ? esc(g.label) : ""}</span>` +
          `<span class="rz-skill-items">${esc(g.items.join(" · "))}</span>`
        ).join("");
        out.push(`<section class="rz-section" data-section="skills">` +
          `<h2 class="rz-section-label">${esc(labels.skills)}</h2>` +
          `<div class="rz-entries rz-skills${opts.layout?.skillsGrid ? " rz-skills--grid" : ""}">${inner}</div></section>`);
        break;
      }
      case "awards": {
        const list = ir.awards ?? [];
        if (!list.length) break;
        const txt = list.map((a) => a.title + (a.issuer ? ` — ${a.issuer}` : "")).join(" · ");
        out.push(section(key, `<p class="rz-awards">${esc(txt)}</p>`));
        break;
      }
      case "languages": {
        const list = ir.languages ?? [];
        if (!list.length) break;
        const txt = list.map((l) => l.language + (l.proficiency ? ` (${l.proficiency}${l.note ? `, ${l.note}` : ""})` : "")).join(" · ");
        out.push(section(key, `<div class="rz-entries rz-skills"><span class="rz-kicker"></span><span class="rz-skill-items">${esc(txt)}</span></div>`));
        break;
      }
      case "publications":
      case "certifications":
        // v0.1: not yet rendered — surface rather than silently drop
        if ((ir as any)[key]?.length) warn("UNKNOWN_SECTION", `${key} present but not rendered in this version`, key);
        break;
    }
  }

  const vs = safeVars(opts.vars, warn);
  const vars = vs.length ? ` style="${vs.map(([k, v]) => `${k}:${v}`).join(";")}"` : "";
  return { html: `<article class="rz"${vars}>${out.join("")}</article>`, warnings };
}
