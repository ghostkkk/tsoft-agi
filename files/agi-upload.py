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


def read_text(file_path: str | None) -> str:
    if file_path:
        return _decode_best(Path(file_path).read_bytes())
    if sys.stdin.isatty():
        sys.exit("ERROR: --file 미지정 + stdin이 비어 있습니다.")
    return _decode_best(sys.stdin.buffer.read())


def main() -> None:
    ap = argparse.ArgumentParser(description="TSoft AGI ingest 업로더")
    ap.add_argument("--source-tool", default="codex",
                    help="codex | cursor | chatgpt | claude_web | other  (기본: codex)")
    ap.add_argument("--file", help="이 파일에서 입력 텍스트 읽기. 생략 시 stdin")
    ap.add_argument("--token", help="토큰 직접 지정 (env/파일보다 우선)")
    ap.add_argument("--url", default=os.environ.get("AGI_INGEST_URL", DEFAULT_URL),
                    help=f"ingest URL (기본 {DEFAULT_URL})")
    ap.add_argument("--quiet", action="store_true", help="성공 시 요약만 출력")
    args = ap.parse_args()

    text = read_text(args.file)
    if "<agi-digest>" not in text:
        sys.exit("ERROR: 입력 텍스트에 <agi-digest> 블록이 없습니다.")

    payload = {
        "format": "agi-digest-text-v1",
        "token": find_token(args.token),
        "source_tool": args.source_tool,
        "digest_text": text,
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
    if args.quiet:
        print(f"✓ ingested commit={res['commit_id']} type={res['commit_type']}")
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
