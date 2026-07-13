"""Smoke tests for the CLI."""
from __future__ import annotations

import json
from pathlib import Path

from hermeneutic.cli import main


def _write_log(path: Path, turns):
    with open(path, "w") as f:
        for role, text in turns:
            f.write(json.dumps({
                "type": role,
                "timestamp": "2026-01-01",
                "content": {"role": role, "content": text},
            }) + "\n")


def test_cli_mine_writes_jsonl(tmp_path):
    _write_log(tmp_path / "s1.jsonl", [
        ("user", "go"),
        ("assistant", "did it"),
        ("user", "no, that's not what i meant"),
        ("assistant", "ok let me retry"),
    ])
    out = tmp_path / "triples.jsonl"
    rc = main(["mine", str(tmp_path), "--out", str(out)])
    assert rc == 0
    lines = [ln for ln in out.read_text().splitlines() if ln.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["session"] == "s1"


def test_cli_gate_clean_returns_zero(capsys, tmp_path):
    draft = tmp_path / "d.txt"
    draft.write_text("Here are the three options. Each has a tradeoff.")
    rc = main(["gate", "--draft", str(draft)])
    assert rc == 0
    assert "PASS" in capsys.readouterr().out


def test_cli_gate_risky_returns_nonzero(capsys, tmp_path):
    draft = tmp_path / "d.txt"
    draft.write_text("Done — shipped 14 files and all 92 tests pass.")
    rc = main(["gate", "--draft", str(draft)])
    assert rc == 1
    out = capsys.readouterr().out
    assert "RISK" in out
    assert "completion_with_number" in out


def test_cli_stats_no_sink_errors(monkeypatch, capsys):
    monkeypatch.delenv("HERMENEUTIC_TELEMETRY", raising=False)
    rc = main(["stats"])
    assert rc == 1
    assert "no telemetry sink" in capsys.readouterr().err


def test_cli_stats_summarizes_end_to_end(monkeypatch, capsys, tmp_path):
    # Real fires through the gate command populate the sink; stats reads it back.
    sink = tmp_path / "telemetry.jsonl"
    monkeypatch.setenv("HERMENEUTIC_TELEMETRY", str(sink))
    monkeypatch.setenv("HERMENEUTIC_TELEMETRY_CONTEXT", "raw")
    risky = tmp_path / "risky.txt"
    risky.write_text("Done — shipped 14 files and all 92 tests pass.")
    clean = tmp_path / "clean.txt"
    clean.write_text("Here are the three options. Each has a tradeoff.")
    main(["gate", "--draft", str(risky)])
    main(["gate", "--draft", str(clean)])
    capsys.readouterr()

    rc = main(["stats", "--json"])
    assert rc == 0
    stats = json.loads(capsys.readouterr().out)
    assert stats["gate"]["total"] == 2
    assert stats["gate"]["verdicts"]["RISK"] == 1
    assert stats["gate"]["verdicts"]["PASS"] == 1
    assert stats["gate"]["risk_rate"] == 0.5
    assert stats["gate"]["rules"]["completion_with_number"] >= 1
    assert stats["gate"]["with_audit_context"] == 1


def test_cli_stats_human_output_and_malformed_lines(monkeypatch, capsys, tmp_path):
    sink = tmp_path / "telemetry.jsonl"
    sink.write_text(
        json.dumps({"ts": "2026-07-08T00:00:00+00:00", "event": "gate", "verdict": "RISK",
                    "severity": "high", "rule_ids": ["unhedged_certainty"], "context": "agent"}) + "\n"
        + "{not json}\n"
        + json.dumps({"ts": "2026-07-08T01:00:00+00:00", "event": "compile", "injected": True,
                      "buckets": ["scope_creep"], "n_matches": 3}) + "\n"
    )
    rc = main(["stats", "--sink", str(sink)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "gate fires: 1" in out
    assert "unhedged_certainty" in out
    assert "malformed: 1" in out
    assert "compile fires: 1" in out
    assert "scope_creep" in out


def test_cli_gate_missing_draft_file_errors_cleanly(capsys):
    rc = main(["gate", "--draft", "/definitely/not/a/file.txt"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "ERROR" in err and "not found" in err


def test_cli_gate_non_utf8_input_errors_cleanly(capsys, tmp_path):
    blob = tmp_path / "binary.bin"
    blob.write_bytes(b"\xff\xfe\xca\x00\xdd binary noise \x80\x81")
    rc = main(["gate", "--draft", str(blob)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "ERROR" in err and "UTF-8" in err


def test_cli_mine_accepts_multiple_directories(tmp_path):
    # The README quickstart passes a shell glob that expands to many dirs.
    d1, d2 = tmp_path / "p1", tmp_path / "p2"
    d1.mkdir()
    d2.mkdir()
    _write_log(d1 / "s1.jsonl", [
        ("user", "go"),
        ("assistant", "did it"),
        ("user", "no, that's not what i meant"),
        ("assistant", "ok let me retry"),
    ])
    _write_log(d2 / "s2.jsonl", [
        ("user", "run it"),
        ("assistant", "done"),
        ("user", "wrong file, i meant the other one"),
        ("assistant", "fixing"),
    ])
    out = tmp_path / "triples.jsonl"
    rc = main(["mine", str(d1), str(d2), "--out", str(out)])
    assert rc == 0
    sessions = {json.loads(ln)["session"] for ln in out.read_text().splitlines() if ln.strip()}
    assert sessions == {"s1", "s2"}


def test_cli_mine_out_creates_missing_parent_dirs(tmp_path):
    _write_log(tmp_path / "s1.jsonl", [
        ("user", "go"),
        ("assistant", "did it"),
        ("user", "no, that's not what i meant"),
        ("assistant", "ok let me retry"),
    ])
    out = tmp_path / "build" / "nested" / "triples.jsonl"
    rc = main(["mine", str(tmp_path), "--out", str(out)])
    assert rc == 0
    assert out.is_file()


def test_cli_harvest_out_creates_missing_parent_dirs(tmp_path):
    _write_log(tmp_path / "s1.jsonl", [
        ("user", "go"),
        ("assistant", "Done — shipped 14 files, all tests pass."),
        ("user", "wait, are you sure?"),
        ("assistant", "let me check"),
    ])
    out = tmp_path / "build" / "report.jsonl"
    rc = main(["harvest", str(tmp_path), "--out", str(out)])
    assert rc == 0
    assert out.is_file()
