# fit 기준값 (tools/fit.py, dense fixture, 1 page, minBodyPt 없음)

브라우저 `plan()` 이 같은 입력에서 이 밀도 ±0.03 이내면 동일 알고리즘으로 본다. `bodyPt = baseBodyPx × density × 0.75`.
재생성: 섹션·엔트리 목록 flex→block 수정(유령 틈 제거)과 날짜 풀어쓰기 이후.

| theme | density | trim | bodyPt |
|---|---|---|---|
| academic | 0.938 | prio≤∞ | 7.7pt |
| broadsheet | 0.978 | prio≤∞ | 7.3pt |
| classic | 0.882 | prio≤∞ | 8.0pt |
| colorfield | 0.904 | prio≤∞ | 7.1pt |
| folio | 0.876 | prio≤∞ | 7.0pt |
| ledger | 0.859 | prio≤2 | 7.1pt |
| marginalia | 0.854 | prio≤2 | 6.5pt |
| masthead | 0.921 | prio≤∞ | 7.2pt |
| minimal | 0.820 | prio≤∞ | 7.1pt |
| numerals | 0.820 | prio≤∞ | 6.5pt |
| plain | 1.000 | prio≤1 | 7.9pt |
| spread | 0.916 | prio≤∞ | 7.1pt |
| standfirst | 0.876 | prio≤∞ | 7.0pt |

이 표는 일반 모드(글자 크기가 density 를 따름)의 값이다. 본문 고정 모드(`--min-body-pt` / `FitPolicy.minBodyPt`)는 priority 티어 대신
가장 조밀한 여백에서 들어가는 최대 N 을 찾는다 — fit.py 와 plan() 동일. 예: 실제 DE 이력서, classic, 10pt → top-11, density 0.876.
