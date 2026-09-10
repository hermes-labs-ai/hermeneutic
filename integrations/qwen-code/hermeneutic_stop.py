#!/usr/bin/env python3
"""Qwen Code Stop adapter for Hermeneutic's deterministic gate.

Qwen Code 0.23.2 dispatches its final-response ``Stop`` hook with
``stop_hook_active`` hardcoded to ``true``, including on the first call of a
turn. The flag therefore cannot tell a first response from a repaired one, and
trusting it would either suppress every repair request or loop. This adapter
ignores the flag and bounds itself with a small per-session marker file
instead: one response gets at most one repair request.

The marker records no response text, no prompt, and no session identifier — the
file name is a SHA-256 digest of the session id and the body is a schema tag
plus the host-supplied event timestamp. A marker is always consumed by the next
``Stop`` of the same session, regardless of age, so a long repair cannot cause
a second block. Old markers belonging to other sessions are swept on later
runs, so abandoned state does not accumulate or carry between sessions.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# A Qwen extension install is a repository checkout, not a Python package
# install. Load the bundled Hermeneutic source without touching user Python.
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))

from hermeneutic import risk_score  # noqa: E402
from hermeneutic.response_gate import (  # noqa: E402
    repair_reason,
    retry_warning,
    summarize_hits,
    unbounded_warning,
)

_STATE_DIR_ENV = "HERMENEUTIC_QWEN_STATE_DIR"
_STATE_DIR_NAME = "hermeneutic-qwen-stop"
_STATE_SCHEMA = 1
# A marker only has to survive the model's immediate repair turn. Anything older
# belongs to an abandoned or cancelled turn and must not spend that turn's one
# repair request.
_STATE_TTL_SECONDS = 1800


def _allow(*, system_message: str | None = None) -> dict[str, Any]:
    output: dict[str, Any] = {"continue": True}
    if system_message:
        output["systemMessage"] = system_message
    return output


def _state_dir() -> Path:
    override = os.environ.get(_STATE_DIR_ENV)
    directory = Path(override) if override else Path(tempfile.gettempdir()) / _STATE_DIR_NAME
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _marker_path(directory: Path, session_id: str) -> Path:
    # Hashing keeps a host-supplied session id out of the file name and out of
    # any path it could otherwise traverse into.
    digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:32]
    return directory / f"{digest}.json"


def _sweep(directory: Path, now: float, current_marker: Path) -> None:
    for marker in directory.glob("*.json"):
        # The current session's marker is the bounding contract. Expiring it
        # before consumption could turn a long-running repair into a second
        # block and therefore a loop.
        if marker == current_marker:
            continue
        try:
            if now - marker.stat().st_mtime > _STATE_TTL_SECONDS:
                marker.unlink()
        except OSError:
            continue


def _take_repair_marker(marker: Path) -> bool | None:
    """Consume this session's marker; return ``None`` if state is unavailable."""
    try:
        marker.unlink()
    except FileNotFoundError:
        return False
    except OSError:
        return None
    return True


def _write_repair_marker(marker: Path, blocked_at: object) -> bool:
    body = {"schema": _STATE_SCHEMA, "blocked_at": blocked_at if isinstance(blocked_at, str) else None}
    try:
        marker.write_text(json.dumps(body), encoding="utf-8")
    except OSError:
        return False
    return True


def _resolve_marker(session_id: object, now: float) -> Path | None:
    if not isinstance(session_id, str) or not session_id.strip():
        return None
    try:
        directory = _state_dir()
        marker = _marker_path(directory, session_id)
        _sweep(directory, now, marker)
        return marker
    except OSError:
        return None


def evaluate(payload: object) -> dict[str, Any]:
    """Return a Qwen Code Stop decision for one parsed hook payload."""
    if not isinstance(payload, dict):
        return _allow(system_message="Hermeneutic skipped: invalid Stop payload.")

    response = payload.get("last_assistant_message")
    if not isinstance(response, str):
        return _allow(system_message="Hermeneutic skipped: last_assistant_message was missing.")

    # Marker age is measured against the same filesystem clock that stamps it.
    now = time.time()
    marker = _resolve_marker(payload.get("session_id"), now)
    # Consume before deciding: a clean repair must also release the session's
    # marker, or the next turn would inherit a spent repair request.
    marker_state = _take_repair_marker(marker) if marker is not None else False

    hits = risk_score(response)
    if not hits:
        if marker_state is None:
            return _allow(system_message="Hermeneutic skipped: could not clear bounded repair state.")
        return _allow()

    summary = summarize_hits(hits)
    if marker_state is True:
        return _allow(system_message=retry_warning(summary))
    if marker_state is None:
        return _allow(system_message=unbounded_warning(summary))
    if marker is None or not _write_repair_marker(marker, payload.get("timestamp")):
        return _allow(system_message=unbounded_warning(summary))

    return {
        "decision": "block",
        "reason": repair_reason(summary),
        "systemMessage": "Hermeneutic requested one evidence-focused revision.",
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        output = evaluate(payload)
    except Exception as exc:  # Fail open: the advisory must not break Qwen Code.
        output = _allow(system_message=f"Hermeneutic skipped: {type(exc).__name__}.")
    json.dump(output, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
