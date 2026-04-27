"""Stage 1: zero-LLM risk classifier.

Scans an outgoing draft for surface patterns that historically attract user
corrections. Patterns derived empirically from mined triples — extend them by
mining your own logs and adding the shapes that show up.

This is the load-bearing cheap stage: ~0ms per draft. Most outputs pass
through untouched. Only drafts that match a risk pattern proceed to the
LLM-based gates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Each pattern is (rule_id, severity, compiled_regex, human_description).
# Severity is "low" | "med" | "high"; the router maps high → must-gate, med → may-gate.
_RAW_PATTERNS: list[tuple[str, str, str, str]] = [
    # The dominant drift mode: post-completion overclaiming.
    # Completion verb co-occurring with a numeric or quantifier claim.
    (
        "completion_with_number",
        "high",
        r"\b(done|shipped|complete[d]?|built|finished|landed|passed|all green)\b.{0,200}?\b(\d+(\.\d+)?(%|ms|s|x|k)?|\d+/\d+)\b",
        "Completion verb co-occurs with a numeric claim — verify the number is tool-derived.",
    ),
    (
        "completion_with_all_quantifier",
        "high",
        r"\b(done|shipped|complete[d]?|built|finished|all (tests|of them|done))\b.{0,120}?\b(all|every|each)\b",
        "Completion claim with universal quantifier — confirm scope coverage.",
    ),
    # Subagent passthrough — summarizing a subagent's output as if verified.
    (
        "subagent_passthrough",
        "high",
        r"\b(subagent|swarm|agent[s]? (converged|agreed|found)|the agents (say|found|confirmed))\b",
        "Subagent output summarized — confirm the subagent actually performed the action.",
    ),
    # Unhedged certainty markers.
    (
        "unhedged_certainty",
        "med",
        r"\b(definitely|certainly|guaranteed|absolutely|always|never|impossible)\b",
        "Unhedged certainty — usually a sign of skipped verification.",
    ),
    # Scope expansion — the assistant volunteering work beyond the ask.
    (
        "scope_expansion",
        "med",
        r"\b(also|additionally|while i'?m at it|i went ahead and|bonus|extra|i'?ll also)\b",
        "Scope expansion language — confirm user requested the additional work.",
    ),
    # Generic fluency tells (hard-to-falsify summary text).
    (
        "fluent_summary_no_evidence",
        "low",
        r"\b(comprehensive|robust|production[- ]?ready|enterprise[- ]?grade|seamless|elegant)\b",
        "High-fluency adjective with no measurable referent.",
    ),
]


@dataclass
class RiskHit:
    rule_id: str
    severity: str
    description: str
    matched_text: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule_id}: {self.matched_text!r}"


_COMPILED = [
    (rid, sev, re.compile(pat, re.IGNORECASE | re.DOTALL), desc)
    for rid, sev, pat, desc in _RAW_PATTERNS
]


def risk_score(draft: str) -> list[RiskHit]:
    """Return all risk hits found in the draft. Empty list = no risk detected."""
    if not draft:
        return []
    hits: list[RiskHit] = []
    for rid, sev, rx, desc in _COMPILED:
        for m in rx.finditer(draft):
            matched = m.group(0)
            if len(matched) > 200:
                matched = matched[:200] + "..."
            hits.append(RiskHit(rule_id=rid, severity=sev, description=desc, matched_text=matched))
    return hits


def highest_severity(hits: list[RiskHit]) -> str | None:
    """Return the highest severity present in a hit list, or None."""
    if not hits:
        return None
    order = {"high": 3, "med": 2, "low": 1}
    return max(hits, key=lambda h: order.get(h.severity, 0)).severity
