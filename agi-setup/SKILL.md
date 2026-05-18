---
name: agi-setup
description: |
  TSoft AGI 자동 회수를 이 환경에 1회 설치한다.
  토큰 입력만 받으면 ~/.config/tsoft-agi/{token, agi-upload.py} + AGENTS.md / CLAUDE.md 자동 구성 + 첫 push 검증까지 끝낸다.
  사용자가 "AGI 설치", "AGI 연동", "TSoft AGI 설정", "새 PC에서 처음 사용", "agi-upload 설정"을 요청하거나 ~/.config/tsoft-agi/token 이 없는 상태에서 push가 필요할 때 호출한다.
  이미 설치 끝난 환경에서는 ERP: skipped already-installed 로 빠진다.
argument-hint: "[project-id]"
---

# AGI Setup — 한 번 설치하면 끝

목표: 사용자 손은 토큰 paste 1회만. 나머지 4단계는 모두 AI 자동.

## 0. 현재 상태 점검 (먼저 한 번)
- 다음 5개를 검사하고 각 항목을 한 줄로 보고: ✅ 있음 / ✗ 없음 / ⚠ 부분
  1. `~/.config/tsoft-agi/token`
  2. `~/.config/tsoft-agi/agi-upload.py`
  3. `~/.codex/AGENTS.md` (Codex/Cursor 환경) 또는 `~/.claude/CLAUDE.md` (Claude Code)
  4. 본문 안에 "TSoft AGI Push Policy" 섹션 존재 여부
  5. **본문 안에 새 룰 마커 (`last-digest.txt` 또는 `Write 도구로`) 존재 여부** — 없으면 옛 룰 (2026-05 이전)
- 분기:
  - 1~4 다 ✅ + 5도 ✅ → **완전 새 룰 적용 상태**. 사용자에게 "설치 완료 상태. 검증만 진행할까요?" 묻고 작업 4로 점프.
  - 1~4 다 ✅ + 5는 ✗ → **옛 룰 박혀있음**. 작업 3 의 마이그레이션 절차로 강제 진입 (skip 금지).
  - 1~4 중 ✗ 있으면 → 통상 설치 흐름 (작업 1부터).

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

## 2. 업로더 설치 (자동)
- `~/.config/tsoft-agi/agi-upload.py` 가 없으면 다음 중 한 가지로 가져옴:
  - **(a) skill 패키지에 동봉된 사본 사용** (권장):
    `cp <plugin-root>/files/agi-upload.py ~/.config/tsoft-agi/agi-upload.py`
  - **(b) GitHub raw 다운로드**:
    `curl -sL https://raw.githubusercontent.com/ghostkkk/tsoft-agi/main/files/agi-upload.py -o ~/.config/tsoft-agi/agi-upload.py`
  - **(c) AGI 서버에서 fetch** (서버가 정적 파일로 노출 시):
    `curl -sL https://erp.t-soft.co.kr/static/agi-upload.py -o ~/.config/tsoft-agi/agi-upload.py`
- 파일 이미 있으면 skip.

## 3. AGENTS.md / CLAUDE.md 정책 merge (자동)
- 환경에 따라 대상 파일 결정:
  - Codex / Cursor → `~/.codex/AGENTS.md`
  - Claude Code  → `~/.claude/CLAUDE.md` (+ 프로젝트 루트에 `./.claude/CLAUDE.md` 가 있으면 프로젝트 컨텍스트만 추가)
- template 가져오기 (이 plugin 의 `memory/agents.md.template` 본문):
  ```
  curl -sL https://raw.githubusercontent.com/ghostkkk/tsoft-agi/main/memory/agents.md.template -o /tmp/agi-template.md
  ```
- **분기 — 작업 0 의 검사 5 (새 룰 마커) 결과 기준**:

  **① 검사 5 = ✗ (옛 룰 박혀있음, 마이그레이션 필요)**:
    1. 대상 파일을 `<file>.bak.<YYYYMMDD_HHMMSS>` 로 백업
    2. 옛 § "TSoft AGI Auto Capture" / "TSoft AGI 자동 회수" / "TSoft AGI Push Policy" / "Secret Guard" 등
       template 와 겹치는 섹션을 본문에서 **삭제**
    3. 그 자리에 `/tmp/agi-template.md` 본문을 insert (이미 fetch 한 새 template)
    4. 사용자가 손댄 다른 섹션 (예: "Response Rules") 은 보존
    5. 한 줄 보고: "✅ 옛 룰 → 새 룰 마이그레이션 완료. 백업 = `<bak path>`"

  **② 검사 4 = ✗ (Push Policy 자체 없음, 첫 설치)**:
    - 대상 파일 끝에 `/tmp/agi-template.md` 본문을 append.

  **③ 검사 4 = ✅ + 검사 5 = ✅ (이미 새 룰)**:
    - skip. "이미 새 룰 적용 상태" 한 줄 보고.

- 절대 통째 덮어쓰지 말 것 — 항상 백업 + 섹션 단위 교체.

### 핵심 변경 (2026-05): Write 도구 → 파일 방식
이전 룰 ("응답 본문 마지막에 `<agi-digest>` 텍스트 첨부") 는 폐기.
새 룰: Write 도구로 `~/.claude/agi_hook/last-digest.txt` 에 저장 → transcript 안 `tool_use.input.file_text` 로 서버 fast-path 가 추출.
사용자 채팅창에 큰 blob 노출되지 않음.

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
