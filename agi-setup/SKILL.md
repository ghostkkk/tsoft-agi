---
name: agi-setup
description: |
  TSoft AGI 자동 회수를 Codex CLI (Windows) 환경에 1회 설치.
  agi-upload.py 가 token / AGENTS.md / hooks.json / project_map 다 자동 처리.
  "AGI 설치/연동/설정" 호출 시.
argument-hint: "<project-id>"
---

# AGI Setup (v2.2, Windows-only)

`<project-id>` 인자 받고 **단일 명령** 실행:

```powershell
python "$env:USERPROFILE\.config\tsoft-agi\agi-upload.py" --setup <project-id>
```

이 한 명령이 5단계 자체 처리:
1. token 자동 발급 / 재사용
2. `tokens/<id>.token` 저장
3. `project_map.yaml` 의 현재 cwd → project_id 매핑
4. `~/.codex/AGENTS.md` template sync (옛 Push Policy 자동 제거)
5. `~/.codex/hooks.json` 의 Stop / SessionStart hook 등록

## Prerequisite

`agi-upload.py` 미설치 시 즉시 STOP + 안내:
```
❌ PowerShell 먼저 실행:
   irm https://erp.t-soft.co.kr/api/agi-upload/install-script?platform=powershell | iex
```

## 응답

명령 출력 그대로 사용자에게 표시. 추가 작업 X.

**금지** — `ERP: pushed ...` / `ERP: skipped ...` 같은 자체 점검 라인 출력 X (옛 v1 잔재).
응답 끝에 `<agi-digest>` 블록만 (또는 setup 같이 짧은 작업이면 그것도 생략).
실제 push 여부는 Stop hook 가 자동 — AI 가 신경 X.

이후 AI 는 응답 끝에 `<agi-digest>` 만 적기 — 나머지 시스템 hook 자동.
