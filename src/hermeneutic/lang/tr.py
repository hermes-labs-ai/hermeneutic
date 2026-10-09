"""Experimental Turkish trigger mapping for the unchanged English gate.

This ordered table substitutes gate vocabulary; it does not translate text
or decide risk. Validation and known limits: ``evals/languages/README.md``.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import lexical_fraction, substitute

# Most-specific first: negative predicates, plans and partials precede triggers.
_RELAY_GAP = "(?:(?!unconfirmed)[^\\n.!?。\\uff01\\uff1f;\\uff1b]){0,30}?"

_MAP: list[tuple[str, str]] = [
    ("\\bkesin(?:likle)?\\s+(?:emin\\s+)?değil(?:im|iz)?\\b", " uncertain "),
    ("\\b(?:tamamlanmad\u0131|bitmedi|düzeltilmedi|tamamlamad\u0131m)\\b", " not yet "),
    ("\\b(?:tamamlayacağ\u0131m|düzelteceğim|tamamlanacak|düzeltilecek)\\b", " next up "),
    ("\\b(?:kesin değil|emin değilim|kesinlikle değil)\\b", " uncertain "),
    ("\\b(?:ama|ancak|fakat)\\b", " but "),
    ("\\b(?:kald\u0131|kalan|bekliyor|devam ediyor)\\b", " remaining "),
    ("\\b(?:yanl\u0131ş|öyle değil|bu değil)\\b", " that's not "),
    ("\\bdemek istediğim\\b", " i meant "),
    (
        "\\b(?:tamamland\u0131|tamamlad\u0131m|tamamlad\u0131k|bitirdim|bitti|düzeltildi|düzelttim|uyguland\u0131|dağ\u0131t\u0131ld\u0131)\\b",
        " completed ",
    ),
    ("\\b(?:geçti|geçildi)\\b", " passed "),
    ("\\b(?:tüm|hepsi|bütün)\\b", " all "),
    ("\\b(?:kesinlikle|kesin|mutlaka|asla|daima)\\b", " definitely "),
    ("\\b(?:ayr\u0131ca|ek olarak|bu arada)\\b", " additionally "),
    (
        "\\b(?:ajanlar|ajan|alt ajan)" + _RELAY_GAP + "(?:doğrulad\u0131|onaylad\u0131|onaylad\u0131lar)\\b",
        " the agents confirmed ",
    ),
    ("\\b(?:ekip|tak\u0131m)" + _RELAY_GAP + "(?:onaylad\u0131|doğrulad\u0131)\\b", " the team approved "),
    ("\\b(?:kusursuz|sağlam|üretime haz\u0131r)\\b", " production-ready "),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in _MAP]


def normalize(text: str) -> str:
    """Map load-bearing tokens while preserving unmapped text and digits."""
    return substitute(text or "", _COMPILED)[0]


_WORDS = frozenset(
    [
        "bir",
        "bu",
        "ve",
        "dosya",
        "dosyalar",
        "test",
        "testler",
        "tüm",
        "hepsi",
        "bütün",
        "tamamland\u0131",
        "tamamlad\u0131m",
        "düzelttim",
        "düzeltildi",
        "kesinlikle",
        "kesin",
        "mutlaka",
        "ayr\u0131ca",
        "ajanlar",
        "ekip",
        "ama",
        "kald\u0131",
        "değil",
        "yar\u0131n",
        "için",
    ]
)


_DISTINCTIVE = frozenset(
    {
        "tamamland\u0131",
        "tamamlad\u0131m",
        "tamamlad\u0131k",
        "tamamlanmad\u0131",
        "düzeltildi",
        "düzelttim",
        "düzeltilmedi",
        "bitirdim",
        "bitti",
        "dağ\u0131t\u0131ld\u0131",
        "uyguland\u0131",
        "geçti",
        "kesinlikle",
        "mutlaka",
        "asla",
        "ayr\u0131ca",
        "kusursuz",
        "doğrulad\u0131",
        "onaylad\u0131",
        "üretime",
    }
)
_WORDS = _WORDS | _DISTINCTIVE

_WORDS = _WORDS | frozenset({"ek", "olarak", "ayarlar", "ayarlar\u0131", "değiştirdim"})


def is_dominant(text: str, threshold: float = 0.2) -> bool:
    """Vocabulary hint; shared or ambiguous tokens still need other context."""
    return lexical_fraction(text, _WORDS, threshold, _DISTINCTIVE)
