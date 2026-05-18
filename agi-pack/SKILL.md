---
name: agi-pack
description: |
  현재 프로젝트의 AGI Project Memory snapshot + 9-field 규칙을 가져와, 새 AI 대화의 첫 메시지로 prepend할 통합본을 만든다.
  사용자가 "Reminder Pack", "Memory 가져와", "다른 도구로 컨텍스트 이관", "새 ChatGPT 대화 시작 키트", "pack 가져와", "프로젝트 컨텍스트 줘"를 요청하거나 새 AI 세션·도구 전환 직전에 호출한다.
  결과는 사용자가 그대로 복사해 다른 AI 채팅창 첫 메시지로 붙여넣을 수 있는 markdown 텍스트.
argument-hint: "[project-id] [target-tool]"
---

# AGI Pack — Memory snapshot 가져오기

목표: AGI 서버에서 현재 Memory + agi-digest 규칙이 합쳐진 한 덩어리를 받아서
사용자에게 통째로 복사 가능한 형태로 제시.

## 0. 인자 정리
- `project-id`: 없으면 현재 cwd → `~/.config/tsoft-agi/project_map.yaml` 로 추론, 그래도 없으면 사용자에게 묻기.
- `target-tool`: 옵션. `claude | chatgpt | claude_code | claude_web | codex | cursor | gemini | perplexity | universal`. 없으면 `universal`.

## 1. AGI 서버에서 pack fetch
```
curl -sL "https://erp.t-soft.co.kr/api/projects/<project-id>/reminder-pack?target_tool=<target>&purpose=continue" \
  -H "Content-Type: application/json"
```
응답 JSON 의 `content` 필드 = 사용자에게 보여줄 markdown.

## 2. 사용자에게 출력
다음 형식으로 응답:
```
📦 Reminder Pack — <project-name> · target=<target>
(약 <approx_tokens> tokens, snapshot @ <memory_snapshot_at>)

─── 아래를 통째로 복사해서 새 AI 채팅 첫 메시지로 ───
<content>
────────────────────────────────────────────────────
```

## 3. 보너스 — 사용자가 "이거 바로 보낼래"라고 하면
사용자가 어느 도구로 이관할지 명시했고 그 도구가 같은 PC에서 호출 가능하면
(예: 다른 Codex/Claude Code 세션 시작) 도구 실행 명령까지 안내.

## 4. 응답 마지막 한 줄
```
ERP: skipped read-only-fetch
```
(pack 가져오기 자체는 새 commit 만들 정보 아님. 단순 조회.)

## 주의
- pack 본문에 토큰 / 비밀이 들어있을 가능성은 거의 없지만,
  본문 출력 전 secret 정규식 (`sk-`, `ghp_`, `AGI_TOKEN=`) 매치 시
  해당 라인 마스킹 + 사용자에게 경고.
