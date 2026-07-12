"""Smoke tests for the shipped plugin gate scripts (Claude Code + Codex)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CLAUDE_SCRIPT = REPO / "claude-plugin" / "scripts" / "hermeneutic-gate.py"
CODEX_SCRIPT = REPO / "codex-plugin" / "scripts" / "codex-gate.py"


def _run(script: Path, stdin: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script)], input=stdin,
        capture_output=True, text=True, timeout=15, cwd=REPO,
    )


def test_claude_script_flags_overclaim_and_never_blocks(tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text(
        '{"type":"assistant","message":{"content":[{"type":"text","text":"Done — shipped 14 files, all tests pass."}]}}\n',
        encoding="utf-8",
    )
    p = _run(CLAUDE_SCRIPT, json.dumps({"transcript_path": str(transcript)}))
    assert p.returncode == 0
    assert "[hermeneutic] RISK" in p.stderr


def test_claude_script_silent_on_garbage_and_missing_transcript():
    assert _run(CLAUDE_SCRIPT, "not json").returncode == 0
    p = _run(CLAUDE_SCRIPT, json.dumps({"transcript_path": "/nonexistent/x.jsonl"}))
    assert p.returncode == 0 and p.stderr == ""


def test_codex_script_emits_valid_json_and_no_decision_field():
    p = _run(CODEX_SCRIPT, json.dumps({"last_assistant_message": "Done — shipped 14 files, all tests pass."}))
    assert p.returncode == 0
    out = json.loads(p.stdout)
    assert "decision" not in out          # advisory: decision=block would auto-continue
    assert "systemMessage" in out and "RISK" in out["systemMessage"]


def test_codex_script_clean_text_and_garbage_both_yield_empty_json():
    p = _run(CODEX_SCRIPT, json.dumps({"last_assistant_message": "Here are three options with tradeoffs."}))
    assert p.returncode == 0 and json.loads(p.stdout) == {}
    p = _run(CODEX_SCRIPT, "not json")
    assert p.returncode == 0 and json.loads(p.stdout) == {}
