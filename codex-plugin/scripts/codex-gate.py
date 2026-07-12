#!/usr/bin/env python3
"""hermeneutic Codex Stop-hook — advisory mode.

Codex Stop hooks must print valid JSON on exit 0. Advisory-only means NEVER
emitting a "decision" field (on Codex Stop, "decision": "block" means
auto-continue with the reason as a new prompt — not a block).
"""
import json
import subprocess
import sys


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("{}")
        return 0

    last_text = payload.get("last_assistant_message") or ""
    if not last_text.strip():
        print("{}")
        return 0

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "hermeneutic.cli", "gate"],
            input=last_text, capture_output=True, text=True, timeout=5,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        print("{}")
        return 0

    if proc.returncode != 0 and proc.stdout.strip():
        print(json.dumps({"systemMessage": f"[hermeneutic] {proc.stdout.splitlines()[0]}"}))
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
