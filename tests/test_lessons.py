"""Teach/transfer mechanics, provenance, abstention, revocation, and storage safety."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import stat

import pytest

from hermeneutic import confirm_lesson, inspect_lessons, learn_lesson, recall_lessons, render_context, revoke_lesson
from hermeneutic import lessons as module
from hermeneutic.cli import main
from hermeneutic.lessons import LessonMemoryError
from hermeneutic.triples import Triple


@pytest.fixture
def setup(tmp_path):
    corpus = tmp_path / "triples.jsonl"
    corpus.write_text(Triple("fictional-session", "synthetic", "I changed unrelated files.",
                             "No, restrict this repair to the requested parser.",
                             "I will limit this repair to the requested parser.",
                             "Repair the request parser.").to_json() + "\n", encoding="utf-8")
    return {"triples": corpus, "evidence": "triple-id-1", "scope": "project/parser",
            "lesson": "Restrict parser repairs to the requested component; check before expanding scope.",
            "when": ["repair request parser", "fix request parser"], "memory": tmp_path / "lessons.json"}


def test_learn_context_inspect_revoke_preserves_provenance(setup):
    record = learn_lesson(**setup)
    assert record["id"].startswith("lesson-")
    assert record["version"] == 1 and record["status"] == "active"
    original = setup["triples"].read_bytes()
    assert record["provenance"]["corpus_sha256"] == hashlib.sha256(original).hexdigest()
    assert record["provenance"]["record_sha256"] == hashlib.sha256(original).hexdigest()
    assert record["provenance"]["episode"]["user_correction"] == "No, restrict this repair to the requested parser."
    result = render_context("Please fix the request parser today.", scope=setup["scope"], memory=setup["memory"])
    assert result["matches"][0]["id"] == record["id"]
    assert result["matches"][0]["shared_terms"] == ["fix", "parser", "request"]
    assert setup["lesson"] in result["context"]
    assert "Current explicit instructions take precedence" in result["context"]
    assert "do not silently choose" in result["context"]
    assert "I changed unrelated files" not in result["context"]
    before_provenance = record["provenance"]
    revoked = revoke_lesson(record["id"], memory=setup["memory"])
    assert revoked["status"] == "revoked"
    assert revoked["provenance"] == before_provenance
    assert recall_lessons("repair request parser", scope=setup["scope"], memory=setup["memory"]) == []
    assert inspect_lessons(memory=setup["memory"])["lessons"][0] == revoked
    assert setup["triples"].read_bytes() == original


def test_stable_idempotent_and_revoked_lesson_cannot_silently_reactivate(setup):
    record = learn_lesson(**setup)
    initial = setup["memory"].read_bytes()
    assert learn_lesson(**setup) == record
    assert setup["memory"].read_bytes() == initial
    revoke_lesson(record["id"], memory=setup["memory"])
    tombstone = setup["memory"].read_bytes()
    assert learn_lesson(**setup)["status"] == "revoked"
    assert revoke_lesson(record["id"], memory=setup["memory"])["status"] == "revoked"
    assert setup["memory"].read_bytes() == tombstone


def test_source_candidate_requires_confirmation_and_no_duplicate_rule_authoring(setup):
    record = learn_lesson(triples=setup["triples"], evidence=setup["evidence"],
                          scope=setup["scope"], memory=setup["memory"])
    assert record["interpretation"] == "source_verbatim"
    assert record["status"] == "candidate"
    assert record["lesson"] == record["provenance"]["episode"]["user_correction"]
    assert record["when"] == ["Repair the request parser."]
    assert recall_lessons("Repair the request parser today.", scope=setup["scope"], memory=setup["memory"]) == []
    confirmed = confirm_lesson(record["id"], memory=setup["memory"])
    assert confirmed["status"] == "active" and confirmed["id"] == record["id"]
    result = render_context("Repair the request parser today.", scope=setup["scope"], memory=setup["memory"])
    assert result["matches"][0]["id"] == record["id"]
    assert record["lesson"] in result["context"]
    revoke_lesson(record["id"], memory=setup["memory"])
    with pytest.raises(LessonMemoryError, match="revoked"):
        confirm_lesson(record["id"], memory=setup["memory"])


def test_cli_source_candidate_confirm_flow(setup, capsys):
    assert main(["learn", "--triples", str(setup["triples"]), "--evidence", "triple-id-1",
                 "--scope", setup["scope"], "--memory", str(setup["memory"])]) == 0
    record = json.loads(capsys.readouterr().out)["lesson"]
    assert record["status"] == "candidate"
    assert main(["confirm", record["id"], "--memory", str(setup["memory"])]) == 0
    assert json.loads(capsys.readouterr().out)["lesson"]["status"] == "active"


def test_public_sparse_task_cue_exposes_weak_match_and_requires_host_applicability(setup):
    setup["triples"].write_text(Triple("public-fiction", "synthetic", "I washed sink dishes.",
                                      "No, collect the dirty table plates and wash those too.",
                                      "I will collect and wash the table plates.",
                                      "Do the dishes.").to_json() + "\n")
    record = learn_lesson(triples=setup["triples"], evidence=setup["evidence"],
                          scope=setup["scope"], memory=setup["memory"])
    confirm_lesson(record["id"], memory=setup["memory"])
    for instruction in ("Do the dishes.", "Dishes after supper.", "Buy dishes."):
        result = render_context(instruction, scope=setup["scope"], memory=setup["memory"])
        assert result["matches"][0]["weak_match"] is True
        assert result["matches"][0]["shared_terms"] == ["dishes"]
        assert "Single-term overlaps are weak cues" in result["context"]
    # A buying task is a retrieval false match. The host must reject its
    # applicability; lexical retrieval deliberately does not execute a task.
    assert recall_lessons("Wash up.", scope=setup["scope"], memory=setup["memory"]) == []


def test_truncated_source_candidate_cannot_activate_without_interpretation(setup):
    setup["triples"].write_text(Triple("synthetic", "t", "prior", "x" * 801,
                                      "repair", "repair request parser").to_json() + "\n")
    record = learn_lesson(triples=setup["triples"], evidence=setup["evidence"],
                          scope=setup["scope"], memory=setup["memory"])
    assert record["provenance"]["truncated"]["user_correction"] is True
    with pytest.raises(LessonMemoryError, match="truncated"):
        confirm_lesson(record["id"], memory=setup["memory"])
    assert inspect_lessons(memory=setup["memory"])["lessons"][0]["status"] == "candidate"
    interpreted = learn_lesson(**setup)
    assert interpreted["interpretation"] == "host_supplied" and interpreted["status"] == "active"


@pytest.mark.parametrize("instruction", [
    "parser", "Fix the compiler.", "Please help with this today.", "repair deployment service",
    "Investigate payment latency across production databases and request unrelated parser ownership reviews",
])
def test_conservative_abstention_including_single_term_overlap(setup, instruction):
    learn_lesson(**setup)
    assert recall_lessons(instruction, scope=setup["scope"], memory=setup["memory"]) == []


def test_only_when_examples_drive_matching_and_scope_is_exact(setup):
    setup["lesson"] = "Always publish payment reports immediately."
    learn_lesson(**setup)
    assert recall_lessons("publish payment reports immediately", scope=setup["scope"], memory=setup["memory"]) == []
    assert recall_lessons("repair request parser", scope="other/project", memory=setup["memory"]) == []
    assert recall_lessons("repair request parser", scope=setup["scope"].upper(), memory=setup["memory"]) == []


def test_multiple_interpretations_are_exposed_without_silent_winner(setup):
    first = learn_lesson(**setup)
    second = learn_lesson(**{**setup, "lesson": "Ask the owner before repairing the parser."})
    result = render_context("repair request parser", scope=setup["scope"], memory=setup["memory"])
    assert {item["id"] for item in result["matches"]} == {first["id"], second["id"]}
    assert "If lessons conflict" in result["usage"]


def test_disabled_does_not_read_or_create_memory(setup, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("disabled memory was accessed")
    monkeypatch.setattr(module, "_load", forbidden)
    result = render_context("repair request parser", scope=setup["scope"], memory=setup["memory"], disabled=True)
    assert result["enabled"] is False and result["context"] == "" and result["matches"] == []
    assert not setup["memory"].exists()


def test_missing_memory_abstains_without_writing(setup):
    assert render_context("repair request parser", scope=setup["scope"], memory=setup["memory"])["matches"] == []
    assert inspect_lessons(memory=setup["memory"])["total"] == 0
    assert not setup["memory"].exists()


def test_new_memory_private_permissions_atomic_replacement(setup):
    learn_lesson(**setup)
    assert stat.S_IMODE(setup["memory"].stat().st_mode) == 0o600
    inode = setup["memory"].stat().st_ino
    setup["memory"].chmod(0o644)
    learn_lesson(**{**setup, "lesson": "A different interpreted lesson."})
    assert setup["memory"].stat().st_ino != inode
    assert stat.S_IMODE(setup["memory"].stat().st_mode) == 0o600
    assert not list(setup["memory"].parent.glob(".hermeneutic-*"))


def test_snapshot_bounded_original_hash_retained(setup):
    original = Triple("s" * 500, "t" * 100, "p" * 3000, "c" * 2000, "n" * 3000, "o" * 3000)
    setup["triples"].write_text(original.to_json() + "\n")
    record = learn_lesson(**setup)
    provenance = record["provenance"]
    assert provenance["episode"]["user_correction"] == "c" * 800
    assert provenance["truncated"]["user_correction"] is True
    assert provenance["record_sha256"] == hashlib.sha256(setup["triples"].read_bytes()).hexdigest()


@pytest.mark.parametrize("patch", [
    {"scope": ""}, {"scope": " project"}, {"lesson": " "}, {"lesson": "x" * 1201},
    {"when": []}, {"when": ["x" * 241]}, {"when": ["repair parser"] * 2},
    {"evidence": "triple-id-0"}, {"evidence": "triple-id-99"},
])
def test_invalid_teaching_inputs_leave_memory_untouched(setup, patch):
    with pytest.raises(LessonMemoryError):
        learn_lesson(**{**setup, **patch})
    assert not setup["memory"].exists()


@pytest.mark.parametrize("raw", [
    b"not JSON", b"\xff", b'{"schema_version":1,"schema_version":1}',
    b'{"schema_version":true,"revision":0,"lessons":[]}',
    b'{"schema_version":1,"revision":NaN,"lessons":[]}',
    b'{"schema_version":2,"revision":0,"lessons":[]}',
    b'{"schema_version":1,"revision":0,"lessons":[{}]}',
])
def test_malformed_memory_is_rejected_without_replacement(setup, raw):
    setup["memory"].write_bytes(raw)
    with pytest.raises(LessonMemoryError):
        learn_lesson(**setup)
    with pytest.raises(LessonMemoryError):
        render_context("repair request parser", scope=setup["scope"], memory=setup["memory"])
    assert setup["memory"].read_bytes() == raw
    assert not list(setup["memory"].parent.glob(".hermeneutic-*"))


def test_modified_lesson_identity_is_not_accepted(setup):
    learn_lesson(**setup)
    store = json.loads(setup["memory"].read_bytes())
    store["lessons"][0]["lesson"] = "Tampered lesson"
    setup["memory"].write_text(json.dumps(store))
    with pytest.raises(LessonMemoryError, match="identity"):
        inspect_lessons(memory=setup["memory"])


def test_malformed_corpus_record_after_selected_episode_is_not_ignored(setup):
    with setup["triples"].open("a") as output:
        output.write("{bad record}\n")
    with pytest.raises(LessonMemoryError):
        learn_lesson(**setup)
    assert not setup["memory"].exists()


@pytest.mark.parametrize("which", ["memory", "triples", "parent"])
def test_symlinks_rejected_and_target_unchanged(setup, tmp_path, which):
    original = setup["triples"].read_bytes()
    if which == "memory":
        setup["memory"].symlink_to(setup["triples"])
    elif which == "triples":
        alias = tmp_path / "alias.jsonl"
        alias.symlink_to(setup["triples"])
        setup["triples"] = alias
    else:
        alias = tmp_path / "directory-alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        setup["memory"] = alias / "memory.json"
    with pytest.raises((OSError, LessonMemoryError)):
        learn_lesson(**setup)
    assert setup["triples"].read_bytes() == original


def test_change_before_replace_is_detected_without_overwriting_external_writer(setup, monkeypatch):
    learn_lesson(**setup)
    expected = module._assert_unchanged
    external = b"external writer must survive"

    def change_then_check(directory, name, token):
        setup["memory"].write_bytes(external)
        expected(directory, name, token)

    monkeypatch.setattr(module, "_assert_unchanged", change_then_check)
    with pytest.raises(LessonMemoryError, match="changed"):
        learn_lesson(**{**setup, "lesson": "New interpretation."})
    assert setup["memory"].read_bytes() == external
    assert not list(setup["memory"].parent.glob(".hermeneutic-*"))


def test_atomic_write_failure_preserves_existing_memory(setup, monkeypatch):
    learn_lesson(**setup)
    before = setup["memory"].read_bytes()

    def fail(*args, **kwargs):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        learn_lesson(**{**setup, "lesson": "New interpretation."})
    assert setup["memory"].read_bytes() == before
    assert not list(setup["memory"].parent.glob(".hermeneutic-*"))


def test_lock_collision_fails_without_touching_existing_lock(setup):
    digest = hashlib.sha256(os.fsencode(setup["memory"].name)).hexdigest()[:16]
    lock = setup["memory"].parent / f".hermeneutic-{digest}.lock"
    lock.write_text("existing owner")
    with pytest.raises(LessonMemoryError, match="progress"):
        learn_lesson(**setup)
    assert lock.read_text() == "existing owner"
    assert not setup["memory"].exists()


def test_no_network_and_no_implicit_corpus_learning(setup, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("lesson memory attempted network")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert inspect_lessons(memory=setup["memory"])["lessons"] == []
    learn_lesson(**setup)
    assert render_context("repair request parser", scope=setup["scope"], memory=setup["memory"])["matches"]


def test_cli_loop_returns_json_and_never_requires_rule_restatement(setup, capsys):
    assert main(["learn", "--triples", str(setup["triples"]), "--evidence", "triple-id-1",
                 "--lesson", setup["lesson"], "--scope", setup["scope"],
                 "--when", "repair request parser", "--memory", str(setup["memory"])]) == 0
    learned = json.loads(capsys.readouterr().out)["lesson"]
    assert main(["context", "Repair the request parser.", "--scope", setup["scope"],
                 "--memory", str(setup["memory"])]) == 0
    context = json.loads(capsys.readouterr().out)
    assert context["matches"][0]["id"] == learned["id"]
    assert setup["lesson"] in context["context"]
    assert main(["lessons", "--memory", str(setup["memory"])]) == 0
    assert json.loads(capsys.readouterr().out)["total"] == 1
    assert main(["revoke", learned["id"], "--memory", str(setup["memory"])]) == 0
    assert json.loads(capsys.readouterr().out)["lesson"]["status"] == "revoked"
    assert main(["context", "repair request parser", "--scope", setup["scope"],
                 "--memory", str(setup["memory"]), "--disabled"]) == 0
    assert json.loads(capsys.readouterr().out)["context"] == ""


def test_cli_errors_do_not_echo_private_content(setup, capsys):
    setup["memory"].write_text("private-secret-malformed-memory")
    assert main(["lessons", "--memory", str(setup["memory"])]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert "private-secret" not in result.err
    assert "ERROR" in result.err


@pytest.mark.parametrize("limit", [0, 6, True])
def test_context_result_limit_validation(setup, limit):
    with pytest.raises(LessonMemoryError):
        recall_lessons("repair request parser", scope=setup["scope"], memory=setup["memory"], limit=limit)
