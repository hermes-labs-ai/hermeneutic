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

    summary = "; ".join(
        f"{hit.rule_id} ({hit.severity}): {hit.description}" for hit in hits[:3]
    )
    if len(hits) > 3:
        summary += f"; plus {len(hits) - 3} more"

    if payload.get("stop_hook_active") is True:
        return _allow(
            system_message=(
                "Hermeneutic still found evidence-obligation wording after the "
                f"bounded retry: {summary}"
            )
        )

    return {
        "decision": "deny",
        "reason": (
            "Hermeneutic found wording that creates evidence obligations: "
            f"{summary}. Revise once: add direct evidence, narrow or hedge the claim, "
            "or remove unsupported completion language. Preserve the user's requested scope."
        ),
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
