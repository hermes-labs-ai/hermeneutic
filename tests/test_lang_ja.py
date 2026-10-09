"""Contract examples for the ja trigger adapter; aggregate fixtures live in evals."""

from __future__ import annotations

import pytest

from hermeneutic import lang
from hermeneutic.gates.regex import risk_score
from hermeneutic.lang import ja

COMPLETION = '5件の修正が完了しました。'
CERTAINTY = 'これは確実に動きます。'
SCOPE = 'さらにログを追加した。'
RELAY = 'エージェントが結果を確認した。'
UNIVERSAL = '完了しました。すべて対応済みです。'
PLAN = '5件の修正は明日完了する予定です。'
UNCERTAIN = '結果は不確実です。'
PARTIAL = '3件は完了した。しかし残り5件があります。'
CORRECTION = '違う、それは依頼した結果ではありません。'


@pytest.mark.parametrize("text,rule", [
    (COMPLETION, "number_then_completion"),
    (CERTAINTY, "unhedged_certainty"),
    (SCOPE, "scope_expansion"),
    (RELAY, "subagent_passthrough"),
    (UNIVERSAL, "completion_with_all_quantifier"),
])
def test_maps_to_canonical_rules(text, rule):
    assert risk_score(text) == []
    assert any(hit.rule_id == rule for hit in risk_score(ja.normalize(text)))


@pytest.mark.parametrize("text", [PLAN, UNCERTAIN, PARTIAL])
def test_plans_negation_and_partials_are_not_drift(text):
    assert risk_score(ja.normalize(text)) == []


def test_maps_correction_vocabulary():
    assert "that's not" in ja.normalize(CORRECTION)
    assert risk_score(ja.normalize(CORRECTION)) == []


def test_routing_and_nonlinguistic_inputs():
    assert ja.is_dominant(COMPLETION)
    assert lang.detect(COMPLETION) == 'ja'
    assert not ja.is_dominant("")
    assert not ja.is_dominant("123!? 🧪")
    assert ja.normalize("") == ""


def test_preserves_unmapped_identifiers_and_numbers():
    assert "identifier_0x123" in ja.normalize("identifier_0x123 " + COMPLETION)
    assert "5" in ja.normalize(COMPLETION)
