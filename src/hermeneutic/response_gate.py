"""Shared decision text for host response hooks.

Hosts disagree about payload keys and decision vocabulary; they do not disagree
about what Hermeneutic found. Every response-hook adapter builds its own
host-specific envelope around these helpers so that
:mod:`hermeneutic.gates.regex` stays the single source of evaluation truth and
no adapter restates a rule.
"""

from __future__ import annotations

from collections.abc import Sequence

from hermeneutic.gates.regex import RiskHit

_MAX_LISTED_HITS = 3


def summarize_hits(hits: Sequence[RiskHit]) -> str:
    """Render an evidence-focused summary of the highest-priority hits."""
    summary = "; ".join(
        f"{hit.rule_id} ({hit.severity}): {hit.description}" for hit in hits[:_MAX_LISTED_HITS]
    )
    remaining = len(hits) - _MAX_LISTED_HITS
    if remaining > 0:
        summary += f"; plus {remaining} more"
    return summary


def repair_reason(summary: str) -> str:
    """The one repair prompt a host feeds back to the model."""
    return (
        "Hermeneutic found wording that creates evidence obligations: "
        f"{summary}. Revise once: add direct evidence, narrow or hedge the claim, "
        "or remove unsupported completion language. Preserve the user's requested scope."
    )


def retry_warning(summary: str) -> str:
    """The visible warning shown when the bounded retry is still risky."""
    return (
        "Hermeneutic still found evidence-obligation wording after the "
        f"bounded retry: {summary}"
    )


def unbounded_warning(summary: str) -> str:
    """The visible warning shown when a repair attempt cannot be bounded.

    A host that gives the adapter no way to remember that it already asked for
    a revision cannot be asked for one: a hook that blocks without bounded
    state loops. Warn instead of blocking.
    """
    return (
        "Hermeneutic found evidence-obligation wording but could not record a "
        f"bounded repair attempt, so it did not request a revision: {summary}"
    )
