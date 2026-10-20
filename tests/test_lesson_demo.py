"""Independent frozen synthetic lesson-transfer protocol and deterministic CLI checks."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-lesson-demo.py"


def _runner():
    spec = importlib.util.spec_from_file_location("lesson_transfer_check", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frozen_validation_files_match_pre_execution_protocol_hashes():
    runner = _runner()
    design, frozen, protocol = runner.load_fixtures()
    assert design["synthetic"] is frozen["synthetic"] is protocol["synthetic"] is True
    assert protocol["frozen_before_first_run"] is True
    assert protocol["design_excluded_from_validation"] is True
    assert protocol["freeze_history"][0]["execution_occurred"] is False
    assert protocol["fresh_agent_protocol"]["same_instruction_and_world_per_pair"] is True
    assert protocol["fresh_agent_protocol"]["no_retry_or_tuning_after_results"] is True
    assert len(frozen["cases"]) == protocol["fresh_agent_protocol"]["pairs"]
    assert len(frozen["cases"]) * 2 == protocol["fresh_agent_protocol"]["jobs"]
    assert {case["kind"] for case in frozen["cases"]} == {
        "transfer",
        "unrelated_control",
        "scope_control",
        "misleading_neighbor",
    }


def test_later_tasks_do_not_repeat_the_taught_lesson():
    _, frozen, _ = _runner().load_fixtures()
    episodes = {episode["key"]: episode for episode in frozen["episodes"]}
    for case in frozen["cases"]:
        lesson = episodes[case["lesson_key"]]["teaching"]["lesson"]
        assert lesson not in case["instruction"]
        assert "triple-id" not in case["instruction"]
        if case["kind"] == "transfer":
            assert case["instruction"] != episodes[case["lesson_key"]]["episode"]["orig_prompt"]


def test_downstream_success_requires_correct_actions_not_a_lesson_id():
    runner = _runner()
    case = {"expected_selected_ids": ["patch", "receipt"]}
    empty_with_attribution = {
        "selected_ids": [],
        "memory_checks": [
            {"source_id": "lesson-1", "applies": True, "reason": "Relevant project."},
        ],
    }
    assert runner.score_action(case, empty_with_attribution)["exact_completion"] is False
    right_actions = {"selected_ids": ["receipt", "patch"], "memory_checks": []}
    assert runner.score_action(case, right_actions)["exact_completion"] is True
    duplicates = {"selected_ids": ["receipt", "patch", "patch"], "memory_checks": []}
    assert runner.score_action(case, duplicates)["exact_completion"] is False
    extra = {"selected_ids": ["receipt", "patch", "credential"], "memory_checks": []}
    assert runner.score_action(case, extra)["extra_ids"] == ["credential"]


def test_summary_distinguishes_candidate_recall_action_transfer_and_controls():
    runner = _runner()
    cases = [{"id": "positive", "kind": "transfer"}, {"id": "negative", "kind": "misleading_neighbor"}]
    success = {"score": {"exact_completion": True, "extra_ids": []}}
    failure = {"score": {"exact_completion": False, "extra_ids": ["unwanted"]}}
    pairs = [
        {"case_id": "positive", "retrieved_candidates": 1, "without_memory": failure, "with_memory": success},
        {"case_id": "negative", "retrieved_candidates": 1, "without_memory": success, "with_memory": success},
    ]
    result = runner.aggregate_pairs(cases, pairs)
    assert result["improved_pairs"] == 1
    assert result["negative_control_denominator"] == 1
    assert result["negative_controls_with_retrieved_candidate"] == 1
    assert result["behavioral_overgeneralizations_with_memory"] == 0


def test_action_prompt_only_changes_supplied_context_between_conditions():
    runner = _runner()
    prompt = runner.action_prompt("Later task.", "select artifacts", [{"id": "artifact"}], "project", None)
    supplied = {"context": "[attributed synthetic lesson] Check applicability before selecting."}
    recalled = runner.action_prompt("Later task.", "select artifacts", [{"id": "artifact"}], "project", supplied)
    assert prompt.split("RECALLED CONTEXT")[0] == recalled.split("RECALLED CONTEXT")[0]
    assert "expected_selected_ids" not in prompt + recalled
    assert "No correction context supplied." in prompt
    assert supplied["context"] in recalled


def test_synthetic_deterministic_cli_mechanics_and_receipt(tmp_path):
    receipt = tmp_path / "receipt.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--receipt", str(receipt)],
        text=True,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    parsed = json.loads(receipt.read_text())
    assert parsed["stage"] == "deterministic_host_mechanics"
    assert parsed["passed"] is True
    assert all(parsed["checks"].values())
    assert "fresh" in " ".join(parsed["limitations"])
    assert parsed["design_demo"]["source_provenance"]["evidence"] == "triple-id-1"


def test_fixture_tampering_is_detected_before_use(tmp_path, monkeypatch):
    runner = _runner()
    design, _, protocol = runner.load_fixtures()
    (tmp_path / "protocol.json").write_text(json.dumps(protocol))
    (tmp_path / "design-demo.json").write_text(json.dumps(design) + "tampering")
    monkeypatch.setattr(runner, "FIXTURES", tmp_path)
    with pytest.raises(ValueError, match="Frozen fixture changed"):
        runner.load_fixtures()


def test_final_counterfactual_is_frozen_and_uses_source_candidate_without_answer_in_task():
    runner = _runner()
    frozen, protocol = runner.load_counterfactual()
    assert protocol["final_authorized_evaluation_iteration"] is True
    assert protocol["source_tuning_allowed"] is False
    assert protocol["retries"] == 0
    assert len(frozen["cases"]) == protocol["pairs"] == 3
    assert protocol["calls"] == 6
    assert {case["kind"] for case in frozen["cases"]} == {"transfer", "misleading_neighbor", "unrelated_control"}
    assert all(episode["teaching_mode"] == "source_default_confirmed" for episode in frozen["episodes"])
    assert all(set(episode["teaching"]) == {"scope"} for episode in frozen["episodes"])
    positive = next(case for case in frozen["cases"] if case["kind"] == "transfer")
    target = positive["prespecified_nonobvious_inclusion"]
    assert target not in positive["instruction"]
    assert target in positive["expected_selected_ids"]
    assert all(target not in case["expected_selected_ids"] for case in frozen["cases"] if case["kind"] != "transfer")
