"""Contract examples for the fr trigger adapter; aggregate fixtures live in evals."""

from __future__ import annotations

import pytest

from hermeneutic import lang
from hermeneutic.gates.regex import risk_score
from hermeneutic.lang import fr

COMPLETION = "J'ai terminé 5 fichiers."
CERTAINTY = 'Cela fonctionne certainement.'
SCOPE = 'En plus, je modifie les réglages.'
RELAY = 'Les agents ont confirmé les résultats.'
UNIVERSAL = 'Terminé; tous les fichiers sont prêts.'
PLAN = 'Je vais terminer 5 fichiers demain.'
UNCERTAIN = 'Je ne suis pas certain.'
PARTIAL = '3 fichiers sont terminés, mais 5 restent.'
CORRECTION = "Ce n'est pas le résultat demandé."


@pytest.mark.parametrize("text,rule", [
    (COMPLETION, "completion_with_number"),
    (CERTAINTY, "unhedged_certainty"),
    (SCOPE, "scope_expansion"),
    (RELAY, "subagent_passthrough"),
    (UNIVERSAL, "completion_with_all_quantifier"),
])
def test_maps_to_canonical_rules(text, rule):
    assert risk_score(text) == []
    assert any(hit.rule_id == rule for hit in risk_score(fr.normalize(text)))


@pytest.mark.parametrize("text", [PLAN, UNCERTAIN, PARTIAL])
def test_plans_negation_and_partials_are_not_drift(text):
    assert risk_score(fr.normalize(text)) == []


def test_maps_correction_vocabulary():
    assert "that's not" in fr.normalize(CORRECTION)
    assert risk_score(fr.normalize(CORRECTION)) == []


def test_routing_and_nonlinguistic_inputs():
    assert fr.is_dominant(COMPLETION)
    assert lang.detect(COMPLETION) == 'fr'
    assert not fr.is_dominant("")
    assert not fr.is_dominant("123!? 🧪")
    assert fr.normalize("") == ""


def test_preserves_unmapped_identifiers_and_numbers():
    assert "identifier_0x123" in fr.normalize("identifier_0x123 " + COMPLETION)
    assert "5" in fr.normalize(COMPLETION)
