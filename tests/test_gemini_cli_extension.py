from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "integrations" / "gemini-cli" / "hermeneutic_after_agent.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("hermeneutic_after_agent", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_clean_response_is_allowed() -> None:
    adapter = _load_adapter()
    assert adapter.evaluate(
        {"prompt_response": "I changed the parser and ran its focused test.", "stop_hook_active": False}
    ) == {"decision": "allow"}


def test_risky_response_requests_one_retry() -> None:
    adapter = _load_adapter()
    result = adapter.evaluate(
        {"prompt_response": "Done — shipped 14 files, all tests pass.", "stop_hook_active": False}
    )
    assert result["decision"] == "deny"
    assert "Revise once" in result["reason"]
    assert result["systemMessage"].startswith("Hermeneutic requested")


def test_active_retry_is_bounded_and_allowed() -> None:
    adapter = _load_adapter()
    result = adapter.evaluate(
        {"prompt_response": "Done — shipped 14 files, all tests pass.", "stop_hook_active": True}
    )
    assert result["decision"] == "allow"
    assert "bounded retry" in result["systemMessage"]


def test_cli_malformed_input_fails_open_with_valid_json() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="not json",
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["decision"] == "allow"


def test_root_manifest_and_hook_registration_are_consistent() -> None:
    manifest = json.loads((ROOT / "gemini-extension.json").read_text())
    hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text())
    assert manifest["name"] == "hermeneutic"
    command = hooks["hooks"]["AfterAgent"][0]["hooks"][0]["command"]
    assert "${extensionPath}" in command
    assert "hermeneutic_after_agent.py" in command
