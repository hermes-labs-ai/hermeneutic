"""Contract examples for the pt trigger adapter; aggregate fixtures live in evals."""

from __future__ import annotations

import pytest

from hermeneutic import lang
from hermeneutic.gates.regex import risk_score
from hermeneutic.lang import pt

COMPLETION = 'Eu concluí 5 arquivos.'
CERTAINTY = 'Isso funciona definitivamente.'
SCOPE = 'Além disso, adicionei registros.'
RELAY = 'Os agentes confirmaram os resultados.'
UNIVERSAL = 'Concluído; todos os arquivos estão prontos.'
PLAN = 'Vou concluir 5 arquivos amanhã.'
UNCERTAIN = 'Não tenho certeza deste método.'
PARTIAL = 'Eu concluí 3 arquivos, mas restam 5.'
CORRECTION = 'Isso não é o que pedi.'


@pytest.mark.parametrize("text,rule", [
    (COMPLETION, "completion_with_number"),
    (CERTAINTY, "unhedged_certainty"),
    (SCOPE, "scope_expansion"),
    (RELAY, "subagent_passthrough"),
    (UNIVERSAL, "completion_with_all_quantifier"),
])
def test_maps_to_canonical_rules(text, rule):
    assert risk_score(text) == []
    assert any(hit.rule_id == rule for hit in risk_score(pt.normalize(text)))


@pytest.mark.parametrize("text", [PLAN, UNCERTAIN, PARTIAL])
def test_plans_negation_and_partials_are_not_drift(text):
    assert risk_score(pt.normalize(text)) == []


def test_maps_correction_vocabulary():
    assert "that's not" in pt.normalize(CORRECTION)
    assert risk_score(pt.normalize(CORRECTION)) == []


def test_routing_and_nonlinguistic_inputs():
    assert pt.is_dominant(COMPLETION)
    assert lang.detect(COMPLETION) == 'pt'
    assert not pt.is_dominant("")
    assert not pt.is_dominant("123!? 🧪")
    assert pt.normalize("") == ""


def test_preserves_unmapped_identifiers_and_numbers():
    assert "identifier_0x123" in pt.normalize("identifier_0x123 " + COMPLETION)
    assert "5" in pt.normalize(COMPLETION)


@pytest.mark.parametrize("text", ["3 módulos não foram concluídos.", "2 erros não foram corrigidos."])
def test_plural_negated_completions_are_not_claims(text):
    assert risk_score(pt.normalize(text)) == []
