# 0004. 배포 경로: 로컬은 plugin marketplace, cloud 는 claude.ai 업로드
- 날짜: 2026-10-12
- 상태: 채택

## 결정
- 저장소(YSJo-KIOM/omics-skills)를 Claude Code plugin marketplace 로 구성. 플러그인 하나(`omics-skills`)에 스킬을 모은다.
  `plugin.json` 에 version 을 두지 않아 커밋마다 새 버전으로 인식시킨다.
- 로컬: `claude plugin marketplace add YSJo-KIOM/omics-skills` → `claude plugin install omics-skills@omics-skills` (user scope).
- cloud 세션: 스킬 폴더 zip 을 claude.ai 계정에 업로드 (cloud 세션은 개인 플러그인·repo 의 enabledPlugins 를 설치하지 않음 — 문서 확인).
- frontmatter 는 `name`, `description` 만 (claude.ai 업로드는 그 밖의 키를 거부).

## 이유
claude-code-guide 조사 결과 ([[contexts/2026-10-12-pipeline-inventory]] 참고). claude.ai 업로드는 API 가 없어 사용자가 직접 한다.

## 관련
[[decisions/0001]], [[decisions/0003]]
