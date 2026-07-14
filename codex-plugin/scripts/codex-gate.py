#!/usr/bin/env python3
"""hermeneutic Codex Stop-hook — advisory mode.

Codex Stop hooks must print valid JSON on exit 0. Advisory-only means NEVER
emitting a "decision" field (on Codex Stop, "decision": "block" means
auto-continue with the reason as a new prompt — not a block).
"""
import json
import os
import subprocess
import sys
from pathlib import Path


def _gate_env() -> dict[str, str]:
    """Use an adjacent source checkout when this script is plugin-packaged."""
    env = os.environ.copy()
    try:
        source = Path(__file__).resolve().parents[2] / "src"
    except IndexError:
        return env
    if source.is_dir():
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(source) + (os.pathsep + existing if existing else "")
    return env


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
            env=_gate_env(),
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        print(json.dumps({"systemMessage": "[hermeneutic] gate unavailable — check the hook's Python install."}))
        return 0

    first_line = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
    if first_line.startswith("RISK"):
        print(json.dumps({"systemMessage": f"[hermeneutic] {first_line}"}))
    elif proc.returncode != 0:
        print(json.dumps({
            "systemMessage": (
                "[hermeneutic] gate unavailable — install hermeneutic in the "
                f"hook interpreter ({sys.executable})."
            )
        }))
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
