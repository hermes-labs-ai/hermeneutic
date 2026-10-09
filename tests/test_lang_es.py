"""Contract examples for the es trigger adapter; aggregate fixtures live in evals."""

from __future__ import annotations

import pytest

from hermeneutic import lang
from hermeneutic.gates.regex import risk_score
from hermeneutic.lang import es

COMPLETION = 'He completado 5 archivos.'
CERTAINTY = 'Esto funciona definitivamente.'
SCOPE = 'Además, agregué registros.'
RELAY = 'Los agentes confirmaron los resultados.'
UNIVERSAL = 'Completado; todos los archivos están listos.'
PLAN = 'Voy a completar 5 archivos mañana.'
UNCERTAIN = 'No estoy seguro de este método.'
PARTIAL = 'He completado 3 archivos, pero quedan 5.'
CORRECTION = 'Eso no es lo que pedí.'


@pytest.mark.parametrize("text,rule", [
    (COMPLETION, "completion_with_number"),
    (CERTAINTY, "unhedged_certainty"),
    (SCOPE, "scope_expansion"),
    (RELAY, "subagent_passthrough"),
    (UNIVERSAL, "completion_with_all_quantifier"),
])
def test_maps_to_canonical_rules(text, rule):
    assert risk_score(text) == []
    assert any(hit.rule_id == rule for hit in risk_score(es.normalize(text)))


@pytest.mark.parametrize("text", [PLAN, UNCERTAIN, PARTIAL])
def test_plans_negation_and_partials_are_not_drift(text):
    assert risk_score(es.normalize(text)) == []


def test_maps_correction_vocabulary():
    assert "that's not" in es.normalize(CORRECTION)
    assert risk_score(es.normalize(CORRECTION)) == []


def test_routing_and_nonlinguistic_inputs():
    assert es.is_dominant(COMPLETION)
    assert lang.detect(COMPLETION) == 'es'
    assert not es.is_dominant("")
    assert not es.is_dominant("123!? 🧪")
    assert es.normalize("") == ""


def test_preserves_unmapped_identifiers_and_numbers():
    assert "identifier_0x123" in es.normalize("identifier_0x123 " + COMPLETION)
    assert "5" in es.normalize(COMPLETION)
