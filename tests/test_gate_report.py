"""Structured draft reports preserve policy, coordinates, and privacy."""
from __future__ import annotations

import io
import json
import socket
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from hermeneutic import __version__, check_draft, telemetry
from hermeneutic.cli import main
from hermeneutic.gates.regex import highest_severity
from hermeneutic.lang import deployment_findings

MAPPED = "5개 파일을 수정했습니다."
ENGLISH = "Done — shipped 14 files and all tests pass."


@pytest.mark.parametrize("draft", ["", "Here is the draft for review."])
def test_clean_report(draft):
    report = check_draft(draft)
    assert report.to_dict() == {
        "schema_version": 1,
        "package_version": __version__,
        "requested_language": "en",
        "resolved_language": "en",
        "verdict": "PASS",
        "highest_severity": None,
        "should_block": False,
        "findings": [],
    }


@pytest.mark.parametrize("draft,lang", [
    (ENGLISH, "en"),
    (MAPPED, "auto"),
    (MAPPED + "\n" + ENGLISH, "auto"),
    (MAPPED + "\n" + ENGLISH, "ko"),
    ("요청하신 변경은 아직 검증하지 않았습니다. 다음 단계에서 확인할 예정입니다. " + ENGLISH, "auto"),
    ("A robust implementation.", "en"),
    ("Certainly.", "en"),
    (ENGLISH, "unknown"),
])
def test_report_matches_deployment_findings(draft, lang):
    hits, raw = deployment_findings(draft, lang=lang)
    raw_ids = {(hit.rule_id, hit.start, hit.end, hit.severity) for hit in raw}
    report = check_draft(draft, lang=lang)
    assert report.verdict == ("RISK" if hits else "PASS")
    assert report.highest_severity == highest_severity(hits)
    assert report.should_block == (highest_severity(raw) in ("med", "high"))
    assert len(report.findings) == len(hits)
    for finding, hit in zip(report.findings, hits, strict=True):
        is_raw = (hit.rule_id, hit.start, hit.end, hit.severity) in raw_ids
        assert finding.rule_id == hit.rule_id
        assert finding.severity == hit.severity
        assert finding.description == hit.description
        assert finding.matched_text == hit.matched_text
        assert (finding.start, finding.end) == (hit.start, hit.end)
        assert finding.origin == ("raw_english" if is_raw else "mapped")
        assert finding.blocking == (is_raw and hit.severity in ("med", "high"))


def test_mixed_report_exposes_mapped_advisory_and_english_blocking():
    report = check_draft(MAPPED + "\n" + ENGLISH, lang="auto")
    assert report.requested_language == "auto"
    assert report.resolved_language == "ko"
    assert any(finding.origin == "mapped" and not finding.blocking for finding in report.findings)
    assert any(finding.origin == "raw_english" and finding.blocking for finding in report.findings)
    assert report.should_block is True


def test_low_only_is_risk_without_blocking():
    report = check_draft("A robust implementation.")
    assert report.verdict == "RISK"
    assert report.highest_severity == "low"
    assert report.should_block is False
    assert report.findings[0].origin == "raw_english"
    assert report.findings[0].blocking is False


def test_unknown_language_preserves_english_fallback():
    report = check_draft(ENGLISH, lang="unknown")
    assert report.requested_language == "unknown"
    assert report.resolved_language == "en"
    assert report.should_block


def test_unicode_offsets_and_line_columns_use_codepoints():
    draft = "🙂 e\u0301\n  certainly\nalso ready."
    findings = {finding.rule_id: finding for finding in check_draft(draft).findings}
    certainty = findings["unhedged_certainty"]
    assert certainty.start == draft.index("certainly") == 7
    assert certainty.end == certainty.start + len("certainly")
    assert (certainty.start_line, certainty.start_column) == (2, 3)
    assert (certainty.end_line, certainty.end_column) == (2, 12)
    expansion = findings["scope_expansion"]
    assert (expansion.start_line, expansion.start_column) == (3, 1)
    assert (expansion.end_line, expansion.end_column) == (3, 5)


def test_multiline_span_end_and_crlf_coordinates():
    draft = "🙂\r\nDone\r\n14 files."
    finding = check_draft(draft).findings[0]
    assert (finding.start, finding.end) == (3, 11)
    assert (finding.start_line, finding.start_column) == (2, 1)
    assert (finding.end_line, finding.end_column) == (3, 3)
    assert draft[finding.start:finding.end] == "Done\r\n14"


def test_mapped_coordinates_refer_to_original_text():
    draft = "🙂\n  " + MAPPED
    report = check_draft(draft, lang="ko")
    assert report.findings
    for finding in report.findings:
        assert finding.origin == "mapped"
        assert draft[finding.start:finding.end] == finding.matched_text
        assert finding.start_line == finding.end_line == 2
        assert finding.start_column == finding.start - 1
        assert finding.end_column == finding.end - 1


def test_serialization_omits_text_by_default_and_returns_detached_data():
    draft = "Done — 37 private files."
    report = check_draft(draft)
    serialized = report.to_dict()
    assert "Done" not in json.dumps(serialized)
    assert "matched_text" not in json.dumps(serialized)
    assert "Done" not in repr(report)
    assert report.to_dict(include_text=True)["findings"][0]["matched_text"] == "Done — 37"
    serialized["findings"][0]["rule_id"] = "changed"
    serialized["findings"].clear()
    assert report.findings[0].rule_id == "completion_with_number"
    with pytest.raises(FrozenInstanceError):
        report.verdict = "PASS"
    with pytest.raises(FrozenInstanceError):
        report.findings[0].blocking = False


def test_include_text_preserves_existing_bounded_match():
    draft = "Done " + "x" * 195 + " 14 files."
    finding = check_draft(draft).findings[0]
    assert finding.end - finding.start > 200
    assert finding.to_dict(include_text=True)["matched_text"] == draft[finding.start:finding.start + 200] + "..."
    assert "matched_text" not in finding.to_dict()


@pytest.mark.parametrize("text,lang", [(b"draft", "en"), ("draft", None)])
def test_api_rejects_non_string_arguments(text, lang):
    with pytest.raises(TypeError):
        check_draft(text, lang=lang)


def test_api_has_no_network_corpus_or_telemetry_side_effects(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("draft API must not perform I/O")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(telemetry, "record_gate", forbidden)
    monkeypatch.setenv("HERMENEUTIC_HOME", str(tmp_path / "private-corpus"))
    monkeypatch.setenv(telemetry.ENV_SINK, str(tmp_path / "telemetry.jsonl"))
    assert check_draft(ENGLISH).should_block
    assert check_draft(MAPPED, lang="auto").findings


@pytest.mark.parametrize("draft,lang,code", [
    ("Ready for review.", "en", 0),
    (ENGLISH, "en", 1),
    (MAPPED, "auto", 0),
    (MAPPED + "\n" + ENGLISH, "auto", 1),
    ("A robust implementation.", "en", 0),
])
def test_cli_json_is_one_object_with_same_policy(draft, lang, code, monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(draft))
    assert main(["gate", "--json", "--lang", lang]) == code
    output = capsys.readouterr()
    assert output.err == ""
    assert len(output.out.splitlines()) == 1
    assert json.loads(output.out) == check_draft(draft, lang=lang).to_dict()


def test_cli_include_text_is_explicit(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(ENGLISH))
    assert main(["gate", "--json", "--include-text"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["findings"][0]["matched_text"] == "Done — shipped 14"


def test_cli_include_text_requires_json_before_reading_input(monkeypatch, capsys):
    class UnreadableInput:
        def read(self):
            raise AssertionError("invalid options must not read input")

    monkeypatch.setattr("sys.stdin", UnreadableInput())
    with pytest.raises(SystemExit) as exc:
        main(["gate", "--include-text"])
    assert exc.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "--include-text requires --json" in output.err


@pytest.mark.parametrize("kind,expected", [
    ("missing", "input_not_found"),
    ("directory", "input_is_directory"),
    ("non_utf8", "input_not_utf8"),
    ("permission", "input_unreadable"),
])
def test_cli_json_input_errors_are_structured_and_private(kind, expected, tmp_path, monkeypatch, capsys):
    private_marker = "private-input-do-not-echo"
    draft = tmp_path / private_marker
    if kind == "directory":
        draft.mkdir()
    elif kind == "non_utf8":
        draft.write_bytes(private_marker.encode() + b"\xff")
    elif kind == "permission":
        def denied(*args, **kwargs):
            raise PermissionError(private_marker)
        monkeypatch.setattr(Path, "read_text", denied)
    assert main(["gate", "--json", "--draft", str(draft)]) == 2
    output = capsys.readouterr()
    result = json.loads(output.out)
    assert result["schema_version"] == 1
    assert result["package_version"] == __version__
    assert result["verdict"] == "ERROR"
    assert result["error"]["code"] == expected
    assert result["findings"] == []
    assert result["resolved_language"] is None
    assert result["highest_severity"] is None
    assert result["should_block"] is None
    assert private_marker not in output.out + output.err
    assert output.err == ""


def test_cli_json_invalid_utf8_stdin(monkeypatch, capsys):
    source = io.TextIOWrapper(io.BytesIO(b"private-input\xff"), encoding="utf-8")
    monkeypatch.setattr("sys.stdin", source)
    assert main(["gate", "--json"]) == 2
    output = capsys.readouterr()
    assert json.loads(output.out)["error"]["code"] == "input_not_utf8"
    assert "private-input" not in output.out + output.err


def test_cli_json_invalid_utf8_stdin_surrogateescape(monkeypatch, capsys):
    source = io.TextIOWrapper(io.BytesIO(b"private-input\xff"), encoding="utf-8", errors="surrogateescape")
    monkeypatch.setattr("sys.stdin", source)
    assert main(["gate", "--json"]) == 2
    output = capsys.readouterr()
    assert json.loads(output.out)["error"]["code"] == "input_not_utf8"
    assert "private-input" not in output.out + output.err


@pytest.mark.parametrize("mode", ["none", "raw"])
def test_cli_json_preserves_opt_in_telemetry(mode, tmp_path, monkeypatch, capsys):
    sink = tmp_path / "telemetry.jsonl"
    monkeypatch.setenv(telemetry.ENV_SINK, str(sink))
    monkeypatch.setenv(telemetry.ENV_CONTEXT, mode)
    monkeypatch.setattr("sys.stdin", io.StringIO(ENGLISH))
    assert main(["gate", "--json"]) == 1
    result = json.loads(capsys.readouterr().out)
    assert "matched_text" not in result["findings"][0]
    recorded = json.loads(sink.read_text())
    assert recorded["verdict"] == result["verdict"]
    assert recorded["severity"] == result["highest_severity"]
    assert recorded["rule_ids"] == [finding["rule_id"] for finding in result["findings"]]
    assert recorded["draft_len"] == len(ENGLISH)
    assert ("audit" in recorded) == (mode == "raw")
    if mode == "raw":
        assert recorded["audit"][0]["matched"] == "Done — shipped 14"


def test_cli_json_does_not_enable_telemetry(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv(telemetry.ENV_SINK, raising=False)
    monkeypatch.setattr("sys.stdin", io.StringIO(ENGLISH))
    assert main(["gate", "--json"]) == 1
    capsys.readouterr()
    assert telemetry.sink_path() is None
    assert list(tmp_path.iterdir()) == []
