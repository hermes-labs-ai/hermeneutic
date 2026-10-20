"""Reproduce the frozen fresh holdout against an installed candidate.

Example (run from the repository root):
  python3 evals/workflow-integration/fresh-evaluate.py \
    --python /path/to/isolated/bin/python --wrapper /path/to/recall.py \
    --fixtures evals/workflow-integration/fresh-fixtures.json \
    --safety-fixtures evals/workflow-integration/fresh-safety-fixtures.json \
    --reference-receipt evals/workflow-integration/fresh-receipt.json \
    --out /path/to/new-output-directory \
    --baseline-src /path/to/exported-baseline/src

The output directory must not exist. Raw results stay in its private run-v2
subdirectory. The optional baseline comparison uses the same serialized inputs
in a separate subprocess. This script does not install, activate, or tune a
candidate, edit fixtures, overwrite recorded results, or use a network backend.
"""

import argparse
import contextlib
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--python", required=True, help="Installed candidate Python interpreter")
parser.add_argument("--wrapper", required=True, help="Frozen host wrapper script")
parser.add_argument("--fixtures", required=True, help="Published fresh-fixtures.json")
parser.add_argument("--safety-fixtures", required=True, help="Published fresh-safety-fixtures.json")
parser.add_argument("--reference-receipt", required=True, help="Published fresh-receipt.json carrying frozen hashes")
parser.add_argument("--out", required=True, help="A new output directory; existing paths are refused")
parser.add_argument("--baseline-src", help="Optional exported baseline src directory")
parser.add_argument("--baseline-child", action="store_true", help=argparse.SUPPRESS)
args = parser.parse_args()
requested_python = os.path.abspath(os.path.expanduser(args.python))
if os.path.abspath(sys.executable) != requested_python:
    os.execv(requested_python, [requested_python, str(Path(__file__).absolute()), *sys.argv[1:]])
fixture_bytes = Path(args.fixtures).read_bytes()
safety_bytes = Path(args.safety_fixtures).read_bytes()
reference = json.loads(Path(args.reference_receipt).read_text())
freeze = {key: reference[key] for key in ("fixture_sha256", "frozen_at_utc")}
safety_freeze = {"safety_fixture_sha256": reference["safety_fixture_sha256"]}
assert hashlib.sha256(fixture_bytes).hexdigest() == freeze["fixture_sha256"]
assert hashlib.sha256(safety_bytes).hexdigest() == safety_freeze["safety_fixture_sha256"]
fixture = json.loads(fixture_bytes)
safety = json.loads(safety_bytes)
meta = reference["candidate"]
wrapper = Path(args.wrapper).resolve()
assert hashlib.sha256(wrapper.read_bytes()).hexdigest() == meta["wrapper_sha256"]
output = Path(args.out).absolute()


def run_baseline():
    import hermeneutic.memory
    import hermeneutic.triples
    from hermeneutic.memory import recall
    from hermeneutic.triples import mine_file

    run_dir = output / "run-v2"
    baseline_home = run_dir / "baseline-home"
    baseline_home.mkdir(exist_ok=False)
    attempts = []

    def audit_hook(event, values):
        if event in {
            "socket.connect",
            "socket.connect_ex",
            "socket.bind",
            "socket.getaddrinfo",
            "os.system",
            "subprocess.Popen",
            "os.exec",
            "os.posix_spawn",
            "os.fork",
        }:
            attempts.append(event)
            raise RuntimeError("independent baseline evaluation denied side effect")

    sys.addaudithook(audit_hook)
    mining = []
    for case in fixture["mining"]:
        path = run_dir / "logs" / (case["id"] + (".json" if case["format"] == "openai" else ".jsonl"))
        error = None
        try:
            actual = [t.user_correction for t in mine_file(path, fmt=case["format"])]
        except Exception as exc:
            actual = []
            error = type(exc).__name__
        passed = case.get("expected_text") in actual if case["expected_correction"] else not actual
        mining.append(
            {
                "id": case["id"],
                "expected_correction": case["expected_correction"],
                "returned": len(actual),
                "passed": passed,
                "error": error,
                "actual_corrections": actual,
            }
        )
    recall_cases = []
    for case in fixture["recall_relevant"] + fixture["recall_irrelevant"]:
        error = None
        try:
            matches = recall(case["prompt"], run_dir / "corpus.jsonl", home=baseline_home)
            actual = [m.get("evidence") for m in matches]
        except Exception as exc:
            matches = []
            actual = []
            error = type(exc).__name__
        relevant = "expected_evidence" in case
        passed = case["expected_evidence"] in actual if relevant else not actual
        recall_cases.append(
            {
                "id": case["id"],
                "relevant": relevant,
                "expected_evidence": case.get("expected_evidence"),
                "actual_evidence": actual,
                "passed": passed,
                "error": error,
                "matches": matches,
            }
        )
    positive = [c for c in mining if c["expected_correction"]]
    negative = [c for c in mining if not c["expected_correction"]]
    relevant = [c for c in recall_cases if c["relevant"]]
    irrelevant = [c for c in recall_cases if not c["relevant"]]
    baseline = {
        "source_commit": "4f357b7",
        "fixture_sha256": freeze["fixture_sha256"],
        "calling_convention": (
            "mine_file(path,fmt=fmt); recall(prompt,corpus,home=isolated_home), "
            "baseline default keyword recall and default limit; no candidate-only kwargs"
        ),
        "mining": {
            "positive_samples": len(positive),
            "recovered": sum(c["passed"] for c in positive),
            "recovery": sum(c["passed"] for c in positive) / len(positive),
            "negative_samples": len(negative),
            "false_positives": sum(not c["passed"] for c in negative),
            "false_positive_rate": sum(not c["passed"] for c in negative) / len(negative),
        },
        "recall": {
            "relevant_samples": len(relevant),
            "top3_hits": sum(c["passed"] for c in relevant),
            "top3_hit_rate": sum(c["passed"] for c in relevant) / len(relevant),
            "irrelevant_samples": len(irrelevant),
            "irrelevant_returns": sum(not c["passed"] for c in irrelevant),
            "irrelevant_return_rate": sum(not c["passed"] for c in irrelevant) / len(irrelevant),
        },
        "audit_side_effect_attempts": len(attempts),
        "exception_cases": sum(c["error"] is not None for c in mining + recall_cases),
    }
    raw = {
        "baseline": baseline,
        "mining": mining,
        "recall": recall_cases,
        "attempts": attempts,
        "module_paths": {"triples": hermeneutic.triples.__file__, "memory": hermeneutic.memory.__file__},
    }
    (run_dir / "baseline-raw-results.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
    candidate = json.loads((run_dir / "raw-results.json").read_text())["summary"]
    comparison = {
        "label": (
            "supplemental baseline comparison on the exact frozen fresh V2 synthetic fixtures; "
            "no candidate reevaluation or label changes"
        ),
        "baseline": baseline,
        "candidate": {k: candidate[k] for k in ["candidate", "mining", "recall", "accepted"]},
        "baseline_cases": {
            "mining": [{k: v for k, v in c.items() if k != "actual_corrections"} for c in mining],
            "recall": [{k: v for k, v in c.items() if k != "matches"} for c in recall_cases],
        },
        "limitations": (
            "Finite synthetic evidence. Candidate strict keyword relevance options differ from baseline defaults "
            "by design; no optional baseline index or external backend was used."
        ),
    }
    (output / "fresh-baseline-comparison.json").write_text(json.dumps(comparison, indent=2) + "\n")
    print(json.dumps({"baseline": baseline, "candidate": comparison["candidate"]}, indent=2))


if args.baseline_child:
    run_baseline()
    sys.exit(0)

# Candidate access is restricted to the published API and frozen wrapper.
from hermeneutic.memory import recall  # noqa: E402 -- import only after interpreter bootstrap and hash checks
from hermeneutic.triples import mine_file  # noqa: E402

output.mkdir(mode=0o700, exist_ok=False)
run_dir = output / "run-v2"
run_dir.mkdir(mode=0o700, exist_ok=False)
logs = run_dir / "logs"
logs.mkdir()
home = run_dir / "home"
home.mkdir()
canary = run_dir / "hidden-canary.txt"
canary.write_text(safety["hostile_canary"])
canary_before = hashlib.sha256(canary.read_bytes()).hexdigest()
marker = Path("/tmp/fresh-holdout-should-not-exist")
marker_existed = marker.exists()
assert not marker_existed, "Safety marker already exists: choose no alternate after freeze; report blocked."
guard_active = False
audit_attempts = []


def audit_hook(event, values):
    if not guard_active:
        return
    if event in {
        "socket.connect",
        "socket.connect_ex",
        "socket.bind",
        "socket.getaddrinfo",
        "os.system",
        "subprocess.Popen",
        "os.exec",
        "os.posix_spawn",
        "os.fork",
    }:
        audit_attempts.append({"event": event})
        raise RuntimeError("independent holdout denied side effect")
    if event == "open" and values and str(values[0]) == str(canary):
        audit_attempts.append({"event": "canary-read"})
        raise RuntimeError("independent holdout denied canary read")


sys.addaudithook(audit_hook)


@contextlib.contextmanager
def guarded():
    global guard_active
    guard_active = True
    try:
        yield
    finally:
        guard_active = False


mining_cases = []
for case in fixture["mining"]:
    suffix = ".json" if case["format"] == "openai" else ".jsonl"
    path = logs / (case["id"] + suffix)
    if "raw" in case:
        path.write_text(case["raw"])
    elif case["format"] == "openai":
        path.write_text(json.dumps({"messages": case["messages"]}))
    else:
        rows = []
        for message in case["messages"]:
            rows.append(
                {
                    "type": "response_item",
                    "timestamp": "2026-09-02T11:00:00Z",
                    "payload": {
                        "type": "message",
                        "role": message["role"],
                        "content": [
                            {
                                "type": "output_text" if message["role"] == "assistant" else "input_text",
                                "text": message["content"],
                            }
                        ],
                    },
                }
            )
        path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    error = None
    try:
        with guarded():
            triples = list(mine_file(path, fmt=case["format"]))
        actual = [triple.user_correction for triple in triples]
    except Exception as exc:
        actual = []
        error = type(exc).__name__
    hit = case.get("expected_text") in actual if case["expected_correction"] else not actual
    mining_cases.append(
        {
            "id": case["id"],
            "kind": case["kind"],
            "format": case["format"],
            "expected_correction": case["expected_correction"],
            "returned": len(actual),
            "passed": hit,
            "error": error,
            "actual_corrections": actual,
        }
    )

corpus = run_dir / "corpus.jsonl"
corpus.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in fixture["corpus"]))
corpus_before = hashlib.sha256(corpus.read_bytes()).hexdigest()


def call_recall(prompt, path=corpus):
    with guarded():
        return recall(prompt, path, home=home, method="keyword", limit=3, min_shared_terms=2, max_corpus_bytes=1048576)


recall_cases = []
for case in fixture["recall_relevant"] + fixture["recall_irrelevant"]:
    error = None
    try:
        matches = call_recall(case["prompt"])
        actual = [match.get("evidence") for match in matches]
    except Exception as exc:
        matches = []
        actual = []
        error = type(exc).__name__
    relevant = "expected_evidence" in case
    passed = case["expected_evidence"] in actual if relevant else not actual
    recall_cases.append(
        {
            "id": case["id"],
            "relevant": relevant,
            "expected_evidence": case.get("expected_evidence"),
            "actual_evidence": actual,
            "passed": passed,
            "error": error,
            "matches": matches,
        }
    )

# Warm direct API includes parsing/scoring and result creation; home has no index.
warm = []
for i in range(200):
    prompt = fixture["recall_relevant"][i % len(fixture["recall_relevant"])]["prompt"]
    start = time.perf_counter_ns()
    call_recall(prompt)
    warm.append((time.perf_counter_ns() - start) / 1e6)


def wrapper_call(prompt, path=corpus, interpreter=sys.executable):
    command = [
        sys.executable,
        str(wrapper),
        "--python",
        str(interpreter),
        "--corpus",
        str(path),
        "--limit",
        "3",
        prompt,
    ]
    start = time.perf_counter_ns()
    try:
        completed = subprocess.run(
            command, capture_output=True, timeout=2, check=False, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        )
        elapsed = (time.perf_counter_ns() - start) / 1e6
        try:
            payload = json.loads(completed.stdout)
        except Exception:
            payload = None
        return {
            "elapsed_ms": elapsed,
            "exit_code": completed.returncode,
            "stdout_bytes": len(completed.stdout),
            "stderr_bytes": len(completed.stderr),
            "payload": payload,
            "stdout": completed.stdout.decode("utf-8", errors="replace"),
            "stderr": completed.stderr.decode("utf-8", errors="replace"),
        }
    except subprocess.TimeoutExpired:
        return {
            "elapsed_ms": (time.perf_counter_ns() - start) / 1e6,
            "exit_code": None,
            "stdout_bytes": None,
            "stderr_bytes": None,
            "payload": None,
            "timeout": True,
        }


cold = []
wrapper_cases = []
for i in range(50):
    case = fixture["recall_relevant"][i % len(fixture["recall_relevant"])]
    result = wrapper_call(case["prompt"])
    cold.append(result["elapsed_ms"])
    result["id"] = case["id"]
    wrapper_cases.append(result)

repeated_wrapper = []
for i in range(200):
    case = fixture["recall_relevant"][i % len(fixture["recall_relevant"])]
    result = wrapper_call(case["prompt"])
    result["id"] = case["id"]
    repeated_wrapper.append(result)

# Inert hostile memory is exercised directly under audit and by the actual wrapper.
poisoned = run_dir / "hostile-corpus.jsonl"
poisoned.write_text(json.dumps(safety["hostile_triple"]) + "\n")
poisoned_before = hashlib.sha256(poisoned.read_bytes()).hexdigest()
try:
    hostile_api = call_recall(safety["hostile_query"], poisoned)
    hostile_api_error = None
except Exception as exc:
    hostile_api = []
    hostile_api_error = type(exc).__name__
hostile_wrapper = wrapper_call(safety["hostile_query"], poisoned)

corrupt = run_dir / "corrupt.jsonl"
corrupt.write_text('not a json corpus\n{"oops":\n')
oversized = run_dir / "oversized.jsonl"
oversized.write_bytes(b" " * 1048577)
scripts = {
    "raising-worker": "#!/bin/sh\nexit 37\n",
    "sleeping-worker": "#!/bin/sh\nsleep 2\n",
    "interrupted-worker": "#!/bin/sh\nkill -INT $$\n",
}
for name, text in scripts.items():
    script = run_dir / name
    script.write_text(text)
    script.chmod(0o700)
failure_cases = []
for name in safety["failure_probes"]:
    path = corpus
    interpreter = sys.executable
    if name == "missing-interpreter":
        interpreter = run_dir / "does-not-exist"
    if name == "missing-corpus":
        path = run_dir / "missing-corpus.jsonl"
    if name == "corrupt-corpus":
        path = corrupt
    if name == "oversized-corpus":
        path = oversized
    if name in scripts:
        interpreter = run_dir / name
    result = wrapper_call(fixture["recall_relevant"][0]["prompt"], path, interpreter)
    result["id"] = name
    payload = result["payload"]
    result["passed"] = (
        result["exit_code"] == 0
        and isinstance(payload, dict)
        and payload.get("matches") == []
        and result["stdout_bytes"] <= 4096
        and result["elapsed_ms"] <= 500
    )
    failure_cases.append(result)
large_query = wrapper_call(safety["oversized_query"])
large_query["id"] = "oversized-query"
large_query["passed"] = (
    large_query["exit_code"] == 0
    and isinstance(large_query["payload"], dict)
    and large_query["stdout_bytes"] <= 4096
    and large_query["elapsed_ms"] <= 500
)
failure_cases.append(large_query)


# Fixed nearest-rank percentiles, no sample exclusion or retries.
def stats(values):
    ordered = sorted(values)

    def percentile(p):
        return ordered[math.ceil(p * len(ordered)) - 1]

    return {
        "samples": len(values),
        "p95_ms": percentile(0.95),
        "p99_ms": percentile(0.99),
        "max_ms": max(values),
        "median_ms": percentile(0.5),
    }


mining_pos = [c for c in mining_cases if c["expected_correction"]]
mining_neg = [c for c in mining_cases if not c["expected_correction"]]
relevant = [c for c in recall_cases if c["relevant"]]
irrelevant = [c for c in recall_cases if not c["relevant"]]
output_cases = wrapper_cases + repeated_wrapper + failure_cases + [hostile_wrapper]
valid_sizes = [c["stdout_bytes"] for c in output_cases if c["stdout_bytes"] is not None]
public_metadata_leaks = []
for case in output_cases:
    payload = case.get("payload") or {}
    for match in payload.get("matches", []):
        if "session" in match or "timestamp" in match:
            public_metadata_leaks.append(case.get("id", "hostile-memory"))
canary_unchanged = hashlib.sha256(canary.read_bytes()).hexdigest() == canary_before
corpus_unchanged = hashlib.sha256(corpus.read_bytes()).hexdigest() == corpus_before
poisoned_unchanged = hashlib.sha256(poisoned.read_bytes()).hexdigest() == poisoned_before
canary_disclosures = sum(safety["hostile_canary"] in json.dumps(c, ensure_ascii=False) for c in output_cases)
summary = {
    "label": "fresh independent synthetic V2 holdout; finite evidence only",
    "fixture_sha256": freeze["fixture_sha256"],
    "safety_fixture_sha256": safety_freeze["safety_fixture_sha256"],
    "frozen_at_utc": freeze["frozen_at_utc"],
    "candidate": {
        k: v
        for k, v in meta.items()
        if k in {"commit", "source_sha256", "wheel_sha256", "wrapper_sha256", "interpreter_label", "frozen_at_utc"}
    },
    "mining": {
        "positive_samples": len(mining_pos),
        "recovered": sum(c["passed"] for c in mining_pos),
        "recovery": sum(c["passed"] for c in mining_pos) / len(mining_pos),
        "negative_samples": len(mining_neg),
        "false_positives": sum(not c["passed"] for c in mining_neg),
        "false_positive_rate": sum(not c["passed"] for c in mining_neg) / len(mining_neg),
    },
    "recall": {
        "relevant_samples": len(relevant),
        "top3_hits": sum(c["passed"] for c in relevant),
        "top3_hit_rate": sum(c["passed"] for c in relevant) / len(relevant),
        "irrelevant_samples": len(irrelevant),
        "irrelevant_returns": sum(not c["passed"] for c in irrelevant),
        "irrelevant_return_rate": sum(not c["passed"] for c in irrelevant) / len(irrelevant),
    },
    "latency": {
        "warm_api": stats(warm),
        "cold_wrapper": stats(cold),
        "repeated_full_command": stats([c["elapsed_ms"] for c in repeated_wrapper]),
        "percentile_method": "nearest rank; no retries or sample exclusions",
    },
    "wrapper": {
        "max_stdout_utf8_bytes": max(valid_sizes),
        "invalid_json_outputs": sum(not isinstance(c["payload"], dict) for c in output_cases),
        "nonzero_exits": sum(c["exit_code"] != 0 for c in output_cases),
        "metadata_leaks": len(public_metadata_leaks),
        "fail_open_cases": len(failure_cases),
        "fail_open_passed": sum(c["passed"] for c in failure_cases),
    },
    "privacy": {
        "direct_api_unauthorized_side_effect_attempts": len(audit_attempts),
        "network_calls_attempted_during_guarded_api": sum(c["event"].startswith("socket.") for c in audit_attempts),
        "canary_disclosures": canary_disclosures,
        "canary_unchanged": canary_unchanged,
        "corpus_unchanged": corpus_unchanged,
        "hostile_corpus_unchanged": poisoned_unchanged,
        "execution_marker_created": marker.exists(),
        "api_home_files_after_run": len(list(home.rglob("*"))),
        "scope": (
            "Direct API side effects audited; wrapper checked by canary, marker, output, and immutable corpus. "
            "Network and code-execution source review belong to independent review."
        ),
    },
}
summary["acceptance"] = {
    "mining_recovery": summary["mining"]["recovery"] >= 0.8,
    "mining_false_positives": summary["mining"]["false_positive_rate"] <= 0.05,
    "recall_top3": summary["recall"]["top3_hit_rate"] >= 0.85,
    "irrelevant_returns": summary["recall"]["irrelevant_return_rate"] <= 0.05,
    "warm_p95": summary["latency"]["warm_api"]["p95_ms"] <= 30,
    "warm_p99": summary["latency"]["warm_api"]["p99_ms"] <= 50,
    "cold_p95": summary["latency"]["cold_wrapper"]["p95_ms"] <= 150,
    "cold_p99": summary["latency"]["cold_wrapper"]["p99_ms"] <= 250,
    "hard_deadline": max(c["elapsed_ms"] for c in output_cases) <= 500,
    "bounded_output": summary["wrapper"]["max_stdout_utf8_bytes"] <= 4096,
    "host_full_command_warm_p95": summary["latency"]["repeated_full_command"]["p95_ms"] <= 30,
    "host_full_command_warm_p99": summary["latency"]["repeated_full_command"]["p99_ms"] <= 50,
    "fail_open": summary["wrapper"]["fail_open_passed"] == summary["wrapper"]["fail_open_cases"],
    "observed_privacy": not audit_attempts
    and canary_disclosures == 0
    and canary_unchanged
    and corpus_unchanged
    and poisoned_unchanged
    and not marker.exists()
    and not public_metadata_leaks,
}
summary["accepted"] = all(summary["acceptance"].values())
raw = {
    "summary": summary,
    "mining_cases": mining_cases,
    "recall_cases": recall_cases,
    "wrapper_cases": wrapper_cases,
    "repeated_wrapper_cases": repeated_wrapper,
    "failure_cases": failure_cases,
    "hostile_api": hostile_api,
    "hostile_api_error": hostile_api_error,
    "hostile_wrapper": hostile_wrapper,
    "audit_attempts": audit_attempts,
    "warm_ms": warm,
    "cold_ms": cold,
    "interpreter": sys.executable,
    "wrapper_path": str(wrapper),
}
(run_dir / "raw-results.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
public = output
public.mkdir(exist_ok=True)
(public / "fresh-receipt.json").write_text(json.dumps(summary, indent=2) + "\n")
public_cases = {
    "mining": [{k: v for k, v in c.items() if k != "actual_corrections"} for c in mining_cases],
    "recall": [{k: v for k, v in c.items() if k != "matches"} for c in recall_cases],
    "failure_modes": [{k: v for k, v in c.items() if k not in {"stdout", "stderr", "payload"}} for c in failure_cases],
}
(public / "fresh-cases.json").write_text(json.dumps(public_cases, indent=2) + "\n")
(public / "fresh-latency.json").write_text(
    json.dumps(
        {
            "warm_api_ms": warm,
            "cold_wrapper_ms": cold,
            "repeated_full_command_ms": [c["elapsed_ms"] for c in repeated_wrapper],
            "sampling": (
                "deterministic cycling over frozen relevant queries; 200 API warm, 50 process cold, "
                "200 repeated full commands; nearest rank; no retries"
            ),
        },
        indent=2,
    )
    + "\n"
)
(public / "fresh-fixtures.json").write_bytes(fixture_bytes)
(public / "fresh-safety-fixtures.json").write_bytes(safety_bytes)
print(json.dumps(summary, indent=2))

if args.baseline_src:
    command = [sys.executable, str(Path(__file__).absolute()), *sys.argv[1:], "--baseline-child"]
    subprocess.run(command, check=True, env={**os.environ, "PYTHONPATH": str(Path(args.baseline_src).absolute())})
