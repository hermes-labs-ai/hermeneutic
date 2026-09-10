#!/usr/bin/env python3
"""Gemini CLI AfterAgent adapter for Hermeneutic's deterministic gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# A Gemini extension install is a repository checkout, not a Python package
# install. Load the bundled Hermeneutic source without touching user Python.
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))

from hermeneutic import risk_score  # noqa: E402
from hermeneutic.response_gate import repair_reason, retry_warning, summarize_hits  # noqa: E402


def _allow(*, system_message: str | None = None) -> dict[str, Any]:
    output: dict[str, Any] = {"decision": "allow"}
    if system_message:
        output["systemMessage"] = system_message
    return output


def evaluate(payload: object) -> dict[str, Any]:
    """Return a Gemini AfterAgent decision for one parsed hook payload."""
    if not isinstance(payload, dict):
        return _allow(system_message="Hermeneutic skipped: invalid AfterAgent payload.")

    response = payload.get("prompt_response")
    if not isinstance(response, str):
        return _allow(system_message="Hermeneutic skipped: prompt_response was missing.")

    hits = risk_score(response)
    if not hits:
        return _allow()

    summary = summarize_hits(hits)

    # Gemini CLI reports a genuine retry here, so the flag alone bounds the loop.
    if payload.get("stop_hook_active") is True:
        return _allow(system_message=retry_warning(summary))

    return {
        "decision": "deny",
        "reason": repair_reason(summary),
        "systemMessage": "Hermeneutic requested one evidence-focused revision.",
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        output = evaluate(payload)
    except Exception as exc:  # Fail open: the advisory must not break Gemini CLI.
        output = _allow(system_message=f"Hermeneutic skipped: {type(exc).__name__}.")
    json.dump(output, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
