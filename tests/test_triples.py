"""Round-trip tests for the triples miner."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermeneutic.triples import Triple, mine_file


def _write_claude_log(path: Path, turns: list[tuple[str, str]]) -> None:
    """turns: list of (role, text) — written as Claude Code JSONL."""
    with open(path, "w") as f:
        for role, text in turns:
            entry = {
                "type": role,
                "timestamp": "2026-01-01T00:00:00Z",
                "content": {"role": role, "content": text},
            }
            f.write(json.dumps(entry) + "\n")


def _write_openai_log(path: Path, turns: list[tuple[str, str]]) -> None:
    msgs = [{"role": r, "content": t} for r, t in turns]
    path.write_text(json.dumps({"messages": msgs}))


def test_mine_extracts_basic_triple(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_claude_log(log, [
        ("user", "Build me a thing"),
        ("assistant", "Done — shipped 5 files with 100% coverage"),
        ("user", "wait, are you sure? show me the test output"),
        ("assistant", "Let me actually verify..."),
    ])
    triples = mine_file(log, fmt="claude-code")
    assert len(triples) == 1
    t = triples[0]
    assert "wait" in t.user_correction.lower()
    assert "Done" in t.prior_assistant
    assert "verify" in t.next_assistant


def test_mine_skips_non_correction_user_turn(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_claude_log(log, [
        ("user", "Build me a thing"),
        ("assistant", "Built it"),
        ("user", "thanks, now also add tests"),  # not a correction
        ("assistant", "Adding tests"),
    ])
    assert mine_file(log) == []


def test_mine_skips_subagent_qa_noise(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_claude_log(log, [
        ("assistant", "Some output"),
        ("user", "You are QA for a drafted fix. Answer ONLY: YES or NO. no, this is wrong."),
    ])
    # The user turn matches a correction pattern but is subagent QA — must be skipped.
    assert mine_file(log) == []


def test_mine_handles_multiple_corrections(tmp_path):
    log = tmp_path / "session.jsonl"
    _write_claude_log(log, [
        ("user", "go"),
        ("assistant", "first attempt"),
        ("user", "no, that's wrong"),
        ("assistant", "second attempt"),
        ("user", "actually, I meant the other thing"),
        ("assistant", "third attempt"),
    ])
    triples = mine_file(log)
    assert len(triples) == 2


def test_mine_openai_format(tmp_path):
    log = tmp_path / "session.json"
    _write_openai_log(log, [
        ("user", "do X"),
        ("assistant", "did X completely"),
        ("user", "wait, are you sure you did X?"),
        ("assistant", "let me check"),
    ])
    triples = mine_file(log, fmt="openai")
    assert len(triples) == 1
    assert triples[0].user_correction.startswith("wait")


def test_unknown_format_raises(tmp_path):
    log = tmp_path / "x.jsonl"
    log.write_text("{}")
    with pytest.raises(ValueError):
        mine_file(log, fmt="not-a-real-format")


def test_triple_to_json_roundtrip():
    t = Triple(
        session="s1",
        timestamp="2026-01-01",
        prior_assistant="a",
        user_correction="no",
        next_assistant="b",
    )
    d = json.loads(t.to_json())
    assert d["session"] == "s1"
    assert d["user_correction"] == "no"


def test_codex_reader_parses_rollout_schema(tmp_path):
    import json as _json

    from hermeneutic.triples import CodexReader
    rows = [
        {"type": "session_meta", "payload": {"id": "x"}},
        {"type": "response_item", "timestamp": "2026-07-08T00:00:00Z", "payload": {
            "type": "message", "role": "user",
            "content": [{"type": "input_text", "text": "<environment_context>...</environment_context>"}]}},
        {"type": "response_item", "timestamp": "2026-07-08T00:00:01Z", "payload": {
            "type": "message", "role": "user",
            "content": [{"type": "input_text", "text": "fix the login bug"}]}},
        {"type": "response_item", "timestamp": "2026-07-08T00:00:02Z", "payload": {
            "type": "message", "role": "developer",
            "content": [{"type": "input_text", "text": "permissions preamble"}]}},
        {"type": "response_item", "timestamp": "2026-07-08T00:00:03Z", "payload": {
            "type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": "Done — fixed all 3 bugs."}]}},
        {"type": "event_msg", "payload": {"type": "task_started"}},
    ]
    p = tmp_path / "rollout-x.jsonl"
    p.write_text("\n".join(_json.dumps(r) for r in rows) + "\n")
    turns = list(CodexReader().iter_turns(p))
    assert turns == [
        ("user", "fix the login bug", "2026-07-08T00:00:01Z"),
        ("assistant", "Done — fixed all 3 bugs.", "2026-07-08T00:00:03Z"),
    ]
