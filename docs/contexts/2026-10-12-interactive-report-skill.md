# 2026-10-12 첫 스킬: interactive-report

## 요청
"위험부담 없이 가장 중요한 스킬" = interactive web report 만들기. 예시: TGFB2_NP_search 보고서들, EK-7 Pilot vs Main,
COPD–근감소 Biomarker Atlas, EPICv2 명세 작성기 (아티팩트). 요구 6가지 → [[decisions/0003]].

## 만든 것
- `plugins/omics-skills/skills/interactive-report/`
  - `SKILL.md` — 작업 순서, 탭 규칙, 블록·열·그래프 요약, 용도별 시작점, 지킬 것
  - `scripts/build_report.py` — spec → 단일 HTML (stdlib). `--artifact` 는 본문만
  - `assets/report.html` — CSS·JS 런타임 템플릿 (탭, 표 필터, 바구니, review, plotly 연동, 확대 보기, 다운로드)
  - `references/spec.md` — 전체 스키마
  - `examples/analysis` (합성 DEG 400·enrichment 30), `examples/literature` (DESeq2·edgeR·limma·GSEA·clusterProfiler 논문 5편)
- `tests/test_build_report.py` (빌더), `tests/browser_check.mjs` (헤드리스 크롬 CDP: 필터·정렬·바구니·Markdown·그래프 연동 24항목)

## 검증
- 빌더 검사 ok, 브라우저 검사 전 항목 PASS, JS 오류 0, 라이트·다크 스크린샷 확인.
- 고친 버그: standalone 에서 `[hidden]` 이 display:flex 에 덮임 / 가로 막대 안 라벨 중복 / 닫힌 details 안 그래프 선그리기 / DOI 의 `/` 인코딩 / 연도 쉼표.

## 추가: 파라미터 위젯 (v0.2, [[decisions/0005]])
- `widget` 블록 + ctx API, 예시 위젯 2개: `examples/analysis/widgets/deg_threshold.js` (기준 탐색, 데이터 연동),
  `power.js` (검증 표본 수 시뮬레이션). analysis 예시에 "기준 탐색" 탭 추가.
- 검증: 브라우저 검사 33항목 PASS (위젯 9항목 포함), 빌더 검사에 위젯 검증·문법 오류 탐지 추가. 400px 모바일 가로 넘침 없음.
- 사용자가 좋아한 claude.ai visualize 위젯(GBDT 원리)을 `examples/explainer` 로 재현: 트리 수 M·η·깊이 → 적합 곡선·잔차+다음 트리·학습/검증 MSE.
  사용자가 붙여 준 위젯 소스는 50,000자 제한에서 잘려 호스트 스타일(폰트·CDS 토큰·SVG/폼 기본 스타일)만 들어옴 — 본체 코드는 미확인.
  설명 문구는 실제 계산으로 검증해 고침: 깊이 1 은 η=1 이어도 과적합이 느림, 깊이 3·η=1 은 m=2 에서 검증 최저 후 상승.
- 표가 없는 보고서는 선택 바구니를 숨김.

## 추가: 로컬 전체판 / Artifact 축소판 (v0.3, [[decisions/0006]])
- `--both` → `spec.html` (원본 전체) + `spec_artifact.html` (상위 결과 ≤15 MB). `tables.<id>.artifact` 로 기준 지정, 없으면 자동 축소.
- 15만 행 합성 표: 로컬 22 MB 1.5초 렌더, 필터·WebGL 산점도 정상 / 축소판 15 MB 로 자동 축소 (102,557행, padj 상위라 유의 행 모두 보존).
- 버그 수정: 10만+ 행에서 슬라이더 범위 계산 `Math.min.apply` call stack 초과 → 루프로. 회귀 검사 추가.
- 검사: 빌더 ok, 브라우저 44 PASS (analysis 28 · literature 5 · explainer 6 · trimmed 5).
- 사용자가 claude.ai 에 zip 을 올려 `anthropic-skills:interactive-report` 로 동기화됨 (v0.2). v0.3 zip 재업로드 필요.

## 배포 상태
- GitHub: YSJo-KIOM/omics-skills (private) push 완료. `gh auth setup-git` 으로 git 자격증명 연결.
- 로컬: `claude plugin marketplace add YSJo-KIOM/omics-skills` + `claude plugin install omics-skills@omics-skills` (user scope) 완료.
  호출 `/omics-skills:interactive-report`. 상시 비용 ~260 tok, 호출 시 ~4.2k tok.
- cloud: `dist/interactive-report.zip` 생성 (gitignore). **사용자가 claude.ai 설정 → Skills 에 업로드해야 함** (API 없음).
  업로드 후 로컬에도 synced 사본이 생기므로 중복이면 로컬 플러그인 disable.
- 시연 Artifact: https://claude.ai/artifact/MFiGc896mom26EdH13FxA7 (capabilities: downloads)
- GBDT 위젯 시연 Artifact: https://claude.ai/artifact/1x7R3EEdqoy9bm7qHYW7ES (표·review 없음 → downloads 미선언, 저장 경로 미사용)

## 다음
- 사용자: zip 업로드, 시연 보고서에서 TSV 저장·Markdown 저장 동작 확인 (Artifact downloads 는 세션에서 시험 불가).
- 다음 스킬화 대상 지시 대기. 인벤토리 high 후보: RNA-seq 모듈형 파이프라인, nf-core 입력 준비, PCSF, Chemical–disease, TGFB2 탐색.
- 보안 점검 항목의 키 폐기·정리 여부 사용자 결정 대기 (로컬 inventory 참조).

## 2026-10-14: 본문 전체 폭 (v0.3.1, [[decisions/0007]])
- 템플릿의 72ch·90ch·1100px 제한 제거. 브라우저 검사에 폭 확인 1항목 추가 (전체 45 PASS).
