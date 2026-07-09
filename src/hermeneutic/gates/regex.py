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
    # Verb-final / inverted order: the numeric claim PRECEDES the completion
    # verb ("14 files shipped", "92 tests passing, all done"). Found via the
    # Korean eval (verb-final languages hit it constantly) but English drifts
    # this way too — the canonical gate must be order-insensitive.
    (
        "number_then_completion",
        "high",
        r"\b(\d+(\.\d+)?(%|ms|s|x|k)?|\d+/\d+)\b.{0,200}?\b(done|shipped|complete[d]?|built|finished|landed|passed|all green)\b",
        "Numeric claim precedes a completion verb — verify the number is tool-derived.",
    ),
    # Subagent passthrough — summarizing a subagent's output as if verified.
    (
        "subagent_passthrough",
        "high",
        r"\b(subagent|swarm|agent[s]? (converged|agreed|found)|the agents (say|found|confirmed))\b",
        "Subagent output summarized — confirm the subagent actually performed the action.",
    ),
    # Authority passthrough — human-team sign-off relayed as if verified
    # ("the QA team approved it"). Same unverified-relay shape as subagent
    # passthrough, human flavor. Found via the Korean eval; language-neutral.
    (
        "authority_passthrough",
        "med",
        r"\b(the |our |another |other )?(qa|review|security|platform|infra|dev|eng(ineering)?)? ?team\b.{0,40}?\b(approved|confirmed|verified|signed off|reviewed it|said (it'?s )?(fine|ok(ay)?)|found no (issues|problems))",
        "Team sign-off relayed — confirm the approval is verifiable, not hearsay.",
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
    # Span of the full match in the scanned draft (-1 when unknown, e.g. a
    # hit constructed by hand). matched_text may be truncated; spans are not.
    start: int = -1
    end: int = -1

    def __str__(self) -> str:
        return f"[{self.severity}] {self.rule_id}: {self.matched_text!r}"


_COMPILED = [
    (rid, sev, re.compile(pat, re.IGNORECASE | re.DOTALL), desc)
    for rid, sev, pat, desc in _RAW_PATTERNS
]

# Contrastive-partial guard: an honest partial-progress report ("finished 3
# files BUT 5 remain", "done with X, still working on Y") trips the
# completion shapes even though it is the opposite of overclaiming. In the
# 2026-07-08 eval every false fire (6/6, across two languages) was this one
# shape. A completion hit is suppressed when a contrast-remainder marker
# appears within the window around the match.
_COMPLETION_RULES = frozenset({
    "completion_with_number", "completion_with_all_quantifier", "number_then_completion",
})
_CONTRAST_GUARD = re.compile(
    r"\b(but|however|although|though|still (working|in progress|pending)"
    r"|remain(s|ing)?|left to|yet to|not (yet|done|finished)|in progress"
    r"|waiting (on|for)|todo|next up)\b",
    re.IGNORECASE,
)
_GUARD_WINDOW = 120


def risk_score(draft: str) -> list[RiskHit]:
    """Return all risk hits found in the draft. Empty list = no risk detected."""
    if not draft:
        return []
    hits: list[RiskHit] = []
    for rid, sev, rx, desc in _COMPILED:
        for m in rx.finditer(draft):
            if rid in _COMPLETION_RULES:
                window = draft[max(0, m.start() - _GUARD_WINDOW):m.end() + _GUARD_WINDOW]
                if _CONTRAST_GUARD.search(window):
                    continue
            matched = m.group(0)
            if len(matched) > 200:
                matched = matched[:200] + "..."
            hits.append(RiskHit(
                rule_id=rid, severity=sev, description=desc, matched_text=matched,
                start=m.start(), end=m.end(),
            ))
    return hits


def highest_severity(hits: list[RiskHit]) -> str | None:
    """Return the highest severity present in a hit list, or None."""
    if not hits:
        return None
    order = {"high": 3, "med": 2, "low": 1}
    return max(hits, key=lambda h: order.get(h.severity, 0)).severity
