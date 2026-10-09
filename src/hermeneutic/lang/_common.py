"""Shared substitution mechanics; risk decisions belong to the English gate."""

from __future__ import annotations

import re
from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import chain

Mapping = Sequence[tuple[re.Pattern[str], str]]
Span = tuple[int, int]


@dataclass(frozen=True)
class _Segment:
    start: int
    end: int
    source_start: int
    source_end: int
    direct: bool


class SourceMap:
    """Piecewise source coordinates, proportional to replacements, not characters."""

    def __init__(self, length: int = 0):
        self.segments = [_Segment(0, length, 0, length, True)] if length else []
        self.ends = [length] if length else []

    def append(self, segment: _Segment) -> None:
        if segment.start == segment.end:
            return
        if self.segments:
            last = self.segments[-1]
            if last.direct and segment.direct and last.source_end == segment.source_start:
                self.segments[-1] = _Segment(last.start, segment.end, last.source_start, segment.source_end, True)
                self.ends[-1] = segment.end
                return
        self.segments.append(segment)
        self.ends.append(segment.end)

    def origin(self, start: int, end: int) -> Span:
        """Return the original interval for a normalized interval.

        Ordered substitutions retain source order. Copied pieces are linear;
        every replacement character refers to its whole original match.
        """
        if not self.segments:
            return (0, 0)
        if start == end:
            if start == self.ends[-1]:
                return (self.segments[-1].source_end,) * 2
            first = self.segments[bisect_right(self.ends, start)]
            point = first.source_start + start - first.start if first.direct else first.source_start
            return (point, point)
        first = self.segments[bisect_right(self.ends, start)]
        last = self.segments[bisect_left(self.ends, end)]
        source_start = first.source_start + start - first.start if first.direct else first.source_start
        source_end = last.source_start + end - last.start if last.direct else last.source_end
        return source_start, source_end

    def copy_to(self, target: SourceMap, start: int, end: int, offset: int) -> None:
        index = bisect_right(self.ends, start)
        while index < len(self.segments):
            segment = self.segments[index]
            if segment.start >= end:
                break
            left, right = max(start, segment.start), min(end, segment.end)
            source_start = segment.source_start + left - segment.start if segment.direct else segment.source_start
            source_end = segment.source_start + right - segment.start if segment.direct else segment.source_end
            target.append(
                _Segment(offset + left - start, offset + right - start, source_start, source_end, segment.direct)
            )
            index += 1


def substitute(text: str, mappings: Mapping, *, track_spans: bool = False) -> tuple[str, SourceMap]:
    """Apply an ordered map, optionally retaining original-text coordinates.

    Each replacement character points to the original token's entire span.
    This keeps gate hits and telemetry anchored to the caller's draft even
    when a replacement changes its length or several substitutions compose.
    """
    out = text
    spans = SourceMap(len(text) if track_spans else 0)
    for pattern, replacement in mappings:
        if not track_spans:
            out = pattern.sub(replacement, out)
            continue
        matches = pattern.finditer(out)
        first = next(matches, None)
        if first is None:
            continue
        parts: list[str] = []
        new_spans = SourceMap()
        cursor = offset = 0
        for match in chain((first,), matches):
            parts.append(out[cursor : match.start()])
            spans.copy_to(new_spans, cursor, match.start(), offset)
            offset += match.start() - cursor
            value = match.expand(replacement)
            parts.append(value)
            source_start, source_end = spans.origin(match.start(), match.end())
            new_spans.append(_Segment(offset, offset + len(value), source_start, source_end, False))
            offset += len(value)
            cursor = match.end()
        parts.append(out[cursor:])
        spans.copy_to(new_spans, cursor, len(out), offset)
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
