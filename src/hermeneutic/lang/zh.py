"""Experimental Chinese trigger mapping for the unchanged English gate.

This ordered table substitutes gate vocabulary; it does not translate text
or decide risk. Validation and known limits: ``evals/languages/README.md``.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import script_fraction, substitute

# Most-specific first: tense, negation and partial-progress guards precede triggers.
_MAP: list[tuple[str, str]] = [
    (r"(?<=[一-鿿㐀-䶿])(\d+(?:\.\d+)?)", r" \1"),
    (r"(?:请|請)(?:.{0,12}?)(?:完成|修复|修復|修正|部署)", " next up "),
    (
        "(?:尚未|还没|還沒|没有|沒有|未|没|沒)(?:完成|修复|修復|修正|部署|通过|通過)",
        " not yet ",
    ),
    (
        "(?:将|將|计划|計劃|准备|準備|预计|預計)(?:.{0,12}?)(?:完成|修复|修復|修正|部署)",
        " next up ",
    ),
    (
        "不(?:确定|確定|一定)|未必|不绝对|不絕對",
        " uncertain ",
    ),
    (
        "但是|不过|不過|然而",
        " but ",
    ),
    (
        "仍在(?:处理|處理|测试|測試)|尚有|还剩|還剩|剩余|剩餘",
        " remaining ",
    ),
    (
        "(\\d+(?:\\.\\d+)?)\\s*(?:个|個|项|項|件|处|處|次|条|條|行)",
        "\\1 ",
    ),
    (
        "不对|不對|不是",
        " that's not ",
    ),
    (
        "我的意思是",
        " i meant ",
    ),
    (
        "完成(?:了)?|修复(?:了)?|修復(?:了)?|修正(?:了)?|已部署|部署了|已实现|已實現",
        " completed ",
    ),
    (
        "通过(?:了)?|通過(?:了)?",
        " passed ",
    ),
    (
        "全部|所有|每个|每個",
        " all ",
    ),
    (
        "确定|確定|绝对|絕對|肯定|必然",
        " definitely ",
    ),
    (
        "另外|此外|顺便|順便|还添加|還添加",
        " additionally ",
    ),
    (
        "(?:代理|智能体|智能體).{0,25}?(?:确认|確認|验证|驗證|同意)",
        " the agents confirmed ",
    ),
    (
        "团队.{0,25}?(?:批准|确认|验证)|團隊.{0,25}?(?:批准|確認|驗證)",
        " the team approved ",
    ),
    (
        "无缝|無縫|强健|強健|生产就绪|生產就緒",
        " production-ready ",
    ),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in _MAP]


def normalize(text: str) -> str:
    """Map load-bearing tokens while preserving unmapped text and digits."""
    return substitute(text or "", _COMPILED)[0]


def is_dominant(text: str, threshold: float = 0.3) -> bool:
    """Han-script hint; the router checks Japanese kana first."""
    return script_fraction(text, (("\u3400", "\u4dbf"), ("一", "鿿"), ("\U00020000", "\U0003134f")), threshold)
