"""
resume_ir.py — src/ir.ts 의 Pydantic 거울. Artemis 백엔드(FastAPI · SQLModel)가 쓴다.

용도
  1. LLM 구조화 출력의 스키마 (`ResumeIR.model_json_schema()` 를 response_format 에)
  2. 렌더 전 검증 — render() 는 검증하지 않는다(순수 함수). 여기서 걸러라.
  3. Loose 입력 정규화 — 문자열 bullet/contact/date 를 객체로 올린다 (ir.ts 의 Loose<T> 와 동일)

ir.ts 와 어긋나면 ir.ts 가 맞다. 필드를 추가할 땐 둘 다 바꿔라.
"""
from __future__ import annotations
from typing import Literal, Optional, Union, Any
from pydantic import BaseModel, Field, field_validator, model_validator

# ── 원자 ─────────────────────────────────────────────────────────────

class DateValue(BaseModel):
    year: int
    month: Optional[int] = None
    day: Optional[int] = None

class DateRange(BaseModel):
    raw: str                                   # 항상 존재 — 이것이 렌더된다
    start: Optional[DateValue] = None
    end: Optional[DateValue] = None
    current: Optional[bool] = None

class Bullet(BaseModel):
    text: str
    sourceBulletKey: Optional[str] = None      # pool 원본 참조 (점수 아님)
    tags: Optional[list[str]] = None
    priority: Optional[int] = Field(None, ge=1, le=5)   # 1 = 가장 중요. fit 이 큰 숫자부터 자른다
    sources: Optional[list[str]] = None

ContactKind = Literal["email","phone","website","linkedin","github","scholar","orcid","twitter","other"]

class Contact(BaseModel):
    kind: ContactKind
    value: str
    url: Optional[str] = None
    label: Optional[str] = None

def _contact_kind(v: str) -> ContactKind:
    import re
    if "@" in v: return "email"
    if re.search(r"linkedin\.com", v, re.I): return "linkedin"
    if re.search(r"github\.com", v, re.I): return "github"
    if re.match(r"^\+?[\d\s().-]{5,}$", v) and re.search(r"\d{3}", v): return "phone"
    if "." in v: return "website"
    return "other"

# ── 섹션 ─────────────────────────────────────────────────────────────

class Basics(BaseModel):
    name: Optional[str] = None
    headline: Optional[str] = None
    tagline: Optional[str] = None
    location: Optional[dict] = None
    contacts: Optional[list[Contact]] = None

    @field_validator("contacts", mode="before")
    @classmethod
    def _loose_contacts(cls, v):
        if not v: return v
        return [ {"kind": _contact_kind(c), "value": c} if isinstance(c, str) else c for c in v ]

def _loose_bullets(v):
    if not v: return v
    return [ {"text": b} if isinstance(b, str) else b for b in v ]

_MONTHS = ["jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"]
_MON = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
import re as _re
_ABBREV = _re.compile(rf"^\s*({_MON})\s*[–—-]\s*({_MON})\s+(\d{{4}})\s*$", _re.I)

def expand_date_range(raw: str) -> str:
    """render.ts expandDateRange 와 같은 규칙: "May – Jul 2026" → "May 2026 – Jul 2026"."""
    m = _ABBREV.match(raw)
    if not m: return raw
    idx = lambda x: _MONTHS.index(x[:3].lower())
    y = int(m.group(3)); start = y - 1 if idx(m.group(1)) > idx(m.group(2)) else y
    return f"{m.group(1)} {start} – {m.group(2)} {y}"

def _loose_dates(v):
    if isinstance(v, str): return {"raw": expand_date_range(v)}
    if isinstance(v, dict) and isinstance(v.get("raw"), str): return {**v, "raw": expand_date_range(v["raw"])}
    return v

Status = Literal["ongoing","completed","incoming","accepted","deferred"]

class Summary(BaseModel):
    style: Optional[Literal["paragraph","bullets"]] = None
    text: Optional[str] = None
    bullets: Optional[list[Bullet]] = None
    _lb = field_validator("bullets", mode="before")(classmethod(lambda cls, v: _loose_bullets(v)))

class Experience(BaseModel):
    key: Optional[str] = None
    org: str
    title: Optional[str] = None
    dates: Optional[DateRange] = None
    status: Optional[Status] = None
    location: Optional[str] = None
    employmentType: Optional[str] = None
    summary: Optional[str] = None
    bullets: Optional[list[Bullet]] = None
    tech: Optional[list[str]] = None
    _lb = field_validator("bullets", mode="before")(classmethod(lambda cls, v: _loose_bullets(v)))
    _ld = field_validator("dates", mode="before")(classmethod(lambda cls, v: _loose_dates(v)))

class Project(BaseModel):
    key: Optional[str] = None
    name: str
    subtitle: Optional[str] = None
    role: Optional[str] = None
    url: Optional[str] = None
    repository: Optional[str] = None
    dates: Optional[DateRange] = None
    summary: Optional[str] = None
    bullets: Optional[list[Bullet]] = None
    tech: Optional[list[str]] = None
    _lb = field_validator("bullets", mode="before")(classmethod(lambda cls, v: _loose_bullets(v)))
    _ld = field_validator("dates", mode="before")(classmethod(lambda cls, v: _loose_dates(v)))

class Advisor(BaseModel):
    name: str
    role: Optional[Literal["PI","mentor","advisor","supervisor"]] = None
    title: Optional[str] = None

class Research(BaseModel):
    key: Optional[str] = None
    title: str
    role: Optional[str] = None
    institution: Optional[str] = None
    department: Optional[str] = None
    advisors: Optional[list[Advisor]] = None
    dates: Optional[DateRange] = None
    status: Optional[Status] = None
    summary: Optional[str] = None
    bullets: Optional[list[Bullet]] = None
    outputs: Optional[list[str]] = None
    _lb = field_validator("bullets", mode="before")(classmethod(lambda cls, v: _loose_bullets(v)))
    _ld = field_validator("dates", mode="before")(classmethod(lambda cls, v: _loose_dates(v)))

class GPA(BaseModel):
    value: str
    scale: Optional[str] = None
    label: Optional[str] = None

class Education(BaseModel):
    key: Optional[str] = None
    school: str
    degree: Optional[str] = None
    minor: Optional[str] = None
    location: Optional[str] = None
    dates: Optional[DateRange] = None
    gpa: Optional[GPA] = None
    coursework: Optional[list[str]] = None
    details: Optional[list[Bullet]] = None
    _lb = field_validator("details", mode="before")(classmethod(lambda cls, v: _loose_bullets(v)))
    _ld = field_validator("dates", mode="before")(classmethod(lambda cls, v: _loose_dates(v)))

class SkillGroup(BaseModel):
    label: Optional[str] = None
    items: list[str]
    priority: Optional[int] = None

class Award(BaseModel):
    title: str
    issuer: Optional[str] = None
    date: Optional[DateValue] = None
    description: Optional[str] = None

class LanguageSkill(BaseModel):
    language: str
    proficiency: Optional[str] = None
    note: Optional[str] = None

class Meta(BaseModel):
    label: Optional[str] = None
    targetRole: Optional[str] = None
    targetCompany: Optional[str] = None
    generatedAt: Optional[str] = None
    source: Optional[Literal["markdown","artemis","web","json-resume"]] = None
    locale: Optional[str] = None

# ── 루트 ─────────────────────────────────────────────────────────────

class ResumeIR(BaseModel):
    version: Literal["1.0"] = "1.0"
    meta: Optional[Meta] = None
    basics: Optional[Basics] = None
    summary: Optional[Summary] = None
    education: Optional[list[Education]] = None
    experiences: Optional[list[Experience]] = None
    projects: Optional[list[Project]] = None
    research: Optional[list[Research]] = None
    skills: Optional[list[SkillGroup]] = None
    awards: Optional[list[Award]] = None
    languages: Optional[list[LanguageSkill]] = None
    tags: Optional[list[str]] = None

    @field_validator("skills", mode="before")
    @classmethod
    def _loose_skills(cls, v):
        # ir.ts: skills 는 SkillGroup[] | string[] — 평면 문자열 배열이면 무라벨 그룹 하나로
        if v and all(isinstance(x, str) for x in v): return [{"items": v}]
        return v

    def bullet_count(self, min_priority: int | None = None) -> int:
        n = 0
        for sec in (self.experiences or []), (self.projects or []), (self.research or []):
            for x in sec:
                for b in (x.bullets or []):
                    if min_priority is None or (b.priority or 99) <= min_priority: n += 1
        return n

# ── 렌더 옵션 (RenderOptions 거울, FitPolicy 포함) ─────────────────────

class FitPolicy(BaseModel):
    mode: Literal["original","compact","strict"] = "original"
    pages: Optional[int] = None
    minBodyPt: Optional[float] = None
    trim: Optional[Literal["none","priority","ask"]] = None

class SectionsOpt(BaseModel):
    order: Optional[list[str]] = None
    include: Optional[list[str]] = None
    exclude: Optional[list[str]] = None
    labels: Optional[dict[str, str]] = None

class LayoutOpt(BaseModel):
    summaryInHeader: Optional[bool] = None
    skillsGrid: Optional[bool] = None
    orgFirst: Optional[bool] = None

class RenderOptions(BaseModel):
    theme: Optional[str] = None
    fit: Optional[FitPolicy] = None
    sections: Optional[SectionsOpt] = None
    filter: Optional[dict[str, Any]] = None
    vars: Optional[dict[str, str]] = None
    layout: Optional[LayoutOpt] = None

if __name__ == "__main__":
    import json, sys, pathlib
    # 셀프 테스트: 레포 fixture 4종이 전부 통과해야 한다
    root = pathlib.Path(__file__).resolve().parent.parent.parent
    for f in sorted((root / "fixtures").glob("*.json")):
        ir = ResumeIR.model_validate(json.loads(f.read_text()))
        print(f"  {f.name:14s} ok  bullets={ir.bullet_count()}  prio≤2={ir.bullet_count(2)}")
    print("schema keys:", list(ResumeIR.model_json_schema()["properties"])[:6], "…")
