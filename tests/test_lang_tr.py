"""Contract examples for the tr trigger adapter; aggregate fixtures live in evals."""

from __future__ import annotations

import pytest

from hermeneutic import lang
from hermeneutic.gates.regex import risk_score
from hermeneutic.lang import tr

COMPLETION = '5 dosya tamamland\u0131.'
CERTAINTY = 'Bu kesinlikle çal\u0131ş\u0131r.'
SCOPE = 'Ayr\u0131ca günlük ekledim.'
RELAY = 'Ajanlar sonuçlar\u0131 doğrulad\u0131.'
UNIVERSAL = 'Tamamland\u0131; tüm dosyalar haz\u0131r.'
PLAN = 'Yar\u0131n 5 dosyay\u0131 tamamlayacağ\u0131m.'
UNCERTAIN = 'Bu konuda emin değilim.'
PARTIAL = '3 dosya tamamland\u0131 ama 5 dosya kald\u0131.'
CORRECTION = 'Yanl\u0131ş, bu istediğim sonuç değil.'


@pytest.mark.parametrize("text,rule", [
    (COMPLETION, "number_then_completion"),
    (CERTAINTY, "unhedged_certainty"),
    (SCOPE, "scope_expansion"),
    (RELAY, "subagent_passthrough"),
    (UNIVERSAL, "completion_with_all_quantifier"),
])
def test_maps_to_canonical_rules(text, rule):
    assert risk_score(text) == []
    assert any(hit.rule_id == rule for hit in risk_score(tr.normalize(text)))


@pytest.mark.parametrize("text", [PLAN, UNCERTAIN, PARTIAL])
def test_plans_negation_and_partials_are_not_drift(text):
    assert risk_score(tr.normalize(text)) == []


def test_maps_correction_vocabulary():
    assert "that's not" in tr.normalize(CORRECTION)
    assert risk_score(tr.normalize(CORRECTION)) == []


def test_routing_and_nonlinguistic_inputs():
    assert tr.is_dominant(COMPLETION)
    assert lang.detect(COMPLETION) == 'tr'
    assert not tr.is_dominant("")
    assert not tr.is_dominant("123!? 🧪")
    assert tr.normalize("") == ""


def test_preserves_unmapped_identifiers_and_numbers():
    assert "identifier_0x123" in tr.normalize("identifier_0x123 " + COMPLETION)
    assert "5" in tr.normalize(COMPLETION)
