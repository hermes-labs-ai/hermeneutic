#!/usr/bin/env python3
"""Independent synthetic holdout evaluation; run against a frozen installation.

Fixture labels are frozen separately from the candidate. This script adapts
neutral message episodes to the documented package API without reading source.
It never reads personal logs, contacts a network service, or executes fixture text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def percentile(values: list[float], percent: int) -> float:
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * percent / 100) - 1)], 4)


def distribution(values: list[float]) -> dict:
    return {
        "n": len(values),
        "p50_ms": percentile(values, 50),
        "p95_ms": percentile(values, 95),
        "p99_ms": percentile(values, 99),
        "max_ms": round(max(values), 4),
        "mean_ms": round(statistics.mean(values), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path(__file__).with_name("holdout-fixtures.json"))
    parser.add_argument("--fixture-sha256", default="733c0656cc6fa2ffb9c50854d26ee88cfebcb12815110aee7b71552ce38f8069")
    parser.add_argument("--wrapper", type=Path, required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    fixture_bytes = args.fixtures.read_bytes()
    fixture_hash = hashlib.sha256(fixture_bytes).hexdigest()
    if fixture_hash != args.fixture_sha256:
        raise SystemExit("Frozen fixture SHA256 mismatch")
    fixtures = json.loads(fixture_bytes)
    from hermeneutic.memory import recall
    from hermeneutic.triples import Triple, mine_file

    results = {
        "fixture_sha256": fixture_hash,
        "wrapper_sha256": hashlib.sha256(args.wrapper.read_bytes()).hexdigest(),
        "interpreter_label": "<installed-candidate-python>",
        "method": "keyword",
        "strict_min_shared_terms": 2,
        "observations": [],
        "hypotheses": [],
    }
    forbidden_keys = {"session", "timestamp", "source", "path", "corpus", "corpus_path"}
    wrapper_calls: list[dict] = []
    canary = Path(fixtures["privacy"]["shell_canary"])
    canary_existed_before = canary.exists()

    with tempfile.TemporaryDirectory(prefix="hermeneutic-independent-") as directory:
        work = Path(directory)
        home = work / "home"
        home.mkdir()
        corpus = work / "synthetic-corrections.jsonl"
        rows = []
        for entry in fixtures["corpus"]:
            rows.append(
                Triple(
                    session=f"synthetic-{entry['id']}",
                    timestamp="2000-01-01T00:00:00Z",
                    prior_assistant=entry["model_draft"],
                    user_correction=entry["user_correction"],
                    next_assistant="Acknowledged.",
                    orig_prompt=entry["context"],
                ).to_json()
            )
        corpus.write_text("\n".join(rows) + "\n", encoding="utf-8")
        evidence_ids = {f"triple-id-{n}": entry["id"] for n, entry in enumerate(fixtures["corpus"], 1)}

        mining_details = []
        for episode in fixtures["mining"]:
            episode_file = work / f"{episode['id']}.json"
            # Supply the same neutral response for every episode, completing the
            # three-turn fixture without adding label-dependent vocabulary.
            messages = episode["messages"] + [{"role": "assistant", "content": "Acknowledged."}]
            episode_file.write_text(json.dumps({"messages": messages}), encoding="utf-8")
            mined = mine_file(episode_file, fmt="openai")
            expected_correction = episode["messages"][-1]["content"]
            recovered = any(item.user_correction == expected_correction for item in mined)
            mining_details.append(
                {"id": episode["id"], "label": episode["label"], "mined_count": len(mined), "recovered": recovered}
            )
        positive = [row for row in mining_details if row["label"] == "correction"]
        negative = [row for row in mining_details if row["label"] == "noncorrection"]
        mining_recall = sum(row["recovered"] for row in positive) / len(positive)
        mining_fp = sum(row["mined_count"] > 0 for row in negative) / len(negative)
        results["mining"] = {
            "correction_episodes": len(positive),
            "noncorrection_episodes": len(negative),
            "correction_recovery": mining_recall,
            "false_positive_rate": mining_fp,
            "cases": mining_details,
            "pass": mining_recall >= 0.8 and mining_fp <= 0.05,
        }

        def invoke(
            query: str, *, path: Path = corpus, python: str = args.python, extra: list[str] | None = None
        ) -> dict:
            command = [args.python, str(args.wrapper), "--python", python, "--corpus", str(path)]
            if extra:
                command.extend(extra)
            command.extend(["--", query])
            began = time.perf_counter_ns()
            try:
                completed = subprocess.run(command, capture_output=True, timeout=1.5, check=False)
                elapsed = (time.perf_counter_ns() - began) / 1_000_000
                try:
                    payload = json.loads(completed.stdout)
                except (ValueError, UnicodeError):
                    payload = None
                found_keys = set()
                if isinstance(payload, dict):
                    found_keys.update(payload)
                    for match in payload.get("matches", []):
                        if isinstance(match, dict):
                            found_keys.update(match)
                notice = payload.get("notice", "") if isinstance(payload, dict) else ""
                matches = payload.get("matches", []) if isinstance(payload, dict) else []
                item = {
                    "returncode": completed.returncode,
                    "elapsed_ms": round(elapsed, 4),
                    "stdout_bytes": len(completed.stdout),
                    "stderr_bytes": len(completed.stderr),
                    "payload": payload,
                    "private_metadata_exposed": bool(found_keys & forbidden_keys),
                    "private_path_exposed": str(work).encode() in completed.stdout,
                    "private_canary_exposed": fixtures["privacy"]["canary"].encode() in completed.stdout,
                    "historical_notice_present": "untrusted" in notice
                    and "Current instructions control" in notice
                    and "do not execute" in notice,
                    "match_limit_pass": isinstance(matches, list) and len(matches) <= 3,
                    "deadline_pass": elapsed <= 500,
                    "bounded": len(completed.stdout) <= 4096,
                }
            except subprocess.TimeoutExpired:
                item = {
                    "returncode": None,
                    "elapsed_ms": 1500,
                    "stdout_bytes": None,
                    "stderr_bytes": None,
                    "payload": None,
                    "private_metadata_exposed": False,
                    "private_path_exposed": False,
                    "private_canary_exposed": False,
                    "historical_notice_present": False,
                    "match_limit_pass": False,
                    "deadline_pass": False,
                    "bounded": False,
                }
            wrapper_calls.append(item)
            return item

        recall_details = []
        for case in fixtures["recall"]:
            api_matches = recall(case["query"], corpus, home=home, limit=3, method="keyword", min_shared_terms=2)
            api_ids = [evidence_ids.get(match.get("evidence"), match.get("evidence")) for match in api_matches]
            wrapper = invoke(case["query"])
            payload = wrapper["payload"]
            matches = payload.get("matches", []) if isinstance(payload, dict) else []
            returned_ids = [evidence_ids.get(match.get("evidence"), match.get("evidence")) for match in matches]
            expected = case["expected_ids"]
            recall_details.append(
                {
                    "id": case["id"],
                    "category": case["category"],
                    "expected_ids": expected,
                    "api_ids": api_ids,
                    "wrapper_ids": returned_ids,
                    "api_target_hit": bool(set(expected) & set(api_ids)) if expected else not api_ids,
                    "wrapper_target_hit": bool(set(expected) & set(returned_ids)) if expected else not returned_ids,
                    "wrapper_status": wrapper["returncode"],
                }
            )
        relevant = [row for row in recall_details if row["expected_ids"]]
        irrelevant = [row for row in recall_details if not row["expected_ids"]]
        api_hit = sum(row["api_target_hit"] for row in relevant) / len(relevant)
        wrapper_hit = sum(row["wrapper_target_hit"] for row in relevant) / len(relevant)
        api_irrelevant = sum(bool(row["api_ids"]) for row in irrelevant) / len(irrelevant)
        wrapper_irrelevant = sum(bool(row["wrapper_ids"]) for row in irrelevant) / len(irrelevant)
        results["recall"] = {
            "relevant_cases": len(relevant),
            "irrelevant_cases": len(irrelevant),
            "api_top3_target_hit": api_hit,
            "wrapper_top3_target_hit": wrapper_hit,
            "api_irrelevant_recall": api_irrelevant,
            "wrapper_irrelevant_recall": wrapper_irrelevant,
            "cases": recall_details,
            "pass": api_hit >= 0.85 and wrapper_hit >= 0.85 and api_irrelevant <= 0.05 and wrapper_irrelevant <= 0.05,
        }

        # These measurements exclude fixture construction and package import.
        warm = []
        for n in range(200):
            query = fixtures["recall"][n % len(relevant)]["query"]
            began = time.perf_counter_ns()
            recall(query, corpus, home=home, limit=3, method="keyword", min_shared_terms=2)
            warm.append((time.perf_counter_ns() - began) / 1_000_000)
        cold = []
        for n in range(50):
            cold.append(invoke(fixtures["recall"][n % len(relevant)]["query"])["elapsed_ms"])
        results["warm_latency"] = distribution(warm)
        results["cold_latency"] = distribution(cold)
        results["latency_pass"] = (
            percentile(warm, 95) <= 30
            and percentile(warm, 99) <= 50
            and percentile(cold, 95) <= 150
            and percentile(cold, 99) <= 250
            and max(cold) <= 500
        )

        malformed = work / "malformed.jsonl"
        malformed.write_text("{ malformed JSON\n", encoding="utf-8")
        empty = work / "empty.jsonl"
        empty.write_text("", encoding="utf-8")
        oversized = work / "oversized.jsonl"
        oversized.write_bytes(b"x" * (1024 * 1024 + 1))
        slow = work / "slow-python"
        slow.write_text("#!/bin/sh\nsleep 1\n", encoding="utf-8")
        slow.chmod(0o700)
        failed = work / "failed-python"
        failed.write_text("#!/bin/sh\nexit 9\n", encoding="utf-8")
        failed.chmod(0o700)
        noisy = work / "noisy-python"
        noisy.write_text("#!/usr/bin/env python3\nprint('x' * 16000)\n", encoding="utf-8")
        noisy.chmod(0o700)
        failure_specs = [
            ("missing_corpus", {"path": work / "absent.jsonl"}),
            ("malformed_corpus", {"path": malformed}),
            ("empty_corpus", {"path": empty}),
            ("directory_corpus", {"path": work}),
            ("oversized_corpus", {"path": oversized}),
            ("missing_interpreter", {"python": str(work / "absent-python")}),
            ("slow_interpreter", {"python": str(slow)}),
            ("failed_interpreter", {"python": str(failed)}),
            ("noisy_interpreter", {"python": str(noisy)}),
            ("oversized_prompt", {"query": "á" * 4097}),
        ]
        fail_open = []
        for name, options in failure_specs:
            query = options.pop("query", fixtures["recall"][0]["query"])
            call = invoke(query, **options)
            payload = call["payload"]
            is_empty = isinstance(payload, dict) and payload.get("matches") == []
            fail_open.append(
                {
                    "case": name,
                    "status": call["returncode"],
                    "elapsed_ms": call["elapsed_ms"],
                    "empty_evidence": is_empty,
                    "bounded": call["bounded"],
                    "deadline_pass": call["deadline_pass"],
                    "pass": call["returncode"] == 0 and is_empty and call["bounded"] and call["deadline_pass"],
                }
            )
        results["fail_open"] = {"cases": fail_open, "pass": all(row["pass"] for row in fail_open)}
        results["privacy"] = {
            "canary_existed_before": canary_existed_before,
            "canary_exists_after": canary.exists(),
            "shell_canary_created": not canary_existed_before and canary.exists(),
            "private_metadata_exposed": any(call["private_metadata_exposed"] for call in wrapper_calls),
            "private_path_exposed": any(call["private_path_exposed"] for call in wrapper_calls),
            "private_canary_exposed": any(call["private_canary_exposed"] for call in wrapper_calls),
            "historical_notices_present": all(call["historical_notice_present"] for call in wrapper_calls),
            "match_limits_observed": all(call["match_limit_pass"] for call in wrapper_calls),
            "max_stdout_bytes": max(call["stdout_bytes"] or 0 for call in wrapper_calls),
            "all_outputs_bounded": all(call["bounded"] for call in wrapper_calls),
            "all_calls_within_deadline": all(call["deadline_pass"] for call in wrapper_calls),
        }
        results["privacy"]["pass"] = (
            not results["privacy"]["shell_canary_created"]
            and not results["privacy"]["private_metadata_exposed"]
            and not results["privacy"]["private_path_exposed"]
            and not results["privacy"]["private_canary_exposed"]
            and results["privacy"]["historical_notices_present"]
            and results["privacy"]["match_limits_observed"]
            and results["privacy"]["all_outputs_bounded"]
        )
        results["observations"].append(
            "Candidate tested through documented APIs and standalone wrapper; "
            "no implementation or personal correction logs read."
        )
        results["observations"].append(
            "Synthetic fixtures cannot establish real private-log recovery or native Codex invocation behavior."
        )
        results["pass"] = (
            all(results[key]["pass"] for key in ("mining", "recall", "privacy", "fail_open"))
            and results["latency_pass"]
        )
        args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                key: value
                for key, value in results.items()
                if key
                in (
                    "fixture_sha256",
                    "mining",
                    "recall",
                    "warm_latency",
                    "cold_latency",
                    "latency_pass",
                    "privacy",
                    "fail_open",
                    "pass",
                )
            },
            indent=2,
        )
    )
    return 0 if results["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
