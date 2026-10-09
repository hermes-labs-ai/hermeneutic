"""Experimental Spanish trigger mapping for the unchanged English gate.

This ordered table substitutes gate vocabulary; it does not translate text
or decide risk. Validation and known limits: ``evals/languages/README.md``.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import lexical_fraction, substitute

# Most-specific first: tense, negation and partial-progress guards precede triggers.
_MAP: list[tuple[str, str]] = [
    (
        "\\b(?:no|no se ha|no he|no está|sin)\\s+(?:completado|terminado|corregido|reparado)\\b",
        " not yet ",
    ),
    (
        "\\b(?:voy a|vamos a|se va a)\\s+(?:completar|terminar|corregir)\\b|\\b(?:completaré|terminaré|corregiré)\\b",
        " next up ",
    ),
    (
        "\\b(?:no es seguro|no estoy seguro|no es cierto|incierto|incierta)\\b",
        " uncertain ",
    ),
    (
        "\\b(?:pero|sin embargo|aunque)\\b",
        " but ",
    ),
    (
        "\\b(?:quedan|queda|pendiente|pendientes|en curso)\\b",
        " remaining ",
    ),
    (
        "\\b(?:eso no es|eso es incorrecto|no es eso)\\b",
        " that's not ",
    ),
    (
        "\\bquise decir\\b",
        " i meant ",
    ),
    (
        "\\b(?:completado|terminado|corregido|reparado|implementado|desplegado|completé|terminé|corregí)(?:s)?\\b",
        " completed ",
    ),
    (
        "\\b(?:aprobado|pasaron|superado)(?:s)?\\b",
        " passed ",
    ),
    (
        "\\b(?:todos|todas|cada)\\b",
        " all ",
    ),
    (
        "\\b(?:definitivamente|absolutamente|garantizado|siempre|nunca)\\b",
        " definitely ",
    ),
    (
        "\\b(?:además|también|de paso)\\b",
        " additionally ",
    ),
    (
        "\\bagentes?\\b.{0,30}?\\b(?:confirmaron|verificaron|aprobaron)\\b",
        " the agents confirmed ",
    ),
    (
        "\\bequipo\\b.{0,30}?\\b(?:aprobó|confirmó|verificó)\\b",
        " the team approved ",
    ),
    (
        "\\b(?:robusto|impecable|listo para producción)\\b",
        " production-ready ",
    ),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in _MAP]


def normalize(text: str) -> str:
    """Map load-bearing tokens while preserving unmapped text and digits."""
    return substitute(text or "", _COMPILED)[0]


_WORDS = frozenset(
    [
        "he",
        "hemos",
        "han",
        "el",
        "la",
        "los",
        "las",
        "y",
        "archivos",
        "completado",
        "terminado",
        "corregido",
        "todos",
        "todas",
        "definitivamente",
        "además",
        "también",
        "agentes",
        "confirmaron",
        "equipo",
        "pero",
        "quedan",
        "no",
        "mañana",
        "pruebas",
    ]
)


_DISTINCTIVE = frozenset(
    {
        "archivos",
        "completado",
        "corregido",
        "implementado",
        "desplegado",
        "completé",
        "terminé",
        "corregí",
        "pasaron",
        "siempre",
        "además",
        "también",
        "equipo",
        "confirmaron",
        "verificaron",
        "aprobaron",
        "aprobó",
        "impecable",
        "producción",
    }
)
_WORDS = _WORDS | _DISTINCTIVE

_WORDS = _WORDS | frozenset(
    {
        "esto",
        "es",
        "errores",
        "fueron",
        "corregidos",
        "módulos",
        "están",
        "implementados",
        "servicios",
        "desplegados",
        "funciona",
        "seguro",
        "fallará",
    }
)


def is_dominant(text: str, threshold: float = 0.2) -> bool:
    """Vocabulary hint; shared or ambiguous tokens still need other context."""
    return lexical_fraction(text, _WORDS, threshold, _DISTINCTIVE)
