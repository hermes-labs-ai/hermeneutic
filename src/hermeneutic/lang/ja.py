"""Experimental Japanese trigger mapping for the unchanged English gate.

This ordered table substitutes gate vocabulary; it does not translate text
or decide risk. Validation and known limits: ``evals/languages/README.md``.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import script_fraction, substitute

# Most-specific first: negative predicates, plans and partials precede triggers.
_RELAY_GAP = "(?:(?!unconfirmed)[^\\n.!?。\\uff01\\uff1f;\\uff1b]){0,25}?"

_MAP: list[tuple[str, str]] = [
    ("(?:確認|検証|同意|承認)(?:していない|していません|しなかった|しない|できない|できません)", " unconfirmed "),
    (
        "(?:完了|修正|終了|実装|デプロイ)(?:してください|して下さい|してほしい|をお願い(?:します)?|できない|できません|できなかった)",
        " requested or unable ",
    ),
    ("(?<=[ぁ-ゖァ-ヺ一-鿿])(\\d+(?:\\.\\d+)?)", " \\1"),
    ("(?:未|まだ)(?:完了|修正|終了)|(?:完了|修正|終了)(?:していない|していません)", " not yet "),
    ("(?:完了|修正|終了|実装|デプロイ)(?:する予定|予定|します|するつもり)", " next up "),
    ("不確実|確実(?:ではない|ではありません|とは限らない)", " uncertain "),
    ("しかし|ですが|けれど|ただし", " but "),
    ("残り|残って|まだ作業中|まだテスト中", " remaining "),
    ("(\\d+(?:\\.\\d+)?)\\s*(?:個|件|本|行|つ)", "\\1 "),
    ("違う|違います|そうではない", " that's not "),
    ("私の意図は", " i meant "),
    (
        "(?:完了|修正)(?:しました|した|済み)|(?:完了|修正)(?=\\s*(?:[。.!?]|$|です|である))"
        "|実装した|デプロイした|終了した",
        " completed ",
    ),
    ("合格した|通過した|パスした", " passed "),
    ("すべて|全て|全部|全件", " all "),
    ("確実|絶対|必ず|間違いなく", " definitely "),
    ("さらに|加えて|ついでに", " additionally "),
    ("エージェント" + _RELAY_GAP + "(?:確認|検証|同意)", " the agents confirmed "),
    ("チーム" + _RELAY_GAP + "(?:承認|確認|検証)", " the team approved "),
    ("堅牢|シームレス|本番対応", " production-ready "),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in _MAP]


def normalize(text: str) -> str:
    """Map load-bearing tokens while preserving unmapped text and digits."""
    return substitute(text or "", _COMPILED)[0]


def is_dominant(text: str, threshold: float = 0.1) -> bool:
    """Kana hint; kanji-only messages need an explicit language override."""
    return script_fraction(text, (("ぁ", "ゖ"), ("ァ", "ヺ"), ("ｦ", "ﾝ")), threshold)
