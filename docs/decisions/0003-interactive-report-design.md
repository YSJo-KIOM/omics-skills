# 0003. interactive-report 스킬 설계
- 날짜: 2026-10-12
- 상태: 채택

## 결정
- 첫 스킬은 분석 데이터가 없는 범용 도구인 **interactive-report** (사용자 지시: "위험부담 없이 가장 중요한 스킬").
- 구조: spec(JSON/YAML) → `build_report.py`(Python 표준 라이브러리만) → **단일 HTML**. 런타임은 데이터(JSON)를 받아 JS 로 그린다 (COPD Atlas 방식).
- 요구사항 대응
  1. 테마별 탭 (질문 하나 = 탭 하나, 블록 많으면 경고)
  2. 첫 탭 요약(빌더가 경고), 마지막 탭 분석 환경·기타(environment 로 자동 생성)
  3. 열 타입 추론 → cat dropdown / num dual slider + 식(`>=`, `abs>=`) / text 검색, 정렬, 200행 페이지
  4. 선택 바구니 → TSV 복사·저장, review 블록(EPICv2 명세 작성기 방식) → Markdown 복사·저장
  5. Plotly 그래프가 표 필터를 따라 다시 그려짐, 점 클릭·올가미 → 바구니
  6. 분석·문헌·스크리닝·계획 검토 예시
- 시각 토큰은 EK-7 / COPD Atlas / TGFB2 보고서 계열을 그대로 잇는다 (보고서 간 일관성).
- Plotly 는 그래프가 있을 때만 cdnjs 2.35.3 을 불러온다. Artifact 에서는 `downloads` capability 로 저장(.tsv 는 허용 목록에 없어 .txt).

## 이유
- R htmlwidgets/Quarto 는 R·pandoc 의존이 커서 cloud 세션·다른 PC 에서 바로 못 쓴다. 표준 라이브러리 Python 은 어디서나 돈다.
- R 파이프라인은 TSV 와 spec JSON 만 쓰면 되므로 언어와 무관하게 붙는다.
- 검증: 빌더 assert 검사 + 헤드리스 크롬 CDP 로 필터·정렬·바구니·Markdown·그래프 연동 24항목 통과.

## 관련
[[decisions/0004]], [[contexts/2026-10-12-interactive-report-skill]]
