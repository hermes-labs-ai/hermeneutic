# Structured draft checks

`check_draft` and `hermeneutic gate --json` expose the deterministic gate's
findings and deployment policy. They do not call an LLM, retrieve correction
memory, or read a personal correction corpus.

```python
from hermeneutic import check_draft

report = check_draft("Draft ready for review.")
payload = report.to_dict()
if report.should_block:
    # Ask the draft's author to review the findings.
    pass
```

`check_draft(text: str, lang: str = "en") -> DraftReport` returns a frozen
dataclass with a tuple of frozen `DraftFinding` values. `DraftReport` and
`DraftFinding` are public exports. The report retains bounded matched strings,
but does not retain the full draft. `to_dict()` returns a detached JSON-ready
dictionary and omits matched strings by default. `repr(report)` also omits them.
Pass `include_text=True` to include each finding's `matched_text`.

```sh
hermeneutic gate --json --draft draft.txt
hermeneutic gate --json --lang auto --draft draft.txt
hermeneutic gate --json --include-text --draft draft.txt
printf '%s' 'Draft ready for review.' | hermeneutic gate --json
```

The JSON command writes one object to stdout without human status lines. It
exits `0` for a pass or advisory findings, `1` when `should_block` is true, and
`2` for unreadable input. `--include-text` requires `--json`. The existing human
output is still the default.

## Schema version 1

The successful report object contains these fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | `1`; the report format version, independent of package releases. |
| `package_version` | string | Version of the package producing the report. |
| `requested_language` | string | The caller's language argument; the default is `en`. |
| `resolved_language` | string | The language adapter actually selected. |
| `verdict` | string | `PASS` when no findings matched; otherwise `RISK`. |
| `highest_severity` | string or null | `low`, `med`, or `high`; null when there are no findings. |
| `should_block` | boolean | Whether a raw English medium/high finding is present. |
| `findings` | array | Finding objects in the underlying deployment scorer's order. |

Each finding has these fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `rule_id` | string | Canonical English rule identifier. |
| `severity` | string | Diagnostic severity: `low`, `med`, or `high`. |
| `description` | string | Static explanation of the rule. |
| `origin` | string | `raw_english` if the same rule, severity, and source span matched the raw English gate; otherwise `mapped`. |
| `blocking` | boolean | True only for a raw English medium/high finding. |
| `start`, `end` | integer | Zero-based Unicode codepoint offsets in the scanned draft; `end` is exclusive. |
| `start_line`, `start_column` | integer | One-based source position of `start`. |
| `end_line`, `end_column` | integer | One-based source position of the exclusive `end`. |
| `matched_text` | string, opt-in | Original source match, included only with `include_text=True` or `--include-text`. |

Codepoints are Python string characters, not UTF-8 bytes, UTF-16 code units, or
display widths. A combining mark counts separately; an emoji may occupy more
than one display column. A newline (`\n`) begins a new line. The CLI uses its
existing text reader, which normalizes file CRLF line endings before scanning.
Mapped findings use the original draft's coordinates rather than normalized
English vocabulary. Matches longer than the scorer's existing text limit are
truncated to the first 200 codepoints followed by `...`; coordinates still cover
the full match.

`RISK` describes a finding, not an automatic rejection. Raw English low-severity
findings and mapped findings at any severity remain advisory. Raw English
medium/high findings retain their enforcement when mixed with another language.
Per-finding `blocking` and report-level `should_block` express this policy;
`highest_severity` alone is insufficient to decide whether to reject a draft.
These language mappings remain experimental and do not establish real-language
coverage.

`lang="auto"` uses the existing conservative language router. Python callers
passing an unknown language code get the existing English fallback, with that
code preserved in `requested_language` and `en` in `resolved_language`. The CLI
accepts only its documented language choices.

## Input errors and privacy

On a draft read failure in JSON mode, stdout contains the same metadata fields
with `verdict: "ERROR"`, null `resolved_language`, null `highest_severity`, null
`should_block`, an empty `findings` array, and an `error` object:

```json
{"schema_version":1,"package_version":"<installed version>","requested_language":"en","resolved_language":null,"verdict":"ERROR","highest_severity":null,"should_block":null,"findings":[],"error":{"code":"input_not_found","message":"Draft file not found."}}
```

Error codes are `input_not_found`, `input_is_directory`, `input_not_utf8`, and
`input_unreadable` (including permission failures). Error messages omit the
input path, draft contents, and raw exception text. Invalid command-line options
still use argparse's stderr error and exit `2`; they are not draft reports.
Consumers must handle `ERROR` before evaluating `should_block`.

The Python API performs no telemetry I/O. The CLI preserves the existing opt-in
`HERMENEUTIC_TELEMETRY` behavior: JSON mode does not enable a sink or raw context.
If a caller has separately enabled `HERMENEUTIC_TELEMETRY_CONTEXT=raw`, that sink
can retain draft windows even when stdout omits matched text. Review that setting
when processing private drafts. Text-free reports still reveal rule types,
language routing, and locations; they are data minimization, not anonymization.
