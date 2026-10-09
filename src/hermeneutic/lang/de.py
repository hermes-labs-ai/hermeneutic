"""Experimental German trigger mapping for the unchanged English gate.

This ordered table substitutes gate vocabulary; it does not translate text
or decide risk. Validation and known limits: ``evals/languages/README.md``.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import lexical_fraction, substitute

# Most-specific first: tense, negation and partial-progress guards precede triggers.
_MAP: list[tuple[str, str]] = [
    (
        "\\b(?:nicht|noch nicht)\\s+(?:abgeschlossen|fertig|behoben|korrigiert)\\b",
        " not yet ",
    ),
    (
        "\\b(?:werde|werden|wird)\\b.{0,35}?\\b(?:abschließen|abgeschlossen|beheben|behoben|fertigstellen)\\b",
        " next up ",
    ),
    (
        "\\b(?:nicht sicher|nicht garantiert|nicht absolut|unsicher)\\b",
        " uncertain ",
    ),
    (
        "\\b(?:aber|jedoch|allerdings)\\b",
        " but ",
    ),
    (
        "\\b(?:verbleiben|verbleibend|übrig|noch offen|in arbeit)\\b",
        " remaining ",
    ),
    (
        "\\b(?:das ist falsch|das stimmt nicht|nicht das)\\b",
        " that's not ",
    ),
    (
        "\\bich meinte\\b",
        " i meant ",
    ),
    (
        "\\b(?:abgeschlossen|fertiggestellt|behoben|korrigiert|implementiert|ausgeliefert)\\b",
        " completed ",
    ),
    (
        "\\bbestanden\\b",
        " passed ",
    ),
    (
        "\\b(?:alle|alles|sämtliche|jede|jeder|jedes)\\b",
        " all ",
    ),
    (
        "\\b(?:definitiv|garantiert|absolut|zweifellos|immer|niemals)\\b",
        " definitely ",
    ),
    (
        "\\b(?:zusätzlich|außerdem|nebenbei)\\b",
        " additionally ",
    ),
    (
        "\\b(?:agenten|unteragenten).{0,30}?\\b(?:bestätigt|geprüft|zugestimmt)\\b",
        " the agents confirmed ",
    ),
    (
        "\\bteam\\b.{0,30}?\\b(?:genehmigt|bestätigt|geprüft)\\b",
        " the team approved ",
    ),
    (
        "\\b(?:nahtlos|robust|produktionsreif)\\b",
        " production-ready ",
    ),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in _MAP]


def normalize(text: str) -> str:
    """Map load-bearing tokens while preserving unmapped text and digits."""
    return substitute(text or "", _COMPILED)[0]


_WORDS = frozenset(
    [
        "ich",
        "habe",
        "haben",
        "wurde",
        "wurden",
        "die",
        "der",
        "das",
        "und",
        "datei",
        "dateien",
        "tests",
        "alle",
        "abgeschlossen",
        "behoben",
        "korrigiert",
        "definitiv",
        "garantiert",
        "außerdem",
        "zusätzlich",
        "agenten",
        "bestätigt",
        "team",
        "aber",
        "noch",
        "nicht",
    ]
)


_DISTINCTIVE = frozenset(
    {
        "abgeschlossen",
        "fertiggestellt",
        "behoben",
        "korrigiert",
        "implementiert",
        "ausgeliefert",
        "bestanden",
        "definitiv",
        "garantiert",
        "zweifellos",
        "niemals",
        "zusätzlich",
        "außerdem",
        "nebenbei",
        "agenten",
        "unteragenten",
        "bestätigt",
        "genehmigt",
        "produktionsreif",
    }
)
_WORDS = _WORDS | _DISTINCTIVE


def is_dominant(text: str, threshold: float = 0.2) -> bool:
    """Vocabulary hint; shared or ambiguous tokens still need other context."""
    return lexical_fraction(text, _WORDS, threshold, _DISTINCTIVE)
