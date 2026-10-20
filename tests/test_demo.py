"""Synthetic onboarding contracts; model-quality checks belong in live receipts."""
from __future__ import annotations

import json
import socket

from hermeneutic.cli import main
from hermeneutic.triples import mine_dir


def test_demo_exports_then_mines_bounded_episodes_without_network(tmp_path, capsys, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline demo attempted network")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    destination = tmp_path / "sessions"
    assert main(["demo", "--out", str(destination)]) == 0
    fixture = destination / "synthetic-corrections.json"
    original = fixture.read_bytes()
    assert json.loads(original)["synthetic"] is True
    triples = list(mine_dir(destination, fmt="openai", glob="*.json"))
    assert len(triples) == 3
    assert triples[0].orig_prompt == "Release the widget service and report the verification results."
    assert triples[0].prior_assistant == "Done, the release is verified."
    assert triples[0].next_assistant.startswith("I have not run verification.")
    output = tmp_path / "triples.jsonl"
    assert main(["mine", str(destination), "--format", "openai", "--glob", "*.json", "--out", str(output)]) == 0
    capsys.readouterr()
    assert main(["bucket", str(output)]) == 0
    result = capsys.readouterr().out
    for bucket in ("over_completion", "scope_creep", "tone_format"):
        assert any(line.split() == [bucket, "1"] for line in result.splitlines())
    assert main(["inspect", str(output), "--limit", "1"]) == 0
    assert "Cite command output" in capsys.readouterr().out
    assert fixture.read_bytes() == original


def test_demo_refuses_existing_destination(tmp_path, capsys):
    existing = tmp_path / "sessions"
    existing.mkdir()
    sentinel = existing / "synthetic-corrections.json"
    sentinel.write_text("keep")
    assert main(["demo", "--out", str(existing)]) == 2
    assert sentinel.read_text() == "keep"
    assert "new writable directory" in capsys.readouterr().err


def test_dishes_demo_teaches_explicit_interpretation_and_retrieves_later_task(tmp_path, capsys):
    from hermeneutic.lessons import learn_lesson, render_context

    destination = tmp_path / "dishes"
    assert main(["demo", "--scenario", "dishes", "--out", str(destination)]) == 0
    assert "Synthetic scripted agent session" in capsys.readouterr().out
    fixture = destination / "dishes-session.json"
    assert json.loads(fixture.read_text())["synthetic"] is True
    triples = list(mine_dir(destination, fmt="openai", glob="*.json"))
    assert len(triples) == 1
    assert triples[0].orig_prompt == "Wash the dishes."
    assert "dirty plates on the table" in triples[0].user_correction
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text(triples[0].to_json() + "\n")
    memory = tmp_path / "lessons.json"
    lesson = "Washing up includes collecting and washing dirty plates on the table, not only dishes in the sink."
    learned = learn_lesson(triples=corpus, evidence="triple-id-1", lesson=lesson, scope="home/kitchen",
                           when=["wash the dishes", "wash up after supper"], memory=memory)
    result = render_context("Wash up after supper.", scope="home/kitchen", memory=memory)
    assert result["matches"][0]["id"] == learned["id"]
    assert lesson in result["context"]
