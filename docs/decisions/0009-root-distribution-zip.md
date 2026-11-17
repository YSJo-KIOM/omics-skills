# 0009. 배포용 zip 을 저장소 루트에 커밋한다
- 날짜: 2026-11-17
- 상태: 채택

## 결정
- interactive-report 의 claude.ai 업로드용 zip 을 저장소 루트의 `interactive-report.zip` 으로 커밋한다 (전에는 `.gitignore` 된 `dist/` 에 그때그때 만들었다).
- zip 안은 `interactive-report/SKILL.md …` 구조이고 `__pycache__` 는 뺀다. 만드는 명령은 README 에 있다.
- 스킬 폴더를 고치면 zip 을 다시 만들어 같은 커밋에 넣는다. `tests/test_build_report.py` 가 zip 과 스킬 폴더의 내용이 같은지 검사한다.

## 이유
- 사용자 지시 (2026-11-17): "github root 에 배포용 zip 파일도 같이 들어가도록 해줘."
- GitHub 에서 zip 하나만 받아 claude.ai 에 올릴 수 있다 (clone 과 zip 명령이 필요 없다).
- 빌드 산출물을 커밋하면 낡을 수 있으므로 검사를 붙였다.

## 관련
[[decisions/0004]], [[contexts/2026-10-12-interactive-report-skill]]
