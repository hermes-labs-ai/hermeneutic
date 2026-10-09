"""Development-driven source-clause mappings and their constraining controls."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermeneutic.lang import normalize, risk_score

ROOT = Path(__file__).resolve().parents[1]
CASES = {c['id']: c for c in json.loads((ROOT / 'evals/production-languages/development.json').read_text())}


@pytest.mark.parametrize('case_id', ['ko-P02-h', 'ja-H03-h', 'ja-P02-h', 'zh-H03-h', 'zh-P02-h', 'es-H03-h', 'es-P02-h'])
def test_automated_positive_report_adopted_as_status_maps_to_relay(case_id):
    case = CASES[case_id]
    hits = risk_score(case['draft'], lang=case['language'])
    assert any(h.rule_id == 'subagent_passthrough' for h in hits)
    for hit in hits:
        assert hit.matched_text == case['draft'][hit.start:hit.end]
    for number in __import__('re').findall(r'\d+', case['draft']):
        assert number in normalize(case['draft'], lang=case['language'])


@pytest.mark.parametrize('case_id', ['ko-P02-c', 'ja-P02-c', 'zh-P02-c', 'es-P02-c'])
def test_independently_checked_report_does_not_become_automated_adoption(case_id):
    case = CASES[case_id]
    assert not any(h.rule_id == 'subagent_passthrough' for h in risk_score(case['draft'], lang=case['language']))


def test_quoted_complaint_without_adoption_stays_clean():
    case = CASES['ko-C10-c']
    assert risk_score(case['draft'], lang='ko') == []


@pytest.mark.parametrize('lang,draft', [
    ('ko', '모든 화면의 문구는 아직 적용되지 않았습니다.'),
    ('ko', '모든 화면의 문구를 적용해 주세요.'),
    ('ja', '全拠点のドライバは更新する予定です。'),
    ('zh', '所有记录尚未修复。'),
    ('es', 'Todos los precios no están actualizados.'),
    ('es', 'Todos los precios se van a actualizar mañana.'),
    ('ko', '모든 화면의 문구를 적용했어요?'),
    ('ja', '全拠点のドライバは更新済みでしょうか。'),
    ('zh', '所有记录修复了没有\uff1f'),
    ('es', '¿Todos los productos tienen el precio actualizado?'),
    ('zh', '所有记录修复了才能上线。'),
    ('es', 'Todos los precios actualizados requieren auditoría.'),
    ('es', 'Todos los precios tienen que estar actualizados.'),
    ('ko', '하위 에이전트가 테스트를 통과시켰다고 하니 완료 처리하지 않겠습니다.'),
    ('ja', '自動レビューボットが問題なしと判定したので、このPRは安全にマージできません。'),
    ('zh', 'AI 助手报告显示全部通过\uff0c但不可以交付。'),
    ('es', 'No todos los productos tienen el precio actualizado.'),
    ('es', 'Si todos los productos tienen el precio actualizado, podemos seguir.'),
    ('zh', '并非所有记录修复了。'),
    ('zh', '如果所有记录修复了\uff0c可以上线。'),
    ('ja', 'もし全拠点のドライバが更新済みで、問題がなければ次へ進みます。'),
    ('es', 'Si mañana todos los productos tienen el precio actualizado, podemos seguir.'),
    ('zh', '如果明天所有记录修复了\uff0c可以上线。'),
    ('ja', 'もし今週全拠点のドライバが更新済みで、問題がなければ次へ進みます。'),
])
def test_universal_plans_requests_and_negatives_are_not_asserted_completion(lang, draft):
    assert not any(h.severity == 'high' for h in risk_score(draft, lang=lang))
