"""Experimental Portuguese trigger mapping for the unchanged English gate.

This ordered table substitutes gate vocabulary; it does not translate text
or decide risk. Validation and known limits: ``evals/languages/README.md``.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import lexical_fraction, substitute

# Most-specific first: negative predicates, plans and partials precede triggers.
_RELAY_GAP = "(?:(?!unconfirmed)[^\\n.!?。\\uff01\\uff1f;\\uff1b]){0,30}?"

_MAP: list[tuple[str, str]] = [
    ("\\bnão\\s+(?:confirmaram|verificaram|aprovaram|aprovou|confirmou|verificou)\\b", " unconfirmed "),
    (
        "\\bnão\\s+(?:(?:estão|está|são|é|foram|foi)\\s+)?(?:concluíd[oa]s?|"
        "terminad[oa]s?|corrigid[oa]s?|aprovad[oa]s?|passaram)\\b",
        " not yet ",
    ),
    ("\\bnão\\s+(?:(?:estão|está|são|é)\\s+)?(?:garantid[oa]s?|definitivamente|absolutamente)\\b", " uncertain "),
    (
        "\\b(?:não|não foi|não está|não foram)\\s+(?:concluído|concluída|terminado|corrigido|corrigida)s?\\b",
        " not yet ",
    ),
    (
        "\\b(?:vou|vamos|vai)\\s+(?:concluir|terminar|corrigir)\\b|\\b(?:concluirei|terminarei|corrigirei)\\b",
        " next up ",
    ),
    ("\\b(?:não é certo|não tenho certeza|não é garantido|incerto|incerta)\\b", " uncertain "),
    ("\\b(?:mas|porém|no entanto|embora)\\b", " but "),
    ("\\b(?:restam|resta|pendente|pendentes|em andamento)\\b", " remaining "),
    ("\\b(?:isso não é|isso está errado|não é isso)\\b", " that's not "),
    ("\\beu quis dizer\\b", " i meant "),
    (
        "\\b(?:concluído|concluída|terminado|terminada|corrigido|corrigida|reparado|"
        "implementado|implantado|concluí|terminei)(?:s)?\\b",
        " completed ",
    ),
    ("\\b(?:aprovado|aprovada|passaram)(?:s)?\\b", " passed "),
    ("\\b(?:todos|todas|cada)\\b", " all "),
    ("\\b(?:definitivamente|absolutamente|garantido|garantida|sempre|nunca)\\b", " definitely "),
    ("\\b(?:além disso|também|adicionalmente)\\b", " additionally "),
    ("\\bagentes?\\b" + _RELAY_GAP + "\\b(?:confirmaram|verificaram|aprovaram)\\b", " the agents confirmed "),
    ("\\bequipe\\b" + _RELAY_GAP + "\\b(?:aprovou|confirmou|verificou)\\b", " the team approved "),
    ("\\b(?:robusto|impecável|pronto para produção)\\b", " production-ready "),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in _MAP]


def normalize(text: str) -> str:
    """Map load-bearing tokens while preserving unmapped text and digits."""
    return substitute(text or "", _COMPILED)[0]


_WORDS = frozenset(
    [
        "eu",
        "nós",
        "foi",
        "foram",
        "os",
        "as",
        "o",
        "a",
        "e",
        "arquivos",
        "concluído",
        "corrigido",
        "todos",
        "todas",
        "definitivamente",
        "sempre",
        "além",
        "também",
        "agentes",
        "confirmaram",
        "equipe",
        "mas",
        "restam",
        "não",
        "amanhã",
        "testes",
    ]
)


_DISTINCTIVE = frozenset(
    {
        "arquivos",
        "concluído",
        "concluídos",
        "concluída",
        "concluídas",
        "corrigido",
        "corrigidos",
        "implantado",
        "concluí",
        "terminei",
        "passaram",
        "sempre",
        "além",
        "também",
        "equipe",
        "confirmaram",
        "verificaram",
        "aprovaram",
        "aprovou",
        "impecável",
        "produção",
    }
)
_WORDS = _WORDS | _DISTINCTIVE

_WORDS = _WORDS | frozenset(
    {
        "isso",
        "é",
        "módulos",
        "serviços",
        "tarefas",
        "estão",
        "prontas",
        "implementados",
        "implantados",
        "terminadas",
        "funciona",
        "seguro",
        "falhará",
    }
)


def is_dominant(text: str, threshold: float = 0.2) -> bool:
    """Vocabulary hint; shared or ambiguous tokens still need other context."""
    return lexical_fraction(text, _WORDS, threshold, _DISTINCTIVE)
