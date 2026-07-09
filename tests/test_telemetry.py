"""Tests for the opt-in fire telemetry sink.

Two invariants under test:
  1. OFF by default — no env var → no file, no behavior change, no raise.
  2. ON — records carry the verdict/severity/rule_ids (gate) or
     injected/buckets (compile) plus a human-vs-agent context label.
"""
from __future__ import annotations

import json

import pytest

from hermeneutic import telemetry


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in (
        telemetry.ENV_SINK,
        telemetry.ENV_CONTEXT,
        "CLAUDE_CODE_CHILD_SESSION",
        "AI_AGENT",
        "CLAUDE_CODE_ENTRYPOINT",
        "CLAUDECODE",
        "CLAUDE_CODE_SESSION_ID",
    ):
        monkeypatch.delenv(k, raising=False)


# ---- OFF by default ----

def test_disabled_by_default(monkeypatch):
    assert telemetry.enabled() is False
    assert telemetry.sink_path() is None


def test_record_is_noop_when_disabled(tmp_path, monkeypatch):
    # No env var set → nothing written anywhere, no exception.
    telemetry.record_gate(verdict="RISK", severity="high", rule_ids=["x"])
    telemetry.record_compile(injected=True, buckets=["scope_creep"], n_matches=3)
    assert list(tmp_path.iterdir()) == []


def test_never_raises_on_bad_path(monkeypatch):
    # Point the sink at an unwritable location; must swallow, not raise.
    monkeypatch.setenv(telemetry.ENV_SINK, "/proc/nonexistent/telemetry.jsonl")
    telemetry.record_gate(verdict="PASS", severity=None, rule_ids=[])  # no raise


# ---- ON ----

def test_gate_record_shape(tmp_path, monkeypatch):
    sink = tmp_path / "t.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink))
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", "sess-123")
    telemetry.record_gate(verdict="RISK", severity="high", rule_ids=["completion_with_number"])
    rec = json.loads(sink.read_text().strip())
    assert rec["event"] == "gate"
    assert rec["verdict"] == "RISK"
    assert rec["severity"] == "high"
    assert rec["rule_ids"] == ["completion_with_number"]
    assert rec["n_hits"] == 1
    assert rec["session_id"] == "sess-123"
    assert "ts" in rec and "context" in rec


def test_compile_record_shape(tmp_path, monkeypatch):
    sink = tmp_path / "t.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink))
    telemetry.record_compile(injected=True, buckets=["scope_creep", "tone_format"], n_matches=4)
    rec = json.loads(sink.read_text().strip())
    assert rec["event"] == "compile"
    assert rec["injected"] is True
    assert rec["buckets"] == ["scope_creep", "tone_format"]
    assert rec["n_matches"] == 4


def test_appends_multiple_records(tmp_path, monkeypatch):
    sink = tmp_path / "t.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink))
    telemetry.record_gate(verdict="PASS", severity=None, rule_ids=[])
    telemetry.record_gate(verdict="RISK", severity="med", rule_ids=["scope_expansion"])
    lines = [json.loads(x) for x in sink.read_text().splitlines() if x.strip()]
    assert len(lines) == 2
    assert lines[0]["verdict"] == "PASS"
    assert lines[1]["verdict"] == "RISK"


# ---- audit context (before/after windows) ----

_DRAFT = "Preamble text before the claim. Done — all 92 tests pass. Trailing text after the claim."


def _hits():
    from hermeneutic.gates.regex import risk_score
    hits = risk_score(_DRAFT)
    assert hits, "fixture draft must trip the gate"
    return hits


def _record_with_audit(sink):
    import json as _json
    return _json.loads(sink.read_text().strip())


def test_context_mode_defaults_none(monkeypatch):
    assert telemetry.context_mode() == "none"
    monkeypatch.setenv(telemetry.ENV_CONTEXT, "bogus-value")
    assert telemetry.context_mode() == "none"


def test_gate_no_audit_without_context_mode(tmp_path, monkeypatch):
    sink = tmp_path / "t.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink))
    hits = _hits()
    telemetry.record_gate(
        verdict="RISK", severity="high", rule_ids=[h.rule_id for h in hits],
        draft=_DRAFT, hits=hits,
    )
    rec = _record_with_audit(sink)
    assert "audit" not in rec
    # Fingerprint present in every mode once the draft is supplied.
    assert rec["draft_len"] == len(_DRAFT)
    assert len(rec["draft_sha256"]) == 64


def test_gate_audit_raw_mode_carries_windows(tmp_path, monkeypatch):
    sink = tmp_path / "t.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink))
    monkeypatch.setenv(telemetry.ENV_CONTEXT, "raw")
    hits = _hits()
    telemetry.record_gate(
        verdict="RISK", severity="high", rule_ids=[h.rule_id for h in hits],
        draft=_DRAFT, hits=hits,
    )
    rec = _record_with_audit(sink)
    assert rec["audit_mode"] == "raw"
    entry = rec["audit"][0]
    assert entry["rule_id"] == hits[0].rule_id
    # Windows must reassemble into a contiguous slice of the draft.
    assert entry["before"] + entry["matched"] + entry["after"] in _DRAFT
    assert "92" in entry["matched"]


def test_gate_audit_hash_mode_has_no_text(tmp_path, monkeypatch):
    sink = tmp_path / "t.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink))
    monkeypatch.setenv(telemetry.ENV_CONTEXT, "hash")
    hits = _hits()
    telemetry.record_gate(
        verdict="RISK", severity="high", rule_ids=[h.rule_id for h in hits],
        draft=_DRAFT, hits=hits,
    )
    rec = _record_with_audit(sink)
    assert rec["audit_mode"] == "hash"
    entry = rec["audit"][0]
    assert "matched" not in entry and "before" not in entry and "after" not in entry
    assert len(entry["matched_sha256"]) == 64
    assert entry["matched_len"] > 0
    # No raw draft text anywhere in the record.
    assert "92 tests" not in sink.read_text()


def test_gate_audit_falls_back_without_spans(tmp_path, monkeypatch):
    from hermeneutic.gates.regex import RiskHit
    sink = tmp_path / "t.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink))
    monkeypatch.setenv(telemetry.ENV_CONTEXT, "raw")
    hit = RiskHit(
        rule_id="completion_with_number", severity="high",
        description="d", matched_text="Done — all 92 tests pass",
    )
    telemetry.record_gate(
        verdict="RISK", severity="high", rule_ids=[hit.rule_id],
        draft=_DRAFT, hits=[hit],
    )
    entry = _record_with_audit(sink)["audit"][0]
    assert entry["matched"] == "Done — all 92 tests pass"
    assert entry["before"].endswith("claim. ")


def test_compile_prompt_fingerprint_and_raw_excerpt(tmp_path, monkeypatch):
    sink = tmp_path / "t.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink))
    telemetry.record_compile(injected=True, buckets=["scope_creep"], n_matches=2, prompt="fix the login bug")
    rec = _record_with_audit(sink)
    assert rec["prompt_len"] == len("fix the login bug")
    assert "prompt_excerpt" not in rec  # mode none → no text

    sink2 = tmp_path / "t2.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink2))
    monkeypatch.setenv(telemetry.ENV_CONTEXT, "raw")
    telemetry.record_compile(injected=True, buckets=["scope_creep"], n_matches=2, prompt="fix the login bug")
    rec2 = _record_with_audit(sink2)
    assert rec2["prompt_excerpt"] == "fix the login bug"


# ---- context detection (human vs agent) ----

def test_context_agent_via_child_session(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_CHILD_SESSION", "1")
    assert telemetry.detect_context()["context"] == "agent"


def test_context_agent_via_ai_agent(monkeypatch):
    monkeypatch.setenv("AI_AGENT", "1")
    ctx = telemetry.detect_context()
    assert ctx["context"] == "agent"
    assert ctx["ai_agent"] is True


def test_context_human_when_only_claudecode(monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    assert telemetry.detect_context()["context"] == "human"


def test_context_unknown_when_bare(monkeypatch):
    assert telemetry.detect_context()["context"] == "unknown"
