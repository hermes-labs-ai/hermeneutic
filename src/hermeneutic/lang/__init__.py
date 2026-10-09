"""Experimental trigger adapters around one unchanged canonical English gate.

Script or conservative vocabulary hints route one language per draft. They
are not general language identification; callers can select a language when
a short, code-switched or shared-script draft is ambiguous.
"""

from __future__ import annotations

import re

from hermeneutic.gates.regex import RiskHit
from hermeneutic.gates.regex import risk_score as _english_risk_score
from hermeneutic.lang import de, es, fr, ja, ko, pt, tr, zh
from hermeneutic.lang._common import substitute

LANGS = ("en", "ko", "zh", "ja", "tr", "de", "fr", "es", "pt")
_MODULES = {"ko": ko, "zh": zh, "ja": ja, "tr": tr, "de": de, "fr": fr, "es": es, "pt": pt}


def detect(text: str) -> str:
    """Best-effort routing, falling back to English on Latin-script ties."""
    if ko.is_dominant(text):
        return "ko"
    if ja.is_dominant(text):
        return "ja"
    if zh.is_dominant(text):
        return "zh"
    tokens = re.findall(r"[^\W\d_]+", text.casefold())
    scores = {
        code: sum(token in module._WORDS for token in tokens)
        for code, module in ((c, _MODULES[c]) for c in ("tr", "de", "fr", "es", "pt"))
        if module.is_dominant(text)
    }
    if scores:
        best = max(scores.values())
        winners = [code for code, score in scores.items() if score == best]
        if len(winners) == 1:
            return winners[0]
    return "en"


def normalize(text: str, lang: str = "auto") -> str:
    """Map triggers; English and unknown language codes pass through intact."""
    code = detect(text) if lang == "auto" else lang
    module = _MODULES.get(code)
    return module.normalize(text) if module else text


def risk_score(draft: str, lang: str = "auto") -> list[RiskHit]:
    """Normalize before the English gate; report hits in original coordinates.

    The canonical gate and its English API remain unchanged. These spans
    describe the source vocabulary that generated a hit, not translation.
    """
    code = detect(draft) if lang == "auto" else lang
    module = _MODULES.get(code)
    if not module:
        return _english_risk_score(draft)
    normalized, spans = substitute(draft, module._COMPILED, track_spans=True)
    hits = _english_risk_score(normalized)
    for hit in hits:
        origins = spans[hit.start : hit.end]
        hit.start = min(s[0] for s in origins)
        hit.end = max(s[1] for s in origins)
        matched = draft[hit.start : hit.end]
        hit.matched_text = matched if len(matched) <= 200 else matched[:200] + "..."
    return hits
