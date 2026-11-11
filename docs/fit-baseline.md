# fit 기준값 (tools/fit.py, dense fixture, 1 page, minBodyPt 없음)

브라우저 `plan()` 이 같은 입력에서 이 밀도 ±0.03 이내면 동일 알고리즘으로 본다. `bodyPt = baseBodyPx × density × 0.75`.
재생성 (2026-10): 페이지 여백 수정 이후 — W17 `box-decoration-break:clone`, W18 다단 테마의 아래 여백을 `@page` 로.
이전 표는 마지막 줄이 아래 여백 안에 찍히던 상태에서 '1페이지' 로 판정한 값이라 수용량을 과대평가했다
(minimal·numerals 는 절삭 없이, plain 은 prio≤1 로 들어간다고 했지만 실제로는 각각 prio≤2, top-6 이 필요하다). 밀도는 테마에 실제로 넘어가는 3자리 값이다.

| theme | density | trim | bodyPt |
|---|---|---|---|
| academic | 0.921 | prio≤∞ | 7.5pt |
| broadsheet | 0.978 | prio≤∞ | 7.3pt |
| classic | 0.848 | prio≤∞ | 7.7pt |
| colorfield | 0.882 | prio≤∞ | 6.9pt |
| folio | 0.865 | prio≤∞ | 6.9pt |
| ledger | 0.826 | prio≤2 | 6.8pt |
| marginalia | 0.831 | prio≤2 | 6.4pt |
| masthead | 0.887 | prio≤∞ | 6.9pt |
| minimal | 0.843 | prio≤2 | 7.3pt |
| numerals | 0.837 | prio≤2 | 6.7pt |
| plain | 0.994 | top-6 | 7.8pt |
| spread | 0.916 | prio≤∞ | 7.1pt |
| standfirst | 0.876 | prio≤∞ | 7.0pt |

이 표는 일반 모드(글자 크기가 density 를 따름)의 값이다. 본문 고정 모드(`--min-body-pt` / `FitPolicy.minBodyPt`)는 priority 티어 대신
가장 조밀한 여백에서 들어가는 최대 N 을 찾는다 — fit.py 와 plan() 동일. 예: 실제 DE 이력서(2026-10), classic, 10pt → top-11, density 0.904.
