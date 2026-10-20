"""Consumer policy regressions: advisory mappings, unchanged English enforcement."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from hermeneutic import Router
from hermeneutic.cli import main
from hermeneutic.gates.regex import risk_score as english_score
from hermeneutic.lang import deployment_findings

ROOT = Path(__file__).resolve().parents[1]
MAPPED = ['5개 파일을 수정했습니다.', '已完成 5 个文件。', '5件の修正が完了しました。', 'He completado 5 archivos.']
ENGLISH = 'Done — shipped 14 files, all tests pass.'


def hook(relative):
    spec = importlib.util.spec_from_file_location('policy_hook', ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('draft', MAPPED)
def test_mapping_only_cli_remains_visible_and_does_not_reject(draft, tmp_path, capsys):
    path = tmp_path / 'draft.txt'
    path.write_text(draft)
    assert main(['gate', '--lang', 'auto', '--draft', str(path)]) == 0
    output = capsys.readouterr().out
    assert 'RISK — highest severity: high' in output and 'ADVISORY' in output


@pytest.mark.parametrize('lang', ['en', 'auto', 'ko', 'ja', 'zh', 'es'])
def test_raw_english_enforcement_survives_mapping_and_routing(lang, tmp_path, capsys):
    draft = MAPPED[0] + '\n' + ENGLISH
    findings, blocking = deployment_findings(draft, lang=lang)
    assert blocking == english_score(draft)
    assert blocking and any(h.severity == 'high' for h in blocking)
    assert {(h.rule_id, h.start, h.end) for h in blocking} <= {(h.rule_id, h.start, h.end) for h in findings}
    path = tmp_path / 'draft.txt'
    path.write_text(draft)
    assert main(['gate', '--lang', lang, '--draft', str(path)]) == 1
    capsys.readouterr()


def test_router_calls_probe_for_raw_english_in_mixed_draft():
    seen = []

    class Probe:
        def review(self, request, draft):
            from hermeneutic.gates.twin import TwinVerdict
            seen.append(draft)
            return TwinVerdict(verdict='ship', reason='control', flip_condition='new evidence')

    draft = MAPPED[0] + '\n' + ENGLISH
    result = Router(probe=Probe(), use_rubric=False, lang='auto').gate('check', draft)
    assert seen == [draft] and result.shipped_at_stage == 'twin'


def test_qwen_advisory_does_not_spend_english_repair_marker(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMENEUTIC_QWEN_STATE_DIR', str(tmp_path / 'state'))
    adapter = hook('integrations/qwen-code/hermeneutic_stop.py')
    payload = {'session_id': 'one', 'last_assistant_message': ENGLISH}
    assert adapter.evaluate(payload)['decision'] == 'block'
    before = {p: p.read_bytes() for p in (tmp_path / 'state').glob('*.json')}
    assert before
    advisory = adapter.evaluate({**payload, 'last_assistant_message': MAPPED[0]})
    assert advisory.get('decision', 'allow') == 'allow'
    assert 'language advisory' in advisory['systemMessage']
    assert before == {p: p.read_bytes() for p in (tmp_path / 'state').glob('*.json')}
    retry = adapter.evaluate(payload)
    assert retry.get('decision', 'allow') == 'allow' and 'bounded retry' in retry['systemMessage']


@pytest.mark.parametrize('draft', MAPPED)
def test_gemini_advisory_and_mixed_english_enforcement(draft):
    adapter = hook('integrations/gemini-cli/hermeneutic_after_agent.py')
    assert adapter.evaluate({'prompt_response': draft})['decision'] == 'allow'
    assert adapter.evaluate({'prompt_response': draft + '\n' + ENGLISH})['decision'] == 'deny'


def test_mapped_empty_cannot_hide_raw_english_findings():
    from hermeneutic.lang import risk_score
    draft = '요청하신 변경은 아직 검증하지 않았습니다. 다음 단계에서 확인할 예정입니다. Done — shipped 14 files and all 92 tests pass.'
    assert risk_score(draft, lang='auto') == []
    findings, blocking = deployment_findings(draft)
    assert findings == blocking == english_score(draft) and blocking
    plain, raw = deployment_findings(ENGLISH, lang='en')
    assert plain == raw == english_score(ENGLISH)
    assert deployment_findings(ENGLISH, lang='unknown') == (plain, raw)


def test_qwen_clean_nonenglish_does_not_touch_or_create_state(tmp_path, monkeypatch):
    state = tmp_path / 'state'
    monkeypatch.setenv('HERMENEUTIC_QWEN_STATE_DIR', str(state))
    adapter = hook('integrations/qwen-code/hermeneutic_stop.py')
    payload = {'session_id': 'one', 'last_assistant_message': '검토 후 알려드리겠습니다.'}
    assert adapter.evaluate(payload).get('decision', 'allow') == 'allow'
    assert not state.exists()
    assert adapter.evaluate({**payload, 'last_assistant_message': ENGLISH})['decision'] == 'block'
    before = {p: p.read_bytes() for p in state.glob('*.json')}
    assert adapter.evaluate(payload).get('decision', 'allow') == 'allow'
    assert before == {p: p.read_bytes() for p in state.glob('*.json')}


def test_hermes_agent_preserves_raw_english_advisory_in_mapped_empty_draft():
    from hermeneutic.hermes_agent_plugin import check_outgoing_claims
    draft = '요청하신 변경은 아직 검증하지 않았습니다. 다음 단계에서 확인할 예정입니다. Done — shipped 14 files and all 92 tests pass.'
    for text in (draft, ENGLISH):
        output = check_outgoing_claims(text)
        assert output.startswith(text + '\n\n[Hermeneutic evidence check: high')
        assert 'completion_with_number' in output and 'completion_with_all_quantifier' in output
