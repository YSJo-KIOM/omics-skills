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

## 배포 상태
- GitHub: YSJo-KIOM/omics-skills (private) push 완료. `gh auth setup-git` 으로 git 자격증명 연결.
- 로컬: `claude plugin marketplace add YSJo-KIOM/omics-skills` + `claude plugin install omics-skills@omics-skills` (user scope) 완료.
  호출 `/omics-skills:interactive-report`. 상시 비용 ~260 tok, 호출 시 ~4.2k tok.
- cloud: `dist/interactive-report.zip` 생성 (gitignore). **사용자가 claude.ai 설정 → Skills 에 업로드해야 함** (API 없음).
  업로드 후 로컬에도 synced 사본이 생기므로 중복이면 로컬 플러그인 disable.
- 시연 Artifact: https://claude.ai/artifact/MFiGc896mom26EdH13FxA7 (capabilities: downloads)

## 다음
- 사용자: zip 업로드, 시연 보고서에서 TSV 저장·Markdown 저장 동작 확인 (Artifact downloads 는 세션에서 시험 불가).
- 다음 스킬화 대상 지시 대기. 인벤토리 high 후보: RNA-seq 모듈형 파이프라인, nf-core 입력 준비, PCSF, Chemical–disease, TGFB2 탐색.
- 보안 점검 항목의 키 폐기·정리 여부 사용자 결정 대기 (로컬 inventory 참조).
