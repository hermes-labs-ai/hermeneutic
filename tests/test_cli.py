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
