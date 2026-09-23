# Template Contract — v0.3

> **v0.2**: 프로토타입으로 §1·§5 를 실측 검증. 주장 하나가 반증되어 정정함(§5-A).
> **v0.3**: fixture 세트로 내용 가변성 검증 → 템플릿 작성 규칙 도출(§5-C), 렌더러 경고 구현.

> 레포의 템플릿이 **무엇인지** 정의한다. Artemis 의 `GET /resume-templates` 와
> 확장의 기존 템플릿 피커가 이걸 그대로 소비한다.

---

## §1. 핵심 결정 — 템플릿은 CSS + 매니페스트뿐이다

**템플릿은 HTML 을 만들지 않는다.** `render(ir, options)` 가 **정규 시맨틱 HTML** 하나를 내고,
템플릿은 그걸 스타일링만 한다.

```
render(ir, options) ──▶ 정규 HTML (모든 템플릿 공통)
                          +
                     theme.css (템플릿마다 다름)
```

**이렇게 하는 이유 네 가지:**

1. **템플릿이 콘텐츠를 못 건드린다.** CSS 는 텍스트를 만들거나 지울 수 없다 →
   "왜 내 이력서에 없는 말이 들어갔지" 가 구조적으로 불가능
2. ~~**ATS 테스트를 한 번만 하면 된다.**~~ **← 반증됨. §5-A 참조.**
   HTML 은 하나지만 **CSS 가 텍스트 추출 결과를 바꾼다.** ATS 검증은 **템플릿마다** 필요하다.
   (매니페스트에 `ats` 를 템플릿 단위로 둔 건 결과적으로 옳았고, 근거가 틀렸던 것)
3. **사용자 업로드 템플릿이 안전해진다** (확장의 `origin: "yours"`). 남의 CSS 를 받는 건
   샌드박싱 가능하지만 남의 HTML/JS 를 받는 건 XSS 다
4. **파서/렌더러 유지보수가 반으로 준다**

**제약**: 레이아웃 차이를 CSS 만으로 내야 한다. 라벨 좌측 컬럼 / 헤딩 상단 / 인라인 —
전부 CSS Grid 로 가능하니 실전 문제는 없다. 만약 어떤 디자인이 CSS 만으로 안 되면
**정규 HTML 에 훅(클래스·data 속성)을 추가**하지, 템플릿에 HTML 권한을 주지 않는다.

### 정규 HTML 스케치

```html
<article class="rz" data-profile="safe">
  <header class="rz-basics">
    <h1 class="rz-name">Taemin Kang</h1>
    <p class="rz-headline">…</p>
    <ul class="rz-contacts">
      <li class="rz-contact" data-kind="email">…</li>
    </ul>
  </header>

  <section class="rz-section" data-section="experiences">
    <h2 class="rz-section-label">Experience</h2>
    <div class="rz-entries">
      <article class="rz-entry">
        <div class="rz-entry-head">
          <span class="rz-title">…</span>
          <span class="rz-org">…</span>
          <span class="rz-dates" data-raw="Feb 2026 – Jul 2026">…</span>
        </div>
        <ul class="rz-bullets">
          <li class="rz-bullet" data-priority="2">…</li>
        </ul>
      </article>
    </div>
  </section>
</article>
```

> `data-priority` 가 DOM 에 있으면 auto-fit 이 **CSS 만으로** 잘라낼 수도 있다
> (`[data-priority="5"] { display:none }`). 텍스트 재생성 없이 밀도 조절.

---

## §2. 레포 안에서의 모양

```
templates/
  classic/
    manifest.json
    theme.css
    preview.png
  modern/
  compact/
  technical/
  academic/
  _shared/
    reset.css          # 정규 HTML 의 구조적 기본값 (모든 템플릿이 import)
    print.css          # @page, break-inside 등 인쇄 공통
fonts/
  <OFL 폰트만>
```

---

## §3. 매니페스트 (레포 내부 전체 형태)

```ts
type TemplateManifest = {
  id: string;                    // "classic" — 확장의 기존 id 와 일치
  name: string;                  // "Classic"
  blurb: string;                 // "Clean serif · one column"
  version: string;               // semver, 템플릿 단위

  engine: "css" | "plain";       // ★ plain = fitz.Story 로도 렌더 가능한 축소 집합
  profile: "safe" | "expressive";
  origin: "builtin" | "user";

  supports: {
    sections: SectionKey[];      // 이 템플릿이 렌더할 수 있는 섹션
    options: OptionPath[];       // UI 에 노출할 조절 항목
  };

  defaults: Partial<RenderOptions>;   // 이 템플릿의 기본 옵션값

  fonts?: Array<{
    family: string;
    license: "OFL" | "Apache-2.0" | "system";
    files?: string[];            // 번들된 경로
  }>;

  ats?: AtsReport;               // §5

  preview?: string;              // preview.png 상대 경로
};

type SectionKey =
  | "basics" | "summary" | "experiences" | "projects" | "research"
  | "education" | "skills" | "awards" | "publications"
  | "certifications" | "languages" | "custom";

type OptionPath =
  | "typography.pairing" | "typography.baseSize" | "typography.lineHeight"
  | "color.accent" | "density" | "page.size" | "page.margins"
  | "sections.order" | "sections.include" | "fit.pages";
```

### 예시

```json
{
  "id": "technical",
  "name": "Technical",
  "blurb": "Mono labels · dense · engineering feel",
  "version": "0.1.0",
  "engine": "css",
  "profile": "safe",
  "origin": "builtin",
  "supports": {
    "sections": ["basics","summary","experiences","projects","research",
                 "education","skills","awards","languages"],
    "options": ["typography.baseSize","color.accent","density",
                "page.margins","sections.order","sections.include","fit.pages"]
  },
  "defaults": {
    "density": "compact",
    "color": { "accent": "#41556B" },
    "typography": { "pairing": "newsreader-hanken-plex", "baseSize": 10 }
  },
  "fonts": [
    { "family": "IBM Plex Mono", "license": "OFL", "files": ["fonts/IBMPlexMono-Regular.ttf"] }
  ],
  "ats": { "verified": true, "checkedAt": "2026-08-27", "extractor": "pdftotext",
           "sectionsRecovered": 8, "sectionsExpected": 8, "readingOrderOk": true }
}
```

> `supports.sections` 에 없는 섹션이 IR 에 있으면 → 렌더 생략 + `warnings: UNKNOWN_SECTION`.
> 조용히 버리지 않는다.

---

## §4. safe / expressive — 정직한 정의

**둘 다 단일 컬럼 · 실제 텍스트다.** 축은 ATS 위험이 아니라 **독자 관례**다.

| | safe | expressive |
|---|---|---|
| 대상 | 금융 · 컨설팅 · 대기업 · 학계 | 테크 · 스타트업 · 디자인 인접 |
| 색 | 무채색 + 액센트 1개 이하 | 액센트 자유 |
| 타이포 | 대비 낮음, 관례적 | 대비 강함, 표현적 |
| 장식 | 얇은 괘선까지 | 괘선 · 블록 · 헤더 구성 자유 |
| 섹션명 | 표준어만 (Experience / Education / Skills) | 표준어 유지 (별칭 금지는 동일) |

**양쪽 모두 금지 (레포 전역 규칙):**
- 다단 · 사이드바 · 레이아웃용 테이블
- 아이콘 · 이미지 · SVG 안의 텍스트
- CSS 로 읽기 순서 바꾸기 (`order`, absolute positioning 재배치)
- 헤더/푸터에 연락처
- 스킬 프로그레스바 · 별점
- 사진

> **`expressive` 는 "ATS 위험"이 아니다.** ATS 검증은 §5 의 독립 필드로 따로 기록한다.
> 표현적이면서 검증 통과인 템플릿이 정상이다.

---

## §5-A. 실측 결과 (2026-08-27, WeasyPrint 69 + pdftotext)

동일 정규 HTML(5,444자) + 테마 3종을 렌더해 추출 검증. **CSS 가 추출을 바꾼다는 것이 확인됨.**

**1차 실행 — 3종 중 1종 실패**

| 테마 | layout 모드 | stream 모드 |
|---|---|---|
| classic | 16/16 ✅ | 16/16 ✅ |
| **technical** | **15/16 ❌** | **13/16 ❌** |
| modern | 16/16 ✅ | 16/16 ✅ |

**원인 3가지 — 전부 CSS 에서 비롯:**

| 현상 | 원인 | 대응 |
|---|---|---|
| `COURSEWORK` → `C O U R S E W O R K` | `.rz-kicker { letter-spacing }` 가 작은 모노 폰트에서 글자별 분리 유발. **양쪽 추출 모드 모두** | safe 템플릿은 본문급 요소에 `letter-spacing` 금지. 라벨은 크기·폰트 조합 검증 후에만 |
| 제목이 줄바꿈되면 우측 날짜가 **제목 중간에 끼어듦** (`…Tail-Risk` / `May – Jul 2026` / `Modeling`) | 좁은 본문 컬럼 + 우측정렬 날짜. layout 모드에서 시각 위치로 읽음 | 본문 measure 확보. 라벨 컬럼 96pt → 70pt 로 해결됨 |
| `end-to-end` → `end-toend`, `point-in-time` → `pointin-time` | 줄끝 하이픈을 추출기가 **음절 하이픈으로 오인해 제거**. 좁을수록 빈발 | CSS 로 완전 차단 불가. **경고로 분류**(§5-B) |

**수정 후 — 3종 전부 통과**
```
[PASS] classic    layout 16/16 · stream 16/16
[PASS] technical  layout 16/16 · stream 15/16 (hyphen=1, 경고)
[PASS] modern     layout 16/16 · stream 16/16
```

**부수 발견 — 빌드 단계 버그**
`theme.css` 안의 `@import "_shared.css"` 가 **해석되지 않았다**(인라인 `<style>` 에 base URL 없음).
결과: `@page{size:letter}` 미적용 → **A4 로 렌더**, `list-style:none` 미적용 → **불릿 이중 표시**.
→ 빌드가 `_shared.css + theme.css` 를 **명시적으로 연결**해야 한다. `@import` 의존 금지.

### §5-B. 판정 등급

| 등급 | 의미 | verified 에 영향 |
|---|---|---|
| `missing` | 텍스트가 추출에 없음 | ❌ 실패 |
| `mangled` | 텍스트는 있으나 문자 사이 공백 삽입 (자간) | ❌ 실패 |
| `hyphenBreaks` | 줄끝 하이픈 소실 | ⚠️ 경고 — 추출기 공통 동작이라 템플릿 탓이 아님 |
| `readingOrderOk` | 추출 순서 == IR 순서 | ❌ 실패 |

**두 추출 모드를 모두 돌린다**: `-layout`(시각 위치 기반)과 기본(콘텐츠 스트림 기반).
ATS 마다 방식이 다르므로 한쪽만 통과하는 건 통과가 아니다.

---

## §5. ATS 검증 — 레포의 차별점

as-built 가 남긴 공백: *"렌더된 PDF 를 실제 ATS 가 제대로 파싱하는지 확인 못함.
테스트는 쓴 라이브러리로 다시 열어 읽는 수준이고, 스스로 'the closest stand-in' 이라 부른다."*

**레포에서 이걸 실측해서 매니페스트에 박는다.**

```ts
type AtsReport = {
  verified: boolean;
  checkedAt: string;              // ISO date
  extractor: string;              // "pdftotext" | "pdfminer" | …
  sectionsRecovered: number;
  sectionsExpected: number;
  readingOrderOk: boolean;        // 추출 텍스트 순서 == IR 순서
  contactRecovered: string[];     // ["email","phone","linkedin"]
  notes?: string[];
};
```

**테스트 방식**: 고정 IR 픽스처 → 템플릿 렌더 → PDF → 텍스트 추출 →
(a) 모든 bullet 문자열이 살아있나 (b) 순서가 보존되나 (c) 섹션 헤딩이 인식되나 (d) 연락처가 복구되나.

> **정직성 주의**: 이건 "진짜 Workday 가 파싱한다"는 증명이 아니라 **텍스트 레이어 무결성** 검증이다.
> 매니페스트 `notes` 와 README 에 그 한계를 명시할 것. 과장하면 as-built 가 지적한 것과 같은 실수를 반복한다.

---

## §5-C. 내용 가변성 — fixture 로 도출된 규칙

**전제**: 디자이너는 "잘 생긴 것 하나"만 만든다. 견고함은 **fixture 세트를 기계적으로 돌려서** 확보한다.
규칙은 미리 상상해서 쓰는 게 아니라 **깨진 데서 나온다.** 아래는 전부 실제 파손에서 도출됐다.

### fixture 세트

| 이름 | 목적 |
|---|---|
| `minimal` | 신입생 — Education + Skills 만. 섹션 대부분 없음 |
| `ragged` | 필드 결손(org·dates 없음) · 극단적 길이 편차(1 vs 8 bullet) · 60자 이메일 · 안 끊기는 URL · 빈 bullets |
| `typical` | 인턴 1 + 프로젝트 2 (기준선) |
| `dense` | 실제 축적된 pool — 2페이지 넘침 |

### 관측된 파손 → 규칙

| # | 관측된 파손 | 규칙 |
|---|---|---|
| R1 | `skills[].label` 없는 그룹에서 **자식이 하나뿐이라 64pt 첫 트랙에 배치** → URL 이 9줄로 갈라짐. WeasyPrint 위치 실측: 라벨 있으면 items `x=169.3`, 없으면 `x=84.0` | **그리드 자식은 `grid-column` 으로 명시 배치.** 소스 순서 의존 금지 |
| R2 | 긴 이름이 `1fr` 컬럼에서 3줄로 깨지며 baseline 어긋남 | 고정폭 대신 `minmax(0,…)`, 그리드/플렉스 자식에 `min-width:0` |
| R3 | `overflow-wrap:anywhere` 를 연락처에 적용하자 `taemin.kang@` / `gmail.com` 으로 분리 → **ATS contacts 4/4 → 0/4 회귀** | **`anywhere` 전면 금지.** 본문은 `break-word`, **연락처는 `white-space:nowrap` 으로 원자 취급** |
| R4 | `letter-spacing` 이 작은 모노에서 `C O U R S E W O R K` 유발 (§5-A) | 본문급 요소에 `letter-spacing` 금지 |
| R5 | bullet 이 빈 엔트리가 제목만 남아 고아로 렌더 | 렌더러가 `ENTRY_NO_BULLETS` 경고 발행 |
| R6 | `skills[].label` optional 인데 렌더러가 필수로 가정 → **KeyError 크래시** | 렌더러는 IR 의 optional 을 실제로 지켜야 함. fixture 가 스펙-구현 불일치를 잡는다 |

> **R3 이 가장 중요한 교훈**: "긴 문자열 방어" 라는 좋은 의도의 규칙이 ATS 를 깨뜨렸다.
> 회귀를 잡은 건 사람 눈이 아니라 **테스트**였다. 모든 CSS 규칙 변경은 ATS 스위트를 다시 돌린다.

### 렌더러 경고 (구현됨)

```
MISSING_NAME        basics.name 없음 → 헤더 이름 생략
ENTRY_NO_BULLETS    엔트리에 bullet 없음 → 제목만 렌더
SECTION_EMPTY       섹션에 렌더할 내용 없음 → 섹션 생략
```
빈 섹션은 **헤딩째 생략**한다. 빈 헤딩을 남기면 사람 눈에도 ATS 에도 결함으로 보인다.

### 담당 분리

| 상황 | 담당 |
|---|---|
| 섹션이 빔 | `render()` — 생략 + 경고 |
| 엔트리 내 필드 결손 | **CSS 규약** — 형제 존재 가정 금지 (R1) |
| 내용 과다 | `options.fit` — density + priority 절삭 |
| 안 끊기는 긴 토큰 | `_shared.css` — R3 |
| 항목 길이 편차 | CSS 규약 — 고정 높이 금지 |

---

## §6. 와이어 포맷 — `GET /resume-templates`

> **정정:** 아래의 mock id(modern/compact/technical) 유지 문구는 낡았다. `GET /resume-templates` 는 `themes/*/manifest.json` **13개를 가공 없이** 반환한다. 존재하지 않는 id 는 없다.


서버가 반환하는 건 매니페스트의 **부분집합**이다. `defaults` 내부나 폰트 경로는 클라이언트에 불필요.

```ts
type TemplateListResponse = {
  templates: Array<{
    id: string;
    name: string;
    blurb: string;
    profile: "safe" | "expressive";
    origin: "builtin" | "user";
    engine: "css" | "plain";
    atsVerified: boolean;
    previewUrl?: string;
  }>;
};
```

**확장 UI 는 변경 불필요** — 기존 `ResumeTemplate` 타입에 `profile` · `atsVerified` · `engine` 만 추가되고
`id` / `name` / `blurb` / `origin` 은 그대로다. mock 6개의 id 도 유지:

| 기존 id | 유지 | profile | engine |
|---|---|---|---|
| `classic` | ✅ | safe | css |
| `modern` | ✅ | safe | css |
| `compact` | ✅ | safe | css |
| `technical` | ✅ | safe | css |
| `academic` | ✅ | safe | css |
| `yours` | ✅ | — | css |
| `plain` | **신규** | safe | **plain** ← 무인 auto-apply 경로용 |

> `plain` 을 추가해야 `APPLY_TAILOR_READY` 를 켤 때 `fitz.Story` 가 렌더할 대상이 생긴다.
> 나머지 6개는 브라우저 전용이다.

### 렌더 요청

```ts
POST /resume-tailor/render
{
  markdown | ir,                 // 전환기 동안 둘 다
  templateId: string,
  format: "pdf" | "docx" | "txt",
  options?: Partial<RenderOptions>
}
```
서버는 `templateId` 의 `engine` 을 보고 `plain` 이면 `fitz`, 아니면 **거부**하고
클라이언트 렌더를 안내한다 (브라우저에서 이미 렌더 가능하므로).

---

## §7. `yours` — 사용자 템플릿

확장 UI 에 이미 있다 (`origin: "yours"`, *"Match your own file"*).

**CSS-only 결정 덕분에 안전하게 구현 가능:**
- 사용자가 올리는 것 = `theme.css` + 최소 매니페스트
- 서버는 CSS 를 파싱해 화이트리스트 밖 구문 거부 (`@import`, `url()` 외부, `position:absolute` 등)
- HTML 은 언제나 우리 것 → 콘텐츠 조작·XSS 불가

> 1차 구현에서는 **"내 파일 매칭"을 자동 추론하지 말고** 프리셋 조합(폰트·간격·액센트)을
> 저장하는 것부터. 임의 PDF 의 디자인을 역공학하는 건 별개의 큰 문제다.

---

## §8. 열린 항목

| # | 항목 |
|---|---|
| T-1 | `plain` 이 `fitz.Story` 에서 실제로 뭘 낼 수 있나 — CSS 서브셋·폰트 임베드 미확인 (as-built §8-4) |
| T-2 | 정규 HTML 클래스 이름 확정 — 디자인 라운드 1 결과 보고 훅이 충분한지 검증 |
| T-3 | `supports.options` 를 템플릿이 실제로 제한할 필요가 있나, 아니면 전부 노출해도 되나 |
| T-4 | 사용자 CSS 화이트리스트 구체안 |
| T-5 | 폰트 번들 vs CDN — 오프라인 인쇄 안정성 vs 레포 용량 |

---

## §10. WeasyPrint 결함 목록 — 실측 (테마 작성 시 반드시 볼 것)

이 렌더러로 검증하므로 이 결함들은 곧 테마 규칙이다. Chrome 에서는 대부분 정상이다.

| # | 결함 | 회피 |
|---|---|---|
| W1 | `font-stretch` 무시 — 가변 폰트 wdth 축을 안 씀 | 압축 인스턴스를 별도 패밀리로 (`ArchivoCond`) |
| W2 | `grid-column: 1 / -1` 의 `-1` 을 거터 폭으로 계산 | `span N` 또는 명시 번호 (R8) |
| W3 | `display:contents` 미지원 — 래퍼가 그리드 아이템이 됨 | 음수 마진 그리드 (R9) |
| W4 | 그리드 자식에 `grid-column` 명시 + 행 자동이면 행을 안 넘겨 전부 1행 | 자동 배치에 맡김 |
| W5 | `column-span:all` 요소가 컨테이너 padding 을 무시하고 페이지 전폭 | 다단 테마는 여백을 `@page` 로 |
| W6 | `column-span` 요소가 flex 컨테이너면 폭 오계산 | `display:block` |
| W7 | flex 컨테이너는 컬럼·페이지 사이에서 분할되지 않음 — 통째로 넘어감 | 다단·2페이지 테마의 섹션·엔트리·불릿 목록은 `block` |
| W8 | 음수 `letter-spacing` 이 intrinsic 폭을 실제보다 작게 계산 → flex 아이템 조기 줄바꿈 | 제목·소속에 음수 자간 금지 (R4 경고) |
| W9 | flex 에서 `flex-shrink:0` 도 무시하고 아이템을 눌러 세로로 꺾음 | 줄을 나누려면 `flex-basis:100%` 로 명시 |
| W10 | `::after{flex:1}` 은 부모가 flex 컨테이너일 때만 늘어남 | 점선 리더는 org 자체를 `display:flex` 로 |
| W11 | 다단 오버플로는 페이지를 늘리지 않고 잘림 | fit 은 페이지 수 + 마지막 문자열 존재로 판정 |
| W12 | `break-inside:avoid` 엔트리가 페이지 경계에 걸리면 통째로 소실 | 불릿 단위로만 보호 |
| W13 | flex 컬럼 아이템이 grid 자손을 품으면 ~1줄 유령 높이 (가장 가까운 flex 조상 아이템에 붙음) | grid 헤드를 쓰는 테마는 섹션·엔트리를 `block` |
| W14 | (추출기) pdfminer 가 세로로 가까운 **우측 정렬 날짜**들을 한 텍스트 박스로 묶어 다른 위치에 뱉는다 | 우측 정렬 날짜 디자인의 고유 리스크. ATS 최대 안전은 인라인 날짜(`plain`) |
| W16 | flex 컬럼 안에서 `break-after:avoid` 무시 → 2페이지에서 섹션 제목이 1쪽 끝에 홀로 남음. 같은 구조에서 줄바꿈되는 flex 머리줄 아래 ~1줄 유령 틈(W13 과 같은 계열) | `.rz-section`·`.rz-entries` 는 block + margin. 린트 R11 이 막는다 |
| W15 | (추출기) poppler `pdftotext` 기본 모드가 줄 끝 하이픈을 지우며 줄을 잇는다(`state-` / `of-the-art` → `stateof-the-art`). 하이픈은 PDF 안에 있다. Chrome·WeasyPrint·fitz 모두 동일 — 어느 단어가 걸리느냐만 다르다 (Artemis 실측) | 엔진 문제가 아니다. `ats_check` 의 `hyphenBreaks` 경고가 이것. 키워드 매칭이 중요하면 `-layout` 또는 pdfminer 를 쓰는 리더가 유리 |

## §11. 린트 규칙 추가분

| 규칙 | 내용 | 근거 |
|---|---|---|
| R8 | `grid-column` 에 `-1` 금지 | W2 |
| R9 | `display:contents` 금지 | W3 |
| R10 | 불릿 마커에 텍스트 글리프(`content:"·"`) 금지 — CSS 박스로 | stream 추출에서 `workday,·smartrecruiters` 삽입 실측 |
| R4' | 음수 자간은 경고 | W8 |
| R4'' | **양수 자간 0.08em 초과 금지 — 섹션 라벨 예외 없음** | 4 엔진 실측: 0.08em 안전, 0.1em 부터 poppler·pdfminer 가 `E D U C A T I O N` 으로 분리 → 헤딩 매처 실패 |

## §12. 검사기가 매니페스트 defaults 를 쓴다 (감사 후 정정)

`ats_check.py` 는 처음엔 기본 순서·기본 라벨로만 렌더해 검사했다 — 즉 `ats.verified` 가 **배포 구성이 아닌 것**을
검증한 값이었다. 지금은 `render_theme.py` 로 매니페스트 `defaults`(순서·라벨·layout) 를 적용해 렌더하고,
기대 문자열 순서도 그 순서를 따른다.

---

## §13. 단위 정정 — CSS px → PDF pt 는 ×0.75

이전 문서와 보고에서 "본문 10pt" 로 적힌 값들은 `pdftotext -bbox` 의 글자 박스 높이(어센더+디센더)를 읽은 것이라
**실제 폰트 크기보다 ~30% 크다.** pdfminer `LTChar.size` 로 실측: CSS 12px → 9.0pt. 따라서
`bodyPt = baseBodyPx × density × bodyScale × 0.75`. `plan()`·`fit.py`·매니페스트 주석 전부 이 식으로 정정했다.

## §14. 두 개의 축 — `--density` 와 `--body-scale`

- `--density`: 모든 크기·간격 균일 스케일. **줄이는** 방향에 쓴다 (1페이지 맞춤).
- `--body-scale`: 본문·제목·메타·라벨(`--fs`, `--fs-entry`, `--fs-meta`, `--fs-sec`, `--fs-lede`)만. 이름·여백·간격은 안 건드린다.
  **키우는** 방향에 쓴다 ("본문 ≥10pt"). 균일 확대는 이름·여백까지 커져 수용량이 급감한다(실측: numerals 0 bullet).
- body-lock 모드(`minBodyPt`): `density` 로 여백을 줄이면서 `bodyScale = minPt / (base × 0.75 × density)` 로 본문을 고정한다.
  `tools/fit.py` 와 `src/browser.ts plan()` 이 같은 식을 쓴다.

## §15. 구조를 모르는 파서로 잰 식별성 (tools/ats_generic.py)

`ats_check.py` 는 IR 과 `rz-*` 를 알아 편향된다. `ats_generic.py` 는 헤딩 사전·정규식만으로 3개 엔진
(poppler · pdfminer.six · pypdf)의 텍스트를 읽고, 변이 4종(짧은 이름 · 연구/수상 없음 · 경력 1개 · 평면 스킬)으로 흔든다.

| 등급 | 테마 | 원인 |
|---|---|---|
| A · `ats-safe` | plain · classic · standfirst · numerals · minimal · folio · marginalia | 3 엔진 × 5 케이스 전부 식별 |
| B · `distinctive` | academic · masthead · colorfield · ledger · broadsheet | W14 — pdfminer 가 우측 정렬 날짜를 이웃 엔트리에 붙임 (poppler·pypdf 정상). ledger 는 WeasyPrint 70 에서 B 로 떨어졌다 — 우측 날짜 디자인은 줄 위치에 민감하다. broadsheet 은 poppler -layout 컬럼 섞임 |
| C · `distinctive-limited` | spread | 랜드스케이프 다단: 이름이 첫 줄이 아닌 케이스 있음 |

**기계 필드:** 각 매니페스트 `ats.generic.{grade,tier,cases}` — `tools/run_generic.sh <theme>` 이 쓴다. UI 티어 뱃지는 여기서 읽는다.

이 등급이 나오기 전엔 A 가 2종뿐이었다 — 원인은 라벨 자간(R4'')이었고, 편향된 검사기가 그걸 통과시키고 있었다.
