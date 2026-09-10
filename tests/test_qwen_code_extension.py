"""Qwen Code native Stop extension: decisions, bounding, and manifest wiring."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "integrations" / "qwen-code" / "hermeneutic_stop.py"
HOOKS = ROOT / "integrations" / "qwen-code" / "hooks.json"
MANIFEST = ROOT / "qwen-extension.json"

CLEAN = "I changed the parser and ran its focused test."
RISKY = "Done — shipped 14 files, all tests pass."


def _load_adapter():
    spec = importlib.util.spec_from_file_location("hermeneutic_stop", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMENEUTIC_QWEN_STATE_DIR", str(tmp_path / "state"))
    return _load_adapter()


def _stop(message: str, **extra) -> dict:
    # Qwen Code 0.23.2 hardcodes stop_hook_active: true on every Stop dispatch,
    # including the first of a turn. Model the payload exactly that way.
    payload = {
        "hook_event_name": "Stop",
        "session_id": "session-a",
        "stop_hook_active": True,
        "last_assistant_message": message,
        "timestamp": "2026-09-10T00:00:00.000Z",
    }
    payload.update(extra)
    return payload


def test_clean_response_is_allowed(adapter) -> None:
    assert adapter.evaluate(_stop(CLEAN)) == {"continue": True}


def test_risky_first_response_blocks_with_one_repair_reason(adapter) -> None:
    result = adapter.evaluate(_stop(RISKY))
    assert result["decision"] == "block"
    assert "Revise once" in result["reason"]
    assert result["systemMessage"].startswith("Hermeneutic requested")


def test_first_call_blocks_even_though_stop_hook_active_is_already_true(adapter) -> None:
    """Regression for the 0.23.2 quirk: the flag is not a retry discriminator."""
    assert adapter.evaluate(_stop(RISKY, stop_hook_active=True))["decision"] == "block"
    assert adapter.evaluate(_stop(RISKY, session_id="other", stop_hook_active=True))["decision"] == "block"


def test_risky_retry_is_bounded_and_allowed_with_a_visible_warning(adapter) -> None:
    assert adapter.evaluate(_stop(RISKY))["decision"] == "block"
    retry = adapter.evaluate(_stop("Still done — shipped 14 files, all tests pass."))
    assert retry == {
        "continue": True,
        "systemMessage": retry["systemMessage"],
    }
    assert "bounded retry" in retry["systemMessage"]
    assert "decision" not in retry


def test_a_third_risky_response_is_blocked_again_not_looped(adapter) -> None:
    """One response gets one retry; a later turn gets its own single attempt."""
    assert adapter.evaluate(_stop(RISKY))["decision"] == "block"
    assert "decision" not in adapter.evaluate(_stop(RISKY))
    assert adapter.evaluate(_stop(RISKY))["decision"] == "block"


def test_clean_retry_releases_the_session_marker(adapter, tmp_path) -> None:
    state_dir = tmp_path / "state"
    assert adapter.evaluate(_stop(RISKY))["decision"] == "block"
    assert list(state_dir.glob("*.json"))
    assert adapter.evaluate(_stop(CLEAN)) == {"continue": True}
    assert not list(state_dir.glob("*.json"))


def test_state_is_scoped_per_session(adapter) -> None:
    assert adapter.evaluate(_stop(RISKY, session_id="one"))["decision"] == "block"
    # A different session must not inherit the first session's spent attempt.
    assert adapter.evaluate(_stop(RISKY, session_id="two"))["decision"] == "block"


def test_marker_filename_does_not_leak_the_session_id(adapter, tmp_path) -> None:
    adapter.evaluate(_stop(RISKY, session_id="user-visible-session"))
    markers = list((tmp_path / "state").glob("*.json"))
    assert len(markers) == 1
    assert "user-visible-session" not in markers[0].name
    body = json.loads(markers[0].read_text())
    assert body == {"schema": 1, "blocked_at": "2026-09-10T00:00:00.000Z"}


def test_old_current_session_marker_still_bounds_the_retry(adapter, tmp_path) -> None:
    assert adapter.evaluate(_stop(RISKY))["decision"] == "block"
    (marker,) = (tmp_path / "state").glob("*.json")
    stale = time.time() - adapter._STATE_TTL_SECONDS - 60
    os.utime(marker, (stale, stale))
    # Age must never turn the repaired response into a second block.
    assert "decision" not in adapter.evaluate(_stop(RISKY))
    assert not list((tmp_path / "state").glob("*.json"))


def test_sweep_preserves_unrelated_stale_json_in_a_shared_state_directory(
    adapter, tmp_path
) -> None:
    """HERMENEUTIC_QWEN_STATE_DIR may be shared; sweep only owned markers."""
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    bystander = state_dir / "some-other-tool.json"
    bystander.write_text('{"not": "ours"}', encoding="utf-8")
    stale = time.time() - adapter._STATE_TTL_SECONDS - 60
    os.utime(bystander, (stale, stale))

    # Write and then sweep past an owned marker for an unrelated session.
    assert adapter.evaluate(_stop(RISKY, session_id="old-session"))["decision"] == "block"
    (owned,) = state_dir.glob(adapter._MARKER_GLOB)
    os.utime(owned, (stale, stale))
    assert adapter.evaluate(_stop(CLEAN, session_id="current-session")) == {"continue": True}

    assert not list(state_dir.glob(adapter._MARKER_GLOB))
    assert bystander.is_file()
    assert bystander.read_text(encoding="utf-8") == '{"not": "ours"}'


def test_bundled_core_import_failure_fails_open_on_exit_zero(tmp_path) -> None:
    """A broken bundle must skip with valid JSON, not crash the Stop hook."""
    # The adapter puts <its parents[2]>/src first on sys.path, so a stub there
    # shadows any installed package and reproduces a real import failure.
    bundle = tmp_path / "bundle"
    (bundle / "integrations" / "qwen-code").mkdir(parents=True)
    (bundle / "src" / "hermeneutic").mkdir(parents=True)
    (bundle / "src" / "hermeneutic" / "__init__.py").write_text(
        'raise RuntimeError("bundled core is broken")\n', encoding="utf-8"
    )
    script = bundle / "integrations" / "qwen-code" / "hermeneutic_stop.py"
    script.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(_stop(RISKY)),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "HERMENEUTIC_QWEN_STATE_DIR": str(tmp_path / "state")},
    )

    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert output["continue"] is True
    assert "decision" not in output
    assert "RuntimeError" in output["systemMessage"]


def test_old_markers_for_other_sessions_are_swept(adapter, tmp_path) -> None:
    assert adapter.evaluate(_stop(RISKY, session_id="old-session"))["decision"] == "block"
    (old_marker,) = (tmp_path / "state").glob("*.json")
    stale = time.time() - adapter._STATE_TTL_SECONDS - 60
    os.utime(old_marker, (stale, stale))

    assert adapter.evaluate(_stop(CLEAN, session_id="current-session")) == {"continue": True}
    assert not list((tmp_path / "state").glob("*.json"))


def test_undeletable_marker_warns_instead_of_claiming_a_bounded_retry(
    adapter, monkeypatch
) -> None:
    assert adapter.evaluate(_stop(RISKY))["decision"] == "block"

    def refuse_unlink(_marker):
        raise PermissionError("marker is not removable")

    monkeypatch.setattr(adapter.Path, "unlink", refuse_unlink)
    result = adapter.evaluate(_stop(RISKY))
    assert "decision" not in result
    assert "could not record a bounded repair attempt" in result["systemMessage"]
    assert "bounded retry" not in result["systemMessage"]


def test_missing_session_id_warns_instead_of_blocking(adapter) -> None:
    result = adapter.evaluate(_stop(RISKY, session_id=None))
    assert "decision" not in result
    assert result["continue"] is True
    assert "could not record a bounded repair attempt" in result["systemMessage"]


def test_unwritable_state_directory_warns_instead_of_blocking(tmp_path, monkeypatch) -> None:
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("", encoding="utf-8")
    monkeypatch.setenv("HERMENEUTIC_QWEN_STATE_DIR", str(blocked / "state"))
    adapter = _load_adapter()
    result = adapter.evaluate(_stop(RISKY))
    assert "decision" not in result
    assert "could not record a bounded repair attempt" in result["systemMessage"]


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="needs symlinks")
def test_hostile_marker_symlink_is_rejected_without_touching_its_target(
    adapter, tmp_path
) -> None:
    state_dir = adapter._state_dir()
    target = tmp_path / "victim.txt"
    target.write_text("original", encoding="utf-8")
    marker = adapter._marker_path(state_dir, "session-a")
    marker.symlink_to(target)

    assert adapter._write_repair_marker(marker, "2026-09-10T00:00:00.000Z") is False
    assert marker.is_symlink()
    assert target.read_text(encoding="utf-8") == "original"
    # Through the hook, the planted link is dropped rather than written through.
    assert "decision" not in adapter.evaluate(_stop(RISKY))
    assert target.read_text(encoding="utf-8") == "original"


def test_failed_marker_write_removes_the_partial_marker_and_warns(
    adapter, tmp_path, monkeypatch
) -> None:
    def fail_after_create(fd, *_args, **_kwargs):
        os.close(fd)
        raise OSError("marker body could not be written")

    monkeypatch.setattr(adapter.os, "fdopen", fail_after_create)
    result = adapter.evaluate(_stop(RISKY))
    assert "decision" not in result
    assert "could not record a bounded repair attempt" in result["systemMessage"]
    assert not list((tmp_path / "state").glob("*.json"))


@pytest.mark.skipif(not hasattr(os, "geteuid"), reason="POSIX ownership and modes")
def test_default_state_directory_and_marker_are_private(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("HERMENEUTIC_QWEN_STATE_DIR", raising=False)
    adapter = _load_adapter()
    monkeypatch.setattr(adapter.tempfile, "tempdir", str(tmp_path))
    state_dir = tmp_path / adapter._STATE_DIR_NAME
    state_dir.mkdir(mode=0o755)
    state_dir.chmod(0o755)

    assert adapter.evaluate(_stop(RISKY))["decision"] == "block"
    (marker,) = state_dir.glob(adapter._MARKER_GLOB)
    assert state_dir.stat().st_mode & 0o777 == 0o700
    assert marker.stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(not hasattr(os, "geteuid"), reason="POSIX ownership and modes")
@pytest.mark.parametrize("unsafe", ["world-writable", "symlink"])
def test_unsafe_override_state_directory_warns_instead_of_blocking(
    unsafe, tmp_path, monkeypatch
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    if unsafe == "world-writable":
        real.chmod(0o777)
        override = real
    else:
        override = tmp_path / "link"
        override.symlink_to(real, target_is_directory=True)
    monkeypatch.setenv("HERMENEUTIC_QWEN_STATE_DIR", str(override))
    adapter = _load_adapter()

    result = adapter.evaluate(_stop(RISKY))
    assert "decision" not in result
    assert "could not record a bounded repair attempt" in result["systemMessage"]
    assert not list(real.iterdir())


def test_malformed_payload_fails_open(adapter) -> None:
    assert "decision" not in adapter.evaluate(["not", "a", "payload"])
    assert "decision" not in adapter.evaluate(_stop(RISKY, last_assistant_message=None))


def test_cli_malformed_input_fails_open_with_valid_json(tmp_path) -> None:
    env = {
        **os.environ,
        "PATH": "/usr/bin:/bin",
        "HERMENEUTIC_QWEN_STATE_DIR": str(tmp_path),
    }
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input="not json",
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert completed.returncode == 0
    output = json.loads(completed.stdout)
    assert output["continue"] is True
    assert "decision" not in output


def test_internal_error_fails_open(adapter, monkeypatch, capsys) -> None:
    def explode(_text):
        raise RuntimeError("gate exploded")

    monkeypatch.setattr(adapter, "risk_score", explode)
    monkeypatch.setattr(adapter.sys, "stdin", io.StringIO(json.dumps(_stop(RISKY))))
    assert adapter.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["continue"] is True
    assert "decision" not in output
    assert "RuntimeError" in output["systemMessage"]


def test_manifest_points_at_the_qwen_stop_hook_config() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["name"] == "hermeneutic"
    assert manifest["hooks"] == "integrations/qwen-code/hooks.json"
    assert (ROOT / manifest["hooks"]).is_file()


def test_hook_config_registers_the_native_stop_event() -> None:
    hooks = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]
    # Qwen Code's converter copies hooks without translating event names, so the
    # Gemini AfterAgent registration is inert here and Stop must be explicit.
    assert list(hooks) == ["Stop"]
    entry = hooks["Stop"][0]["hooks"][0]
    assert entry["type"] == "command"
    # Only ${CLAUDE_PLUGIN_ROOT} is substituted inside an external hooks file.
    assert "${CLAUDE_PLUGIN_ROOT}" in entry["command"]
    assert "${extensionPath}" not in entry["command"]
    assert "integrations/qwen-code/hermeneutic_stop.py" in entry["command"]
    assert SCRIPT.is_file()


def test_qwen_and_gemini_manifests_declare_the_same_version() -> None:
    qwen = json.loads(MANIFEST.read_text(encoding="utf-8"))
    gemini = json.loads((ROOT / "gemini-extension.json").read_text(encoding="utf-8"))
    assert qwen["version"] == gemini["version"]


def test_qwen_manifest_ships_in_the_source_distribution() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"qwen-extension.json"' in pyproject


def test_both_adapters_share_one_evaluation_summary(adapter) -> None:
    """Neither adapter may restate a rule; both render the same finding text."""
    gemini_spec = importlib.util.spec_from_file_location(
        "hermeneutic_after_agent",
        ROOT / "integrations" / "gemini-cli" / "hermeneutic_after_agent.py",
    )
    assert gemini_spec and gemini_spec.loader
    gemini = importlib.util.module_from_spec(gemini_spec)
    gemini_spec.loader.exec_module(gemini)

    qwen_reason = adapter.evaluate(_stop(RISKY))["reason"]
    gemini_reason = gemini.evaluate({"prompt_response": RISKY, "stop_hook_active": False})["reason"]
    assert qwen_reason == gemini_reason
