"""Experimental Spanish trigger mapping for the unchanged English gate.

This ordered table substitutes gate vocabulary; it does not translate text
or decide risk. Validation and known limits: ``evals/languages/README.md``.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import lexical_fraction, substitute

# Most-specific first: negative predicates, plans and partials precede triggers.
_RELAY_GAP = "(?:(?!unconfirmed)[^\\n.!?。\\uff01\\uff1f;\\uff1b]){0,30}?"

_AUTO_GAP = (
    '(?:(?!unconfirmed|not yet|next up|remaining|but|\\bno\\b|\\bsin\\b|yo mismo|independiente)'
    '[^\\n.!?。\uff01\uff1f;\uff1b¿¡\\"“”«»]){0,120}?'
)

_MAP: list[tuple[str, str]] = [
    (
        "\\bno\\s+(?:(?:han|ha|habían|había)\\s+)?(?:confirmaron|verificaron|aprobaron|"
        "aprobó|confirmó|verificó|confirmado|verificado|aprobado)\\b",
        " unconfirmed ",
    ),
    (
        "\\bno\\s+(?:(?:está|están|es|son)\\s+)?(?:garantizado|garantizada|definitivamente|absolutamente)\\b",
        " uncertain ",
    ),
    ("\\b(?:no|no se ha|no he|no está|no están|sin)\\s+(?:completado|terminado|corregido|reparado)s?\\b", " not yet "),
    (
        "\\b(?:voy a|vamos a|se va a)\\s+(?:completar|terminar|corregir)\\b|\\b(?:completaré|terminaré|corregiré)\\b",
        " next up ",
    ),
    ("\\b(?:no es seguro|no estoy seguro|no es cierto|incierto|incierta)\\b", " uncertain "),
    ("\\b(?:pero|sin embargo|aunque)\\b", " but "),
    ("\\b(?:quedan|queda|pendiente|pendientes|en curso)\\b", " remaining "),
    ("\\b(?:eso no es|eso es incorrecto|no es eso)\\b", " that's not "),
    ("\\bquise decir\\b", " i meant "),
    # An affirmative automated report explicitly adopted as status/permission.
    (
        '\\b(?:subagente|herramienta de análisis automático)\\b'
        + _AUTO_GAP + '(?:reportó'
        + _AUTO_GAP + '(?:funciona|completad[oa]|terminad[oa])|no encontró nada)'
        + _AUTO_GAP + 'así que'
        + _AUTO_GAP + '(?:doy por cerrad[oa]|está libre de vulnerabilidades|podemos entregar)'
        + _AUTO_GAP
        + r'(?=\s*(?:[.!;,]|$))',
        r" the agents confirmed \g<0>",
    ),
    (
        "\\b(?:completado|terminado|corregido|reparado|implementado|desplegado|completé|terminé|corregí)(?:s)?\\b",
        " completed ",
    ),
    ("\\b(?:aprobado|pasaron|superado)(?:s)?\\b", " passed "),
    ("\\b(?:todos|todas|cada)\\b", " all "),
    ("\\b(?:definitivamente|absolutamente|garantizado|siempre|nunca)\\b", " definitely "),
    ("\\b(?:además|también|de paso)\\b", " additionally "),
    ("\\bagentes?\\b" + _RELAY_GAP + "\\b(?:confirmaron|verificaron|aprobaron)\\b", " the agents confirmed "),
    ("\\bequipo\\b" + _RELAY_GAP + "\\b(?:aprobó|confirmó|verificó)\\b", " the team approved "),
    ("\\b(?:robusto|impecable|listo para producción)\\b", " production-ready "),
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
