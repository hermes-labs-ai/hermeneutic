"""Shared substitution mechanics; risk decisions belong to the English gate."""

from __future__ import annotations

import re
from collections.abc import Sequence

Mapping = Sequence[tuple[re.Pattern[str], str]]
Span = tuple[int, int]


def substitute(text: str, mappings: Mapping, *, track_spans: bool = False) -> tuple[str, list[Span]]:
    """Apply an ordered map, optionally retaining original-text coordinates.

    Each replacement character points to the original token's entire span.
    This keeps gate hits and telemetry anchored to the caller's draft even
    when a replacement changes its length or several substitutions compose.
    """
    out = text
    spans = [(i, i + 1) for i in range(len(text))] if track_spans else []
    for pattern, replacement in mappings:
        if not track_spans:
            out = pattern.sub(replacement, out)
            continue
        parts: list[str] = []
        new_spans: list[Span] = []
        cursor = 0
        for match in pattern.finditer(out):
            parts.append(out[cursor : match.start()])
            new_spans.extend(spans[cursor : match.start()])
            value = match.expand(replacement)
            parts.append(value)
            origins = spans[match.start() : match.end()]
            if origins:
                origin = (min(s[0] for s in origins), max(s[1] for s in origins))
                new_spans.extend([origin] * len(value))
            cursor = match.end()
        parts.append(out[cursor:])
        new_spans.extend(spans[cursor:])
        out, spans = "".join(parts), new_spans
    return out, spans


def script_fraction(text: str, ranges: Sequence[tuple[str, str]], threshold: float) -> bool:
    """Measure script membership among letters, ignoring digits/punctuation."""
    letters = [c for c in text if c.isalpha()]
    count = sum(any(start <= c <= end for start, end in ranges) for c in letters)
    return bool(letters) and count / len(letters) >= threshold


def lexical_fraction(
    text: str, words: frozenset[str], threshold: float, distinctive: frozenset[str] = frozenset()
) -> bool:
    """Latin-script hint: two known words or a distinctive vocabulary token.

    This is a routing heuristic, not language identification. Ambiguous short
    messages require an explicit language selection.
    """
    tokens = re.findall(r"[^\W\d_]+", text.casefold())
    hits = set(tokens) & words
    confident = len(hits) >= 2 or bool(hits & distinctive)
    return confident and sum(t in words for t in tokens) / len(tokens) >= threshold
