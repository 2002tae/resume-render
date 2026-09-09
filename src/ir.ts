/**
 * Resume IR — the contract between producers (markdown parser, Artemis, web UI)
 * and the renderer. Content only; never presentation.
 *
 * Every field is optional except `version`. Producers may not have more.
 */

export type DateValue = { year: number; month?: number; day?: number };

export type DateRange = {
  /** Always present. This is the truth and what gets rendered. */
  raw: string;
  start?: DateValue;
  end?: DateValue;
  current?: boolean;
};

export type Bullet = {
  text: string;
  /** Hard provenance back to the source pool, not a score. */
  sourceBulletKey?: string;
  tags?: string[];
  /** 1 = most important. auto-fit trims from the high end. */
  priority?: number;
  sources?: string[];
};

/** Producers may send a bare string; normalize() lifts it. */
export type LooseBullet = Bullet | string;

export type Contact = {
  kind: "email" | "phone" | "website" | "linkedin" | "github" | "scholar" | "orcid" | "twitter" | "other";
  value: string;
  url?: string;
  label?: string;
};
export type LooseContact = Contact | string;

export type Basics = {
  name?: string;
  headline?: string;
  tagline?: string;
  location?: { city?: string; region?: string; country?: string };
  contacts?: LooseContact[];
};

export type Summary = {
  style?: "paragraph" | "bullets";
  text?: string;
  bullets?: LooseBullet[];
};

export type Experience = {
  key?: string;
  org: string;
  title?: string;
  dates?: DateRange | string;
  /** 오퍼 수락 후 입사 전 등. 문구는 dates.raw 가 담당, 이건 정렬·배지용 */
  status?: "ongoing" | "completed" | "incoming" | "accepted" | "deferred";
  location?: string;
  employmentType?: string;
  summary?: string;
  bullets?: LooseBullet[];
  tech?: string[];
};

export type Project = {
  key?: string;
  name: string;
  subtitle?: string;
  role?: string;
  url?: string;
  repository?: string;
  dates?: DateRange | string;
  summary?: string;
  bullets?: LooseBullet[];
  tech?: string[];
};

export type Advisor = { name: string; role?: "PI" | "mentor" | "advisor" | "supervisor"; title?: string };

export type Research = {
  key?: string;
  title: string;
  role?: string;
  institution?: string;
  department?: string;
  advisors?: Advisor[];
  dates?: DateRange | string;
  status?: "ongoing" | "completed" | "incoming";
  summary?: string;
  bullets?: LooseBullet[];
  outputs?: string[];
};

export type Education = {
  key?: string;
  school: string;
  degree?: string;
  minor?: string;
  location?: string;
  dates?: DateRange | string;
  gpa?: { value: string; scale?: string; label?: string };
  coursework?: string[];
  details?: LooseBullet[];
};

export type SkillGroup = {
  /** Optional — a bare list renders as one unlabeled line. */
  label?: string;
  items: string[];
  priority?: number;
};

export type Award = { title: string; issuer?: string; date?: DateValue; description?: string };
export type Publication = { title: string; authors?: string[]; venue?: string; date?: DateValue; url?: string; doi?: string; note?: string };
export type Certification = { name: string; issuer?: string; date?: DateValue; expires?: DateValue; credentialId?: string; url?: string };
export type LanguageSkill = { language: string; proficiency?: string; note?: string };

export type CustomItem = { title?: string; subtitle?: string; dates?: DateRange | string; text?: string; bullets?: LooseBullet[] };
export type CustomSection = { key: string; label: string; layout?: "bullets" | "entries" | "inline" | "paragraph"; items: CustomItem[] };

export type Meta = {
  label?: string;
  targetRole?: string;
  targetCompany?: string;
  generatedAt?: string;
  source?: "markdown" | "artemis" | "web" | "json-resume";
  locale?: string;
};

export type ResumeIR = {
  version: "1.0";
  meta?: Meta;
  basics?: Basics;
  summary?: Summary;
  education?: Education[];
  experiences?: Experience[];
  projects?: Project[];
  research?: Research[];
  skills?: SkillGroup[] | string[];
  awards?: Award[];
  publications?: Publication[];
  certifications?: Certification[];
  languages?: LanguageSkill[];
  /** Résumé-level tags for JD matching (Artemis). */
  tags?: string[];
  custom?: CustomSection[];
};

export type SectionKey =
  | "summary" | "education" | "experiences" | "projects" | "research"
  | "skills" | "awards" | "publications" | "certifications" | "languages";

export type FitPolicy = {
  mode: "original" | "compact" | "strict";
  pages?: number;
  minBodyPt?: number;
  trim?: "none" | "priority" | "ask";
};

export type RenderOptions = {
  theme?: string;
  /** 렌더러는 이 값을 읽지 않는다(순수 함수). 어댑터(plan/fit)가 읽는다. */
  fit?: FitPolicy;
  sections?: {
    order?: SectionKey[];
    include?: SectionKey[];
    exclude?: SectionKey[];
    labels?: Partial<Record<SectionKey, string>>;
  };
  filter?: { tags?: string[]; maxBulletsPerEntry?: number; minPriority?: number };
  /** CSS custom property overrides applied on .rz */
  vars?: Record<string, string>;
  layout?: {
    /** 요약을 헤더 안(이름 아래, 연락처 위)에 렌더. 매거진형 테마(standfirst, marginalia)가 쓴다. */
    summaryInHeader?: boolean;
    /** 스킬을 라벨 열이 정렬된 그리드로. 기본은 원본대로 '라벨 + 항목' 인라인 */
    skillsGrid?: boolean;
    /** CV 관례: 엔트리 헤드에서 기관명(org)을 직함(title)보다 먼저 렌더 */
    orgFirst?: boolean;
  };
  locale?: string;
};

export type WarningCode =
  | "MISSING_NAME" | "SECTION_EMPTY" | "ENTRY_NO_BULLETS"
  | "UNKNOWN_SECTION" | "DATE_UNPARSEABLE" | "LOOSE_INPUT";

export type Warning = { code: WarningCode; message: string; path?: string };

export type RenderResult = { html: string; warnings: Warning[] };
