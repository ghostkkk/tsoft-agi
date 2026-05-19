#!/usr/bin/env python3
"""TSoft AGI 표준 업로더 — Codex / Cursor / 기타 AI 도구가 매 turn 끝에 호출.

이 스크립트는 ~/.config/tsoft-agi/agi-upload.py 로 설치되어 운영자/AI가 사용한다.

사용법:
  # 파일에서 읽기 (권장 — escape 문제 없음)
  python ~/.config/tsoft-agi/agi-upload.py --file ./last_turn.txt --source-tool codex

  # 표준입력 파이프
  cat last_turn.txt | python ~/.config/tsoft-agi/agi-upload.py --source-tool cursor

입력 텍스트 안에 <agi-digest>...</agi-digest> 블록 1개가 있어야 한다.
서버는 그 블록을 파싱해 Digest + Commit 후보를 생성한다 (LLM 비용 0).

토큰 조회 순서:
  1. --token CLI 인자
  2. AGI_TOKEN 환경변수
  3. ~/.config/tsoft-agi/token  파일 (한 줄, 평문)

엔드포인트:
  --url CLI 인자 또는 AGI_INGEST_URL 환경변수 또는 기본 https://erp.t-soft.co.kr/api/ingest
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DEFAULT_URL = "https://erp.t-soft.co.kr/api/ingest"
TOKEN_FILE = Path.home() / ".config" / "tsoft-agi" / "token"


# Windows cp949 등에서 utf-8 출력 강제 (Python 3.7+)
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass


def find_token(cli_token: str | None) -> str:
    if cli_token:
        return cli_token.strip()
    env = os.environ.get("AGI_TOKEN")
    if env:
        return env.strip()
    if TOKEN_FILE.exists():
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    sys.exit(
        f"ERROR: 토큰을 찾을 수 없습니다.\n"
        f"다음 중 하나로 설정하세요:\n"
        f"  1) --token <value>\n"
        f"  2) export AGI_TOKEN=<value>\n"
        f"  3) {TOKEN_FILE} 파일에 한 줄 평문으로 저장"
    )


def _decode_best(raw: bytes) -> str:
    """UTF-8 우선, 실패 시 Windows 한글 (cp949) fallback, 그래도 안 되면 utf-8 replace.

    Codex / PowerShell 등에서 cp949 로 저장한 임시 파일도 한글 깨지지 않게.
    """
    # BOM 처리
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        # UTF-16 BOM
        try:
            return raw.decode("utf-16")
        except UnicodeDecodeError:
            pass
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _warn_powershell_stdin(text: str) -> None:
    """Windows + stdin pipe 입력 시 한글 깨짐 의심 detect → stderr 경고.

    PowerShell native pipe 가 UTF-8 보장 안 해서 한글이 `?` 로 깨지는 케이스.
    의심 지표: '?' 비율 > 5% 또는 '???' 같은 연속 ? 패턴.
    """
    if sys.platform != "win32":
        return
    if not text:
        return
    q_count = text.count("?")
    triple_q = "???" in text
    if triple_q or (len(text) > 50 and q_count / len(text) > 0.05):
        print(
            "⚠ Windows stdin pipe — '?' 비율 이상 / 한글 깨짐 의심.\n"
            "   PowerShell 은 stdin pipe 가 UTF-8 보장 안 함. --file 옵션 사용 권장:\n"
            "     $tmp = \"$env:TEMP\\agi-digest.txt\"\n"
            "     [System.IO.File]::WriteAllText($tmp, $digest, (New-Object System.Text.UTF8Encoding($false)))\n"
            "     python agi-upload.py --file $tmp ...",
            file=sys.stderr,
        )


def read_text(file_path: str | None) -> str:
    if file_path:
        return _decode_best(Path(file_path).read_bytes())
    if sys.stdin.isatty():
        sys.exit("ERROR: --file 미지정 + stdin이 비어 있습니다.")
    text = _decode_best(sys.stdin.buffer.read())
    _warn_powershell_stdin(text)
    return text


PHASE_STATE_FILE = Path.home() / ".config" / "tsoft-agi" / "phase-state.json"


def _load_phase_state() -> dict:
    if not PHASE_STATE_FILE.exists():
        return {}
    try:
        return json.loads(PHASE_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_phase_state(state: dict) -> None:
    try:
        PHASE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        PHASE_STATE_FILE.write_text(json.dumps(state), encoding="utf-8")
    except Exception as e:
        print(f"[agi-upload] phase-state save failed: {e}", file=sys.stderr)


def _new_phase_group() -> str:
    """ULID-스타일 — 26자 base32. 외부 패키지 없이 구현."""
    import time, secrets, string
    enc = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32
    ts = int(time.time() * 1000)
    # 48-bit timestamp (10 chars) + 80-bit random (16 chars)
    ts_part = ""
    for _ in range(10):
        ts_part = enc[ts & 0x1F] + ts_part
        ts = ts >> 5
    rand_part = "".join(enc[secrets.randbelow(32)] for _ in range(16))
    return ts_part + rand_part


def resolve_phase(args) -> dict:
    """args + 환경변수 + state 파일 기준으로 phase 정보 결정.

    반환: {"phase_group": ..., "phase_seq": ..., "phase_kind": ...} 또는 빈 dict.
    """
    if not (args.phase or args.phase_group):
        return {}

    state = _load_phase_state()
    cur = state.get("current") or {}

    # phase_group 결정 — CLI 인자 > 환경변수 > state.current > 새로 생성
    group = (
        args.phase_group
        or os.environ.get("AGI_PHASE_GROUP")
        or cur.get("phase_group")
    )
    if not group:
        group = _new_phase_group()

    # 자동 seq 증가 (state 의 last_seq + 1)
    last_seq = cur.get("last_seq", 0) if cur.get("phase_group") == group else 0
    seq = args.phase_seq if args.phase_seq is not None else (last_seq + 1)

    kind = args.phase_kind or "phase"

    # state 갱신
    state["current"] = {"phase_group": group, "last_seq": seq, "phase_kind": kind}
    _save_phase_state(state)

    return {"phase_group": group, "phase_seq": seq, "phase_kind": kind}


def main() -> None:
    ap = argparse.ArgumentParser(description="TSoft AGI ingest 업로더")
    ap.add_argument("--source-tool", default="codex",
                    help="codex | cursor | chatgpt | claude_web | other  (기본: codex)")
    ap.add_argument("--file", help="이 파일에서 입력 텍스트 읽기. 생략 시 stdin")
    ap.add_argument("--token", help="토큰 직접 지정 (env/파일보다 우선)")
    ap.add_argument("--url", default=os.environ.get("AGI_INGEST_URL", DEFAULT_URL),
                    help=f"ingest URL (기본 {DEFAULT_URL})")
    ap.add_argument("--quiet", action="store_true", help="성공 시 요약만 출력")
    # 큰 turn 의 phase 별 commit 그룹화 (2026-05-19)
    ap.add_argument("--phase", action="store_true",
                    help="이 push 를 phase commit 으로 표시 — 자동으로 group ID 발급/재사용")
    ap.add_argument("--phase-group", help="phase 그룹 ID 명시 (생략 시 자동)")
    ap.add_argument("--phase-seq", type=int, help="phase 순서 (생략 시 자동 증가)")
    ap.add_argument("--phase-kind", choices=["phase", "final"], help="기본 phase. 마지막은 final")
    ap.add_argument("--phase-reset", action="store_true",
                    help="phase state 초기화 (새 turn 시작 — 다음 push 가 새 group 만듦)")
    args = ap.parse_args()

    if args.phase_reset:
        try:
            if PHASE_STATE_FILE.exists():
                PHASE_STATE_FILE.unlink()
            if not args.quiet:
                print("✓ phase state reset")
        except Exception as e:
            print(f"phase reset failed: {e}", file=sys.stderr)
        if not (args.phase or args.phase_group):
            return

    text = read_text(args.file)
    if "<agi-digest>" not in text:
        sys.exit("ERROR: 입력 텍스트에 <agi-digest> 블록이 없습니다.")

    phase = resolve_phase(args)

    payload = {
        "format": "agi-digest-text-v1",
        "token": find_token(args.token),
        "source_tool": args.source_tool,
        "digest_text": text,
        **phase,   # phase_group / phase_seq / phase_kind (있을 때만)
    }

    req = urllib.request.Request(
        args.url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")[:300]
        sys.exit(f"ERROR: HTTP {e.code} — {body}")
    except urllib.error.URLError as e:
        sys.exit(f"ERROR: 네트워크 — {e.reason}")

    stats = res.get("stats", {})
    phase_tag = ""
    if phase:
        phase_tag = f" [phase {phase['phase_seq']} group={phase['phase_group'][:8]}…]"
    if args.quiet:
        print(f"✓ ingested commit={res['commit_id']} type={res['commit_type']}{phase_tag}")
    else:
        print(f"✓ ingested → {args.url}")
        print(f"  raw_id      : {res['raw_id']}")
        print(f"  digest_id   : {res['digest_id']}")
        print(f"  commit_id   : {res['commit_id']}  ({res['commit_type']})")
        print(f"  stats       : decisions={stats.get('decisions',0)} "
              f"tasks={stats.get('tasks',0)} risks={stats.get('risks',0)} "
              f"deprecated={stats.get('deprecated',0)} "
              f"artifacts={stats.get('artifacts',0)} next_context={stats.get('next_context',0)}")


if __name__ == "__main__":
    main()
