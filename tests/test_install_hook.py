"""Tests for install_hook subcommand — uses tmp_path as fake $HOME."""
from __future__ import annotations

import json

import pytest

from hermeneutic import install_hook


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Stand up a fake ~/ with a fresh ~/.claude/ inside."""
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    return tmp_path


def test_install_writes_wrapper_and_settings(fake_home):
    res = install_hook.install()
    wrapper = fake_home / ".claude" / "hooks" / "hermeneutic-gate.py"
    settings = fake_home / ".claude" / "settings.json"
    assert wrapper.is_file()
    assert wrapper.stat().st_mode & 0o111  # executable
    assert install_hook.WRAPPER_MARKER in wrapper.read_text()
    assert settings.is_file()
    cfg = json.loads(settings.read_text())
    assert "hermeneutic-gate.py" in json.dumps(cfg["hooks"]["Stop"])
    assert res["settings_state"] == "added"


def test_install_idempotent(fake_home):
    install_hook.install()
    res2 = install_hook.install()
    cfg = json.loads((fake_home / ".claude" / "settings.json").read_text())
    # Only one Stop entry referencing our wrapper, even after two installs.
    matches = [
        h for entry in cfg["hooks"]["Stop"]
        for h in entry.get("hooks", [])
        if "hermeneutic-gate.py" in h.get("command", "")
    ]
    assert len(matches) == 1
    assert res2["settings_state"] == "already-present"


def test_install_preserves_existing_stop_hook(fake_home):
    settings = fake_home / ".claude" / "settings.json"
    pre = {
        "hooks": {
            "Stop": [
                {"hooks": [{"type": "command", "command": "bash /some/other/hook.sh"}]}
            ]
        }
    }
    settings.write_text(json.dumps(pre))
    install_hook.install()
    cfg = json.loads(settings.read_text())
    cmds = [h["command"] for entry in cfg["hooks"]["Stop"] for h in entry["hooks"]]
    assert "bash /some/other/hook.sh" in cmds
    assert any("hermeneutic-gate.py" in c for c in cmds)
    assert len(cfg["hooks"]["Stop"]) == 2


def test_install_refuses_foreign_wrapper(fake_home):
    hooks_dir = fake_home / ".claude" / "hooks"
    hooks_dir.mkdir()
    foreign = hooks_dir / "hermeneutic-gate.py"
    foreign.write_text("# Some user's own script, not ours\nprint('hi')\n")
    with pytest.raises(install_hook.InstallError, match="Refusing to overwrite"):
        install_hook.install()


def test_install_fails_without_claude_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # No ~/.claude — should fail cleanly
    with pytest.raises(install_hook.InstallError, match="Claude Code config dir not found"):
        install_hook.install()


def test_install_fails_on_malformed_settings(fake_home):
    settings = fake_home / ".claude" / "settings.json"
    settings.write_text("{not valid json")
    with pytest.raises(install_hook.InstallError, match="malformed JSON"):
        install_hook.install()


def test_uninstall_removes_both(fake_home):
    install_hook.install()
    res = install_hook.uninstall()
    wrapper = fake_home / ".claude" / "hooks" / "hermeneutic-gate.py"
    settings = fake_home / ".claude" / "settings.json"
    assert not wrapper.exists()
    cfg = json.loads(settings.read_text())
    assert "hermeneutic-gate.py" not in json.dumps(cfg.get("hooks", {}))
    assert res["wrapper_state"] == "removed"
    assert res["settings_state"] == "removed"


def test_uninstall_preserves_other_hooks(fake_home):
    install_hook.install()
    settings = fake_home / ".claude" / "settings.json"
    cfg = json.loads(settings.read_text())
    cfg["hooks"]["Stop"].append(
        {"hooks": [{"type": "command", "command": "bash /unrelated/hook.sh"}]}
    )
    settings.write_text(json.dumps(cfg))
    install_hook.uninstall()
    cfg = json.loads(settings.read_text())
    cmds = [h["command"] for entry in cfg["hooks"]["Stop"] for h in entry["hooks"]]
    assert "bash /unrelated/hook.sh" in cmds
    assert not any("hermeneutic-gate.py" in c for c in cmds)


def test_uninstall_preserves_foreign_wrapper(fake_home):
    hooks_dir = fake_home / ".claude" / "hooks"
    hooks_dir.mkdir()
    foreign = hooks_dir / "hermeneutic-gate.py"
    foreign.write_text("# user's own thing\nprint('foreign')\n")
    res = install_hook.uninstall()
    assert foreign.exists()
    assert res["wrapper_state"] == "preserved-foreign"


def test_uninstall_when_nothing_installed(fake_home):
    res = install_hook.uninstall()
    assert res["wrapper_state"] == "absent"
    assert res["settings_state"] == "absent"


def test_wrapper_handles_missing_transcript(fake_home, monkeypatch, capfd):
    """Wrapper should silently exit 0 on missing transcript_path (new session)."""
    install_hook.install()
    wrapper = fake_home / ".claude" / "hooks" / "hermeneutic-gate.py"
    import subprocess
    proc = subprocess.run(
        ["python3", str(wrapper)],
        input='{"session_id": "x", "transcript_path": ""}',
        capture_output=True, text=True, timeout=5,
    )
    assert proc.returncode == 0


def test_wrapper_handles_malformed_jsonl(fake_home, tmp_path):
    install_hook.install()
    wrapper = fake_home / ".claude" / "hooks" / "hermeneutic-gate.py"
    transcript = tmp_path / "session.jsonl"
    # Write a transcript with one bad line followed by a good assistant turn.
    transcript.write_text(
        "{not valid json\n"
        + json.dumps({
            "type": "assistant",
            "content": {"role": "assistant", "content": "All good here, no risk."},
          }) + "\n"
    )
    import subprocess
    proc = subprocess.run(
        ["python3", str(wrapper)],
        input=json.dumps({"transcript_path": str(transcript), "session_id": "x"}),
        capture_output=True, text=True, timeout=5,
    )
    assert proc.returncode == 0  # advisory — never blocks even on bad data
