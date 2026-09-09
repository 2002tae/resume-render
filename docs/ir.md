# Resume IR — v1.1

> v0 대비 변경: as-built 문서(2026-08-26) 반영. 렌더 위치 결정, `ResumeStructured`/pool 과의 갭 정리,
> 마이그레이션 비용이 드는 필드 전부 완화.
>
> **v1.1 추가**: 실제 tailor 출력 샘플 1건 확보(§0-A) — 파싱 실패가 추정이 아니라 **관측**이 됨.
> 그리고 Claude Code 측 결정 5건 반영(§0-B).

---

## §0-A. 실제 출력 샘플 — 관측된 것

as-built §8-4 가 "확인 못함"으로 세워뒀던 항목. 실물 1건 확보(2026-08-26, quant 이력서 기준).

### 관측된 형태

```
Taemin Kang
taemin.kang@gmail.com | +1 (814) 555-0100 | linkedin.com/in/Taemin-Kang | ...

## Summary
<문단>

## Experience

**Undergraduate Researcher — Bayesian Volatility & Tail-Risk Modeling** — Penn State SURE Program, Department of Statistics — May – Jul 2026
- <bullet>
```

- 섹션 헤더 `##`
- 불릿 마커 `-` (하이픈)
- 엔트리 줄 `**...**` + ` — ` 구분
- 연락처 ` | ` 구분

### ★ 파싱이 불가능한 이유 (관측)

**1. em-dash 가 구분자이면서 동시에 내용이다.**
```
**Undergraduate Researcher — Bayesian Volatility & Tail-Risk Modeling** — Penn State SURE — May – Jul 2026
                           ↑ 내용                                        ↑ 구분자      ↑ 구분자
```
` — ` 로 split 하면 4조각이 나오는데 필드는 3개다. **어느 게 제목의 일부인지 알 방법이 없다.**
이건 재파싱기를 잘 짜면 되는 문제가 아니라 **정보가 이미 소실된** 문제다.

**2. arity 가 가변이다.**
| 관측된 줄 | 조각 수 |
|---|---|
| `**Undergraduate Researcher — Bayesian…** — Penn State SURE… — May – Jul 2026` | 4 (제목에 em-dash) |
| `**Independent Derivatives Trader (self-directed)** — Feb – Jul 2026` | 2 (org 없음) |
| `**Intelligence Analyst** — Korea Defense Intelligence Command — Dec 2023 – Jun 2025` | 3 (정상) |
| `**Market Regime Detection — Applied Data Mining (graduate)**` | 1 (날짜 없음, 제목에 em-dash) |

→ 위치로 필드를 정할 수 없다. as-built §8-1 의 "위치 관습 의존"이 실제로 깨지는 케이스가 4줄 중 3줄.

### ★ 프롬프트 버그 — Education 이 통째로 사라진다

출력에 **Education 섹션이 없다.** 학교·GPA·coursework 전부 소실.

원인은 모델이 아니라 프롬프트다. `resume_from_pool.txt` 원문:
> *sections in this order: **Summary, Experience …, Projects …, Skills** (one line)*

**Education 이 목록에 없다.** 보수 버전도 마찬가지(거긴 Summary 도 없음).
학부생 이력서에서 Education 누락은 치명적. → **IR 전환과 무관하게 즉시 고칠 것.**
Awards/Honors 도 같은 이유로 갈 곳이 없다.

### 그 외 관측된 결함

| 결함 | 관측 | 원인 |
|---|---|---|
| **같은 연구가 2번 나옴** | SURE 가 Experience 의 "Undergraduate Researcher" 와 Projects 의 "Statistical Detection & Forecast Evaluation" 으로 중복 | pool 이 여러 이력서에서 온 **다른 프레이밍**을 별개 항목으로 축적. variant 그룹핑이 없음 |
| **역순 정렬 깨짐** | Artemis(Mar 2026–현재)가 Intelligence Analyst(–Jun 2025) **뒤에** | 날짜가 자유 텍스트라 정렬 불가 |
| **인라인 강조 전부 소실** | 원본 `**42% detection rate**` → 출력 `42% detection rate` | markdown 왕복에서 유실 |
| **연락처 문자열 변조** | `linkedin.com/in/taemin-kang` → `…/Taemin-Kang` | 모델이 연락처를 자유롭게 다시 씀 |
| **언어 항목 유실** | Mandarin 사라짐, Korean/English 는 skills 문자열에 섞임 | `skills: list[str]` 평면화 |
| **skills 그룹 소실** | 47개가 콤마 한 줄 | 동일 |

> **결론**: as-built 가 "프롬프트 기준의 주장"이라고 표시했던 것들이 전부 **관측으로 확정**됐고,
> 예상보다 나쁘다. 특히 **Education 누락**과 **연구 중복**은 IR 이전에 존재하는 버그다.

---

## §0-B. 확정된 설계 결정 (Claude Code 측)

| # | 결정 | IR 반영 |
|---|---|---|
| 1 | 각 bullet 은 `sourceBulletKey` 를 들고 나온다 — 점수 대신 하드 출처 | `Bullet.sourceBulletKey` ★ §4 |
| 2 | 날짜는 원문 + 파싱값 둘 다, 파싱 실패해도 원문 생존 | v1 `DateRange.raw` 필수 유지 ✅ |
| 3 | 렌더러는 검증하지 않는다. 검증은 생성 시점 Pydantic | §4-B 로 계층 분리 |
| 4 | 라이브러리는 IR → HTML+CSS 까지만. **PDF 안 만듦** | §0 수정 |
| 5 | IR 은 pool 이 실제로 가진 것만 요구 | **`version` 외 전부 optional** |

### 4번의 결과 — 라이브러리 경계가 더 깨끗해진다

```
repo(TS):  normalize(input) → IR
           render(IR, options) → { html, css, warnings }     ← 여기까지
소비자:     브라우저 print / Playwright / fitz — 각자 선택
```
의존성 0, 브라우저·Node 양쪽 동작, 테스트 쉬움. **PDF 백엔드 논쟁이 라이브러리 밖으로 나간다.**

### 3번 — 다만 계층은 나눠야 한다

레포는 오픈소스라 **손으로 md 를 쓰는 사용자**가 있다. 그쪽 입력은 검증이 필요하다.

```
normalize(loose) → { ir, warnings }    ← 관용적. md 파서·외부 입력용
render(ir, opts)  → { html, css, warnings }  ← 순수. IR 유효 가정 (Claude Code 결정대로)
```
Artemis 는 `normalize` 를 건너뛰고 `render` 를 직접 부르면 된다 — Pydantic 이 이미 보장하므로.
`render` 의 `warnings` 는 **검증이 아니라 렌더 진단**(오버플로, 섹션 비어있음, ATS 위험)만 담는다.

### 5번 — 필수 필드 재조정

pool 은 `dict[str, Any]` 이고 옛 shape 행이 실재하므로 **아무것도 보장하지 않는다.**

```ts
type ResumeIR = {
  version: "1.0";     // ★ 유일한 필수
  // 나머지 전부 optional
};
```
`basics.name` 조차 optional (`ResumeStructured.name: str | None`). 이름이 없으면 렌더러는
헤더 블록을 생략하고 `warnings` 에 `SECTION_EMPTY` 를 넣는다.

---

## §0. 먼저 — 렌더러는 어디서 도는가

as-built 문서가 설계 전 결정하라고 짚은 것. **답: 브라우저 우선, 서버는 그대로 둔다.**

### 세 후보

| | CSS 충실도 | 새 의존성 | 무인 경로 | 비용 |
|---|---|---|---|---|
| **브라우저** (Paged.js + print) | 완전 | 없음 | ❌ 인쇄 대화상자 필요 | 0 |
| **`fitz.Story`** (현행) | 부분 — CSS 서브셋, `font-family` 미확인 | 없음 (이미 있음) | ✅ | 0 |
| **Playwright 서버** | 완전 | 무거움 (~300MB+/인스턴스) | ✅ | Railway 비용 |

### 결정

**사람이 검토하는 경로 = 브라우저.** 웹앱과 확장은 이미 브라우저다. 라이브러리가 HTML+CSS 를 뱉으면
그 자리에서 렌더하고 인쇄한다. `apps/api` 에 새 의존성이 0 이므로 *"NO NEW DEPENDENCY"* 결정과
**충돌하지 않는다** — 그 결정은 API 서버에 관한 것이고, 브라우저 렌더는 API 서버를 지나가지 않는다.

**무인 경로(auto-apply) = `fitz.Story` 유지.** 지금 `APPLY_TAILOR_READY = false` 로 도달 불가라 급하지 않다.
살릴 때는 `plain` 템플릿 하나만 지원한다고 명시 — fitz 가 낼 수 있는 것만.

**Playwright 는 나중에, 그리고 `apps/api` 밖에.** 무인 경로에서도 예쁜 템플릿이 필요해지면 그때
별도 Node 서비스로. 파이썬 API 는 계속 안 건드린다.

### 언어 경계가 사라진다

레포가 TS 라이브러리면 파이썬이 소비할 방법을 고민할 필요가 없다 — **소비자가 파이썬이 아니다.**

```
repo (TS, npm)  render(IR, opts) → { html, css, warnings }   ← 라이브러리는 여기까지
                ──import──▶  웹앱 (TS)  → Paged.js → print → PDF
                ──import──▶  확장 (TS)  → 동일
apps/api (Python) ─── 안 건드림. fitz.Story 는 무인 경로 폴백으로 잔류.
```
> **PDF 생성은 라이브러리 밖.** 소비자가 브라우저 print / Playwright / fitz 중 고른다.

**부수 효과 하나**: 웹은 지금 markdown 렌더러 의존성이 아예 없어서 `**bold**` 가 글자로 보인다.
라이브러리를 import 하면 그게 같이 해결된다.

---

## §1. 가장 큰 발견 — 구조를 되살릴 기계가 이미 있다

as-built 다이어그램의 핵심:

```
ResumeStructured (타입 있음) → pool (JSONB) → _serialize_pool (평문) → LLM → markdown: str  ★ 여기서 죽음
                                                                              ├→ 서버 정규식 재파싱
                                                                              └→ 확장 다른 정규식 재파싱
```

**재파싱기 둘, 규칙 서로 다름, 둘 다 "첫 줄=이름" 위치 관습 의존.** 이게 IR 이 실제로 푸는 문제다.

그런데 — **instructor + Pydantic 강제 스키마가 이미 돌아가고 있다.** `ResumeStructured` 를 그렇게 뽑고 있고,
`NullTolerantModel`·reask·`strict=False` 까지 다 갖춰져 있다. 출력만 `markdown: str` 로 골랐을 뿐이다.

> **출력 스키마를 IR 로 바꾸면 재파싱기 둘이 동시에 사라진다.** 새 기계가 필요 없다.

### 다만 공짜는 아니다

| 비용 | 정도 |
|---|---|
| 출력 토큰 증가 | 구조 오버헤드. 현재 `max_tokens=2000` 재검토 필요 |
| reask 실패율 | 스키마가 커질수록 상승. 실측 필요 |
| 프롬프트 재작성 | *"Return clean markdown with sections in this order"* 가 통째로 무의미해짐 |
| 회귀 위험 | 프로덕션 118건이 현 형태 기준. eval 스위트 재보정 |

**권고: 한 경로만 먼저 바꾼다.** `resume_from_pool` (review) 하나로 A/B. 나머지 다섯은 그대로 두고
측정 후 확대.

---

## §2. 더 나은 선택지 — pool 경로는 "참조 선택"으로

`resume_from_pool_conservative` 프롬프트가 산문으로 강제하려는 것:

> *every sentence in the output must already be a pool bullet*

이건 **스키마로 강제할 수 있다.** pool 은 이미 `experiences[].key`, `bullets[].text` 를 갖고 있으므로,
LLM 이 텍스트를 다시 뱉는 대신 **뭘 고를지만** 반환하면 된다:

```ts
type PoolSelection = {
  version: "1.0";
  experiences: Array<{ key: string; bulletIndices: number[] }>;
  projects:    Array<{ key: string; bulletIndices: number[] }>;
  education:   string[];        // keys
  skills:      string[];        // pool skills 중 선택
  order?:      string[];        // 섹션 순서
};
```

**이래서 얻는 것:**

1. **날조가 구조적으로 불가능해진다** — 보수 경로가 프롬프트 산문으로 하려던 걸 타입이 보장
2. **출력 토큰 급감** — 텍스트 재생성이 아니라 인덱스 배열
3. **선택 근거가 남는다** — "무엇을 왜 뺐는지 어디에도 안 나온다"는 §4 한계가 해소. `dropped[]` 필드 추가 가능
4. **§G self-audit 을 보수 경로에선 건너뛸 수 있다** — 감사할 새 사실이 없음. LLM 호출 1회 절감

**한계:** *"you may lightly trim wording for length"* 가 안 됨. 필요하면 `{index, override?: string}` 하이브리드로 —
override 가 있으면 audit 대상, 없으면 무조건 통과.

> review 경로(요약 작성, 문구 다듬기 허용)는 이 방식이 안 맞는다. 거긴 전체 IR 반환이 맞다.

---

## §3. 갭 분석 — IR v0 vs 현행

### 3-1. 이름이 다른 것 (기계적, 쉬움)

| 현행 | IR v0 | 결정 |
|---|---|---|
| `experiences[]` | `experience[]` | **현행 채택** — 복수형 유지 |
| `ResumeExperience.org` | `organization` | **현행 채택** — `org` |
| `ResumeExperience.title` | `role` | **현행 채택** — `title` |
| `ResumeEducation.school` | `institution` | **현행 채택** — `school` |
| `ResumeEducation.details[]` | `bullets[]` | **현행 채택** — `details` |

> 원칙: **이름 차이는 전부 현행에 맞춘다.** 변환기 하나 더 만들 이유가 없다.
> IR 이 추가하는 건 *구조*지 *어휘*가 아니다.

### 3-2. 현행에 아예 없는 것 (추가 필요)

| 없는 것 | 영향 |
|---|---|
| **`research[]`** | Tae 본인 이력서의 최강 콘텐츠(SURE·GNN)를 담을 곳이 없다. 지금은 `projects` 에 욱여넣어야 함 |
| `awards[]` | 장학금·honor society·군 표창 — 현재 갈 곳 없음 |
| `publications[]` | 학계 지원자 전반 |
| `certifications[]` | 일반 사용자 다수 |
| `languages[]` | 현재 `skills` 평문에 섞임 |

> **`research[]` 가 제일 급하다.** 나머지는 `custom[]` 로 우회 가능하지만 research 는 advisor/status 같은
> 고유 필드가 있어 우회가 지저분하다.

### 3-3. 구조가 부족한 것

| 현행 | 문제 | IR v1 대응 |
|---|---|---|
| `skills: list[str]` **평면** | 라벨 그룹("Programming", "Bayesian & Inference")을 못 만듦 | `SkillGroup[]`, **`label` optional** → 평면 리스트는 `[{items:[...]}]` 로 무손실 승격 |
| `contact: list[str]` 평문 | 이메일/링크 구분 불가 → ATS 위험 판정 불가 | `Contact[]`, **평문 문자열도 허용**(kind 추론) |
| `dates: str \| None` | 정렬·로케일 불가 | **`raw` 를 1급으로.** §3-4 참조 |
| `bullets: list[str]` | 우선순위·태그·출처 못 담음 | `Bullet` 객체, **평문 문자열도 허용** |
| pool `bullets[].sources` | ResumeStructured 에는 없음 (pool 이 더 부자) | `Bullet.sources` 로 승격 |
| `tags[]` (이력서 단위) | IR v0 은 bullet 단위만 있었음 | **둘 다 유지** — 목적이 다름 |

### 3-4. 날짜 — v0 설계를 뒤집는다

v0 은 `DateRange{start,end,current}` 를 요구하고 `raw` 를 폴백으로 뒀다. **as-built 를 보면 반대가 맞다.**

- 저장된 모든 날짜가 자유 텍스트
- 옛 shape 행이 dev DB 에 실재
- 파싱된 날짜 타입이 저장소 어디에도 없음
- `"Incoming Fall 2026"` 같은 건 애초에 파싱 대상이 아님

```ts
type DateRange = {
  raw: string;                 // ★ 필수. 이게 진실이고 렌더도 이걸 쓴다
  start?: DateValue;           // 선택 — 있으면 정렬/재포맷 가능
  end?: DateValue;
  current?: boolean;
};
```

**마이그레이션 비용 0.** 기존 `dates: "Feb 2026 – Jul 2026"` → `{raw: "Feb 2026 – Jul 2026"}`.
구조화 필드는 파서가 나중에 백필하는 **개선**이지 요구사항이 아니다.

### 3-5. 관용 입력 (Poe's law 대비)

pool shape 이 강제되지 않고 옛 행이 실재하므로, IR 검증기는 **좁게 받고 넓게 읽어야** 한다:

```ts
type Loose<T> = T | string;          // Bullet | "text", Contact | "a@b.com"
```
- `bullets: ["text"]` → `[{text: "text"}]`
- `contact: ["a@b.com"]` → `[{kind: "email", value: "a@b.com"}]` (패턴 추론)
- `skills: ["Python"]` → `[{items: ["Python"]}]`
- `dates: "..."` → `{raw: "..."}`

정규화기가 이걸 처리하고, **경고를 남긴다** (`warnings[]`).

---

## §4. IR v1 스키마 (변경분만)

```ts
type ResumeIR = {
  version: "1.0";
  meta?: Meta;
  basics: Basics;
  summary?: Summary;
  experiences?: Experience[];      // ← 복수형, 현행 맞춤
  projects?: Project[];
  research?: Research[];           // ← 신규
  education?: Education[];
  skills?: SkillGroup[];
  awards?: Award[];                // ← 신규
  publications?: Publication[];    // ← 신규
  certifications?: Certification[];// ← 신규
  languages?: LanguageSkill[];     // ← 신규
  tags?: string[];                 // ← 이력서 단위 (현행 유지, JD 매칭용)
  custom?: CustomSection[];
};

type Experience = {
  key?: string;                    // ← pool 참조용
  org: string;                     // ← 현행 이름
  title?: string;                  // ← 현행 이름
  dates?: DateRange;
  location?: string;
  employmentType?: string;
  summary?: string;
  bullets?: Loose<Bullet>[];
  tech?: string[];
};

type Bullet = {
  text: string;
  sourceBulletKey?: string;        // ★ pool 원본 참조 — 점수 대신 하드 출처
  tags?: string[];
  priority?: number;               // 1(최상) ~ 5. auto-fit 이 참조
  sources?: string[];              // pool 의 sources (resume_id 목록)
};

type SkillGroup = {
  label?: string;                  // ← optional. 없으면 라벨 없는 한 줄
  items: string[];
  priority?: number;
};

type Education = {
  key?: string;
  school: string;                  // ← 현행 이름
  degree?: string;
  minor?: string;
  location?: string;
  dates?: DateRange;
  gpa?: { value: string; scale?: string; label?: string };
  coursework?: string[];
  details?: Loose<Bullet>[];       // ← 현행 이름
};

type Research = {                  // ← 신규 섹션
  key?: string;
  title: string;
  role?: string;
  institution?: string;
  department?: string;
  advisors?: Array<{ name: string; role?: "PI"|"mentor"|"advisor"; title?: string }>;
  dates?: DateRange;
  status?: "ongoing" | "completed" | "incoming";
  summary?: string;
  bullets?: Loose<Bullet>[];
  outputs?: string[];
};
```

나머지(`Meta`, `Basics`, `Contact`, `Summary`, `Project`, `Award`, `Publication`,
`Certification`, `LanguageSkill`, `CustomSection`, `RenderOptions`, `RenderResult`)는 **v0 그대로**.

---

## §5. 템플릿 계약 — 지금 유일한 블로커

as-built 가 명시: *"이 기능 전체를 막고 있는 단 하나가 템플릿 계약"*.
확장에 이미 템플릿 6개 UI 가 있고 서버가 `templateId` 를 못 받는다.

**레포가 이걸 정의하는 게 자연스럽다.** 레포의 존재 이유가 템플릿이니까.

```ts
type TemplateManifest = {
  id: string;                      // "classic" | "modern" | ...
  name: string;
  blurb: string;
  engine: "css" | "plain";         // ★ plain = fitz.Story 로도 렌더 가능
  atsSafe: boolean;
  supports: {
    sections: string[];            // 이 템플릿이 렌더할 수 있는 섹션
    options: string[];             // 노출할 옵션 키
  };
  preview?: string;                // 썸네일 URL
};
```

`GET /resume-templates` 는 이 배열을 반환. `engine` 필드가 무인 경로 문제를 해결한다 —
`fitz.Story` 는 `engine: "plain"` 만 렌더하고, 나머지는 브라우저 전용.

확장의 기존 6개 id 를 그대로 쓰면 UI 변경도 0.

---

## §6. 현행 한계 중 IR 이 해결하는 것 / 못 하는 것

| as-built §8 한계 | IR 이 해결? |
|---|---|
| 재파싱기 둘, 규칙 다름 | ✅ 구조화 출력이면 재파싱 자체가 사라짐 |
| "첫 줄=이름" 위치 관습 | ✅ `basics.name` 이 명시적 |
| markdown 구조 검증 없음 | ✅ 스키마가 검증 |
| 불릿 개수 코드 상한 없음 | ✅ `options.filter.maxBulletsPerEntry` |
| mode 별 섹션 목록 불일치 | ✅ `options.sections` 가 단일 진실 |
| 무엇을 왜 뺐는지 안 나옴 | ✅ `warnings[]` + `dropped[]` |
| guidance 구조가 HTTP 못 건넘 | ✅ 구조 유지 (별도 계약 변경 필요) |
| 템플릿 계약 없음 | ✅ §5 |
| 웹에 markdown 렌더러 없음 | ✅ 라이브러리 import 로 해소 |
| pool 단조 증가 (18,257자) | ❌ **IR 밖.** 별도 정리 정책 필요 |
| 이름 마스킹 앵커 취약성 | ❌ **IR 밖.** 다만 `basics.name` 이 명시적이면 앵커 추정이 불필요해져 간접 완화 |
| 자동 교정 프로덕션 0회 | ❌ 무관 |
| PDF 시각 품질 미검증 | ⚠️ 레포가 이걸 담당 — 브라우저 렌더면 눈으로 확인 가능 |
| ATS 실제 파싱 미검증 | ⚠️ **레포에서 실측 가능** (§8) |

---

## §7. 열린 질문 — 갱신

**v0 Q1 (같은 사실, 다른 언어) → 해소.**
as-built 확인 결과 tailoring 이 **매번 새로 생성**되고 저장되지 않는다.
따라서 "DE본 언어 / Quant본 언어"는 Artemis 가 생성 시점에 결정하는 게 맞다.
레포는 완성된 IR 만 받는다. → v0 의 (c)안 확정.

**v0 Q2 (priority 를 누가 채우나) → 부분 해소.**
현행 LLM 은 순서로만 중요도를 표현한다(점수·랭크 없음). 구조화 출력으로 바꾸면
`priority` 를 채우게 시킬 수 있고, 그게 auto-fit 의 입력이 된다. **다만 이건 새 능력 요구라
실패율 측정 필요.** 없으면 순서 기반 fallback.

**v0 Q3 (인라인 마크업) → `**` 만.** 웹에 렌더러가 없어 지금 글자로 보이는 상태이므로,
라이브러리가 `**` 만 처리하고 나머지 이스케이프하면 현행보다 무조건 낫다.

**신규 Q6. 구조화 출력 전환을 어느 경로부터?**
→ `resume_from_pool` (review) 권고. 이유: pool 이 이미 구조화돼 있어 입력 손실이 가장 적고,
review 경로라 실패해도 사람이 본다.

**신규 Q7. 보수 경로를 §2 참조 선택으로 바꿀 것인가?**
→ 이게 진짜 큰 개선인데 프롬프트·계약·eval 을 다 건드린다. **IR v1 범위 밖으로 두고 별도 판단.**

**신규 Q9. `sourceBulletKey` 를 무엇으로 하나?** ⚠️
pool 의 **엔트리**에는 `key` 가 있지만 **bullet 에는 없다** (`bullets: [{text, sources}]`).
따라서 참조하려면 둘 중 하나가 필요하다:
- (a) `{entryKey, bulletIndex}` 복합키 — pool 스키마 변경 없음. 단, bullet 순서가 바뀌면 깨짐
- (b) pool bullet 에 안정적 `key` 부여 — 스키마 변경 + 마이그레이션. 순서 무관하게 안정
→ pool 정리 작업이 어차피 예정돼 있으니 **(b) 를 그때 같이** 하는 게 낫다.

**신규 Q10. variant 그룹핑** ⚠️ *(§0-A 에서 관측된 중복 버그)*
같은 사실의 다른 프레이밍이 pool 에 별개 항목으로 쌓여 **출력에 둘 다 나온다.**
프롬프트는 *"When a bullet has multiple variants, pick the ONE most relevant"* 라고 하지만,
**엔트리 레벨 중복**(SURE 가 Experience 와 Projects 에 각각)은 막지 못한다.
→ pool 에 `variantGroup` 개념이 필요. IR 밖이지만 IR 품질을 직접 좌우.

**신규 Q8. `_serialize_pool` 은 그대로 두나?**
IR 을 입력으로도 쓸 수 있지만, 지금 평문 직렬화가 토큰 효율이 좋다(`_POOL_CAP = 40,000`).
→ **입력은 건드리지 말 것.** 출력만 바꾼다.

---

## §8. 레포가 채울 수 있는 검증 공백

as-built §8-4 의 "확인 못한 것" 중 둘은 **레포에서 바로 실측 가능**하다:

1. **ATS 실제 파싱** — 렌더된 PDF 를 실제 파서에 넣어본다.
   현행 테스트는 *"쓴 라이브러리로 다시 열어 읽는 수준"*(스스로 *"the closest stand-in"* 이라 인정).
   → 레포에 텍스트 추출 + 섹션 인식 회귀 테스트를 두면 **템플릿마다** ATS 안전성을 측정 가능.
   이게 레포의 차별점이 된다 (대부분의 이력서 템플릿 레포가 이걸 안 함).

2. **시각 품질** — *"아무도 PDF 를 만들어 눈으로 보지 않았다"*.
   → 브라우저 렌더면 프리뷰가 곧 결과물.

> ⚠️ **Tae 가 채워야 할 것 하나**: 실제 저장된 LLM 출력 1건.
> 권한 분류기가 막아서 as-built 문서가 못 가져왔고, 그래서 "모델이 실제로 어떤 섹션 헤더/불릿 마커를
> 쓰는가"는 **프롬프트 기준 주장이지 측정이 아니다.** 마크다운 파서를 짜려면 이게 필요하다.

---

## §9. 순서

1. **템플릿 계약 먼저** (`GET /resume-templates` + `templateId`) — IR 과 독립이고, 이미 만들어진 확장 UI 를 살린다
2. Claude Design 라운드 1~2 → 템플릿이 실제로 요구하는 필드 확인
3. IR v1 확정 → JSON Schema + 정규화기(§3-5) + 검증기
4. TS 라이브러리: `normalize(input) → IR`, `render(IR, options) → {html, css, warnings}`
5. 브라우저 어댑터 (Paged.js + print) → 웹앱/확장 import
6. ATS 회귀 테스트 (§8-1)
7. *(별건)* 구조화 출력 전환 — `resume_from_pool` 한 경로 A/B

---

## §10. RenderOptions.layout (추가)

```ts
layout?: {
  summaryInHeader?: boolean;   // 요약을 헤더 안(이름 아래, 연락처 위)에 라벨 없이
  skillsGrid?: boolean;        // 스킬을 정렬 그리드로. 기본은 인라인 'Label  items'
  orgFirst?: boolean;          // CV 관례: experiences·research 에서 기관명이 표제, 직함은 아래
}
```
`orgFirst` 는 DOM 순서 자체를 바꾸므로 추출 순서도 같이 바뀐다 — CSS `order` 와 달리 읽기 순서와 시각 순서가 일치한다.
education·projects 에는 적용하지 않는다(org 슬롯이 각각 위치·역할이라 뜻이 깨짐).
