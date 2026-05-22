---
name: agi-setup
description: |
  TSoft AGI 자동 회수를 이 환경에 1회 설치한다.
  토큰 입력만 받으면 ~/.config/tsoft-agi/{token, agi-upload.py} + AGENTS.md / CLAUDE.md 자동 구성 + 첫 push 검증까지 끝낸다.
  사용자가 "AGI 설치", "AGI 연동", "TSoft AGI 설정", "새 PC에서 처음 사용", "agi-upload 설정"을 요청하거나 ~/.config/tsoft-agi/token 이 없는 상태에서 push가 필요할 때 호출한다.
  이미 설치된 환경에서도 매번 template 최신본과 비교 후 다르면 자동 sync — 룰 변경 반영 보장.
argument-hint: "[project-id]"
---

# AGI Setup — 한 번 설치하면 끝

목표: 사용자 손은 토큰 paste 1회만. 나머지 4단계는 모두 AI 자동.

## 0. 현재 상태 점검 (먼저 한 번)
- 다음 4개를 검사하고 각 항목을 한 줄로 보고: ✅ 있음 / ✗ 없음 / ⚠ 부분
  1. `~/.config/tsoft-agi/token`
  2. `~/.config/tsoft-agi/agi-upload.py`
  3. `~/.codex/AGENTS.md` (Codex/Cursor 환경) 또는 `~/.claude/CLAUDE.md` (Claude Code)
  4. 본문 안에 "TSoft AGI Push Policy" 섹션 존재 여부

- 분기:
  - **1, 2 중 ✗** 있으면 → 통상 설치 흐름 (작업 1, 2 진행)
  - **그 외** (1, 2 다 ✅) → 작업 3 항상 진입 (template 최신본과 비교, 다르면 갱신)

**핵심 원칙 (2026-05-19 갱신):** 사용자가 `/agi-setup` 을 명시적으로 호출했다는 것 자체가
"최신 룰을 받겠다" 는 의도. "이미 설치돼 있으니 skip" 으로 빠지지 말 것.
다만 사용자가 손댄 다른 섹션은 항상 보존 — 작업 3 의 섹션 단위 비교 + 백업 + 교체 절차로.

## 1. 토큰 저장 (사용자 입력 필요한 유일한 단계)
- 사용자에게 안내:
  ```
  1) https://erp.t-soft.co.kr/projects/<project-id>/integrations 열기
     (project-id 인자 받았으면 그대로 사용. 없으면 사용자에게 묻기.)
  2) 상단 🔑 Ingest 토큰 패널에서 [+ 새 토큰 발급] → 평문 복사
  3) 여기 채팅에 paste 해주세요
  ```
- 사용자가 paste한 토큰을 받으면:
  - `~/.config/tsoft-agi/` 디렉토리 없으면 생성
  - `~/.config/tsoft-agi/token` 에 줄바꿈/공백 없이 저장 (이미 있으면 `token.bak` 으로 백업 후 교체)
  - **토큰 평문은 응답에 다시 출력하지 말 것**. 마스킹 형태(`abc12345…xyz789`)로만 확인 메시지.

## 2. 업로더 설치 / 갱신 (자동, 항상 진입)

우선순위 (위에서 아래로 시도, 첫 성공에서 stop):

- **(a) AGI 서버 endpoint (권장 — 항상 latest + 자동 self-update 코드 포함, sha 검증):**
  - 한 줄 install (가장 간단):
    - Windows PowerShell:
      `irm https://erp.t-soft.co.kr/api/agi-upload/install-script?platform=powershell | iex`
    - Linux / Mac bash:
      `curl -fsS https://erp.t-soft.co.kr/api/agi-upload/install-script?platform=bash | bash`
  - 또는 raw source endpoint (수동 sha 검증 시):
    `curl -fsS https://erp.t-soft.co.kr/api/agi-upload/source -o ~/.config/tsoft-agi/agi-upload.py`
    응답 헤더의 `X-Source-Sha256` 와 `sha256(file)` 비교 (불일치 시 rollback).

- **(b) skill 패키지에 동봉된 사본 (offline fallback):**
  `cp <plugin-root>/files/agi-upload.py ~/.config/tsoft-agi/agi-upload.py`
  ⚠ 옛 사본 (`__version__` 없거나 1.2 이하) 가능 — 설치 직후 `python ~/.config/tsoft-agi/agi-upload.py --self-update` 1회 호출해서 latest 진입 권장.

- **(c) GitHub raw fallback:**
  `curl -fsS https://raw.githubusercontent.com/ghostkkk/tsoft-agi/main/files/agi-upload.py -o ~/.config/tsoft-agi/agi-upload.py`
  ⚠ 옛 사본 가능 — 위와 동일 `--self-update` 권장.

### 이미 있는 경우 (idempotent)
```
python ~/.config/tsoft-agi/agi-upload.py --version
```
- `1.3.0` 이상: 다음 ingest 호출 시 자동 self-update 동작. **추가 작업 X.**
- `1.0 ~ 1.2.x`: 한 번 `python ~/.config/tsoft-agi/agi-upload.py --self-update` 실행 또는 (a) one-liner 재실행 → 즉시 latest.
- 그 외 (version 없음): 옛 사본 — `--self-update` 또는 (a) 재실행 필수.

## 3. AGENTS.md / CLAUDE.md 정책 sync (자동, 항상 진입)
- 환경에 따라 대상 파일 결정:
  - Codex / Cursor → `~/.codex/AGENTS.md`
  - Claude Code  → `~/.claude/CLAUDE.md` (+ 프로젝트 루트에 `./.claude/CLAUDE.md` 가 있으면 프로젝트 컨텍스트만 추가)

- **항상 template 최신본 fetch** (옛/새/없음 구분 없이):
  ```
  curl -sL https://raw.githubusercontent.com/ghostkkk/tsoft-agi/main/memory/agents.md.template -o /tmp/agi-template.md
  ```

- **분기 (대상 파일 상태 + template 비교)**:

  **① 대상 파일 없음 (첫 설치)**:
    - 새로 생성 후 `/tmp/agi-template.md` 본문 그대로 저장.
    - 한 줄 보고: "✅ 첫 설치 완료. 파일 = `<file>`"

  **② 대상 파일 있음, 본문에 "TSoft AGI Push Policy" 없음 (옛 첫 설치 형식)**:
    - 대상 파일 끝에 `/tmp/agi-template.md` 본문을 append.
    - 한 줄 보고: "✅ Push Policy 추가."

  **③ 대상 파일 있음, "TSoft AGI Push Policy" 있음**:
    - template 본문에서 다음 섹션들을 추출:
      - `## TSoft AGI 자동 회수 — ...`
      - `## TSoft AGI Push Policy ...`
      - `## Skill 호출 가이드`
    - 대상 파일의 해당 섹션들과 본문 비교 (whitespace normalize 후):
      - **모두 동일** → skip. 한 줄 보고: "✓ 이미 최신 룰 (변경 없음)."
      - **하나라도 다름** → 대상 파일을 `<file>.bak.<YYYYMMDD_HHMMSS>` 로 백업 + 해당 섹션들만
        template 본문으로 교체 (사용자 손댄 다른 섹션은 보존).
        한 줄 보고: "✅ 룰 갱신 완료. 백업 = `<bak path>` · 변경된 섹션: <목록>"

- **핵심 원칙**: 사용자가 `/agi-setup` 명시 호출 = "최신 받겠다" 의도.
  "이미 설치돼 있으니 skip" 으로 빠지지 말고 항상 template 과 비교, 다르면 갱신.
  단, 절대 통째 덮어쓰지 말 것 — 백업 + 섹션 단위 교체로 사용자 손댄 부분 보존.

### 변경 이력 (참고)
- 2026-05-19: Write 도구 → `~/.claude/agi_hook/last-digest.txt` 파일 저장 방식
- 2026-05-19: RAW 13 sub-header 표준화
- 2026-05-19: phase 별 commit 그룹화 + PreToolUse hook 알림
- 2026-05-19: `/agi-setup` 매번 호출 시 sync 보장 (이 문서)

## 4. 검증 push (자동)
- 다음 셸 명령 실행:
  ```
  printf '%s\n' '<agi-digest>' \
    'SUMMARY: agi-setup 설치 검증' \
    'TASKS:' '- 첫 push 동작 확인' \
    '</agi-digest>' \
  | python ~/.config/tsoft-agi/agi-upload.py --source-tool <현재-agent> --quiet
  ```
- 출력에 `✓ ingested commit=<id> type=<type>` 이 보이면 성공.
- 사용자에게 한 줄 요약: `✅ 설치 완료 / 토큰 마스킹 / 첫 push commit=<id>`
- 실패하면 stderr 본문 그대로 보고 + 가능한 원인 (잘못된 토큰 / 네트워크 / 서버 다운) 안내.

## 5. 응답 형식
모든 step 결과를 한 줄씩 요약 후 마지막에:
```
ERP: pushed commit=<id>
```

push 자체에 비밀이 들어있을 수 있으므로 이 setup 작업 자체는 push 안 해도 됨:
```
ERP: skipped setup-self
```
