"""Hermes Agent plugin for the deterministic outgoing evidence gate."""

from __future__ import annotations

from typing import Any

from .gates.regex import highest_severity, risk_score

_ACTIONABLE_SEVERITIES = frozenset({"med", "high"})


def check_outgoing_claims(response_text: str, **_: Any) -> str | None:
    """Append an advisory when the final response creates an evidence obligation."""
    if not isinstance(response_text, str) or not response_text:
        return None

    hits = [
        hit for hit in risk_score(response_text)
        if hit.severity in _ACTIONABLE_SEVERITIES
    ]
    if not hits:
        return None

    rule_ids = list(dict.fromkeys(hit.rule_id for hit in hits))
    severity = highest_severity(hits) or "med"
    rules = ", ".join(rule_ids)
    return (
        f"{response_text}\n\n"
        f"[Hermeneutic evidence check: {severity} — review evidence for "
        f"{rules} before relying on these claims.]"
    )


def register(ctx: Any) -> None:
    """Register Hermeneutic on Hermes Agent's final-output transform hook."""
    ctx.register_hook("transform_llm_output", check_outgoing_claims)
