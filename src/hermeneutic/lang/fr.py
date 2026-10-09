"""Experimental French trigger mapping for the unchanged English gate.

This ordered table substitutes gate vocabulary; it does not translate text
or decide risk. Validation and known limits: ``evals/languages/README.md``.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import lexical_fraction, substitute

# Most-specific first: tense, negation and partial-progress guards precede triggers.
_MAP: list[tuple[str, str]] = [
    (
        "\\b(?:pas encore|pas|non)\\s+(?:terminé(?:e|s|es)?|corrigé(?:e|s|es)?|achevé(?:e|s|es)?)\\b",
        " not yet ",
    ),
    (
        "\\b(?:vais|allons|va|vont)\\s+(?:terminer|corriger|achever)\\b|\\b(?:terminerai|corrigerai|terminerons)\\b",
        " next up ",
    ),
    (
        "\\b(?:pas certain|pas certaine|pas sûr|pas sûre|incertain|incertaine)\\b",
        " uncertain ",
    ),
    (
        "\\b(?:mais|cependant|pourtant)\\b",
        " but ",
    ),
    (
        "\\b(?:reste|restent|restant|en cours)\\b",
        " remaining ",
    ),
    (
        "\\b(?:ce n['\u2019]est pas|c['\u2019]est faux)\\b",
        " that's not ",
    ),
    (
        "\\bje voulais dire\\b",
        " i meant ",
    ),
    (
        "\\b(?:terminé|achevé|corrigé|réparé|déployé|implémenté|fini)(?:e|s|es)?\\b",
        " completed ",
    ),
    (
        "\\b(?:réussi|validé)(?:e|s|es)?\\b",
        " passed ",
    ),
    (
        "\\b(?:tous|toutes|chaque)\\b",
        " all ",
    ),
    (
        "\\b(?:certainement|absolument|garanti|garantie|toujours|jamais)\\b",
        " definitely ",
    ),
    (
        "\\b(?:également|en plus|de plus|aussi)\\b",
        " additionally ",
    ),
    (
        "\\bagents?\\b.{0,30}?\\b(?:confirmé|vérifié|approuvé)\\b",
        " the agents confirmed ",
    ),
    (
        "\\béquipe\\b.{0,30}?\\b(?:approuvé|confirmé|vérifié)\\b",
        " the team approved ",
    ),
    (
        "\\b(?:robuste|sans faille|prêt pour la production)\\b",
        " production-ready ",
    ),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in _MAP]


def normalize(text: str) -> str:
    """Map load-bearing tokens while preserving unmapped text and digits."""
    return substitute(text or "", _COMPILED)[0]


_WORDS = frozenset(
    [
        "je",
        "nous",
        "ai",
        "avons",
        "les",
        "des",
        "le",
        "la",
        "et",
        "fichiers",
        "terminé",
        "terminés",
        "corrigé",
        "tous",
        "toutes",
        "certainement",
        "absolument",
        "également",
        "agents",
        "confirmé",
        "équipe",
        "mais",
        "encore",
        "pas",
        "demain",
    ]
)


_DISTINCTIVE = frozenset(
    {
        "terminé",
        "terminés",
        "terminée",
        "terminées",
        "achevé",
        "achevés",
        "corrigé",
        "corrigés",
        "réparé",
        "déployé",
        "implémenté",
        "certainement",
        "absolument",
        "garanti",
        "garantie",
        "également",
        "équipe",
        "approuvé",
        "vérifié",
        "confirmé",
        "robuste",
    }
)
_WORDS = _WORDS | _DISTINCTIVE

_WORDS = _WORDS | frozenset(
    {
        "sont",
        "ont",
        "été",
        "erreurs",
        "tâches",
        "modules",
        "services",
        "tests",
        "corrigées",
        "implémentés",
        "déployés",
        "achevées",
        "validés",
    }
)


def is_dominant(text: str, threshold: float = 0.2) -> bool:
    """Vocabulary hint; shared or ambiguous tokens still need other context."""
    return lexical_fraction(text, _WORDS, threshold, _DISTINCTIVE)
