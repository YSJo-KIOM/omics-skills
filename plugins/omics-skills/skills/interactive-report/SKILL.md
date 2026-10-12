---
name: interactive-report
description: Build a single-file interactive HTML report from analysis results or literature findings — theme tabs (summary first, environment last), tables with dropdown/slider/expression filters, a selection basket that exports TSV, a review form that exports Markdown decisions for the next step, Plotly charts linked to table filters (volcano, bar, histogram, box), and embedded figures. Opens locally or publishes as a claude.ai Artifact. Use when the user asks for an interactive report, web report, HTML 보고서, 인터랙티브 보고서, 결과 정리 페이지, 아티팩트 보고서, or wants DEG / enrichment / screening / candidate / literature tables turned into a browsable, filterable page with exportable selections.
---

# interactive-report

분석 결과·문헌 근거를 **탭으로 나뉜 단일 HTML 보고서**로 만든다. 내용은 spec(JSON) 하나로 적고,
`scripts/build_report.py` 가 데이터·그림을 묶어 파일 하나로 만든다. 외부 의존은 Plotly CDN(그래프가 있을 때만)뿐이다.

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/build_report.py" report/spec.json                 # -> report/spec.html
python3 "${CLAUDE_SKILL_DIR}/scripts/build_report.py" report/spec.json -o report/x_artifact.html --artifact
```

`CLAUDE_SKILL_DIR` 는 이 SKILL.md 가 있는 폴더다. 빌더는 Python 표준 라이브러리만 쓴다 (YAML spec 만 PyYAML 필요).

## 언제 쓰나

| 쓴다 | 다른 걸 쓴다 |
|---|---|
| DEG·enrichment·네트워크 결과 정리, 후보 스크리닝 표, 데이터셋 비교, 문헌 근거 정리, 분석 계획의 선택지 검토 | 발표 슬라이드 → scientific-slides / pptx · 출판용 정적 그림 → scientific-visualization · 실시간 대시보드 → Artifact Dashboard 타입 |

## 작업 순서

1. **독자와 목적을 한 줄로** 정한다 — 누가 읽고, 읽은 뒤 무엇을 결정하는가. 이것이 요약 탭과 review 항목이 된다.
2. **탭을 계획**한다 (아래 규칙). 탭 3–8개.
3. **데이터를 TSV 로** 저장한다. 숫자는 숫자 그대로 (반올림·`"1.2e-5"` 같은 문자열 포맷 금지 — 정렬·필터가 깨진다).
   - R: `write.table(df, "deg.tsv", sep = "\t", quote = FALSE, row.names = FALSE)`
   - Python: `df.to_csv("deg.tsv", sep="\t", index=False)`
   - 그림: PNG 150–200 dpi 또는 SVG. 그림 하나 3 MB 이하.
4. **spec.json 을 보고서 폴더에 작성**한다 (데이터와 같은 폴더 — 경로는 spec 기준 상대경로). 스키마: [references/spec.md](references/spec.md). 시작점은 [examples/](examples/) 를 복사.
   R 에서는 `jsonlite::write_json(spec, "spec.json", auto_unbox = TRUE, pretty = TRUE)` 로 써도 된다.
5. **빌드하고 경고를 모두 해결**한다. 오류 메시지는 어떤 탭·블록·열이 문제인지 알려 준다.
6. **확인** (선택, 그래프·레이아웃을 바꿨을 때):
   `google-chrome --headless=new --no-sandbox --virtual-time-budget=8000 --window-size=1400,1300 --screenshot=shot.png "file://$PWD/report/spec.html#<탭id>"` 후 스크린샷을 본다.
7. **전달**: 로컬 HTML 경로를 알려 준다. 공유·열람용 링크가 필요하면 `--artifact` 로 만든 파일을 Artifact 도구로 게시하고
   `capabilities: {"downloads": true}` 를 함께 준다 (TSV·Markdown **저장** 버튼이 이 기능을 쓴다. 없어도 **복사**는 된다).

## 탭 설계 규칙

- **첫 탭 = 요약** (`"role": "summary"`). 순서: 핵심 수치 카드 3–6개 → `## 핵심 결과` 3–5줄 (결론 먼저, 숫자 포함) →
  `## 판단이 필요한 것` → 필요하면 "이 보고서 쓰는 법" tip. 큰 표는 넣지 않는다.
- **중간 탭 = 질문 하나에 탭 하나** (차등발현 / 기능 분석 / 네트워크 / 문헌 근거 …). 탭 안 순서는
  한두 문장 설명 → 그래프 → 표 → 해석·주의. 블록이 8개를 넘으면 `details` 로 접거나 탭을 나눈다.
- **다음 단계 탭** (권장): `review` 블록으로 사용자가 고를 방향을 항목화한다.
- **마지막 탭 = 분석 환경·기타**: spec 의 `environment` (software · parameters · data · reproduce · notes) 와 `glossary` 로
  빌더가 자동으로 만든다. 마지막 탭 role 이 `environment` 이면 그 탭 뒤에 붙인다. 빌더가 생성 시각·도구 버전도 넣는다.

## 블록

| type | 용도 | 핵심 키 |
|---|---|---|
| 문자열 / `md` | 서술 (markdown 일부: 제목·목록·표·인용·코드, `PMID 123`·`doi:10.x` 자동 링크) | `text` |
| `cards` | 핵심 수치 | `items[{value,label,note,tone}]` |
| `callout` | 주의·팁·결론 강조 | `tone` note/warn/good/tip, `title`, `text` |
| `table` | 필터 표 | `table`(id) 또는 인라인 `source`/`rows` |
| `chart` | 표와 연동된 그래프 | `table`, `kind` scatter/bar/histogram/box, `x`,`y`,`color` |
| `figure` | 그림 파일 내장 (클릭 확대) | `src` 또는 `images[]` |
| `review` | 방향 검토 → Markdown | `id`, `items[{id,title,fields}]` |
| `kv` · `glossary` · `code` · `html` | 키-값 표 · 용어 · 코드 · 원시 HTML | |
| `details` | 접어 두는 부록 | `summary`, `blocks` |

모든 블록에 `title`, `intro`(md) 를 줄 수 있다.

## 표 — dropdown · slider 필터

열 타입은 데이터에서 추론한다: 모두 숫자 → `num` (dual slider + 식 입력), 반복되는 값 12종 이하 → `cat` (dropdown),
`http` 값 → `link`, 나머지 → `text` (포함 검색). 이름이 `*_id`·`pmid`·`entrez`·`cid` 인 정수 열은 숫자로 보지 않는다.
필요한 것만 직접 지정한다:

```json
{"key": "log2FC", "tone": "sign", "dp": 2, "tip": "처리/대조 log2 비"}
{"key": "padj", "fmt": "sci"}
{"key": "direction", "type": "cat", "badges": {"up": "up", "down": "down"}}
{"key": "pathways", "type": "cat", "sep": ";"}
{"key": "pmid", "type": "link", "link": "https://pubmed.ncbi.nlm.nih.gov/{v}/"}
{"key": "evidence", "wrap": true}
```

숫자 필터 칸에는 `>=1`, `<0.05`, `abs>=1`, `>0 <5` 같은 식을 쓸 수 있다. 표는 200행씩 그리므로 수만 행도 된다.
머리 클릭 = 정렬, 행 클릭 = 바구니, 긴 칸 클릭 = 펼침.

## 다음 단계로 넘기는 장치

- **선택 바구니** (모든 보고서에 자동): 행 클릭, "보이는 행 담기"(필터 통과 행 전부), 그래프 점 클릭·올가미 선택으로 담는다.
  **TSV 복사·저장** — 머리행은 원래 열 이름, 값은 원본 값이라 다음 분석 입력으로 바로 쓴다. 여러 표에서 담으면 `# table: <제목>` 으로 구분된다.
- **review 블록** (EPICv2 명세 작성기 방식): 항목마다 필드(`choice`·`multi`·`text`·`textarea`·`number`)를 두고,
  선택지에 설명(`d`)·근거(`r`)·권고(`rec`)·주의(`warn`)를 단다. **Markdown 생성** → 복사·저장. 바구니 내용을 표로 덧붙일 수 있다.
  선택은 브라우저에 자동 저장된다.
- 사용자가 이 Markdown 이나 TSV 를 다시 붙여 넣으면 그것을 다음 단계(검증 대상, 추가 분석, 명세 확정)의 입력으로 쓴다.

## 그래프 — 시각적 탐색

`chart` 는 같은 표 블록의 **필터·정렬 결과를 따라 다시 그려진다**.
- volcano: `{"kind":"scatter","x":"log2FC","y":"padj","y_transform":"-log10","color":"direction","lines":{"x":[-1,1],"y":[1.301]}}`
  (`color` 값 up/down/ns 는 자동으로 빨강/파랑/회색. 다른 값은 `colors` 로 지정)
- 상위 term 막대: `{"kind":"bar","x":"term","y":"padj","y_transform":"-log10","top":15}` — 표 정렬 순서대로 위 N개
- 범주 개수: `{"kind":"bar","x":"source","color":"direction"}` · 분포: `histogram` · 군 비교: `box`
- 그 밖의 그래프는 `{"type":"chart","data":[plotly traces],"layout":{...}}` (표 연동 없음).
그래프는 탭이 처음 보일 때 그린다. Plotly 를 못 불러오면 안내문이 뜨고 표는 그대로 동작한다.

## 용도별 시작점

- **분석 결과**: [examples/analysis/spec.json](examples/analysis/spec.json) — 요약 · volcano+DEG 표 · 상위 term 막대+enrichment 표 · 다음 단계 review.
- **문헌 보고**: [examples/literature/spec.json](examples/literature/spec.json) — 인라인 `rows`, PMID/DOI 링크, 근거 수준 `cat`, 키워드 `sep`, 요지 `wrap`, 도구 선택 review.
- **후보 스크리닝**: 점수 `num`, tier `cat`+`badges`, 플래그 `sep`, 근거 `wrap`, 외부 ID `link`; 요약 탭에 tier 별 카드.
- **계획·명세 검토**: review 중심 탭 + 근거 표. 선택지마다 `r`(근거)와 `rec`/`warn`.

## 지킬 것

- 환자 실명·식별 번호, API 키·토큰을 표·그림·spec 에 넣지 않는다. Artifact 는 비공개로 시작하지만 공유될 수 있다.
- 결과는 16 MB 이하 (Artifact 한도). 넘으면 필요한 열만, 유의 행만, 상위 N 으로 줄인다.
- 외부 이미지 URL 은 Artifact 에서 차단된다 — 파일로 받아 `src` 에 경로로 넣는다.
- spec.json·데이터를 보고서 옆에 두고, 재생성 명령을 `environment.reproduce` 에 적는다.
- 숫자 결론(카드·핵심 결과)은 표 데이터에서 계산해 넣는다. 손으로 옮겨 적지 않는다.
- 필터·바구니·검토 선택은 보는 사람의 브라우저에만 남는다 (공유 상태가 아님). 공동 기록이 필요하면 별도 설계가 필요하다.
