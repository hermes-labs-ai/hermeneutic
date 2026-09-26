"""Check latest CHANGELOG test-count claims against pytest collection."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _pytest_collected_count() -> int:
    """Run `pytest --collect-only -q` and parse the trailing count line."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=REPO_ROOT,
        env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )
    # Last non-empty line is "N tests collected in X.XXs"
    for line in reversed(out.stdout.strip().splitlines()):
        line = line.strip()
        m = re.match(r"(\d+)\s+tests?\s+collected", line)
        if m:
            return int(m.group(1))
    raise RuntimeError(
        f"could not parse pytest --collect-only output:\n{out.stdout}\n---\n{out.stderr}"
    )


def _changelog_test_count_claim() -> int | None:
    """Extract the test-count claim from the LATEST CHANGELOG entry.

    Reads from the first '## [' header to the next '## [' header. Returns
    None if the latest entry makes no numeric tests claim (acceptable).
    """
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    # Find the first '## [' header and the next one
    headers = list(re.finditer(r"^## \[", text, re.MULTILINE))
    if len(headers) < 1:
        return None
    start = headers[0].start()
    end = headers[1].start() if len(headers) >= 2 else len(text)
    section = text[start:end]
    m = re.search(r"(\d+)\s+tests?\b", section)
    return int(m.group(1)) if m else None


def test_changelog_test_count_matches_pytest_collection():
    """Latest CHANGELOG entry's test count claim must equal pytest collection.

    If this fails, update CHANGELOG.md's most-recent version entry.
    """
    actual = _pytest_collected_count()
    claimed = _changelog_test_count_claim()
    if claimed is None:
        pytest.skip(
            "Latest CHANGELOG entry does not claim a test count "
            "(acceptable; gate is opt-in per entry)"
        )
    assert claimed == actual, (
        f"\n\nLatest CHANGELOG entry claims {claimed} tests; "
        f"pytest --collect-only returns {actual}.\n"
        f"Fix: update CHANGELOG.md's most-recent version entry to cite "
        f"'{actual} tests'.\n"
    )


def test_cline_known_bad_recipe_is_not_published_as_ready():
    document = (REPO_ROOT / "integrations" / "cline.md").read_text(encoding="utf-8")
    assert "Maturity: `REMOVE`" in document
    assert "tool_name" in document and "obsolete" in document
    assert 'case "$verdict" in' not in document
    assert "RISK*)" not in document
