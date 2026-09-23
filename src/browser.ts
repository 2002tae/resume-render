/**
 * Browser adapter — what the Artemis web app and extension import.
 *
 *   buildDocument(ir, theme, opts)  → full HTML string (shared css + theme css + render())
 *   mount(container, doc)            → renders into an iframe for preview
 *   plan(ir, theme, policy, measure) → page count / density / trim options, by measuring the DOM
 *   printCurrent(iframe)             → browser print dialog → the user saves as PDF
 *
 * Pure DOM; no dependencies. The measurer is injected so plan() is testable in Node with a stub.
 * Mirrors tools/fit.py — same search, same floor, same trim order — so server and browser agree.
 */
import { render } from "./render.js";
import type { ResumeIR, RenderOptions, FitPolicy, Bullet } from "./ir.js";

/** fontsCss: fonts/fonts.css with url() rewritten to wherever the host serves fonts/. Browsers need it; WeasyPrint does not. */
export type ThemeAssets = { sharedCss: string; themeCss: string; manifest: ThemeManifest; fontsCss?: string };
export type ThemeManifest = {
  id: string; profile: "safe" | "expressive"; engine: "css" | "plain";
  defaults?: RenderOptions; baseBodyPx?: number;
  page?: { size?: "letter" | "a4"; orientation?: "portrait" | "landscape" };
  pages?: { supports: number[] };
  capacity?: { bulletsAt1Page?: number };
  limits?: { nameMaxChars?: number; summaryChars?: number };
};

const PAGE_PX = { letter: { portrait: [816, 1056], landscape: [1056, 816] },
                  a4:     { portrait: [794, 1123], landscape: [1123, 794] } } as const;

/** Merge manifest defaults with caller options (caller wins), then set density. */
export function optionsFor(assets: ThemeAssets, opts: RenderOptions = {}, density = 1): RenderOptions {
  const d = assets.manifest.defaults ?? {};
  return {
    ...d, ...opts,
    sections: { ...(d.sections ?? {}), ...(opts.sections ?? {}) },
    layout:   { ...(d.layout ?? {}),   ...(opts.layout ?? {}) },
    filter:   { ...(d.filter ?? {}),   ...(opts.filter ?? {}) },
    vars:     { ...(d.vars ?? {}),     ...(opts.vars ?? {}), "--density": density.toFixed(3) },
  };
}

/** Full standalone HTML. Same composition as tools/render_theme.py + ats_check.to_pdf. */
export function buildDocument(ir: ResumeIR, assets: ThemeAssets, opts: RenderOptions = {}, density = 1) {
  const r = render(ir, optionsFor(assets, opts, density));
  const html =
    `<!DOCTYPE html><html><head><meta charset="utf-8">` +
    `<style>${assets.fontsCss ?? ""}\n${assets.sharedCss}\n${assets.themeCss}</style></head><body>${r.html}</body></html>`;
  return { html, warnings: r.warnings };
}

/** Render into an iframe. Returns the iframe once its layout is done. */
export function mount(container: HTMLElement, html: string): Promise<HTMLIFrameElement> {
  return new Promise((resolve) => {
    const f = document.createElement("iframe");
    f.style.cssText = "border:0;width:100%;height:100%";
    f.srcdoc = html;
    f.onload = () => resolve(f);
    container.replaceChildren(f);
  });
}

/** Height of the rendered .rz in CSS px — the only thing plan() needs from the browser. */
export type Measure = (html: string) => Promise<number>;

export const domMeasure = (host: HTMLElement): Measure => async (html) => {
  const f = await mount(host, html);
  const rz = f.contentDocument?.querySelector(".rz") as HTMLElement | null;
  return rz ? rz.getBoundingClientRect().height : Infinity;
};

export type PlanOption =
  | { kind: "shrink";   density: number; bodyPt: number; pages: number }
  | { kind: "trim";     remove: string[]; density: number; bodyPt: number; pages: number }
  | { kind: "overflow"; pages: number; bodyPt: number }
  | { kind: "infeasible"; reason: string };

export type Plan = {
  /** a configuration satisfying the policy exists */
  feasible: boolean;
  /** true when trim:"ask" found a solution that removes bullets — the UI must let the user confirm */
  needsChoice: boolean;
  atOriginal: { pages: number; bodyPt: number };
  best?: { density: number; bodyPt: number; pages: number; removed: string[] };
  options: PlanOption[];
  warnings: string[];
};

const FLOOR = 0.82;   // same as tools/fit.py — below this body text drops under readable size

/**
 * Pre-generation planner. Mirrors tools/fit.py:
 *   1. density 1.0 → FLOOR by bisection
 *   2. if still over, trim by priority (5 → 1), re-searching density each time
 * Multi-column themes overflow *without* adding pages, so "pages" here is height / page-height,
 * which is what the user experiences.
 */
export async function plan(ir: ResumeIR, assets: ThemeAssets, policy: FitPolicy, measure: Measure,
                           opts: RenderOptions = {}): Promise<Plan> {
  const m = assets.manifest;
  const size = m.page?.size ?? "letter", orient = m.page?.orientation ?? "portrait";
  const pageH = PAGE_PX[size][orient][1];
  const bodyPx = m.baseBodyPx ?? 11;
  const lock = policy.mode !== "original" && policy.minBodyPt != null;
  const pt = (d: number) => lock ? minBodyPt : Math.round(bodyPx * d * 0.75 * 10) / 10;   // 1 CSS px = 0.75 pt, 실측
  const target = policy.pages ?? 1;
  const minBodyPt = policy.minBodyPt ?? 10;
  const warnings: string[] = [];

  // body-lock: minBodyPt 가 있으면 density 는 여백·이름·간격만 줄이고 --body-scale 이 본문을 minBodyPt 에 붙든다.
  // tools/fit.py 의 BODY_LOCK 과 같은 규칙 — 서버와 브라우저가 같은 답을 낸다.
  const pagesAt = async (density: number, minPriority?: number, irX: ResumeIR = ir) => {
    const vars = lock ? { ...(opts.vars ?? {}), "--body-scale": (minBodyPt / (bodyPx * 0.75 * density)).toFixed(4) } : opts.vars;
    const o = { ...opts, vars, filter: { ...(opts.filter ?? {}), ...(minPriority ? { minPriority } : {}) } };
    const { html, warnings: w } = buildDocument(irX, assets, o, density);
    for (const x of w) warnings.push(`${x.code}${x.path ? "@" + x.path : ""}`);
    const h = await measure(html);
    return Math.max(1, Math.ceil(h / pageH));
  };

  const p0 = await pagesAt(1);
  const atOriginal = { pages: p0, bodyPt: pt(1) };
  if (pt(1) < minBodyPt) warnings.push(`BODY_BELOW_MIN@density1:${pt(1)}pt<${minBodyPt}pt`);
  const options: PlanOption[] = [];

  if (policy.mode === "original" || p0 <= target) {
    if (p0 > target) options.push({ kind: "overflow", pages: p0, bodyPt: pt(1) });
    return { feasible: true, needsChoice: false, atOriginal, best: { density: 1, bodyPt: pt(1), pages: p0, removed: [] }, options, warnings };
  }

  // floor by policy: don't go below minBodyPt
  const floor = lock ? FLOOR : Math.max(FLOOR, minBodyPt / (bodyPx * 0.75));

  // body-lock fill: 본문이 고정이면 density 는 여백만 바꾸므로 "많이 넣기"가 항상 낫다. priority 티어는
  // 들어가는 순간 멈춰 남은 공간을 버린다(실측 11 → 6) — FLOOR 에서 최대 N 을 찾고 그 N 에서 여백을 되돌린다.
  // tools/fit.py 의 body-lock 분기와 같은 알고리즘.
  if (lock) {
    const total = (["experiences", "projects", "research"] as const).reduce((n, k) => n + (ir[k] ?? []).reduce((m, x) => m + (x.bullets ?? []).length, 0), 0);
    let lo = 0, hi = total + 1;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if ((await pagesAt(floor, undefined, keepTop(ir, mid).ir)) <= target) lo = mid; else hi = mid;
    }
    if (lo === 0 && total > 0) {
      options.push({ kind: "infeasible", reason: `does not fit at ${minBodyPt}pt even with no bullets` });
      return { feasible: false, needsChoice: false, atOriginal, options, warnings };
    }
    const { ir: kept, removed } = keepTop(ir, lo);
    let dlo = floor, dhi = 1;
    if ((await pagesAt(1, undefined, kept)) <= target) dlo = 1;
    else for (let i = 0; i < 5; i++) { const m = (dlo + dhi) / 2; if ((await pagesAt(m, undefined, kept)) <= target) dlo = m; else dhi = m; }
    if (removed.length) options.push({ kind: "trim", remove: removed, density: dlo, bodyPt: pt(dlo), pages: target });
    else options.push({ kind: "shrink", density: dlo, bodyPt: pt(dlo), pages: target });
    options.push({ kind: "overflow", pages: p0, bodyPt: pt(1) });
    return { feasible: true, needsChoice: removed.length > 0 && policy.trim === "ask", atOriginal,
             best: { density: dlo, bodyPt: pt(dlo), pages: target, removed }, options, warnings };
  }

  const search = async (minPriority?: number) => {
    if ((await pagesAt(floor, minPriority)) > target) return null;
    let lo = floor, hi = 1;
    for (let i = 0; i < 5; i++) {   // tools/fit.py STEPS 와 동일
      const mid = (lo + hi) / 2;
      if ((await pagesAt(mid, minPriority)) <= target) lo = mid; else hi = mid;
    }
    return lo;
  };

  // 1. shrink only
  const d1 = await search();
  if (d1 != null) {
    options.push({ kind: "shrink", density: d1, bodyPt: pt(d1), pages: target });
    return { feasible: true, needsChoice: false, atOriginal, best: { density: d1, bodyPt: pt(d1), pages: target, removed: [] }, options, warnings };
  }

  // 2. trim by priority — only if policy allows
  if (policy.trim === "none") {
    options.push({ kind: "overflow", pages: p0, bodyPt: pt(1) });
    options.push({ kind: "infeasible", reason: `needs < ${minBodyPt}pt body or trimming` });
    return { feasible: false, needsChoice: false, atOriginal, options, warnings };
  }
  for (const minP of [5, 4, 3, 2, 1]) {
    const d = await search(minP);
    if (d != null) {
      const removed = bulletsAbove(ir, minP);
      options.push({ kind: "trim", remove: removed, density: d, bodyPt: pt(d), pages: target });
      options.push({ kind: "overflow", pages: p0, bodyPt: pt(1) });
      return { feasible: true, needsChoice: policy.trim === "ask", atOriginal,
               best: { density: d, bodyPt: pt(d), pages: target, removed }, options, warnings };
    }
  }
  // 3. priority 티어가 거칠어 실패하면 top-N 이분탐색 (tools/fit.py 와 동일)
  const total = (["experiences", "projects", "research"] as const).reduce((n, s) => n + (ir[s] ?? []).reduce((m, x) => m + (x.bullets ?? []).length, 0), 0);
  let lo = 0, hi = total;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if ((await pagesAt(floor, undefined, keepTop(ir, mid).ir)) <= target) lo = mid; else hi = mid;
  }
  if (lo > 0) {
    const { ir: kept, removed } = keepTop(ir, lo);
    let dlo = floor, dhi = 1;
    for (let i = 0; i < 5; i++) { const m = (dlo + dhi) / 2; if ((await pagesAt(m, undefined, kept)) <= target) dlo = m; else dhi = m; }
    options.push({ kind: "trim", remove: removed, density: dlo, bodyPt: pt(dlo), pages: target });
    options.push({ kind: "overflow", pages: p0, bodyPt: pt(1) });
    return { feasible: true, needsChoice: policy.trim === "ask", atOriginal,
             best: { density: dlo, bodyPt: pt(dlo), pages: target, removed }, options, warnings };
  }
  options.push({ kind: "overflow", pages: p0, bodyPt: pt(1) });
  options.push({ kind: "infeasible", reason: "does not fit even with a single bullet at floor density" });
  return { feasible: false, needsChoice: false, atOriginal, options, warnings };
}

/** Keep the top-N bullets by (priority, document order); returns the trimmed IR and removed paths. */
export function keepTop(ir: ResumeIR, n: number): { ir: ResumeIR; removed: string[] } {
  const items: { p: number; sec: "experiences" | "projects" | "research"; i: number; j: number }[] = [];
  for (const sec of ["experiences", "projects", "research"] as const)
    (ir[sec] ?? []).forEach((x, i) => (x.bullets ?? []).forEach((b, j) =>
      items.push({ p: typeof b === "string" ? 99 : ((b as Bullet).priority ?? 99), sec, i, j })));
  const keep = new Set(items.slice().sort((a, b) => a.p - b.p || a.i - b.i || a.j - b.j).slice(0, n).map((k) => `${k.sec}[${k.i}].bullets[${k.j}]`));
  const removed: string[] = [];
  const out: ResumeIR = JSON.parse(JSON.stringify(ir));
  for (const sec of ["experiences", "projects", "research"] as const)
    (out[sec] ?? []).forEach((x, i) => {
      x.bullets = (x.bullets ?? []).filter((_, j) => { const k = `${sec}[${i}].bullets[${j}]`; if (keep.has(k)) return true; removed.push(k); return false; });
    });
  return { ir: out, removed };
}

/** IR paths of bullets with priority > minPriority (what a trim would remove). */
export function bulletsAbove(ir: ResumeIR, minPriority: number): string[] {
  const out: string[] = [];
  for (const sec of ["experiences", "projects", "research"] as const) {
    (ir[sec] ?? []).forEach((x, i) =>
      (x.bullets ?? []).forEach((b, j) => {
        const p = typeof b === "string" ? 99 : ((b as Bullet).priority ?? 99);
        if (p > minPriority) out.push(`${sec}[${i}].bullets[${j}]`);
      }));
  }
  return out;
}

/** Open the browser print dialog on a mounted iframe. The user picks "Save as PDF". */
export function printCurrent(iframe: HTMLIFrameElement) {
  iframe.contentWindow?.focus();
  iframe.contentWindow?.print();
}
