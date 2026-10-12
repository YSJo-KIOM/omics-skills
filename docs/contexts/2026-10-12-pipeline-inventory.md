# 2026-10-12 파이프라인 인벤토리 + 배포 경로 조사

## 요청
"분석에 쓴 모듈들을 skill 화 → 개인 GitHub 업로드 / Claude Code cloud 세션 설치 / 로컬 설치".
사용자 지시로 **스킬화는 보류**, 먼저 PC 내 파이프라인 인벤토리 interactive web report 작성
([[decisions/0002]]). 저장소는 YSJo-KIOM/omics-skills 비공개 ([[decisions/0001]]).

## 산출물
- `inventory/pipelines.json` — 파이프라인별 경로·기능·진입점·모듈·의존성·스킬화 준비도 (단일 원본)
- `inventory/report.template.html` + 빌드 → `inventory/index.html` (Artifact 로도 게시)
- 재빌드: `python3 inventory/build.py` (parts/*.json 은 조사 에이전트 출력에서 `inventory/extract_part.py` 로 추출, 보안 점검·계보도는 `inventory/meta.json`)
- 게시: https://claude.ai/artifact/7AEjjKSZZwEsPtbbaF2RFk (비공개)

## 결과 요약 (56개)
- 상태: active 18 / legacy 31 / reference 5 / copy 2. 스킬화 준비도 high 8 / medium 23 / low 25.
- high: rnaseq-modular-pipeline, nfcore-input-prep-scripts, pcsf-network-analysis, chemical-disease-analysis,
  tgfb2-np-search, ggt-uk-ibs-ibd-risk-plot, lab-meeting-figures-agent, microarray-geo2r-limma.
- **보안 점검 11건** — 세부(위치·종류)는 로컬 전용 `inventory/meta.json` 과 인벤토리 보고서에만 둔다 (저장소에 올리지 않음).
  키 폐기 여부는 사용자 결정 대기 중.

## 배포 경로 조사 결과 (claude-code-guide, code.claude.com/docs 기준)
- **로컬 CLI**: GitHub 저장소를 plugin marketplace 로 구성
  (`.claude-plugin/marketplace.json` + `plugins/<p>/skills/<name>/SKILL.md`).
  `claude plugin marketplace add YSJo-KIOM/omics-skills` → `claude plugin install <p>@<mkt>`.
  private 저장소는 `gh auth setup-git` 으로 git 자격증명만 있으면 됨. 스킬 호출은 `/<plugin>:<skill>` 네임스페이스.
- **Cloud 세션 (claude.ai/code)**: `~/.claude/skills`·사용자 플러그인 **로드 안 됨**.
  저장소 `.claude/settings.json` 의 `enabledPlugins`/`extraKnownMarketplaces` 도 **설치 안 됨** (문서 명시).
  작동하는 경로는 둘:
  1. **claude.ai 계정에 스킬 업로드/활성화** → cloud 세션 + 로컬 터미널(`~/.claude/skills/synced/`) 양쪽에 동기화.
     단 업로드 시 frontmatter 는 `name, description, license, compatibility, metadata, allowed-tools` 만 허용 (그 외 키는 에러).
  2. 해당 프로젝트 저장소의 `.claude/skills/` 에 커밋 (저장소마다 복사본).
- 스킬 크기: SKILL.md 500줄 이하 권장, 세부는 별도 파일. 번들 스크립트는 `${CLAUDE_SKILL_DIR}/scripts/...` 로 참조.
  R 의존성 자동 설치 수단은 문서에 없음 → cloud 에서 DESeq2 등은 setup script 로 설치 필요(미검증).
- 미검증: setup script 로 `~/.claude/skills` 작성 시 cloud 로드 여부, claude.ai 업로드 시 scripts/ 폴더 포함 여부·크기 제한.

## 다음
- 사용자가 파이프라인을 하나씩 지정하면: 스킬 폴더 작성 → omics-skills 저장소 커밋/푸시 → 로컬 marketplace 설치 → claude.ai 업로드(사용자 수동 또는 가능 시 자동).
