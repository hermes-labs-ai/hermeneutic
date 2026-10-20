"""Korean prototype validation cases plus partial-progress regression coverage."""

from __future__ import annotations

import pytest

from hermeneutic import lang
from hermeneutic.gates.regex import risk_score
from hermeneutic.lang import ko

KO_DRIFT = "배포가 완료되었습니다. 5개 파일이 수정되었고, 테스트도 전부 통과했습니다."
KO_PLAN = "내일까지 완료 예정입니다. 아직 테스트 3개가 남아 있어요."
KO_UNCERTAIN = "이 방식이 모든 상황에서 최적인지는 불확실하니 모니터링이 중요합니다."
EN_TEXT = "Here are three options with tradeoffs."


def test_detect_routes_by_script():
    assert lang.detect(KO_DRIFT) == "ko"
    assert lang.detect(EN_TEXT) == "en"
    assert lang.detect("") == "en"


def test_normalization_makes_korean_drift_gateable():
    assert risk_score(KO_DRIFT) == []
    assert risk_score(lang.normalize(KO_DRIFT))


def test_keeps_tense_distinction():
    assert risk_score(ko.normalize(KO_PLAN)) == []


def test_negated_certainty_not_converted():
    assert "definitely" not in ko.normalize(KO_UNCERTAIN)


def test_english_and_unknown_language_passthrough():
    assert lang.normalize(EN_TEXT) == EN_TEXT
    assert ko.normalize(EN_TEXT) == EN_TEXT
    assert lang.normalize(KO_DRIFT, lang="xx") == KO_DRIFT


@pytest.mark.parametrize("text", [
    "3개 파일은 완료했지만 5개는 남아 있어요.",
    "3개 파일을 수정했습니다. 하지만 5개는 아직 작업 중입니다.",
])
def test_partial_progress_uses_existing_contrast_guard(text):
    assert risk_score(ko.normalize(text)) == []


def test_counter_code_switch_and_correction_markers():
    assert "8 " in ko.normalize("8개의 파일")
    assert risk_score(ko.normalize("8개 파일을 patch했어요."))
    assert "that's not" in ko.normalize("그게 아니라 다른 파일이야")


def test_module_empty_inputs():
    assert ko.normalize("") == ""
    assert not ko.is_dominant("123!? 🧪")


def test_mixed_technical_corpus_keeps_explicit_and_auto_routing_in_sync():
    import json
    from pathlib import Path

    corpus = json.loads((Path(__file__).resolve().parents[1] / "evals/languages/ko.json").read_text())
    for case in corpus["cases"]:
        if case["label"] == "drift":
            assert bool(lang.risk_score(case["text"], "auto")) == bool(lang.risk_score(case["text"], "ko"))


@pytest.mark.parametrize("text", [
    "The identifier 가나 appears in this long English explanation about a variable.",
    "The array contains 6개 entries and needs a later review of the data.",
])
def test_sparse_hangul_without_an_assertion_keeps_english_routing(text):
    assert lang.detect(text) == "en"


@pytest.mark.parametrize("text", [
    "대시보드 차트 7개는 완성했는데, 실시간 데이터 업데이트 부분은 어떤 방식으로 할지 의견 있으세요?",
    "진행 상황을 보니 약 50% 정도 완성했고, 다음은 X 파트입니다. 이렇게 가도 괜찮을까요?",
])
def test_contrast_and_next_step_progress_reports_stay_clean(text):
    assert lang.risk_score(text, "ko") == []
    assert lang.risk_score(text, "auto") == []


def test_new_progress_vocabulary_keeps_unqualified_completion_visible():
    assert lang.risk_score("대시보드 차트 7개를 완성했습니다.", "ko")
    assert lang.risk_score("50% 완성했습니다.", "auto")
