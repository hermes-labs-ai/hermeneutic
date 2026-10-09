"""Experimental Chinese trigger mapping for the unchanged English gate.

This ordered table substitutes gate vocabulary; it does not translate text
or decide risk. Validation and known limits: ``evals/languages/README.md``.
"""

from __future__ import annotations

import re

from hermeneutic.lang._common import script_fraction, substitute

# Most-specific first: negative predicates, plans and partials precede triggers.
_RELAY_GAP = "(?:(?!unconfirmed)[^\\n.!?。\\uff01\\uff1f;\\uff1b]){0,25}?"

_MAP: list[tuple[str, str]] = [
    ("(?:没有|沒有|未|没|沒|无法|無法|不能|不)(?:确认|確認|验证|驗證|同意|批准)", " unconfirmed "),
    ("(?:确认|確認|验证|驗證|同意|批准)(?:不了|不到|不成)", " unconfirmed "),
    ("(?:无法|無法|不能|未能|没能|沒能)(?:完成|修复|修復|修正|部署|通过|通過)", " unable "),
    ("(?<=[一-鿿㐀-䶿])(\\d+(?:\\.\\d+)?)", " \\1"),
    ("(?:请|請)(?:.{0,12}?)(?:完成|修复|修復|修正|部署)", " requested "),
    ("(?:尚未|还没|還沒|没有|沒有|未|没|沒)(?:完成|修复|修復|修正|部署|通过|通過)", " not yet "),
    ("(?:将|將|计划|計劃|准备|準備|预计|預計)(?:.{0,12}?)(?:完成|修复|修復|修正|部署)", " next up "),
    ("不(?:确定|確定|一定)|未必|不绝对|不絕對", " uncertain "),
    ("但是|不过|不過|然而", " but "),
    ("仍在(?:处理|處理|测试|測試)|尚有|还剩|還剩|剩余|剩餘", " remaining "),
    ("(\\d+(?:\\.\\d+)?)\\s*(?:个|個|项|項|件|处|處|次|条|條|行)", "\\1 "),
    ("不对|不對|不是", " that's not "),
    ("我的意思是", " i meant "),
    (
        "(?:已(?:经|經)?(?:完成|修复|修復|修正)|(?:完成|修复|修復|修正)了|(?:完成|修复|修復|修正)(?=\\s*(?:[。.!?]|$)))|已部署|部署了|已实现|已實現",
        " completed ",
    ),
    ("通过(?:了)?|通過(?:了)?", " passed "),
    ("全部|所有|每个|每個", " all "),
    ("确定|確定|绝对|絕對|肯定|必然", " definitely "),
    ("另外|此外|顺便|順便|还添加|還添加", " additionally "),
    ("(?:代理|智能体|智能體)" + _RELAY_GAP + "(?:确认|確認|验证|驗證|同意)", " the agents confirmed "),
    ("团队" + _RELAY_GAP + "(?:批准|确认|验证)|團隊" + _RELAY_GAP + "(?:批准|確認|驗證)", " the team approved "),
    ("无缝|無縫|强健|強健|生产就绪|生產就緒", " production-ready "),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), replacement) for pattern, replacement in _MAP]


def normalize(text: str) -> str:
    """Map load-bearing tokens while preserving unmapped text and digits."""
    return substitute(text or "", _COMPILED)[0]


def is_dominant(text: str, threshold: float = 0.3) -> bool:
    """Han-script hint; the router checks Japanese kana first."""
    return script_fraction(text, (("\u3400", "\u4dbf"), ("一", "鿿"), ("\U00020000", "\U0003134f")), threshold)
