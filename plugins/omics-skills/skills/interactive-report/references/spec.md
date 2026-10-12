# spec 스키마 (build_report.py v0.3)

spec 은 JSON(또는 YAML) 객체 하나다. 상대경로는 spec 파일 위치 기준.

```json
{
  "meta": {...},
  "tables": {"<id>": {...}},
  "tabs": [{"id": "...", "title": "...", "role": "...", "blocks": [...]}],
  "environment": {...},
  "glossary": [["용어", "설명"]],
  "cat_max": 12
}
```

## meta

| 키 | 필수 | 설명 |
|---|---|---|
| `title` | ✔ | 보고서 이름 (브라우저 탭·머리글) |
| `subtitle` | | 한 줄 설명 |
| `date` | | 기본값: 빌드한 날 |
| `author`, `source` | | 머리글 보조 줄 |
| `id` | | 브라우저 저장 키. 보고서마다 다르게 (기본: title) |

## tables

표는 `tables` 에 id 로 정의하고 블록에서 `"table": "<id>"` 로 부른다. 같은 표를 여러 블록이 쓸 수 있고,
그래프는 그 표를 보여 주는 **첫 표 블록**의 필터를 따른다. 표 블록 안에 바로 `source`/`rows` 를 써도 된다 (id 는 `id` 키 또는 자동).

| 키 | 설명 |
|---|---|
| `source` | TSV/CSV 경로. `.tsv/.tab/.txt` 또는 첫 줄에 탭이 있으면 탭 구분 |
| `rows` | 인라인 행: `[{열: 값}]` 또는 `[[...]]` + `header` |
| `title` | 표 제목 (블록 제목·바구니 그룹명) |
| `key` | 바구니 목록에 보일 열 (기본: 첫 열) |
| `columns` | 보일 열과 순서. 문자열 또는 열 객체. 생략하면 모든 열 |
| `labels` | `{열: 표시 이름}` 간단 지정 |
| `sort` | 기본 정렬. `"padj"` (오름차순), `"-score"` (내림차순), 또는 `{"key":..,"desc":true}` |
| `artifact` | Artifact 판에 남길 상위 결과 `{top, sort, where, columns}` (아래). 로컬 전체판에는 영향 없음 |

결측으로 보는 값: 빈칸, `NA`, `NaN`, `null`, `None`, `N/A`, `#N/A`, 무한대.

### artifact (Artifact 축소판 기준)

```json
"artifact": {"top": 3000, "sort": "padj", "where": {"padj": "<0.1", "log2FC": "abs>=0.5"}, "columns": ["gene", "log2FC", "padj"]}
```
순서: `where` 로 거른 뒤 → `sort` (기본은 표의 sort) 로 정렬 → 위에서 `top` 행 → `columns` 만 남김 (key 열은 항상 포함).
조건 문법은 표의 숫자 필터와 같다 (`<0.05`, `>=1`, `abs>=1`, `>0 <5`, 숫자가 아니면 포함 검색).
`--artifact`/`--both` 빌드에서만 적용된다. 그래도 크기 상한을 넘으면 가장 큰 표부터 정렬 순 상위로 자동 축소한다.

### 열 객체

| 키 | 값 | 설명 |
|---|---|---|
| `key` | | 데이터 열 이름 (필수) |
| `label` | | 머리 표시 이름 |
| `type` | `num` `cat` `text` `link` | 생략하면 추론 (SKILL.md 참고) |
| `tip` | | 머리에 마우스를 올리면 보이는 설명 (`?` 표시) |
| `fmt` | `int` `pct` `sci` | 정수(천 단위 쉼표) · 0–1 을 % · 지수 표기 |
| `dp` | 정수 | 소수 자릿수 |
| `tone` | `sign` | 양수 빨강 / 음수 파랑 (log2FC 등) |
| `badges` | `{값: 톤}` | cat 값을 알약으로. 톤: `up` `down` `good` `warn` `acc` `mut` |
| `sep` | `";"` 등 | 한 칸에 여러 값. dropdown 은 값 하나를 고르면 그 값을 포함한 행 |
| `link` | URL 틀 | `{v}` 자리에 값. `"{v}"` 또는 생략 시 값이 http(s) URL 일 때만 링크 |
| `wrap` | bool | 긴 글: 세 줄로 접고 클릭하면 펼침 (평균 50자 넘으면 자동) |
| `width` | px | 최소 너비 |
| `range` | `[lo, hi]` | 슬라이더 범위 제한 (극단값이 있을 때) |
| `filter` | `false` | 이 열의 필터 칸 숨김 |

## tabs

| 키 | 설명 |
|---|---|
| `id` | URL `#id` 로 바로 열림. 영문·숫자·`-_.~` |
| `title` | 탭 버튼 이름 (필수) |
| `role` | `summary` (첫 탭에 권장) · `environment` (마지막 탭; 환경 블록이 여기에 붙음) |
| `blocks` | 블록 목록 |

빌더 경고: 첫 탭이 요약이 아님 · 빈 탭 · 블록 14개 초과 · 탭 10개 초과.

## blocks

모든 블록 공통: `title` (h3, `"level": 2` 면 h2), `intro` (제목 아래 md 한 단락).

### 문자열 / md / html / code
- 문자열 하나 = `{"type":"md","text":...}`.
- md 지원: `#`–`####` 제목(→h2–h4), 문단, `-`/`1.` 목록, `>` 인용, ``` 코드, `| 표 |`, `**굵게**`, `*기울임*`, `` `코드` ``,
  `[글](url)`, 맨 URL, `PMID 12345678`, `doi:10.xxx/yyy` 자동 링크. 원시 HTML 은 이스케이프된다.
- `{"type":"html","html":"..."}` 는 그대로 넣는다 (직접 만든 SVG 도식 등).
- `{"type":"code","text":"..."}`.

### cards
```json
{"type":"cards","items":[{"value":119,"label":"DEG","note":"padj<0.05","tone":"up"}]}
```

### callout
```json
{"type":"callout","tone":"warn","title":"주의","text":"md"}
```
tone: `note`(기본) `warn` `good` `tip`.

### table
```json
{"type":"table","table":"deg","height":620,"page":200,"sort":"-score"}
```
`height`: 표 스크롤 높이(px). `page`: 한 번에 그리는 행 수. `sort`: 이 블록만의 기본 정렬.
도구 막대: 전체 검색 · 필터 초기화 · 보이는 행 담기 · TSV 복사 · TSV 저장(필터 결과 전체).

### chart
```json
{"type":"chart","table":"deg","kind":"scatter","x":"log2FC","y":"padj","y_transform":"-log10",
 "color":"direction","hover":["baseMean"],"label":"gene","lines":{"x":[-1,1],"y":[1.301]},"height":460}
```
| 키 | 설명 |
|---|---|
| `kind` | `scatter` (x,y 숫자) · `bar` (x 범주; y 를 주면 표 순서 상위 `top` 행의 값, 안 주면 x 범주별 행 수) · `histogram` (x 숫자) · `box` (y 숫자, x 범주 선택) |
| `color` | cat 열이면 범주별 색 (up/down/ns 자동), num 열이면 색 척도 |
| `colors` | `{범주: "#hex" 또는 "--up" 같은 토큰}` |
| `x_transform`, `y_transform` | `-log10` `log10` `log2` |
| `log_x`, `log_y` | 축을 로그 눈금으로 |
| `lines` | `{"x":[...],"y":[...]}` 점선 기준선 (변환 후 단위) |
| `label`, `hover` | 마우스오버 제목 열 (기본: 표 key), 추가로 보일 열 |
| `top`, `horizontal` | 값 막대의 개수 (기본 20), 가로 막대 (기본 true) |
| `bins` | histogram 구간 수 |
| `x_label`, `y_label`, `title_in_plot`, `height`, `dragmode`, `layout` | 표시 조정 (`layout` 은 plotly layout 에 병합) |

원시 plotly: `{"type":"chart","data":[...],"layout":{...}}` — 표와 연동되지 않는다.
점·값 막대 클릭 = 바구니 토글, 올가미/상자 선택 = 바구니에 추가.

### widget
조건(controls)을 바꾸면 `script` 를 다시 실행해 카드·그래프를 새로 그린다.

```json
{"type":"widget","id":"power","title":"검증 표본 수","table":"deg","script_file":"widgets/power.js",
 "controls":[
  {"id":"d","label":"효과 크기 d","type":"range","min":0.2,"max":3,"step":0.05,"value":1,"dp":2,"help":"평균 차 / SD"},
  {"id":"padj","label":"padj <","type":"range","min":1e-6,"max":0.1,"value":0.05,"log":true},
  {"id":"n","label":"군당 표본 수","type":"range","min":2,"max":50,"step":1,"value":6,"unit":"명"},
  {"id":"alpha","label":"α","type":"select","options":[0.05,0.01],"value":0.05},
  {"id":"show","label":"보조선 표시","type":"toggle","value":true}]}
```

| 키 | 설명 |
|---|---|
| `id` | 보고서 안에서 고유. 브라우저 저장 키 (`#` 링크는 아님) |
| `controls[].type` | `range` (기본) · `select` · `toggle` |
| range | `min` < `max` (필수), `value` (기본 min), `step` (기본: 범위/200), `log` (로그 눈금, min > 0), `dp`·`fmt`·`unit` (값 표시) |
| select | `options`: 값 목록 또는 `{v, l}`. `value` 기본은 첫 값. 값은 숫자·문자 그대로 ctx.v 에 들어감 |
| toggle | `value` true/false |
| `help` | 컨트롤 아래 작은 설명 |
| `script` / `script_file` | render(ctx) 함수의 **본문** (JS). 둘 중 하나 필수. `script` 는 문자열 또는 줄 목록 |
| `table` | `tables` 의 id. `ctx.rows` 로 받고, `ctx.result()` 로 바구니 버튼을 켤 수 있다 |

ctx 는 조건이 바뀔 때마다 새로 만들어진다 (requestAnimationFrame 으로 프레임당 1회):

| ctx | |
|---|---|
| `v` | `{control id: 현재 값}` (range 는 숫자, toggle 은 bool) |
| `rows` · `table(id)` | 행 배열 (spec 의 원본 값, 결측은 `null`) |
| `cards(items)` | `[{value,label,note,tone}]` 카드 줄 (tone: up/down/good/warn/acc/mut) |
| `plot(key, traces, layout)` | key 마다 그래프 하나. 이번 실행에서 부르지 않은 key 의 그래프는 지워진다. `layout` 은 테마 위에 병합, `height` 기본 340 |
| `note(html)` | 위젯 아래 설명 (HTML 그대로) |
| `el` | 직접 DOM/SVG 를 그릴 빈 영역 |
| `result(idxs)` | 표 행 index 배열 → "조건에 맞는 N행 담기" 버튼 |
| `summary(text)` | 결과 한 줄 → "조건 복사" 와 review Markdown `## 탐색 조건` |
| `color(name)` | 테마 토큰 값: `up` `dn` `ns` `acc` `mut` `ink` `line` `c1`–`c8` 등 |
| `fmt(x, {fmt,dp})` | 표와 같은 숫자 표기 |
| `state` · `first` | 실행 사이에 유지되는 객체 (캐시) · 첫 실행이면 true |

최소 스크립트:
```js
const k = ctx.v.fc, n = ctx.rows.filter(r => Math.abs(r.log2FC) >= k).length;
ctx.cards([{value: n, label: `|log2FC| ≥ ${k}`}]);
ctx.plot("hist", [{type: "histogram", x: ctx.rows.map(r => r.log2FC), marker: {color: ctx.color("acc")}}],
         {height: 260, shapes: [{type: "line", x0: k, x1: k, yref: "paper", y0: 0, y1: 1}]});
ctx.summary(`${n}개`);
```
스크립트는 인라인 `<script>` 함수로 들어가므로 eval 을 쓰지 않는다 (Artifact CSP 와 무관). 빌드 시 node 가 있으면 문법을 검사한다.
실행 오류는 위젯 안에 "위젯 오류: …" 로 표시된다.

### figure
```json
{"type":"figure","src":"fig/volcano.png","caption":"...","alt":"..."}
{"type":"figure","images":[{"src":"a.png","caption":"A"},{"src":"b.svg","caption":"B"}],"caption":"공통 설명","min_width":320}
```
파일은 base64 로 내장된다. 클릭하면 확대.

### review
```json
{"type":"review","id":"next-step","md_title":"다음 단계 입력","md_intro":"...","include_basket":true,
 "basket_cols":{"deg":["gene","log2FC","padj"]},
 "items":[
  {"id":"validate","title":"qPCR 검증 대상","desc":"md","md_desc":"Markdown 에 넣을 설명",
   "fields":[
    {"id":"how","label":"선정 방식","type":"choice","def":"top10","options":[
      {"v":"top10","l":"padj 상위 10개","d":"설명","r":"근거","rec":true},
      {"v":"pathway","l":"경로별 대표","warn":true}]},
    {"id":"extra","label":"추가 분석","type":"multi","options":["GSEA","decoupleR"]},
    {"id":"n","label":"최대 개수","type":"number","def":10},
    {"id":"note","label":"메모","type":"textarea","placeholder":"..."}]}]}
```
- `id` 는 보고서 안에서 고유. 브라우저 저장 키에 쓰인다 (보고서를 다시 빌드해도 선택이 유지된다).
- `fields` 를 생략하면 판정(진행/보류/제외) + 메모.
- 선택지는 객체 `{v,l,d,r,rec,warn}` 또는 문자열.
- 생성되는 Markdown: `# md_title` → 보고서·작성일 → 항목별 `## title` 과 `- **label**: 선택 — 설명 _(근거)_` → (선택 시) `## 관심 항목 (선택 바구니)` 표.
  바구니 표의 열은 `basket_cols[표id]` 또는 앞 8개 열.

### kv · glossary · details
```json
{"type":"kv","title":"파라미터","data":{"padj":"<0.05"}}
{"type":"kv","rows":[["설명","경로","부가"]],"code":true}
{"type":"glossary","items":[["padj","BH 보정 p"]]}
{"type":"details","summary":"부록: 전체 표","open":false,"blocks":[...]}
```
details 안의 그래프는 펼칠 때 그린다.

## environment (마지막 탭 자동 생성)

```json
"environment": {
  "software": {"R": "4.5.1", "DESeq2": "1.48.2"},
  "parameters": {"DEG 기준": "padj<0.05, |log2FC|≥1"},
  "data": [{"desc": "count matrix", "path": "/path/salmon.merged.gene_counts.tsv"}],
  "reproduce": "Rscript run.R config.yaml && python3 build_report.py spec.json",
  "notes": "md — 한계, 제외 표본, 배치 등"
}
```
`software` 는 `[{name, version, note}]` 또는 `[[name, version, note]]` 도 된다. `glossary` 는 최상위 또는 environment 안.
빌더가 "보고서 정보"(생성 시각, 도구 버전, spec 파일, 표·행 수)를 덧붙인다.

## 출력

| 명령 | 결과 |
|---|---|
| `build_report.py spec.json` | 로컬 전체판 `spec.html` (`-o` 로 경로 지정). 원본 전체, 크기 제한 없음 (150 MB 넘으면 경고) |
| `--artifact` | Artifact 축소판만 `spec_artifact.html` (`-o` 로 지정). 본문만 (Artifact 도구가 감쌈), 표는 `artifact` 기준 축소, `--max-mb` (기본 15) 이하 보장 |
| `--both` | 둘 다. 축소판 환경 탭에 로컬 전체판 절대경로가 들어감 |

- 게시할 때 `capabilities: {"downloads": true}`. Artifact 저장 허용 확장자에 `.tsv` 가 없어서 TSV 는 `.txt` (탭 구분) 로 저장된다.
- 축소된 표: 도구 막대 아래 안내, 행 수 옆 "(원본 N행 중)", 그 표를 쓰는 위젯에 경고, 환경 탭 "Artifact 판" 표.
- Plotly 는 cdnjs 2.35.3 을 chart·widget 이 있을 때만 불러온다. 표는 10만 행 이상도 된다 (200행씩 그림, 그래프는 4,000점 넘으면 WebGL).
