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


@pytest.mark.parametrize("clarification", [
    "When I type cargo scan, I mean invoke the Cargo Scan skill.",
    "When I say cargo scan I mean invoke the Cargo Scan skill.",
    "Whenever I write release check, I am referring to the existing release checklist.",
    "If I mention the amber report, I mean the local audit report.",
    "When I ask for the cedar build, I mean the existing build task.",
    "If I say cargo scna = cargo scan, remember that meaning.",
    "If I type cedar biuld = cedar build, please remember this mapping.",
    "cargo-scan allways means invoke the Cargo Scan skill. if i say cargo scna = cargo-scan, "
    "that should be remembered for future requests.",
    "The cedar build means the existing task. If I say cedar biuld = cedar build, "
    "that should be part of this clarification lesson.",
    "By branch I meant the local Git branch, not a release deployment.",
    "I wanted the exit status. Do not print the process environment.",
    "I wanted a local draft, not a published update.",
    "I requested an estimate. I did not authorize a subscription.",
    "I already asked you to apply the local fix. Continue with verification.",
    "Here scratch means use the disposable experiment directory; it does not mean edit shared configuration.",
])
def test_mine_explicit_self_referential_clarification(tmp_path, clarification):
    log = tmp_path / "clarification.json"
    _write_openai_log(log, [
        ("user", "cargo scan"),
        ("assistant", "I will write a scanner."),
        ("user", clarification),
        ("assistant", "I will use the existing task."),
    ])
    triples = mine_file(log, fmt="openai")
    assert [triple.user_correction for triple in triples] == [clarification]
    assert triples[0].orig_prompt == "cargo scan"


@pytest.mark.parametrize("ordinary", [
    "When the scan runs, produce a report.",
    "If I say hello, respond politely.",
    "When I type the report, I mean to finish before lunch.",
    "If I say cargo scna = cargo scan, would that be clear?",
    "If the cargo scan fails, remember that meaning.",
    '"When I say cargo scan, I mean invoke the skill."',
    "> When I type cargo scan, I mean invoke the skill.",
    "Example: When I say cargo scan, I mean invoke the skill.",
    "```text\nWhen I say cargo scan, I mean invoke the skill.\n```",
    "The manual says: If I say cargo scna = cargo scan, remember that meaning.",
    '"cargo-scan means invoke the skill. if i say cargo scna = cargo-scan, that should be remembered."',
    "Example: cargo-scan means invoke the skill. if i say cargo scna = cargo-scan, that should be remembered.",
    "When I type cargo scan, what do you think I mean?",
    "By sunset I want the report ready.",
    "I wanted to ask you to add a download button.",
    "I wanted to ask for a recipe, not a restaurant recommendation.",
    "I wanted a recipe for lunch.",
    "I requested the meeting room yesterday.",
    "Here voltage means electric potential difference.",
    "Here archive means a historical collection.",
    "Here scratch means the disposable experiment directory; it does not mean shared configuration.",
    "Here voltage means electric potential difference; it does not mean electric current.",
    "Here archive means a historical collection; it does not mean a compressed file.",
    'Explain this quotation: "By branch I meant the local Git branch, not deployment."',
    '"I wanted a local draft, not a published update."',
    "> I requested an estimate. I did not authorize a subscription.",
])
def test_mine_does_not_infer_clarification_from_ordinary_or_quoted_text(tmp_path, ordinary):
    log = tmp_path / "ordinary.json"
    _write_openai_log(log, [("assistant", "Prior response."), ("user", ordinary)])
    assert mine_file(log, fmt="openai") == []


def test_codex_reader_ignores_malformed_record_shapes(tmp_path):
    from hermeneutic.triples import CodexReader

    rows = [
        None, [], "text", 7,
        {"type": "response_item", "payload": ["message"]},
        {"type": "response_item", "payload": "message"},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [
            {"type": "output_text", "text": {"malformed": "text"}},
            {"type": "output_text", "text": None},
            {"type": "output_text", "text": "Readable response."},
        ]}},
    ]
    log = tmp_path / "malformed.jsonl"
    log.write_text("\n".join(json.dumps(row) for row in rows))
    assert list(CodexReader().iter_turns(log)) == [("assistant", "Readable response.", "")]
