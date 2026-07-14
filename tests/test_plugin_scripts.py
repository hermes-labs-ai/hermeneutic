"""Smoke tests for the shipped plugin gate scripts (Claude Code + Codex)."""
from __future__ import annotations

import io
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


def test_plugin_scripts_surface_low_severity_advisories(tmp_path):
    draft = "This is a robust, production-ready result."
    transcript = tmp_path / "low.jsonl"
    transcript.write_text(
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": draft}]}}) + "\n",
        encoding="utf-8",
    )
    claude = _run(CLAUDE_SCRIPT, json.dumps({"transcript_path": str(transcript)}))
    assert claude.returncode == 0 and "RISK" in claude.stderr and "low" in claude.stderr

    codex = _run(CODEX_SCRIPT, json.dumps({"last_assistant_message": draft}))
    out = json.loads(codex.stdout)
    assert codex.returncode == 0 and "decision" not in out
    assert "RISK" in out["systemMessage"] and "low" in out["systemMessage"]


def test_codex_script_clean_text_and_garbage_both_yield_empty_json():
    p = _run(CODEX_SCRIPT, json.dumps({"last_assistant_message": "Here are three options with tradeoffs."}))
    assert p.returncode == 0 and json.loads(p.stdout) == {}
    p = _run(CODEX_SCRIPT, "not json")
    assert p.returncode == 0 and json.loads(p.stdout) == {}


def test_codex_script_surfaces_missing_gate_dependency(monkeypatch, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("codex_gate_hook", CODEX_SCRIPT)
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    monkeypatch.setattr(
        hook.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="ModuleNotFoundError"),
    )
    monkeypatch.setattr(
        hook.sys,
        "stdin",
        io.StringIO(json.dumps({"last_assistant_message": "Done — shipped everything."})),
    )
    assert hook.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert "decision" not in out
    assert "unavailable" in out["systemMessage"]


def test_codex_plugin_manifest_shape():
    """Pin the manifest to the schema the Codex plugin validator accepts:
    no top-level `hooks` key, and a complete `interface` object."""
    import json
    from pathlib import Path

    manifest = json.loads(
        (Path(__file__).resolve().parent.parent
         / "codex-plugin" / ".codex-plugin" / "plugin.json").read_text()
    )
    assert "hooks" not in manifest, "validator rejects a top-level hooks field"
    interface = manifest.get("interface")
    assert isinstance(interface, dict)
    for field in ("displayName", "shortDescription", "longDescription",
                  "developerName", "category"):
        assert isinstance(interface.get(field), str) and interface[field].strip()
    assert "defaultPrompt" in interface or "default_prompt" in interface
