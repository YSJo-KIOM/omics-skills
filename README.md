# omics-skills

ysjo 의 오믹스 분석 모듈을 Claude Code 스킬로 묶은 개인 저장소 (private).
저장소 자체가 Claude Code **plugin marketplace** 다.

| 스킬 | 호출 | 하는 일 |
|---|---|---|
| [interactive-report](plugins/omics-skills/skills/interactive-report/SKILL.md) | `/omics-skills:interactive-report` 또는 "인터랙티브 보고서 만들어줘" | 분석 결과·문헌을 탭·필터 표·선택 바구니(TSV)·검토(Markdown)·연동 그래프·**파라미터 위젯**(슬라이더 → 재계산·재시각화)이 있는 단일 HTML 로 |

## 설치

### 로컬 Claude Code (이 PC 또는 다른 PC)

```bash
gh auth login && gh auth setup-git          # private 저장소 clone 권한 (PC 마다 한 번)
claude plugin marketplace add YSJo-KIOM/omics-skills
claude plugin install omics-skills@omics-skills
# 갱신
claude plugin marketplace update omics-skills && claude plugin update omics-skills@omics-skills
```

### Claude Code cloud 세션 (claude.ai/code)

cloud 세션은 개인 플러그인과 `~/.claude/skills` 를 불러오지 않는다. 두 가지 중 하나:

1. **claude.ai 계정에 스킬 업로드** (권장) — cloud 세션과 로컬 터미널(`~/.claude/skills/synced/`) 양쪽에 동기화된다.
   ```bash
   mkdir -p dist && (cd plugins/omics-skills/skills && zip -r ../../../dist/interactive-report.zip interactive-report -x '*/__pycache__/*')
   ```
   claude.ai → 설정 → Capabilities(기능) → Skills 에서 zip 업로드 후 켜기.
   업로드 시 frontmatter 는 `name`, `description` (그 밖에 license, compatibility, metadata, allowed-tools) 만 허용된다.
2. 작업할 프로젝트 저장소의 `.claude/skills/` 에 스킬 폴더를 복사해 커밋.

claude.ai 업로드와 로컬 플러그인을 둘 다 켜면 로컬에 같은 스킬이 두 개(`interactive-report`, `omics-skills:interactive-report`) 보인다.
그럴 땐 로컬 플러그인을 끈다: `claude plugin disable omics-skills@omics-skills`.

## 개발

```
.claude-plugin/marketplace.json
plugins/omics-skills/.claude-plugin/plugin.json      # version 생략: 커밋마다 새 버전으로 인식
plugins/omics-skills/skills/<스킬>/SKILL.md (+ scripts/ assets/ references/ examples/)
tests/                                              # 스킬 번들에 들어가지 않는 개발용 검사
docs/decisions/  docs/contexts/                     # 결정·맥락 기록
```

검사:

```bash
python3 tests/test_build_report.py                  # 빌더
claude plugin validate .                             # 매니페스트
# 런타임(브라우저) — google-chrome, Node ≥ 22
S=interactive-report; O=$(mktemp -d)
python3 plugins/omics-skills/skills/$S/scripts/build_report.py plugins/omics-skills/skills/$S/examples/analysis/spec.json -o $O/analysis.html
node tests/browser_check.mjs "file://$O/analysis.html#deg" analysis
```

새 스킬을 넣을 때: 원본 데이터·환자 정보·키를 넣지 않는다. 예시는 합성 데이터나 공개 데이터로. 하드코딩 경로는 인자·설정으로 뺀다.
