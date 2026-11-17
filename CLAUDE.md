# CLAUDE.md — omics-skills

개인 분석 모듈을 Claude Code 스킬로 만들어 배포하는 저장소. 사용자용 설명은 [README.md](README.md).

## 기록 (장기기억)
- 결정 → [docs/decisions/](docs/decisions/) (ADR-lite, 파일당 하나, README 색인 갱신)
- 진행 맥락 → [docs/contexts/](docs/contexts/) (날짜별). 이어서 작업할 때 최신 노트부터 읽는다.

## 규칙
- 스킬은 사용자가 파이프라인별로 지시할 때만 만든다 ([[decisions/0002]]).
- 원본 데이터·환자 정보·API 키는 저장소에 넣지 않는다. `inventory/` 는 로컬 전용(.gitignore).
- SKILL.md frontmatter 는 `name`, `description` 만 쓴다 (claude.ai 업로드 호환, [[decisions/0004]]).
- 스킬 번들 안에는 사용 시 필요한 것만 (SKILL.md, scripts, assets, references, examples). 개발용 검사는 `tests/`.
- 스크립트는 가능한 한 표준 라이브러리만. 외부 도구가 필요하면 SKILL.md 에 사전조건과 설치 명령을 적는다.
- 변경 후 `python3 tests/test_build_report.py` 와 `claude plugin validate .` 를 돌린다. 런타임(assets/report.html)을 바꿨으면 `tests/browser_check.mjs` 도.
- interactive-report 스킬 폴더를 고쳤으면 루트의 배포용 `interactive-report.zip` 을 다시 만들어 같은 커밋에 넣는다 (명령은 README, [[decisions/0009]]).
- 런타임은 10만 행 이상 표에서도 동작해야 한다: 행 배열에 spread·`apply` 금지 (call stack 초과). 큰 데이터 확인은 15만 행 합성 표로.
