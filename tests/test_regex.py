"""Risk-regex gate tests."""
from __future__ import annotations

from hermeneutic.gates.regex import highest_severity, risk_score


def test_clean_draft_has_no_hits():
    draft = "Here are the three options you asked about. Each has a tradeoff."
    assert risk_score(draft) == []


def test_completion_with_number_fires_high():
    draft = "Done — shipped 14 files and all 92 tests pass."
    hits = risk_score(draft)
    assert any(h.rule_id == "completion_with_number" for h in hits)
    assert highest_severity(hits) == "high"


def test_subagent_passthrough_fires_high():
    draft = "The agents converged on three patterns and confirmed the implementation."
    hits = risk_score(draft)
    assert any(h.rule_id == "subagent_passthrough" for h in hits)
    assert highest_severity(hits) == "high"


def test_unhedged_certainty_fires_med():
    draft = "This will definitely work in production with no edge cases."
    hits = risk_score(draft)
    assert any(h.rule_id == "unhedged_certainty" for h in hits)


def test_scope_expansion_fires_med():
    draft = "I went ahead and also refactored the helper module while I was at it."
    hits = risk_score(draft)
    assert any(h.rule_id == "scope_expansion" for h in hits)


def test_fluency_tell_fires_low():
    draft = "Built a comprehensive, production-ready, enterprise-grade solution."
    hits = risk_score(draft)
    assert any(h.rule_id == "fluent_summary_no_evidence" for h in hits)


def test_highest_severity_picks_highest():
    draft = "Done with 5 files. This is comprehensive and definitely correct."
    sev = highest_severity(risk_score(draft))
    assert sev == "high"


def test_highest_severity_none_for_empty():
    assert highest_severity([]) is None


def test_empty_draft_no_hits():
    assert risk_score("") == []
