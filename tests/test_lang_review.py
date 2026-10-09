"""Review counterexamples and positive controls frozen before remediation."""

import importlib.util
import json
import os
import random
import re
import tracemalloc
from pathlib import Path

import pytest

from hermeneutic import lang
from hermeneutic.lang._common import substitute

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "evals/languages/review-cases.json").read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_review_language_contract(case):
    hits = lang.risk_score(case["text"], lang=case["lang"])
    if case["label"] == "clean":
        assert hits == []
    else:
        assert case["rule"] in {hit.rule_id for hit in hits}
        if case["id"].endswith("negative-then-positive"):
            negative = next(c for c in CASES if c["id"] == case["lang"] + "-relay-agent")["text"]
            assert len(hits) == 1
            assert hits[0].start >= len(negative)


@pytest.mark.parametrize("code,text", [
    ("ko", "에이전트가 결과를 확인할 수 없습니다."),
    ("zh", "代理不能确认结果。"),
    ("zh", "代理确认不了结果。"),
    ("ja", "5件を修正することはできません。"),
])
def test_inability_is_not_an_affirmative_claim(code, text):
    assert lang.risk_score(text, lang=code) == []


@pytest.mark.parametrize("code,request_text,claim", [
    ("zh", "请完成所有任务。", "已完成5个文件。"),
    ("ja", "5件を修正してください。", "7件を修正しました。"),
])
def test_request_guard_keeps_neighboring_asserted_completion(code, request_text, claim):
    assert lang.risk_score(request_text, lang=code) == []
    assert lang.risk_score(claim, lang=code)
    hits = lang.risk_score(request_text + claim, lang=code)
    # The unchanged English gate can pair a number in the request with a
    # later completion verb. The claim must still fire, with its original
    # completion in the hit; the request alone must stay clean.
    assert hits and all(h.end > len(request_text) for h in hits)


def test_large_draft_keeps_source_spans_without_per_character_allocation():
    # 300k unmapped characters and a real claim at the end: no truncation.
    draft = "가나다라 " * 60000 + "5개 파일을 수정했습니다."
    tracemalloc.start()
    try:
        hits = lang.risk_score(draft, lang="ko")
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert any(hit.rule_id == "number_then_completion" for hit in hits)
    assert all(hit.matched_text == draft[hit.start : hit.end] for hit in hits)
    # A bounded memory contract for this fixture, not a throughput claim.
    assert peak < 12_000_000


def test_composed_replacements_keep_original_coordinates(monkeypatch):
    monkeypatch.setattr(lang.ko, "_COMPILED", [(re.compile("猫"), "expanded"), (re.compile("aexpanded"), "completed ")])
    (hit,) = lang.risk_score("2 a猫b", lang="ko")
    assert (hit.start, hit.end, hit.matched_text) == (0, 4, "2 a猫")


def test_compressed_spans_match_frozen_character_reference():
    # Independent reference: the previous character-by-character definition.
    # Expansions, contractions, deleted tokens and composed replacements must
    # retain the same origins even when a match cuts through a replacement.
    mappings = [(re.compile("猫"), "expanded"), (re.compile("aexpanded"), "joined"),
                (re.compile("dog"), "x"), (re.compile("remove"), ""),
                (re.compile(r"(\d+)件"), r"\1 "), (re.compile("oin"), "O")]
    rng = random.Random(56)
    for _ in range(30):
        draft = "".join(rng.choice(["a猫", "dog", "remove", "5件", " text ", "猫"]) for _ in range(30))
        reference = draft
        origins = [(i, i + 1) for i in range(len(draft))]
        for pattern, replacement in mappings:
            parts, rewritten = [], []
            cursor = 0
            for match in pattern.finditer(reference):
                parts.extend([reference[cursor:match.start()], match.expand(replacement)])
                rewritten.extend(origins[cursor:match.start()])
                source = origins[match.start():match.end()]
                span = (min(s[0] for s in source), max(s[1] for s in source))
                rewritten.extend([span] * len(match.expand(replacement)))
                cursor = match.end()
            parts.append(reference[cursor:])
            rewritten.extend(origins[cursor:])
            reference, origins = "".join(parts), rewritten
        normalized, compressed = substitute(draft, mappings, track_spans=True)
        assert normalized == reference
        for start in range(len(normalized)):
            for end in (start + 1, min(start + 17, len(normalized))):
                expected = origins[start:end]
                assert compressed.origin(start, end) == (min(s[0] for s in expected), max(s[1] for s in expected))


def _eval_module():
    spec = importlib.util.spec_from_file_location("review_eval", ROOT / "evals/languages/run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_failed_receipt_replace_preserves_previous_bytes(tmp_path, monkeypatch):
    module = _eval_module()
    receipt = tmp_path / "results.json"
    receipt.write_text('{"previous": true}\n', encoding="utf-8")
    monkeypatch.setattr(module, "HERE", tmp_path)
    monkeypatch.setattr(module, "evaluate", lambda: {"languages": {}})
    monkeypatch.setattr(module.sys, "argv", ["run.py", "--write"])

    def interrupted_replace(*_args):
        raise OSError("interrupted before publication")

    monkeypatch.setattr(os, "replace", interrupted_replace)
    with pytest.raises(OSError, match="interrupted"):
        module.main()
    assert receipt.read_bytes() == b'{"previous": true}\n'
    assert list(tmp_path.iterdir()) == [receipt]
