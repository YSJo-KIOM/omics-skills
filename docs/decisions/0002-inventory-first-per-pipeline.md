# 0002. 인벤토리 먼저, 스킬화는 파이프라인별 개별 지시로
- 날짜: 2026-10-12
- 상태: 채택

## 결정
일괄 스킬화하지 않는다. 먼저 PC 내 파이프라인 인벤토리(interactive web report)를 만들고,
사용자가 파이프라인마다 개별로 스킬화를 지시하면 그때 진행한다.
배포 대상: GitHub 업로드 → Claude Code cloud 세션 → 로컬 Claude Code.

## 이유
사용자 지시 ("아직 시작하지는 마. 내가 개별 파이프라인마다 명령을 내릴게").

## 관련
[[decisions/0001]], [[contexts/2026-10-12-pipeline-inventory]]
