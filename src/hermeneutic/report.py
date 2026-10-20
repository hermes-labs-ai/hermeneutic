"""Structured, text-minimized reports from the deterministic draft gate."""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field

from hermeneutic.gates.regex import highest_severity
from hermeneutic.lang import LANGS, deployment_findings, detect


@dataclass(frozen=True)
class DraftFinding:
    """One finding in original Unicode codepoint coordinates.

    Offsets are zero-based and end-exclusive. Lines and columns are one-based;
    the end position is also exclusive. ``matched_text`` follows the scorer's
    existing truncation and is omitted from serialization unless requested.
    """

    rule_id: str
    severity: str
    description: str
    origin: str
    blocking: bool
    start: int
    end: int
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    matched_text: str = field(repr=False)

    def to_dict(self, include_text: bool = False) -> dict:
        """Return a detached dictionary, with matched text only by opt-in."""
        result = {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "description": self.description,
            "origin": self.origin,
            "blocking": self.blocking,
            "start": self.start,
            "end": self.end,
            "start_line": self.start_line,
            "start_column": self.start_column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }
        if include_text:
            result["matched_text"] = self.matched_text
        return result


@dataclass(frozen=True)
class DraftReport:
    """Immutable result of a local draft check; no full draft is retained."""

    schema_version: int
    package_version: str
    requested_language: str
    resolved_language: str
    verdict: str
    highest_severity: str | None
    should_block: bool
    findings: tuple[DraftFinding, ...]

    def to_dict(self, include_text: bool = False) -> dict:
        """Return JSON-ready data without draft snippets by default."""
        return {
            "schema_version": self.schema_version,
            "package_version": self.package_version,
            "requested_language": self.requested_language,
            "resolved_language": self.resolved_language,
            "verdict": self.verdict,
            "highest_severity": self.highest_severity,
            "should_block": self.should_block,
            "findings": [finding.to_dict(include_text=include_text) for finding in self.findings],
        }


def check_draft(text: str, lang: str = "en") -> DraftReport:
    """Check text locally, preserving the shipped deployment policy.

    Raw English medium/high findings block; low English findings and mapped
    findings remain advisory. ``auto`` uses the existing conservative router;
    unknown codes fall back to English, as in ``deployment_findings``. This
    function performs no I/O, inference, telemetry, or corpus retrieval.
    """
    from hermeneutic import __version__

    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not isinstance(lang, str):
        raise TypeError("lang must be a string")
    resolved = detect(text) if lang == "auto" else lang
    if resolved not in LANGS:
        resolved = "en"
    hits, raw_english = deployment_findings(text, lang=resolved)
    raw_identities = {(hit.rule_id, hit.start, hit.end, hit.severity) for hit in raw_english}
    line_starts = [0, *(index + 1 for index, char in enumerate(text) if char == "\n")]

    def position(offset: int) -> tuple[int, int]:
        line = bisect_right(line_starts, offset)
        return line, offset - line_starts[line - 1] + 1

    findings = []
    for hit in hits:
        raw = (hit.rule_id, hit.start, hit.end, hit.severity) in raw_identities
        start_line, start_column = position(hit.start)
        end_line, end_column = position(hit.end)
        findings.append(DraftFinding(
            rule_id=hit.rule_id,
            severity=hit.severity,
            description=hit.description,
            origin="raw_english" if raw else "mapped",
            blocking=raw and hit.severity in ("med", "high"),
            start=hit.start,
            end=hit.end,
            start_line=start_line,
            start_column=start_column,
            end_line=end_line,
            end_column=end_column,
            matched_text=hit.matched_text,
        ))
    return DraftReport(
        schema_version=1,
        package_version=__version__,
        requested_language=lang,
        resolved_language=resolved,
        verdict="RISK" if hits else "PASS",
        highest_severity=highest_severity(hits),
        should_block=any(finding.blocking for finding in findings),
        findings=tuple(findings),
    )
