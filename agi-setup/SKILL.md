---
name: agi-setup
description: |
  TSoft AGI 자동 회수를 Codex CLI (Windows) 환경에 1회 설치한다.
  실행 즉시 (운영자 paste 0): 유효 토큰 자동 발급/재사용 +
  %USERPROFILE%\.config\tsoft-agi\{tokens\<id>.token, agi-upload.py} 배치 +
  %USERPROFILE%\.codex\hooks.json 의 Stop/SessionStart hook 등록 +
  %USERPROFILE%\.codex\AGENTS.md 단순화 (v2.1 원칙) +
  첫 push 검증까지 끝낸다.
  사용자가 "AGI 설치", "AGI 연동", "TSoft AGI 설정", "새 PC에서 처음 사용",
  "agi-upload 설정" 을 요청하거나 ~/.config/tsoft-agi/tokens/ 가 빈 상태에서
  push 가 필요할 때 호출.
  이미 설치된 환경에서도 매번 template 최신본과 비교 후 다르면 자동 sync.
argument-hint: "[project-id]"
---

# AGI Setup — 한 번 설치하면 끝 (v2.1)

목표: 사용자 손 0. Codex hook 가 자동 회수 / 공급. AI 는 응답에 `<agi-digest>` 적기만.

## 0. 현재 상태 점검 (먼저 한 번, Windows)

검사 + 한 줄 보고 (✅ 있음 / ✗ 없음 / ⚠ 부분):
  1. `%USERPROFILE%\.config\tsoft-agi\tokens\<project_id>.token`
  2. `%USERPROFILE%\.config\tsoft-agi\agi-upload.py` (`--version` 으로 확인, 1.4.0 이상)
  3. `%USERPROFILE%\.codex\hooks.json` 의 Stop / SessionStart hook 등록
  4. `%USERPROFILE%\.codex\AGENTS.md` 의 "TSoft AGI 자동 회수" 섹션 (v2.1 형식)

- **1, 2, 3, 4 다 ✅** → 작업 4 (template 갱신 검사) 만 진입
- **하나라도 ✗** → 통상 설치 흐름

**핵심 원칙 (v2.1, 2026-05-23):** AI 는 AGI 에게 능동 행동 X.
오직 응답에 `<agi-digest>` 적기만. push / inject / 첨부 / Worker 매핑 — 시스템 hook 자동.

## 1. 토큰 확보 (자동)

운영자 paste 0 — AI 가 자동 발급.

### 1.A — 기존 활성 토큰 재사용 먼저
```
curl -fsS https://erp.t-soft.co.kr/api/projects/<project_id>/ingest-tokens
```
응답에서 `revoked_at` null + `scope=write|admin` 첫 entry 채택 → 1.C 로.

### 1.B — 없으면 자동 발급
```
curl -fsS -X POST https://erp.t-soft.co.kr/api/projects/<project_id>/ingest-tokens \
  -H "Content-Type: application/json" \
  -d '{"label": "agi-setup auto", "scope": "write"}'
```

### 1.C — 저장 (Windows)
- `%USERPROFILE%\.config\tsoft-agi\tokens\` 디렉토리 생성 (없으면)
- `%USERPROFILE%\.config\tsoft-agi\tokens\<project_id>.token` 에 token 평문 저장 (개행 없이, UTF-8 no BOM)
- 기존 다른 token 파일 있으면 `.bak.<yyyyMMdd_HHmmss>` 백업 후 교체

### 1.D — project_map.yaml 매핑
`%USERPROFILE%\.config\tsoft-agi\project_map.yaml`:
```yaml
projects:
  - match:
      cwd_prefix: "D:/project/work/<프로젝트 cwd>"
    project_id: "<project_id>"
    token_file: "~/.config/tsoft-agi/tokens/<project_id>.token"
```

(yaml 안의 `~` 는 Windows 에서도 `%USERPROFILE%` 로 자동 expand — agi-upload.py 가 처리)

### 안전 규칙
- 토큰 평문 응답/로그에 절대 X. 마스킹 (`abc12345…xyz789`) 만.
- 운영자가 직접 paste 한 토큰 있으면 그것 우선 (자동 발급 skip).

## 2. 업로더 설치 / 갱신 (자동, Windows PowerShell)

운영 환경은 **Windows 전용**. PowerShell 한 줄:

```powershell
irm https://erp.t-soft.co.kr/api/agi-upload/install-script?platform=powershell | iex
```

- 항상 latest + 자동 self-update 포함
- 이미 있는 PC 도 재실행 OK (idempotent)
- `%USERPROFILE%\.config\tsoft-agi\agi-upload.py` 에 설치

### 이미 있는 경우
```powershell
python "$env:USERPROFILE\.config\tsoft-agi\agi-upload.py" --version
```
- `1.4.0` 이상: OK (Stop hook 모드 지원, 자동 self-update 동작)
- 그 이전: 위 install 한 줄 재실행 → 1.4.0+ 진입

## 3. Codex Hooks 등록 (핵심, Windows)

`%USERPROFILE%\.codex\hooks.json` 작성 (없으면 새로). 이미 있으면 백업 후 hook 항목 merge:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.config/tsoft-agi/agi-upload.py --stop-hook",
            "timeout": 30
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python ~/.config/tsoft-agi/agi-upload.py --session-start",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

이 등록이 끝나면:
- 매 turn 종료 → Stop hook 가 transcript 자동 push (git/originator/Worker metadata 같이)
- 새 thread 시작 → SessionStart 가 Memory + pending instructions 자동 inject
- AI 는 응답에 `<agi-digest>` 적기만, 다른 명령 실행 X

## 4. AGENTS.md sync (단순, Windows)

template fetch:
```powershell
$tmpl = "$env:TEMP\agi-template.md"
irm https://raw.githubusercontent.com/ghostkkk/tsoft-agi/main/memory/agents.md.template -OutFile $tmpl
```

대상 = `%USERPROFILE%\.codex\AGENTS.md` (Codex 글로벌)

분기:
- **파일 없음** → 새로 생성 + `/tmp/agi-template.md` 본문 그대로.
- **파일 있음 + "TSoft AGI 자동 회수" 섹션 없음** → 끝에 template 본문 append.
- **파일 있음 + "TSoft AGI 자동 회수" 섹션 있음**:
  - template 의 "## TSoft AGI 자동 회수" 섹션과 본문 비교 (whitespace normalize).
  - 같음 → skip.
  - 다름 → 대상 파일 `<file>.bak.<yyyyMMdd_HHmmss>` 백업 + 해당 섹션만 template 으로 교체.
- **옛 "TSoft AGI Push Policy" 섹션 있으면 제거** (v2.1 에선 사용 안 함 — AI 능동 명령 안내였음).

**원칙**: 사용자가 손댄 다른 섹션은 보존. AGI 섹션만 갱신.

## 5. 검증 (Stop hook 자동 동작 확인)

설치 직후 검증:
- 새 Codex thread 한 번 시작
- 사용자가 짧은 메시지 ("test agi setup") 보냄
- AI 는 응답 끝에 `<agi-digest>\nSUMMARY: agi-setup 검증\n</agi-digest>` 적음
- turn 종료 → Stop hook 자동 실행 → 서버에 commit 생성
- `https://erp.t-soft.co.kr/projects/<project_id>` 에서 새 commit 확인

또는 강제 1 회 push (디버그용 — 운영자 명령, PowerShell):
```powershell
'{"session_id":"setup-test","transcript_path":"<rollout path>","cwd":"<cwd>"}' | `
  python "$env:USERPROFILE\.config\tsoft-agi\agi-upload.py" --stop-hook
```

## 6. 응답 형식

각 단계 한 줄 보고. 끝에:
```
✅ 설치 완료
  · 토큰: abc123…xyz (마스킹)
  · 업로더: agi-upload.py v1.4.x
  · Hooks: Stop ✓ SessionStart ✓
  · AGENTS.md: 갱신/유지
```

이 setup 작업 자체는 push 안 함 (AI 능동 호출 X — Hook 가 next turn 부터 자동).
