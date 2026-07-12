#!/usr/bin/env python3
"""hermeneutic Stop-hook — advisory mode (never blocks).

Reads Claude Code Stop-hook stdin JSON, extracts the last assistant turn
from the transcript JSONL, pipes it through `hermeneutic gate`, writes a
one-line stderr notice if RISK fires. Always exits 0.
"""
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    transcript = payload.get("transcript_path", "")
    if not transcript or not Path(transcript).is_file():
        return 0

    last_text = ""
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for line in reversed(f.readlines()):
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if d.get("type") != "assistant":
                    continue
                msg = d.get("content") or d.get("message") or {}
                content = msg.get("content", "") if isinstance(msg, dict) else ""
                if isinstance(content, list):
                    parts = [b.get("text", "") for b in content
                             if isinstance(b, dict) and b.get("type") == "text"]
                    last_text = "\n".join(p for p in parts if p)
                elif isinstance(content, str):
                    last_text = content
                if last_text.strip():
                    break
    except OSError:
        return 0

    if not last_text.strip():
        return 0

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "hermeneutic.cli", "gate"],
            input=last_text, capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return 0

    if proc.returncode != 0 and proc.stdout.strip():
        print(f"[hermeneutic] {proc.stdout.splitlines()[0]}", file=sys.stderr)

    return 0  # advisory only — never block


if __name__ == "__main__":
    raise SystemExit(main())
