"""Exploratory target-retrieval evaluation. Private text stays in caller-owned files.

Cases JSON: [{"id": "case-1", "query": "subsequent task", "expected": [1]}].
Empty expected lists mark negative cases. Labels must be supplied before the run.
No behavior-improvement or generalization estimate is produced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

import hermeneutic.memory as memory
from hermeneutic import __version__
from hermeneutic.memory import recall


def evaluate(corpus, home, cases, methods, limit):
    rows = [json.loads(line) for line in corpus.read_text().splitlines() if line.strip()]
    results = {}
    for method in methods:
        trials = []
        for case in cases:
            started = time.perf_counter()
            matches = recall(case["query"], corpus, home=home, method=method, limit=limit)
            elapsed = time.perf_counter() - started
            retrieved = [int(match["evidence"].removeprefix("triple-id-")) for match in matches]
            expected = case["expected"]
            trials.append({"id": case["id"], "expected": expected, "retrieved": retrieved,
                           "target_hit": bool(set(expected) & set(retrieved)) if expected else None,
                           "negative_empty": not retrieved if not expected else None,
                           "evidence_chars": sum(len(m["correction_preview"]) for m in matches),
                           "seconds": round(elapsed, 4)})
        positive = [t for t in trials if t["target_hit"] is not None]
        negative = [t for t in trials if t["negative_empty"] is not None]
        results[method] = {"positive_hits": sum(t["target_hit"] for t in positive),
                           "positive_trials": len(positive),
                           "negative_empty": sum(t["negative_empty"] for t in negative),
                           "negative_trials": len(negative),
                           "mean_evidence_chars": round(statistics.mean(t["evidence_chars"] for t in trials), 1),
                           "median_seconds": round(statistics.median(t["seconds"] for t in trials), 4),
                           "trials": trials}
    return {"measurement": "exploratory_annotated_target_retrieval", "limit": limit,
            "package_version": __version__,
            "memory_source_sha256": hashlib.sha256(Path(memory.__file__).read_bytes()).hexdigest(),
            "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
            "cases_sha256": hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest(),
            "episodes": len(rows), "private_text_emitted": False,
            "always_include_baseline": {"positive_target_coverage": "all targets included by construction",
                                         "correction_chars_per_task": sum(len(r["user_correction"]) for r in rows)},
            "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--triples", type=Path, required=True)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--methods", nargs="+", choices=("keyword", "semantic", "hybrid"),
                        default=["keyword", "semantic", "hybrid"])
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text())
    if not cases:
        parser.error("cases must not be empty")
    receipt = evaluate(args.triples, args.home, cases, args.methods, args.limit)
    args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({method: {k: v for k, v in result.items() if k != "trials"}
                      for method, result in receipt["results"].items()}, indent=2))
