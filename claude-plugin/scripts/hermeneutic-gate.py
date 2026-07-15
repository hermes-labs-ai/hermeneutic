#!/usr/bin/env python3
"""Legacy Hermeneutic Claude Code Stop hook retained for compatibility.

This transcript/stderr adapter is not a supported v0.1.7 integration against
the current Claude Code Stop contract. Prefer the standalone gate CLI or the
mechanically tested UserPromptSubmit compile hook.

Reads Claude Code Stop-hook stdin JSON, extracts the last assistant turn
from the transcript JSONL, pipes it through `hermeneutic gate`, writes a
one-line stderr notice if RISK fires. Always exits 0.
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
            env=_gate_env(),
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        print("[hermeneutic] gate unavailable — check the hook's Python install.", file=sys.stderr)
        return 0

    first_line = proc.stdout.strip().splitlines()[0] if proc.stdout.strip() else ""
    if first_line.startswith("RISK"):
        print(f"[hermeneutic] {first_line}", file=sys.stderr)
    elif proc.returncode != 0:
        print(
            "[hermeneutic] gate unavailable — install hermeneutic in the "
            f"hook interpreter ({sys.executable}).",
            file=sys.stderr,
        )

    return 0  # advisory only — never block


if __name__ == "__main__":
    raise SystemExit(main())
