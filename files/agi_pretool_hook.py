#!/usr/bin/env python3
"""Claude Code / Codex CLI PreToolUse hook → 누적 변경성 tool 카운트 + phase push 알림.

매 변경성 tool 호출 (Edit / Write / Bash / NotebookEdit / MultiEdit / Update) 시:
  - state 파일에 session_id 별 카운트 누적
  - threshold (기본 5) 마다 stderr 로 "⏱ 누적 N tools — phase push 고려" 한 줄
  - AI 가 그 신호 보고 적절한 시점에 `agi-upload.py --phase` 호출

이 스크립트는 항상 빠르게 (수십 ms) 끝나야 하므로 네트워크 X, 동기화 X.
실패는 silent — hook 이 절대 tool 실행을 막지 않음.

state 파일: ~/.claude/agi_hook/tool-count.json
  {
    "<session_id>": {
      "count":         12,        # 누적 변경성 tool 수
      "last_warn_at":  10,        # 마지막 알림 시 count
      "started_at":    "ISO-8601" # session 첫 발화
    }
  }

session 이 바뀌면 자동 reset. 1주일 이상된 session 항목은 정리.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path


STATE_DIR  = Path(os.environ.get("AGI_HOOK_STATE_DIR", str(Path.home() / ".claude" / "agi_hook")))
STATE_FILE = STATE_DIR / "tool-count.json"

THRESHOLD = int(os.environ.get("AGI_PRETOOL_THRESHOLD", "5"))   # 매 N 변경성 tool 마다 알림

# 변경성/실행 tool 만 카운트. Read/Grep/Glob/WebSearch/WebFetch/TaskCreate/TaskUpdate 같은 조회는 무시.
MUTATING_TOOLS = {
    "Edit", "Write", "Bash", "PowerShell", "NotebookEdit", "MultiEdit", "Update",
    # MCP 변경성 tool 들도 같이 — generic prefix 매치는 따로
}

# MCP 도구 prefix — write/edit/exec/run/patch 같은 동사가 들어있으면 변경성으로 간주 (best-effort)
MUTATING_HINTS = ("write", "edit", "exec", "run", "patch", "set_", "create", "delete", "remove", "update")


def _is_mutating(tool_name: str) -> bool:
    if tool_name in MUTATING_TOOLS:
        return True
    low = tool_name.lower()
    return any(h in low for h in MUTATING_HINTS)


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    except Exception:
        pass


def _gc(state: dict) -> dict:
    """1주일 이상된 session 항목 정리."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    keep = {}
    for sid, info in state.items():
        try:
            started = datetime.fromisoformat(info["started_at"])
            if started >= cutoff:
                keep[sid] = info
        except Exception:
            keep[sid] = info   # parse 실패 시 보존
    return keep


def main() -> int:
    if os.environ.get("AGI_HOOK_DISABLED") == "1":
        return 0

    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        payload = json.loads(raw)
    except Exception:
        return 0

    session_id = payload.get("session_id") or "unknown"
    tool_name  = payload.get("tool_name") or ""

    if not _is_mutating(tool_name):
        return 0

    state = _load_state()
    info = state.get(session_id) or {
        "count": 0,
        "last_warn_at": 0,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    info["count"] = int(info.get("count", 0)) + 1

    if info["count"] - int(info.get("last_warn_at", 0)) >= THRESHOLD:
        info["last_warn_at"] = info["count"]
        print(
            f"⏱ AGI: 누적 {info['count']} 변경성 tools — phase push 고려.\n"
            f"   `python ~/.config/tsoft-agi/agi-upload.py --file <tmp> --phase --source-tool <agent> --quiet`",
            file=sys.stderr,
        )

    state[session_id] = info
    state = _gc(state)
    _save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
