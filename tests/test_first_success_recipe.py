"""Exercise the first-success gate recipe and its offline behavior."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from hermeneutic.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent

RISKY_DRAFT = "Done — shipped 14 files, all tests pass."
NEUTRAL_DRAFT = "Draft ready for review."
RISKY_RULE_IDS = ("completion_with_number", "completion_with_all_quantifier")

MISSING_DRAFT_NAME = "missing.txt"

NON_UTF8_DIAGNOSTIC = (
    "ERROR: input is not valid UTF-8 text — the gate reads text drafts only."
)

# The installed console script is not on PATH inside a stripped environment,
# so drive the same entry point the script wraps.
_GATE_ENTRY = "from hermeneutic.cli import main; raise SystemExit(main(['gate']))"


def test_published_risky_draft_fires_both_rules(capsys, tmp_path):
    draft = tmp_path / "risky.txt"
    draft.write_text(RISKY_DRAFT, encoding="utf-8")

    rc = main(["gate", "--draft", str(draft)])

    out = capsys.readouterr().out
    assert rc == 1
    assert "RISK — highest severity: high" in out
    for rule_id in RISKY_RULE_IDS:
        assert rule_id in out


def test_published_neutral_draft_passes(capsys, tmp_path):
    draft = tmp_path / "neutral.txt"
    draft.write_text(NEUTRAL_DRAFT, encoding="utf-8")

    rc = main(["gate", "--draft", str(draft)])

    assert rc == 0
    assert "PASS — no risk patterns matched." in capsys.readouterr().out


def test_missing_draft_stays_a_distinct_error(capsys, tmp_path):
    rc = main(["gate", "--draft", str(tmp_path / MISSING_DRAFT_NAME)])

    assert rc == 2, "a missing draft must not collapse into the RISK exit code"
    captured = capsys.readouterr()
    assert "not found" in (captured.out + captured.err)


def test_non_utf8_draft_exits_2_with_the_published_diagnostic(capsys, tmp_path):
    """Unreadable text must return a distinct error with its CLI diagnostic."""
    draft = tmp_path / "not-utf8.txt"
    # 0xFF is not a legal UTF-8 start byte, so decoding fails outright.
    draft.write_bytes(b"Done \xff shipped 14 files, all tests pass.")

    rc = main(["gate", "--draft", str(draft)])

    assert rc == 2, "unreadable input must not collapse into PASS or RISK"
    captured = capsys.readouterr()
    assert NON_UTF8_DIAGNOSTIC in captured.err
    assert "PASS" not in captured.out and "RISK" not in captured.out


def test_gate_recipe_needs_no_credentials_or_private_files(tmp_path):
    """The recipe must work with no inherited env and no readable home."""
    stripped = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path / "no-such-home"),
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }

    risky = subprocess.run(
        [sys.executable, "-c", _GATE_ENTRY],
        input=RISKY_DRAFT + "\n",
        capture_output=True,
        text=True,
        env=stripped,
        cwd=os.fspath(tmp_path),
        check=False,
    )
    assert risky.returncode == 1
    for rule_id in RISKY_RULE_IDS:
        assert rule_id in risky.stdout

    neutral = subprocess.run(
        [sys.executable, "-c", _GATE_ENTRY],
        input=NEUTRAL_DRAFT + "\n",
        capture_output=True,
        text=True,
        env=stripped,
        cwd=os.fspath(tmp_path),
        check=False,
    )
    assert neutral.returncode == 0
    assert "PASS — no risk patterns matched." in neutral.stdout


# --- outbound-network deny guard ------------------------------------------

# Prepended to the CHILD script, so the denial is installed in the gate's own
# process before hermeneutic is imported rather than asserted from the parent.
# A `sitecustomize.py` would shadow the interpreter's own, which on some builds
# is what puts site-packages on the path.
_DENY_OUTBOUND = """\
import socket


class OutboundNetworkDenied(RuntimeError):
    pass


def _deny(*args, **kwargs):
    raise OutboundNetworkDenied("outbound network access attempted")


socket.socket = _deny
socket.create_connection = _deny
socket.getaddrinfo = _deny
"""


def test_default_gate_runs_with_outbound_network_denied(tmp_path):
    """The advertised offline claim, enforced inside the gate's own process.

    The prepended denial guard runs before the CLI imports anything, so any
    socket attempt raises. The published risky/neutral pair must still produce
    its exact verdicts and exit codes.
    """
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path / "no-such-home"),
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }

    def _gate(draft: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-c", _DENY_OUTBOUND + "\n" + _GATE_ENTRY],
            input=draft + "\n",
            capture_output=True,
            text=True,
            env=env,
            cwd=os.fspath(tmp_path),
            check=False,
        )

    # The guard must actually bite, or this test proves nothing.
    proof = subprocess.run(
        [sys.executable, "-c", _DENY_OUTBOUND + "\nimport socket\nsocket.socket()\n"],
        capture_output=True, text=True, env=env, cwd=os.fspath(tmp_path), check=False,
    )
    assert proof.returncode != 0
    assert "OutboundNetworkDenied" in proof.stderr

    risky = _gate(RISKY_DRAFT)
    assert risky.returncode == 1
    for rule_id in RISKY_RULE_IDS:
        assert rule_id in risky.stdout

    neutral = _gate(NEUTRAL_DRAFT)
    assert neutral.returncode == 0
    assert "PASS — no risk patterns matched." in neutral.stdout
