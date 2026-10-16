"""Consumer contracts for bounded, read-only correction inspection."""
from __future__ import annotations

import json
import socket

import pytest

from hermeneutic.cli import main


def _triple(**changes):
    return {
        "session": "synthetic-session",
        "timestamp": "2026-10-16",
        "prior_assistant": "PRIVATE PRIOR MESSAGE",
        "user_correction": "Use the owning repository.",
        "next_assistant": "PRIVATE NEXT MESSAGE",
        "orig_prompt": "PRIVATE ORIGINAL PROMPT",
        **changes,
    }


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("inspection attempted a network connection")
    monkeypatch.setattr(socket, "create_connection", forbidden)


def test_inspect_default_is_bounded_read_only_and_omits_assistant_text(tmp_path, capsys):
    source = tmp_path / "triples.jsonl"
    source.write_text("\n" + "\n".join(json.dumps(_triple(session=f"s{i}")) for i in range(7)) + "\n")
    before = source.read_bytes(), source.stat().st_mtime_ns

    assert main(["inspect", str(source)]) == 0

    result = capsys.readouterr()
    previews = [json.loads(line) for line in result.out.splitlines()]
    assert len(previews) == 5
    assert previews[0]["line"] == 2
    assert [p["session_preview"] for p in previews] == [f"s{i}" for i in range(5)]
    assert "PRIVATE" not in result.out
    assert "Showing 5 of 7 records; complete file validated." in result.err
    assert (source.read_bytes(), source.stat().st_mtime_ns) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["triples.jsonl"]


@pytest.mark.parametrize("limit", [1, 3, 20])
def test_inspect_respects_caller_limit(limit, tmp_path, capsys):
    source = tmp_path / "triples.jsonl"
    source.write_text((json.dumps(_triple()) + "\n") * 4)
    assert main(["inspect", str(source), "--limit", str(limit)]) == 0
    assert len(capsys.readouterr().out.splitlines()) == min(limit, 4)


@pytest.mark.parametrize("limit", ["0", "-1", "wrong"])
def test_inspect_rejects_invalid_limit_before_reading(limit, capsys):
    with pytest.raises(SystemExit) as error:
        main(["inspect", "/missing.jsonl", "--limit", limit])
    assert error.value.code == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert "--limit" in result.err


def test_inspect_marks_provenance_and_correction_truncation(tmp_path, capsys):
    source = tmp_path / "triples.jsonl"
    source.write_text(json.dumps(_triple(session="s" * 200, timestamp="t" * 200,
                                         user_correction="\x1b\n修" * 100)) + "\n")
    assert main(["inspect", str(source)]) == 0
    result = capsys.readouterr()
    preview = json.loads(result.out)
    for field, cap in (("session", 128), ("timestamp", 64), ("user_correction", 160)):
        assert len(preview[f"{field}_preview"]) == cap
        assert preview[f"{field}_truncated"] is True
    assert "\x1b" not in result.out
    assert len(result.out.splitlines()) == 1


@pytest.mark.parametrize("timestamp", [123, None, {"legacy": "opaque"}])
def test_inspect_accepts_legacy_triples_and_opaque_timestamp(timestamp, tmp_path, capsys):
    source = tmp_path / "legacy.jsonl"
    record = _triple(timestamp=timestamp)
    del record["orig_prompt"]
    source.write_text(json.dumps(record) + "\n")
    assert main(["inspect", str(source)]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["timestamp_preview"] == json.dumps(timestamp)
    assert preview["timestamp_truncated"] is False
    assert preview["user_correction_truncated"] is False


@pytest.mark.parametrize("malformed", [
    b"{bad JSON}\n", b"[]\n", b"null\n", b"{}\n",
    (json.dumps(_triple(user_correction=42)) + "\n").encode(),
    (json.dumps(_triple(unexpected="PRIVATE ERROR VALUE")) + "\n").encode(),
    b"\xff\n",
    b'{"timestamp":' + b"9" * 5000 + b"}\n",
])
def test_inspect_validates_beyond_limit_without_partial_output(malformed, tmp_path, capsys):
    source = tmp_path / "triples.jsonl"
    original = (json.dumps(_triple()) + "\n\n").encode() + malformed
    source.write_bytes(original)
    assert main(["inspect", str(source), "--limit", "1"]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert "line 3:" in result.err
    assert "PRIVATE" not in result.err and "Traceback" not in result.err
    assert source.read_bytes() == original


@pytest.mark.parametrize("kind", ["missing", "directory"])
def test_inspect_file_errors_are_clean(kind, tmp_path, capsys):
    source = tmp_path if kind == "directory" else tmp_path / "missing.jsonl"
    assert main(["inspect", str(source)]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert "ERROR: cannot read triples file" in result.err
    assert "Traceback" not in result.err


def test_inspect_empty_file(tmp_path, capsys):
    source = tmp_path / "empty.jsonl"
    source.write_text("\n \n")
    assert main(["inspect", str(source)]) == 0
    result = capsys.readouterr()
    assert result.out == ""
    assert "Showing 0 of 0" in result.err
