# fit 기준값 (tools/fit.py, dense fixture, 1 page, minBodyPt 없음)

브라우저 `plan()` 이 같은 입력에서 이 밀도 ±0.03 이내면 동일 알고리즘으로 본다. `bodyPt = baseBodyPx × density × 0.75`.

| theme | density | bodyPt |
|---|---|---|
| academic | 0.932 | 7.6 |
| broadsheet | 0.978 | 7.3 |
| classic | 0.865 | 7.8 |
| colorfield | 0.899 | 7.0 |
| folio | 0.876 | 7.0 |
| ledger | 0.831 | 6.9 |
| marginalia | 0.854 | 6.5 |
| masthead | 0.899 | 7.0 |
| minimal | 0.820 | 7.1 |
| numerals | 0.854 | 6.8 |
| plain | 1.000 | 7.9 |
| spread | 0.910 | 7.0 |
| standfirst | 0.876 | 7.0 |

10pt 고정(body-lock)·요약 없음·스킬 4그룹에서의 수용량은 각 매니페스트 `capacity.bulletsAt1Page.bodyPt10` 에 있다.
