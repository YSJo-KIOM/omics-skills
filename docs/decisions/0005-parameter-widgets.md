# 0005. 파라미터 위젯 (조건 변경 → 재계산 → 시각화)
- 날짜: 2026-10-12
- 상태: 채택

## 결정
interactive-report 에 `widget` 블록을 넣는다. 슬라이더·선택·토글(controls) 값이 바뀔 때마다 spec 의 `script`(render(ctx) 본문, JS)를
다시 실행해 카드·Plotly 그래프·설명을 새로 그린다. 선언형 위젯 종류를 늘리지 않고 **스크립트 + 얇은 ctx API** 하나로 간다.
- ctx: v, rows/table, cards, plot(key,…), note, el, result(→ 바구니 버튼), summary(→ 조건 복사·review Markdown), color, fmt, state.
- 스크립트는 인라인 `<script>` 함수로 넣는다 (eval 없음). 빌드 시 node 로 문법 검사.
- 조건은 브라우저에 저장, review Markdown 에 `## 탐색 조건` 으로 들어간다 (다음 단계 입력 장치와 연결).

## 이유
사용자가 claude.ai 채팅의 visualize 위젯(GBDT 원리: 트리 수·학습률·깊이 슬라이더 → 적합 곡선·잔차가 실시간 변화)을 원함.
기준 탐색·민감도·시뮬레이션·원리 설명은 계산이 매번 달라서 선언형으로 일반화하기 어렵고, Claude 가 짧은 JS 를 쓰는 편이 유연하다.
공유 링크에서는 위젯이 숨겨지고 회사 네트워크에서 visualize 연결이 안 되어 원본은 직접 보지 못했다 — 답변 본문에서 구조를 확인.

## 관련
[[decisions/0003]], [[contexts/2026-10-12-interactive-report-skill]]
