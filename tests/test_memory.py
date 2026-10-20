"""Evidence retrieval contracts; use real model receipts for retrieval quality."""
from __future__ import annotations

import json

import pytest

from hermeneutic import compile as compiler
from hermeneutic.cli import main
from hermeneutic.memory import recall
from hermeneutic.triples import Triple


@pytest.fixture
def corpus(tmp_path):
    path = tmp_path / "triples.jsonl"
    records = [
        Triple("s1", "t1", "prior", "Use persimmons instead.", "repair", "Make a fruit salad."),
        Triple("s2", "t2", "prior", "No, cite evidence.", "repair", "Release the service."),
    ]
    path.write_text("\n".join(t.to_json() for t in records) + "\n")
    return path


def test_keyword_needs_neither_index_nor_inference(corpus, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("keyword retrieval attempted inference")
    monkeypatch.setattr(compiler, "ollama_embed", forbidden)
    matches = recall("persimmons", corpus, home=tmp_path, method="keyword", limit=1)
    assert matches[0]["evidence"] == "triple-id-1"
    assert matches[0]["correction_preview"] == "Use persimmons instead."
    assert compiler.bucket_for(matches[0]["correction_preview"]) is None
    assert recall("spaceships", corpus, home=tmp_path, method="keyword") == []


@pytest.mark.parametrize("method", ["semantic", "hybrid"])
def test_evidence_resolves_and_stale_index_is_rejected(corpus, tmp_path, method):
    embed = lambda text: [1.0, 0.0] if "fruit" in text.lower() else [0.0, 1.0]  # noqa: E731
    compiler.compile_index(corpus, home=tmp_path, embedder=embed)
    before = corpus.read_bytes()
    matches = recall("fruit salad", corpus, home=tmp_path, method=method, embedder=embed, limit=1)
    assert matches[0]["session"] == "s1"
    assert matches[0]["evidence"] == "triple-id-1"
    assert corpus.read_bytes() == before
    corpus.write_bytes(before + b"\n")
    with pytest.raises(ValueError, match="stale"):
        recall("fruit", corpus, home=tmp_path, method=method, embedder=embed)


def test_cli_recall_is_bounded_and_escapes_data(corpus, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HERMENEUTIC_HOME", str(tmp_path))
    assert main(["recall", "persimmons", "--triples", str(corpus), "--method", "keyword", "--limit", "1"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["matches"]) == 1
    assert "Historical evidence" in result["usage"]
    assert "prior" not in result["matches"][0]


def test_cli_recall_missing_index_is_error(corpus, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HERMENEUTIC_HOME", str(tmp_path))
    assert main(["recall", "fruit", "--triples", str(corpus), "--method", "semantic"]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert "index and local Ollama" in result.err


def test_preview_caps_and_invalid_dimensions(corpus, tmp_path):
    record = Triple("s" * 200, "t" * 200, "private", "persimmons " * 200, "private", "fruit " * 300)
    corpus.write_text(record.to_json() + "\n")
    result = recall("persimmons", corpus, home=tmp_path, method="keyword")[0]
    assert len(result["correction_preview"]) == 800
    assert len(result["prompt_preview"]) == 240
    assert result["correction_truncated"] and result["prompt_truncated"]
    compiler.compile_index(corpus, home=tmp_path, embedder=lambda _: [1.0, 0.0])
    with pytest.raises(ValueError, match="dimension"):
        recall("fruit", corpus, home=tmp_path, method="semantic", embedder=lambda _: [1.0])


def test_evaluation_reports_targets_and_abstention_without_private_text(corpus, tmp_path):
    import runpy
    from pathlib import Path

    runner = runpy.run_path(str(Path(__file__).resolve().parents[1] / "evals/correction-memory/runner.py"))
    cases = [{"id": "positive", "query": "persimmons", "expected": [1]},
             {"id": "negative", "query": "spaceships", "expected": []}]
    result = runner["evaluate"](corpus, tmp_path, cases, ["keyword"], 1)
    assert result["results"]["keyword"]["positive_hits"] == 1
    assert result["results"]["keyword"]["negative_empty"] == 1
    assert "persimmons" not in json.dumps(result)
    assert "prior" not in json.dumps(result)


@pytest.mark.parametrize("cases", [
    [],
    [{"id": "case", "query": "persimmons", "expected": [0]}],
    [{"id": "case", "query": "persimmons", "expected": [3]}],
    [{"id": "case", "query": "persimmons", "expected": [True]}],
    [{"id": "case", "query": "", "expected": [1]}],
    [{"id": "same", "query": "persimmons", "expected": [1]}] * 2,
])
def test_evaluation_rejects_invalid_labels(corpus, tmp_path, cases):
    import runpy
    from pathlib import Path

    runner = runpy.run_path(str(Path(__file__).resolve().parents[1] / "evals/correction-memory/runner.py"))
    with pytest.raises(ValueError):
        runner["evaluate"](corpus, tmp_path, cases, ["keyword"], 1)


def test_public_keyword_retrieval_regression_floor(tmp_path):
    import runpy
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    data = root / "evals/correction-memory/public"
    runner = runpy.run_path(str(root / "evals/correction-memory/runner.py"))
    result = runner["evaluate"](data / "triples.jsonl", tmp_path,
                                json.loads((data / "cases.json").read_text()), ["keyword"], 3)
    keyword = result["results"]["keyword"]
    assert keyword["positive_trials"] == 18
    assert keyword["negative_trials"] == 8
    assert keyword["positive_hits"] >= 15
    assert keyword["negative_empty"] >= 4
