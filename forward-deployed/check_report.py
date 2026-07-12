#!/usr/bin/env python3
"""Leak-lint a forward-deployed report before it leaves the machine.

    python3 forward-deployed/check_report.py FORWARD-DEPLOYED-REPORT.md

Enforces the report's sanitization rule the same way ``--sanitized``
enforces the harvest's: mechanically, not on trust. Flags lines that look
like they carry environment or session content:

- absolute paths outside this repository (``/Users/...``, ``/home/...``, ``C:\\...``)
- home-relative paths that aren't this repo (``~/projects/...``)
- email addresses and phone-number shapes (the author's contact address is allowed)
- session-log filenames (``rollout-*.jsonl`` with timestamps)
- long quoted strings (>120 chars inside quotes — likely pasted content)
- Hangul runs longer than 40 chars (short Korean examples from this repo's
  own corpora and docs are fine; long runs look like session text)

Exit 0: clean. Exit 1: review the flagged lines — a human decides; this
tool only points. Stdlib only, no network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_CONTACTS = {"roli@hermes-labs.ai"}

CHECKS = [
    ("out-of-repo absolute path",
     re.compile(r"(?:^|[\s'\"(=])(/(?:Users|home|var|opt|private)/[^\s'\")]+|[A-Za-z]:\\[^\s'\")]+)")),
    # ~/.hermeneutic and ~/.codex/sessions are this package's own documented
    # defaults (category, not content) — anything else home-relative flags.
    ("home-relative path", re.compile(r"~/(?!\.hermeneutic\b|\.codex/sessions\b)[^\s'\")]+")),
    ("email address", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("phone-number shape", re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{8,}\d)(?!\d)")),
    ("session-log filename", re.compile(r"rollout-[\w.-]*\.jsonl|\d{4}-\d{2}-\d{2}T[\d:.-]+\.jsonl")),
    ("long quoted string", re.compile(r"[\"“'‘]([^\"”'’]{120,})[\"”'’]")),  # noqa: RUF001 — smart quotes intended
    ("long Hangul run", re.compile(r"[가-힣][가-힣\s.,!?0-9%()~-]{40,}")),
]


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"ERROR: no such file: {path.name}", file=sys.stderr)
        return 2

    flags: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for label, rx in CHECKS:
            m = rx.search(line)
            if not m:
                continue
            if label == "email address" and m.group(0).lower() in ALLOWED_CONTACTS:
                continue
            # ISO dates/timestamps are honest report content, not phone numbers
            if label == "phone-number shape" and re.search(r"\d{4}-\d{2}-\d{2}", m.group(0)):
                continue
            flags.append((lineno, label, line.strip()[:120]))
            break

    if not flags:
        print(f"CLEAN — {path.name} carries no recognizable environment or session content.")
        return 0
    print(f"REVIEW NEEDED — {len(flags)} line(s) look like they carry environment/session content:")
    for lineno, label, snippet in flags:
        print(f"  line {lineno:4d}  [{label}]  {snippet}")
    print("\nA human decides — edit or approve deliberately, then re-run.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
