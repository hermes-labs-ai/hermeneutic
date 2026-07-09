"""Tests for the reject-mining harvester.

The harvester replays the (pure) regex gate over session logs and classifies
each assistant turn by the user's actual next reaction:
  gate fired + correction   → confirmed_catch
  gate fired + no correction → possible_false_positive
  gate silent + correction   → missed_drift
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermeneutic import harvest
from hermeneutic.cli import main

RISKY = "Done — shipped 14 files and all 92 tests pass."
CLEAN = "Here are the three options. Each has a tradeoff."
CORRECTION = "no, that's not what i asked for"
ACCEPTANCE = "great, thanks — looks good"
# Drift the regex rules don't cover: no completion verb, no certainty marker.
SILENT_DRIFT = "The refactor you wanted lives in utils.py now."


def _write_log(path: Path, turns):
    with open(path, "w") as f:
        for role, text in turns:
            f.write(json.dumps({
                "type": role,
                "timestamp": "2026-07-08",
                "content": {"role": role, "content": text},
            }) + "\n")


def test_confirmed_catch(tmp_path):
    _write_log(tmp_path / "s1.jsonl", [
        ("user", "run the tests"),
        ("assistant", RISKY),
        ("user", CORRECTION),
    ])
    recs = list(harvest.harvest_dir(tmp_path))
    assert len(recs) == 1
    r = recs[0]
    assert r.kind == "confirmed_catch"
    assert "completion_with_number" in r.rule_ids
    assert r.severity == "high"
    assert r.orig_prompt == "run the tests"
    assert r.user_reaction == CORRECTION
    assert r.status == "pending"
    assert len(r.draft_sha256) == 64


def test_possible_false_positive(tmp_path):
    _write_log(tmp_path / "s1.jsonl", [
        ("user", "run the tests"),
        ("assistant", RISKY),
        ("user", ACCEPTANCE),
    ])
    recs = list(harvest.harvest_dir(tmp_path))
    assert len(recs) == 1
    assert recs[0].kind == "possible_false_positive"


def test_missed_drift(tmp_path):
    _write_log(tmp_path / "s1.jsonl", [
        ("user", "refactor utils"),
        ("assistant", SILENT_DRIFT),
        ("user", CORRECTION),
    ])
    recs = list(harvest.harvest_dir(tmp_path))
    assert len(recs) == 1
    r = recs[0]
    assert r.kind == "missed_drift"
    assert r.rule_ids == []
    assert r.severity is None


def test_clean_exchange_yields_nothing(tmp_path):
    _write_log(tmp_path / "s1.jsonl", [
        ("user", "what are my options?"),
        ("assistant", CLEAN),
        ("user", ACCEPTANCE),
    ])
    assert list(harvest.harvest_dir(tmp_path)) == []


def test_trailing_assistant_turn_is_unknowable(tmp_path):
    # No user reaction after the risky turn → cannot classify → skip.
    _write_log(tmp_path / "s1.jsonl", [
        ("user", "run the tests"),
        ("assistant", RISKY),
    ])
    assert list(harvest.harvest_dir(tmp_path)) == []


def test_dedup_across_sessions(tmp_path):
    turns = [
        ("user", "run the tests"),
        ("assistant", RISKY),
        ("user", CORRECTION),
    ]
    _write_log(tmp_path / "s1.jsonl", turns)
    _write_log(tmp_path / "s2.jsonl", turns)
    recs = list(harvest.harvest_dir(tmp_path))
    assert len(recs) == 1


def test_live_fire_cross_reference(tmp_path, monkeypatch):
    # A telemetry record whose draft_sha256 matches the replayed turn marks it live.
    from hermeneutic import telemetry
    sink = tmp_path / "telemetry.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink))
    telemetry.record_gate(verdict="RISK", severity="high",
                          rule_ids=["completion_with_number"], draft=RISKY)
    monkeypatch.delenv(telemetry.ENV_SINK)

    logs = tmp_path / "logs"
    logs.mkdir()
    _write_log(logs / "s1.jsonl", [
        ("user", "run the tests"),
        ("assistant", RISKY),
        ("user", CORRECTION),
    ])
    recs = list(harvest.harvest_dir(logs, telemetry_path=sink))
    assert recs[0].live_fire is True
    # Without the sink, the same replay is not marked live.
    assert next(iter(harvest.harvest_dir(logs))).live_fire is False


def test_promote_only_accepted_correction_kinds(tmp_path):
    queue = tmp_path / "queue.jsonl"
    logs = tmp_path / "logs"
    logs.mkdir()
    _write_log(logs / "s1.jsonl", [
        ("user", "run the tests"),
        ("assistant", RISKY),
        ("user", CORRECTION),
        ("user", "also do this"),
        ("assistant", RISKY + " Definitely."),
        ("user", ACCEPTANCE),
    ])
    recs = list(harvest.harvest_dir(logs))
    kinds = {r.kind for r in recs}
    assert kinds == {"confirmed_catch", "possible_false_positive"}
    with open(queue, "w") as f:
        for r in recs:
            d = json.loads(r.to_json())
            d["status"] = "accepted"  # accept everything; promote must still filter FP
            f.write(json.dumps(d) + "\n")

    triples = list(harvest.promote(queue))
    assert len(triples) == 1
    t = triples[0]
    assert t.user_correction == CORRECTION
    assert t.orig_prompt == "run the tests"
    assert t.prior_assistant.startswith("Done")


def test_promote_skips_pending(tmp_path):
    queue = tmp_path / "queue.jsonl"
    rec = {"kind": "confirmed_catch", "status": "pending", "session": "s",
           "timestamp": "", "orig_prompt": "", "assistant_excerpt": "x",
           "user_reaction": "no"}
    queue.write_text(json.dumps(rec) + "\n")
    assert list(harvest.promote(queue)) == []


def test_unknown_format_raises(tmp_path):
    with pytest.raises(ValueError, match="unknown format"):
        harvest.harvest_file(tmp_path / "x.jsonl", fmt="nope")


# ---- CLI ----

def test_cli_harvest_writes_queue_and_summary(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("HERMENEUTIC_TELEMETRY", raising=False)
    _write_log(tmp_path / "s1.jsonl", [
        ("user", "run the tests"),
        ("assistant", RISKY),
        ("user", CORRECTION),
    ])
    out = tmp_path / "queue.jsonl"
    rc = main(["harvest", str(tmp_path), "--out", str(out)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "harvested 1 review candidates" in err
    rec = json.loads(out.read_text().strip())
    assert rec["kind"] == "confirmed_catch"
    assert rec["status"] == "pending"


def test_cli_promote_appends_triples(tmp_path, capsys):
    queue = tmp_path / "queue.jsonl"
    rec = {"kind": "missed_drift", "status": "accepted", "session": "s",
           "timestamp": "t", "orig_prompt": "p", "assistant_excerpt": "a",
           "user_reaction": "no, wrong"}
    queue.write_text(json.dumps(rec) + "\n")
    corpus = tmp_path / "triples.jsonl"
    rc = main(["promote", str(queue), "--out", str(corpus)])
    assert rc == 0
    assert "promoted 1 accepted records" in capsys.readouterr().err
    trip = json.loads(corpus.read_text().strip())
    assert trip["user_correction"] == "no, wrong"
    assert trip["prior_assistant"] == "a"


def test_sanitized_json_strips_all_text(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    _write_log(logs / "secret-project.jsonl", [
        ("user", "run the tests on the acme takeover repo"),
        ("assistant", RISKY),
        ("user", CORRECTION),
    ])
    rec = next(iter(harvest.harvest_dir(logs)))
    d = json.loads(rec.to_sanitized_json())
    blob = rec.to_sanitized_json()
    assert d["sanitized"] is True
    assert d["kind"] == "confirmed_catch"
    assert d["rule_ids"]
    assert d["orig_prompt_len"] > 0 and "orig_prompt" not in d
    assert "acme" not in blob and "shipped" not in blob and CORRECTION not in blob
    assert d["session"] != "secret-project" and "secret" not in blob
    assert len(d["draft_sha256"]) == 64


def test_cli_harvest_sanitized_flag(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("HERMENEUTIC_TELEMETRY", raising=False)
    _write_log(tmp_path / "s1.jsonl", [
        ("user", "run the tests"),
        ("assistant", RISKY),
        ("user", CORRECTION),
    ])
    out = tmp_path / "queue.jsonl"
    rc = main(["harvest", str(tmp_path), "--out", str(out), "--sanitized"])
    assert rc == 0
    rec = json.loads(out.read_text().strip())
    assert rec["sanitized"] is True
    assert "assistant_excerpt" not in rec
