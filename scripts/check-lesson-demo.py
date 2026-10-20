"""Check synthetic interpreted-lesson contracts; optionally run frozen fresh-agent pairs.

No private logs or credentials are read. Live agent calls are explicit opt-in.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evals" / "lesson-transfer"
CLI_PYTHON = sys.executable
SOURCE_MODE = False
EVENT_DIRECTORY: Path | None = None
ACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "selected_ids": {"type": "array", "items": {"type": "string"}},
        "memory_checks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "source_id": {"type": "string"},
                    "applies": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["source_id", "applies", "reason"],
            },
        },
        "explanation": {"type": "string"},
    },
    "required": ["selected_ids", "memory_checks", "explanation"],
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fixtures() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = json.loads((FIXTURES / "protocol.json").read_text())
    for filename, expected in protocol["files_sha256"].items():
        if digest(FIXTURES / filename) != expected:
            raise ValueError(f"Frozen fixture changed: {filename}")
    return (
        json.loads((FIXTURES / "design-demo.json").read_text()),
        json.loads((FIXTURES / "frozen-cases.json").read_text()),
        protocol,
    )


def clean_environment(home: Path) -> dict[str, str]:
    environment = {**os.environ, "HERMENEUTIC_HOME": str(home)}
    environment.pop("HERMENEUTIC_TELEMETRY", None)
    environment.pop("PYTHONPATH", None)
    return environment


def cli(workspace: Path, *arguments: str, success: bool = True) -> Any:
    # Default is the installed package under isolated Python, outside its checkout.
    command = [CLI_PYTHON, "-I", "-m", "hermeneutic.cli", *arguments]
    if SOURCE_MODE:
        command = [
            CLI_PYTHON,
            "-I",
            "-c",
            "import sys; sys.path.insert(0, sys.argv.pop(1)); "
            "from hermeneutic.cli import main; raise SystemExit(main())",
            str(ROOT / "src"),
            *arguments,
        ]
    result = subprocess.run(
        command,
        cwd=workspace,
        env=clean_environment(workspace / "home"),
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )
    if success and result.returncode != 0:
        raise RuntimeError(f"CLI {arguments[0]} failed with exit {result.returncode}: {result.stderr}")
    if not success:
        return result
    return json.loads(result.stdout)


def teach(
    workspace: Path,
    name: str,
    episode: dict,
    teaching: dict,
    memory: Path,
    *,
    explicit=True,
) -> tuple[dict, Path]:
    session_root = workspace / name
    session_root.mkdir()
    session = session_root / "session.json"
    session.write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": episode["orig_prompt"]},
                    {"role": "assistant", "content": episode["prior_assistant"]},
                    {"role": "user", "content": episode["user_correction"]},
                    {"role": "assistant", "content": episode["next_assistant"]},
                ]
            }
        )
    )
    corpus = workspace / f"{name}-triples.jsonl"
    result = cli(
        workspace,
        "mine",
        str(session_root),
        "--format",
        "openai",
        "--glob",
        "session.json",
        "--out",
        str(corpus),
        success=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"CLI mine failed with exit {result.returncode}: {result.stderr}")
    rows = [json.loads(line) for line in corpus.read_text().splitlines()]
    if len(rows) != 1 or rows[0]["user_correction"] != episode["user_correction"]:
        raise AssertionError("Synthetic correction was not mined as its attributed source episode.")
    arguments = [
        "learn",
        "--triples",
        str(corpus),
        "--evidence",
        "triple-id-1",
        "--scope",
        teaching["scope"],
        "--memory",
        str(memory),
    ]
    if explicit:
        arguments.extend(["--lesson", teaching["lesson"]])
        for example in teaching["when"]:
            arguments.extend(["--when", example])
    before = corpus.read_bytes()
    learned = cli(workspace, *arguments)["lesson"]
    if corpus.read_bytes() != before:
        raise AssertionError("Teaching changed source correction evidence.")
    return learned, corpus


def context(workspace: Path, instruction: str, scope: str, memory: Path, *, disabled=False) -> dict:
    arguments = ["context", instruction, "--scope", scope, "--memory", str(memory)]
    if disabled:
        arguments.append("--disabled")
    return cli(workspace, *arguments)


def records(value: Any) -> list[dict]:
    if isinstance(value, list):
        return value
    return value["lessons"]


def package_identity(workspace: Path) -> dict:
    identity_code = (
        "import json,hashlib,pathlib,hermeneutic,hermeneutic.lessons,hermeneutic.cli; "
        "print(json.dumps({'version':hermeneutic.__version__,'package_path':hermeneutic.__file__,"
        "'lessons_sha256':hashlib.sha256(pathlib.Path(hermeneutic.lessons.__file__).read_bytes()).hexdigest(),"
        "'cli_sha256':hashlib.sha256(pathlib.Path(hermeneutic.cli.__file__).read_bytes()).hexdigest()}))"
    )
    if SOURCE_MODE:
        identity_code = f"import sys; sys.path.insert(0, {str(ROOT / 'src')!r}); " + identity_code
    identity_result = subprocess.run(
        [CLI_PYTHON, "-I", "-c", identity_code],
        cwd=workspace,
        env=clean_environment(workspace / "home"),
        text=True,
        capture_output=True,
        check=True,
        timeout=20,
    )
    return json.loads(identity_result.stdout)


def deterministic(workspace: Path, design: dict, frozen: dict, protocol: dict) -> tuple[dict, dict, dict]:
    checks: dict[str, bool] = {}
    candidate_memory = workspace / "source-candidate.json"
    candidate, _ = teach(
        workspace, "public-source-candidate", design["episode"], design["teaching"], candidate_memory, explicit=False
    )
    checks["default_capture_is_source_verbatim_candidate"] = (
        candidate["status"] == "candidate"
        and candidate["interpretation"] == "source_verbatim"
        and candidate["lesson"] == design["episode"]["user_correction"]
    )
    pending = context(workspace, design["episode"]["orig_prompt"], design["teaching"]["scope"], candidate_memory)
    checks["unconfirmed_candidate_is_not_supplied"] = pending["matches"] == [] and not pending["context"]
    confirmed = cli(workspace, "confirm", candidate["id"], "--memory", str(candidate_memory))["lesson"]
    confirmed_context = context(
        workspace, design["episode"]["orig_prompt"], design["teaching"]["scope"], candidate_memory
    )
    checks["confirmation_activates_source_candidate"] = confirmed["status"] == "active" and any(
        match["id"] == candidate["id"] for match in confirmed_context["matches"]
    )
    source_later_context = context(
        workspace, design["later_instruction"], design["teaching"]["scope"], candidate_memory
    )
    memory = workspace / "lessons.json"
    demo, demo_corpus = teach(workspace, "public-dishes", design["episode"], design["teaching"], memory)
    demo_context = context(workspace, design["later_instruction"], design["teaching"]["scope"], memory)
    interpreted_demo_retrieved = (
        len(demo_context["matches"]) == 1
        and demo_context["matches"][0]["id"] == demo["id"]
        and "provenance" in demo_context["matches"][0]
    )
    inspected = records(cli(workspace, "lessons", "--memory", str(memory)))
    checks["inspect_contains_explicit_interpretation"] = any(
        record["id"] == demo["id"] and record["lesson"] == design["teaching"]["lesson"] for record in inspected
    )
    checks["provenance_matches_source_episode"] = (
        demo["provenance"]["evidence"] == "triple-id-1"
        and demo["provenance"]["corpus_sha256"] == digest(demo_corpus)
        and demo["provenance"]["episode"]["user_correction"] == design["episode"]["user_correction"]
    )
    checks["source_correction_preserved"] = (
        json.loads(demo_corpus.read_text().strip())["user_correction"] == design["episode"]["user_correction"]
    )
    disabled = context(workspace, design["later_instruction"], design["teaching"]["scope"], memory, disabled=True)
    checks["disabled_has_no_matches_or_context"] = disabled["matches"] == [] and not disabled["context"]
    empty = context(workspace, design["later_instruction"], design["teaching"]["scope"], workspace / "untaught.json")
    checks["uncorrected_memory_has_no_context"] = empty["matches"] == [] and not empty["context"]
    uncorrected_root = workspace / "uncorrected"
    uncorrected_root.mkdir()
    uncorrected = uncorrected_root / "session.json"
    uncorrected.write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": design["episode"]["orig_prompt"]},
                    {"role": "assistant", "content": design["episode"]["prior_assistant"]},
                ]
            }
        )
    )
    untaught_corpus = workspace / "uncorrected-triples.jsonl"
    cli(
        workspace,
        "mine",
        str(uncorrected_root),
        "--format",
        "openai",
        "--glob",
        "session.json",
        "--out",
        str(untaught_corpus),
        success=False,
    )
    checks["uncorrected_episode_mines_no_evidence"] = untaught_corpus.read_text() == ""
    unavailable = cli(
        workspace,
        "learn",
        "--triples",
        str(untaught_corpus),
        "--evidence",
        "triple-id-1",
        "--lesson",
        design["teaching"]["lesson"],
        "--scope",
        design["teaching"]["scope"],
        "--when",
        design["teaching"]["when"][0],
        "--memory",
        str(workspace / "untaught.json"),
        success=False,
    )
    checks["uncorrected_episode_cannot_teach_attributed_lesson"] = unavailable.returncode != 0
    revoked = cli(workspace, "revoke", demo["id"], "--memory", str(memory))["lesson"]
    after_revoke = context(workspace, design["later_instruction"], design["teaching"]["scope"], memory)
    checks["revoke_removes_context"] = revoked["status"] == "revoked" and after_revoke["matches"] == []
    checks["inspect_retains_revoked_tombstone"] = any(
        record["id"] == demo["id"] and record["status"] == "revoked"
        for record in records(cli(workspace, "lessons", "--memory", str(memory)))
    )
    sources: dict[str, dict] = {}
    for episode in frozen["episodes"]:
        learned, _ = teach(workspace, episode["key"], episode["episode"], episode["teaching"], memory)
        sources[episode["key"]] = learned
    contexts = {}
    retrieval = []
    for case in frozen["cases"]:
        supplied = context(workspace, case["instruction"], case["scope"], memory)
        contexts[case["id"]] = supplied
        expected_match = case["kind"] in {"transfer", "misleading_neighbor"}
        matching = any(match["id"] == sources[case["lesson_key"]]["id"] for match in supplied["matches"])
        retrieval.append(
            {
                "case_id": case["id"],
                "kind": case["kind"],
                "candidate_expected": expected_match,
                "candidate_retrieved": matching,
                "matches_count": len(supplied["matches"]),
                "attributed": all("provenance" in match for match in supplied["matches"]),
            }
        )
        checks[f"frozen_retrieval:{case['id']}"] = matching == expected_match
    source_paths = [ROOT / "src/hermeneutic/cli.py", ROOT / "src/hermeneutic/lessons.py"]
    identity = package_identity(workspace)
    checks["evaluated_core_matches_source_freeze"] = (
        identity["lessons_sha256"] == protocol["core_source_freeze"]["lessons_sha256"]
        and identity["cli_sha256"] == protocol["core_source_freeze"]["cli_sha256"]
    )
    receipt = {
        "schema_version": 1,
        "synthetic": True,
        "stage": "deterministic_host_mechanics",
        "python": CLI_PYTHON,
        "package_mode": "source" if SOURCE_MODE else "installed",
        "package_identity": identity,
        "fixture_sha256": protocol["files_sha256"],
        "source_sha256": {str(path.relative_to(ROOT)): digest(path) for path in source_paths if path.exists()},
        "checks": checks,
        "passed": all(checks.values()),
        "design_diagnostics": {
            "source_default_later_context_retrieved": bool(source_later_context["matches"]),
            "host_interpreted_later_context_retrieved": interpreted_demo_retrieved,
            "excluded_from_required_frozen_checks": True,
        },
        "retrieval": retrieval,
        "retrieval_metrics": {
            "positive_denominator": sum(row["kind"] == "transfer" for row in retrieval),
            "positives_retrieved": sum(row["candidate_retrieved"] for row in retrieval if row["kind"] == "transfer"),
            "strict_negative_denominator": sum(
                row["kind"] in {"unrelated_control", "scope_control"} for row in retrieval
            ),
            "strict_negative_false_matches": sum(
                row["matches_count"] > 0 for row in retrieval if row["kind"] in {"unrelated_control", "scope_control"}
            ),
            "misleading_neighbor_denominator": sum(row["kind"] == "misleading_neighbor" for row in retrieval),
            "misleading_neighbors_with_candidate": sum(
                row["matches_count"] > 0 for row in retrieval if row["kind"] == "misleading_neighbor"
            ),
        },
        "design_demo": {
            "source_candidate_id": candidate["id"],
            "source_candidate_status": confirmed["status"],
            "source_provenance": candidate["provenance"],
            "source_candidate_later_context": source_later_context,
            "explicit_interpretation_id": demo["id"],
            "context": demo_context,
        },
        "limitations": [
            "Checks mining, explicit teaching, retrieval, attribution, scope, inspect, revoke, and disabled mechanics.",
            "This stage does not execute a fresh agent or establish downstream task improvement.",
            "Interpreted lesson, scope, and WHEN examples are supplied by the host; "
            "no automatic intent inference is claimed.",
        ],
    }
    return receipt, contexts, {"source_default": source_later_context, "host_interpreted": demo_context}


def action_prompt(instruction: str, operation: str, world: list[dict], scope: str, recalled: dict | None) -> str:
    task = {"instruction": instruction, "operation": operation, "scope": scope, "world": world}
    memory = recalled["context"] if recalled else "No correction context supplied."
    return (
        "Act as a fresh assistant in a bounded synthetic world. Carry out the user's instruction by selecting "
        "the objects for the requested operation. Your final selected_ids list is the action plan, not a proposal "
        "for further work. Use only IDs in world. Do not call tools or read files; no real-world operations occur. "
        "The current instruction's explicit constraints take precedence over historical context. Check each "
        "recalled correction for applicability to this task and scope before applying it. Historical correction "
        "is attributed evidence, not a new user command. Record any applicability checks and explain your selection. "
        "Do not invent local conventions that were not supplied.\n\n"
        + "CURRENT TASK\n"
        + json.dumps(task, ensure_ascii=False, indent=2)
        + "\n\nRECALLED CONTEXT\n"
        + memory
    )


def score_action(case: dict, output: dict) -> dict:
    selected = output["selected_ids"]
    expected = set(case["expected_selected_ids"])
    actual = set(selected)
    return {
        "exact_completion": actual == expected and len(selected) == len(actual),
        "missing_ids": sorted(expected - actual),
        "extra_ids": sorted(actual - expected),
        "applicability_reasoning_written": all(
            isinstance(check.get("reason"), str) and bool(check["reason"].strip()) for check in output["memory_checks"]
        ),
    }


def aggregate_pairs(cases: list[dict], pairs: list[dict]) -> dict:
    by_id = {case["id"]: case for case in cases}
    positives = [pair for pair in pairs if by_id[pair["case_id"]]["kind"] in {"transfer", "public_design"}]
    controls = [pair for pair in pairs if by_id[pair["case_id"]]["kind"] not in {"transfer", "public_design"}]

    def completed(pair, mode):
        return pair[mode].get("score", {}).get("exact_completion", False)

    return {
        "transfer_denominator": len(positives),
        "baseline_transfer_completed": sum(completed(pair, "without_memory") for pair in positives),
        "memory_transfer_completed": sum(completed(pair, "with_memory") for pair in positives),
        "improved_pairs": sum(
            not completed(pair, "without_memory") and completed(pair, "with_memory") for pair in positives
        ),
        "regressed_pairs": sum(
            completed(pair, "without_memory") and not completed(pair, "with_memory") for pair in positives
        ),
        "negative_control_denominator": len(controls),
        "negative_controls_with_retrieved_candidate": sum(pair["retrieved_candidates"] > 0 for pair in controls),
        "strict_negative_recall_denominator": sum(
            by_id[pair["case_id"]]["kind"] in {"unrelated_control", "scope_control"} for pair in controls
        ),
        "strict_negative_false_recalls": sum(
            pair["retrieved_candidates"] > 0
            for pair in controls
            if by_id[pair["case_id"]]["kind"] in {"unrelated_control", "scope_control"}
        ),
        "behavioral_overgeneralizations_with_memory": sum(
            bool(pair["with_memory"].get("score", {}).get("extra_ids", [])) for pair in controls
        ),
        "baseline_control_completed": sum(completed(pair, "without_memory") for pair in controls),
        "memory_control_completed": sum(completed(pair, "with_memory") for pair in controls),
        "execution_errors": sum("error" in pair[mode] for pair in pairs for mode in ("without_memory", "with_memory")),
    }


def run_live(
    workspace: Path,
    frozen: dict,
    contexts: dict,
    protocol: dict,
    destination: Path,
    *,
    public=False,
) -> dict:
    executable = shutil.which("codex")
    if executable is None:
        raise RuntimeError("codex executable is unavailable; no fresh-agent comparison was run.")
    version = subprocess.run([executable, "--version"], text=True, capture_output=True, check=True).stdout.strip()
    output_root = destination.parent / "runs"
    output_root.mkdir(parents=True, exist_ok=True)
    event_root = EVENT_DIRECTORY or Path(tempfile.mkdtemp(prefix="hermeneutic-agent-events-")).resolve()
    event_root.mkdir(parents=True, exist_ok=True)
    final_iteration = protocol.get("final_authorized_evaluation_iteration", False)
    receipt = {
        "schema_version": 1,
        "synthetic": True,
        "stage": (
            "fresh_codex_final_counterfactual"
            if final_iteration
            else "fresh_codex_public_design"
            if public
            else "fresh_codex_action_plans"
        ),
        "excluded_from_original_denominators": public or final_iteration,
        "raw_events_retained_outside_git": True,
        "excluded_from_frozen_denominators": public,
        "fixture_sha256": protocol["files_sha256"],
        "codex_version": version,
        "protocol": protocol.get("fresh_agent_protocol", protocol),
        "pairs": [],
        "limitations": [
            "Synthetic object-selection action plans, not effects in a real repository or household.",
            "One fresh invocation per condition; stochastic results do not establish general effectiveness.",
            "No retries, lesson changes, WHEN changes, or fixture tuning after results.",
            "Applicability explanations are recorded for inspection; exact action sets are scored independently.",
        ],
    }
    for case in frozen["cases"]:
        pair = {
            "case_id": case["id"],
            "kind": case["kind"],
            "retrieved_candidates": len(contexts[case["id"]]["matches"]),
        }
        for mode in ("without_memory", "with_memory"):
            print(f"Fresh agent: {case['id']} / {mode}", flush=True)
            prompt = action_prompt(
                case["instruction"],
                case["operation"],
                case["world"],
                case["scope"],
                contexts[case["id"]] if mode == "with_memory" else None,
            )
            result_file = output_root / f"{case['id']}-{mode}.json"
            event_file = event_root / f"{case['id']}-{mode}.jsonl"
            # A separate empty working directory prevents a baseline invocation
            # from seeing teaching files or another invocation's artifacts.
            agent_directory = tempfile.TemporaryDirectory(prefix="hermeneutic-fresh-agent-")
            agent_workspace = Path(agent_directory.name).resolve()
            schema = agent_workspace / "action-schema.json"
            schema.write_text(json.dumps(ACTION_SCHEMA))
            command = [
                executable,
                "exec",
                "--ignore-user-config",
                "--ignore-rules",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--color",
                "never",
                "--json",
                "--cd",
                str(agent_workspace),
                "--output-schema",
                str(schema),
                "--output-last-message",
                str(result_file),
                "-",
            ]
            try:
                result = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    check=False,
                    env=clean_environment(agent_workspace / "host-home"),
                    timeout=120,
                )
                event_file.write_text(result.stdout)
                if result.returncode != 0:
                    pair[mode] = {
                        "error": "codex returned a nonzero exit",
                        "exit_code": result.returncode,
                        "events_sha256": digest(event_file),
                    }
                else:
                    output = json.loads(result_file.read_text())
                    pair[mode] = {
                        "output": output,
                        "score": score_action(case, output),
                        "exit_code": 0,
                        "events_sha256": digest(event_file),
                        "tool_items": sum(
                            event.get("item", {}).get("type") in {"command_execution", "mcp_tool_call"}
                            for line in result.stdout.splitlines()
                            if line.strip()
                            for event in [json.loads(line)]
                        ),
                    }
            except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
                pair[mode] = {"error": type(exc).__name__}
            finally:
                agent_directory.cleanup()
        receipt["pairs"].append(pair)
        receipt["metrics"] = aggregate_pairs(frozen["cases"], receipt["pairs"])
        destination.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    return receipt


def load_counterfactual() -> tuple[dict, dict]:
    protocol = json.loads((FIXTURES / "counterfactual-protocol.json").read_text())
    for filename, expected in {**protocol["files_sha256"], **protocol["original_fixture_sha256_unchanged"]}.items():
        if digest(FIXTURES / filename) != expected:
            raise ValueError(f"Frozen fixture changed: {filename}")
    return json.loads((FIXTURES / "counterfactual-cases.json").read_text()), protocol


def counterfactual_mechanics(workspace: Path, frozen: dict, protocol: dict) -> tuple[dict, dict]:
    memory = workspace / "final-candidates.json"
    checks = {}
    learned = {}
    for episode in frozen["episodes"]:
        candidate, _ = teach(workspace, episode["key"], episode["episode"], episode["teaching"], memory, explicit=False)
        checks["source_verbatim_candidate"] = (
            candidate["status"] == "candidate" and candidate["interpretation"] == "source_verbatim"
        )
        pending = context(workspace, episode["episode"]["orig_prompt"], episode["teaching"]["scope"], memory)
        checks["unconfirmed_not_supplied"] = not pending["matches"]
        confirmed = cli(workspace, "confirm", candidate["id"], "--memory", str(memory))["lesson"]
        checks["confirmed_active"] = confirmed["status"] == "active"
        checks["attributed_correction"] = (
            confirmed["provenance"]["episode"]["user_correction"] == episode["episode"]["user_correction"]
        )
        learned[episode["key"]] = confirmed
    contexts = {}
    retrieval = []
    for case in frozen["cases"]:
        supplied = context(workspace, case["instruction"], case["scope"], memory)
        contexts[case["id"]] = supplied
        retrieved = any(match["id"] == learned[case["lesson_key"]]["id"] for match in supplied["matches"])
        expected = case["kind"] in {"transfer", "misleading_neighbor"}
        checks[f"retrieval:{case['id']}"] = retrieved == expected
        retrieval.append(
            {
                "case_id": case["id"],
                "kind": case["kind"],
                "candidate_retrieved": retrieved,
                "candidate_expected": expected,
                "matches_count": len(supplied["matches"]),
            }
        )
    identity = package_identity(workspace)
    checks["core_unchanged"] = (
        identity["lessons_sha256"] == protocol["core_source_freeze"]["lessons_sha256"]
        and identity["cli_sha256"] == protocol["core_source_freeze"]["cli_sha256"]
    )
    return {
        "schema_version": 1,
        "synthetic": True,
        "stage": "final_counterfactual_mechanics",
        "package_identity": identity,
        "package_mode": "source" if SOURCE_MODE else "installed",
        "fixture_sha256": protocol["files_sha256"],
        "checks": checks,
        "passed": all(checks.values()),
        "retrieval": retrieval,
        "lesson_path": "source_default_confirmed",
        "separate_from_original_denominators": True,
    }, contexts


def main() -> int:
    global CLI_PYTHON, SOURCE_MODE, EVENT_DIRECTORY
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, help="Python from the installed wheel environment.")
    parser.add_argument(
        "--source", action="store_true", help="Explicitly use checkout source instead of installed package."
    )
    parser.add_argument("--counterfactual", action="store_true", help="Use the final frozen evaluation iteration.")
    parser.add_argument("--event-dir", type=Path, help="Keep raw runtime JSONL outside the repository.")
    parser.add_argument("--receipt", type=Path, help="Write deterministic mechanics receipt.")
    parser.add_argument("--live-agents", action="store_true", help="Opt into frozen fresh Codex comparisons.")
    parser.add_argument("--live-public-demo", action="store_true", help="Opt into a separate public dishes Codex pair.")
    parser.add_argument("--demo-memory", choices=["source_default", "host_interpreted"], default="host_interpreted")
    parser.add_argument("--live-receipt", type=Path, default=FIXTURES / "fresh-agent-results.json")
    parser.add_argument("--emit-demo-prompt", choices=["without_memory", "with_memory"])
    args = parser.parse_args()
    if args.python:
        CLI_PYTHON = str(args.python.absolute())
    SOURCE_MODE = args.source
    if args.event_dir:
        EVENT_DIRECTORY = args.event_dir.absolute()
    if args.counterfactual:
        if args.live_public_demo or args.emit_demo_prompt:
            parser.error("Final counterfactual cannot add public-demo agent calls.")
        frozen, protocol = load_counterfactual()
        with tempfile.TemporaryDirectory(prefix="hermeneutic-final-eval-") as directory:
            workspace = Path(directory).resolve()
            receipt, contexts = counterfactual_mechanics(workspace, frozen, protocol)
            if args.receipt:
                args.receipt.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
            print(json.dumps(receipt, indent=2), flush=True)
            if not receipt["passed"]:
                return 1
            if args.live_agents:
                live = run_live(workspace, frozen, contexts, protocol, args.live_receipt)
                print(json.dumps(live["metrics"], indent=2))
                return 1 if live["metrics"]["execution_errors"] else 0
        return 0
    design, frozen, protocol = load_fixtures()
    with tempfile.TemporaryDirectory(prefix="hermeneutic-lesson-check-") as directory:
        workspace = Path(directory).resolve()
        receipt, contexts, demo_contexts = deterministic(workspace, design, frozen, protocol)
        demo_context = demo_contexts[args.demo_memory]
        if args.emit_demo_prompt:
            print(
                action_prompt(
                    design["later_instruction"],
                    "wash selected dirty dishes",
                    design["world"],
                    design["teaching"]["scope"],
                    demo_context if args.emit_demo_prompt == "with_memory" else None,
                )
            )
            return 0 if receipt["passed"] else 1
        if args.receipt:
            args.receipt.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
        print(json.dumps(receipt, indent=2, ensure_ascii=False), flush=True)
        if not receipt["passed"]:
            return 1
        errors = 0
        if args.live_agents:
            live = run_live(workspace, frozen, contexts, protocol, args.live_receipt)
            print(json.dumps(live["metrics"], indent=2))
            errors += live["metrics"]["execution_errors"]
        if args.live_public_demo:
            public_case = {
                "id": "public-table-dishes",
                "kind": "public_design",
                "instruction": design["later_instruction"],
                "operation": "wash selected dirty dishes",
                "world": design["world"],
                "scope": design["teaching"]["scope"],
                "expected_selected_ids": design["expected_selected_ids"],
            }
            public_result = run_live(
                workspace,
                {"cases": [public_case]},
                {public_case["id"]: demo_context},
                protocol,
                args.live_receipt.with_name("public-dishes-agent-results.json"),
                public=True,
            )
            print(json.dumps(public_result["metrics"], indent=2))
            errors += public_result["metrics"]["execution_errors"]
        if errors:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
