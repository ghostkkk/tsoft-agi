# tsoft-agi — Agent Skills for AI-Driven Development Memory

[TSoft AGI](https://erp.t-soft.co.kr/) 는 외부 AI 도구(Claude Code, Codex, Cursor, ChatGPT 등)의 대화를 **회수 → 큐레이션 → 공급**하는 Project Memory Harness 플랫폼이다. 이 저장소는 그 통합을 한 줄로 만드는 Agent Skills + AGENTS.md template 묶음.

## 한 줄 설치 (예정)

```bash
# Codex 전역 설치
npx skills@latest add ghostkkk/tsoft-agi --agent codex --global --yes

# Claude Code 전역 설치
npx skills@latest add ghostkkk/tsoft-agi --agent claude-code --global --yes
```

> 현재는 marketplace publish 전이라 로컬에서 직접 cp 또는 git submodule로 가져가서 쓴다. 자세히는 [수동 설치](#수동-설치).

## Skills

| Skill | 호출 | 설명 |
| --- | --- | --- |
| `agi-setup` | `/agi-setup` | 환경 1회 설치 — 토큰 저장 + 업로더 설치 + AGENTS.md merge + 첫 push 검증 |
| `agi-charter` | `/agi-charter` | 새 프로젝트 초기 정체성 문서(목표/범위/원칙/결정)를 9-field로 작성 후 push — 빈 Memory 초기화 |
| `agi-pack` | `/agi-pack` | 현재 Memory snapshot + 9-field 규칙을 가져와 다른 AI 도구로 이관할 통합본 생성 |
| `agi-review` | `/agi-review` | candidate commits 목록을 가져와 표로 보여주고 일괄/개별 merge |

## 항상 적용되는 정책 (Memory)

`memory/agents.md.template` — `~/.codex/AGENTS.md` (Codex/Cursor) 또는 `~/.claude/CLAUDE.md` (Claude Code) 에 merge되는 always-on 정책.

- 9-field `<agi-digest>` 블록 매 turn 끝 첨부
- Push Policy 강화 — 의지 의존 ❌ / 4단계 체크리스트 ✅
- 응답 맨 마지막 한 줄 자체 점검 라인: `ERP: pushed commit=<id>` / `skipped <reason>` / `failed <reason>`
- Secret 정규식 가드 — `sk-*` / `ghp_*` / `AGI_TOKEN=` 매치 시 push 자동 skip

## 수동 설치 (marketplace 전)

```bash
# 1. 이 repo 클론 또는 sparse-checkout
git clone https://github.com/ghostkkk/tsoft-agi.git ~/.local/share/tsoft-agi-skills

# 2. Skill 파일 복사
mkdir -p ~/.codex/skills ~/.claude/skills
cp -r ~/.local/share/tsoft-agi-skills/agi-* ~/.codex/skills/
cp -r ~/.local/share/tsoft-agi-skills/agi-* ~/.claude/skills/

# 3. AGENTS.md / CLAUDE.md 정책 merge (Skill `/agi-setup` 가 자동 처리)

# 4. AI 채팅창에서:
/agi-setup
```

## 관련 자산

- **agi-upload.py** — `~/.config/tsoft-agi/agi-upload.py` 로 설치되는 업로더 (Python stdlib only, cross-platform). 토큰을 `~/.config/tsoft-agi/token` 에서 자동 조회.
- **`/api/ingest`** — `https://erp.t-soft.co.kr/api/ingest` 9-field digest 표준 endpoint.

## 라이선스

MIT
