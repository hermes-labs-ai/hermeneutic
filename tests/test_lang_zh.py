"""Contract examples for the zh trigger adapter; aggregate fixtures live in evals."""

from __future__ import annotations

import pytest

from hermeneutic import lang
from hermeneutic.gates.regex import risk_score
from hermeneutic.lang import zh

COMPLETION = '已完成 5 个文件。'
CERTAINTY = '这个方案绝对不会失败。'
SCOPE = '另外我添加了日志。'
RELAY = '代理确认了所有结果。'
UNIVERSAL = '已完成所有任务。'
PLAN = '明天计划完成 5 个文件。'
UNCERTAIN = '不确定这种方法是否合适。'
PARTIAL = '完成了 3 个文件\uff0c但是还剩 5 个。'
CORRECTION = '不对\uff0c这不是要求的结果。'


@pytest.mark.parametrize("text,rule", [
    (COMPLETION, "completion_with_number"),
    (CERTAINTY, "unhedged_certainty"),
    (SCOPE, "scope_expansion"),
    (RELAY, "subagent_passthrough"),
    (UNIVERSAL, "completion_with_all_quantifier"),
])
def test_maps_to_canonical_rules(text, rule):
    assert risk_score(text) == []
    assert any(hit.rule_id == rule for hit in risk_score(zh.normalize(text)))


@pytest.mark.parametrize("text", [PLAN, UNCERTAIN, PARTIAL])
def test_plans_negation_and_partials_are_not_drift(text):
    assert risk_score(zh.normalize(text)) == []


def test_maps_correction_vocabulary():
    assert "that's not" in zh.normalize(CORRECTION)
    assert risk_score(zh.normalize(CORRECTION)) == []


def test_routing_and_nonlinguistic_inputs():
    assert zh.is_dominant(COMPLETION)
    assert lang.detect(COMPLETION) == 'zh'
    assert not zh.is_dominant("")
    assert not zh.is_dominant("123!? 🧪")
    assert zh.normalize("") == ""


def test_preserves_unmapped_identifiers_and_numbers():
    assert "identifier_0x123" in zh.normalize("identifier_0x123 " + COMPLETION)
    assert "5" in zh.normalize(COMPLETION)


def test_request_to_fix_is_not_a_completion_claim():
    assert risk_score(zh.normalize("请修复 4 个错误。")) == []
