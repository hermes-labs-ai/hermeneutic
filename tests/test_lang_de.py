"""Contract examples for the de trigger adapter; aggregate fixtures live in evals."""

from __future__ import annotations

import pytest

from hermeneutic import lang
from hermeneutic.gates.regex import risk_score
from hermeneutic.lang import de

COMPLETION = 'Ich habe 5 Dateien abgeschlossen.'
CERTAINTY = 'Das funktioniert definitiv.'
SCOPE = 'Zusätzlich habe ich Protokolle ergänzt.'
RELAY = 'Die Agenten haben die Ergebnisse bestätigt.'
UNIVERSAL = 'Abgeschlossen; alle Dateien sind bereit.'
PLAN = 'Ich werde morgen 5 Dateien abschließen.'
UNCERTAIN = 'Ich bin nicht sicher.'
PARTIAL = '3 Dateien sind abgeschlossen, aber 5 verbleiben.'
CORRECTION = 'Das stimmt nicht; ich meinte eine andere Datei.'


@pytest.mark.parametrize("text,rule", [
    (COMPLETION, "number_then_completion"),
    (CERTAINTY, "unhedged_certainty"),
    (SCOPE, "scope_expansion"),
    (RELAY, "subagent_passthrough"),
    (UNIVERSAL, "completion_with_all_quantifier"),
])
def test_maps_to_canonical_rules(text, rule):
    assert risk_score(text) == []
    assert any(hit.rule_id == rule for hit in risk_score(de.normalize(text)))


@pytest.mark.parametrize("text", [PLAN, UNCERTAIN, PARTIAL])
def test_plans_negation_and_partials_are_not_drift(text):
    assert risk_score(de.normalize(text)) == []


def test_maps_correction_vocabulary():
    assert "that's not" in de.normalize(CORRECTION)
    assert risk_score(de.normalize(CORRECTION)) == []


def test_routing_and_nonlinguistic_inputs():
    assert de.is_dominant(COMPLETION)
    assert lang.detect(COMPLETION) == 'de'
    assert not de.is_dominant("")
    assert not de.is_dominant("123!? 🧪")
    assert de.normalize("") == ""


def test_preserves_unmapped_identifiers_and_numbers():
    assert "identifier_0x123" in de.normalize("identifier_0x123 " + COMPLETION)
    assert "5" in de.normalize(COMPLETION)
