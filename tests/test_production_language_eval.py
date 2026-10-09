"""Metric semantics and sealing invariants, independent of authored fixtures."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('production_eval', ROOT / 'evals/production-languages/run.py')
EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVAL)


def test_intervals_include_sampling_uncertainty_at_perfect_observations():
    low, high = EVAL.wilson(0, 40)
    assert low == 0 and .08 < high < .09
    low, high = EVAL.wilson(40, 40)
    assert .91 < low < .92 and high == 1
    assert EVAL.wilson(0, 0) is None


def test_medium_and_low_hits_do_not_inflate_high_recall(monkeypatch):
    from hermeneutic.gates.regex import RiskHit

    def score(draft, lang):
        return [RiskHit(rule_id='control', severity=draft, description='test',
                        matched_text=draft, start=0, end=len(draft))]

    monkeypatch.setattr(EVAL, 'risk_score', score)
    cases = [{'id': 'clean', 'family': 'clean-family', 'lang': 'ko', 'label': 'clean', 'draft': 'low'},
             {'id': 'medium', 'family': 'medium-family', 'lang': 'ko', 'label': 'high', 'draft': 'med'},
             {'id': 'high', 'family': 'high-family', 'lang': 'ko', 'label': 'high', 'draft': 'high'}]
    metrics = EVAL.evaluate(cases)['ko']['explicit']
    assert metrics['false_positive']['rate'] == 1
    assert metrics['high_severity_recall']['rate'] == .5
    assert metrics['actionable_recall']['rate'] == 1
    assert not metrics['observed_targets_met']
    assert not EVAL.evaluate([])['ko']['explicit']['observed_targets_met']


def test_missing_provenance_is_rejected(tmp_path):
    import json

    path = tmp_path / 'cases.json'
    path.write_text(json.dumps([{'id': 'x', 'lang': 'ko', 'label': 'clean', 'draft': 'hi'}]))
    with pytest.raises(ValueError, match='Missing scenario'):
        EVAL.load_cases(path)


def test_failed_exposure_cannot_be_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(EVAL, 'HERE', tmp_path)
    monkeypatch.setattr(EVAL, 'source_hashes', lambda: {})
    for name in ('PROTOCOL.md', 'development.json', 'holdout.json'):
        (tmp_path / name).write_text('[]')
    base_args = ['run.py', '--holdout', str(tmp_path / 'holdout.json')]
    monkeypatch.setattr(EVAL.sys, 'argv', [*base_args, '--freeze'])
    EVAL.main()
    monkeypatch.setattr(EVAL.sys, 'argv', base_args)

    def broken(_path):
        raise ValueError('malformed corpus')

    monkeypatch.setattr(EVAL, 'load_cases', broken)
    with pytest.raises(ValueError, match='malformed corpus'):
        EVAL.main()
    assert (tmp_path / 'holdout-exposure.json').exists()
    with pytest.raises(ValueError, match='already exposed'):
        EVAL.main()
