---
name: agi-setup
description: |
  TSoft AGI 자동 회수를 Codex CLI (Windows) 환경에 1회 설치.
  토큰 자동 발급/재사용 + AGENTS.md sync + hooks.json 등록 + 첫 push 검증.
  "AGI 설치/연동/설정" 또는 처음 사용 시 호출.
argument-hint: "<project-id>"
---

# AGI Setup (v2.1, Windows-only, Codex 전용)

**핵심 원칙**: AI 는 응답 끝에 `<agi-digest>` 만 적기. push/inject/첨부 모두 Codex hook 자동.

## 0. Prerequisite (STOP gate)

`%USERPROFILE%\.config\tsoft-agi\agi-upload.py` 존재 확인 (`Test-Path`).
**없으면 즉시 STOP** + 안내:
```
❌ agi-upload.py 누락 — PowerShell 한 줄 먼저 실행:
   irm https://erp.t-soft.co.kr/api/agi-upload/install-script?platform=powershell | iex
```

## 1. 토큰 (자동)

`<project-id>` 의 활성 토큰 list → 첫 활성 사용. 없으면 새로 발급:
- `GET  /api/projects/<id>/ingest-tokens` (활성 = `revoked_at`/`expires_at` null, scope=write|admin)
- `POST /api/projects/<id>/ingest-tokens` body `{"label":"agi-setup","scope":"write"}` (없을 때만)

`%USERPROFILE%\.config\tsoft-agi\tokens\<id>.token` 에 평문 저장 (UTF-8 no BOM, 줄바꿈 X).
응답/로그엔 마스킹만 (`abc123…xyz`).

## 2. project_map.yaml

`%USERPROFILE%\.config\tsoft-agi\project_map.yaml` 의 `projects:` list 에 entry 추가 (같은 cwd 있으면 skip):
```yaml
- match:
    cwd_prefix: "<현재 cwd 절대 경로>"
  project_id: "<id>"
  token_file: "~/.config/tsoft-agi/tokens/<id>.token"
```

## 3. hooks.json

`%USERPROFILE%\.codex\hooks.json` 에 Stop + SessionStart hook 등록 (기존 있으면 백업 후 merge):
```json
{
  "hooks": {
    "Stop":         [{"matcher":"","hooks":[{"type":"command","command":"python ~/.config/tsoft-agi/agi-upload.py --stop-hook","timeout":30}]}],
    "SessionStart": [{"matcher":"","hooks":[{"type":"command","command":"python ~/.config/tsoft-agi/agi-upload.py --session-start","timeout":15}]}]
  }
}
```

## 4. AGENTS.md sync

`irm https://raw.githubusercontent.com/ghostkkk/tsoft-agi/main/memory/agents.md.template -OutFile $env:TEMP\agi-template.md`

대상 `%USERPROFILE%\.codex\AGENTS.md`:
- 없음 → 새로 생성, template 본문 그대로
- "TSoft AGI 자동 회수" 섹션 없음 → 끝에 append
- 있음 + 본문 다름 → 백업 (`.bak.<yyyyMMdd_HHmmss>`) + 해당 섹션만 교체 (다른 섹션 보존)
- 옛 "TSoft AGI Push Policy" 섹션 있으면 제거 (v2.1 에선 불필요)

## 5. 응답

각 단계 한 줄 보고 + 마지막에:
```
✅ 설치 완료
  토큰: abc123…xyz
  업로더: v1.4.x
  Hooks: Stop ✓ SessionStart ✓
  AGENTS.md: ✓ / 갱신
  cwd 매핑: <cwd> → <id>

이후 AI 는 응답 끝에 <agi-digest> 만 적기. 그게 전부.
```

검증 push 는 안 함 — 다음 turn 의 Stop hook 가 자연스러운 검증.
