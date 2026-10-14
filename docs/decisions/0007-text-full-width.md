# 0007. 보고서 본문 글은 전체 폭
- 날짜: 2026-10-14
- 상태: 채택

## 결정
interactive-report 템플릿에서 글 너비 제한을 없앤다: `.prose p/li/blockquote{max-width:72ch}`, `.blk>.intro{max-width:90ch}`,
`table.kv{max-width:1100px}`. 글도 표·그림과 같은 콘텐츠 폭(main, 최대 1500px)을 쓴다. v0.3.1.

## 이유
사용자 피드백 (2026-10-13, EK-7 신경·염증 대응 보고서 v2): "텍스트 너비가 고정값이라 가독성이 떨어진다. 다른 요소처럼 전체 너비를 쓰게."
일반적인 한 줄 65자 원칙보다 이 선호가 우선. 그 프로젝트는 spec 에 `<style>` html 블록(WIDE_CSS)으로 우회하고 있었다 — 이제 불필요(남아 있어도 무해).
근거 노트: `~/.claude/projects/-ys-data1-Analysis-RNA-seq-unreplicated/memory/report-text-full-width.md`

## 관련
[[decisions/0003]]
