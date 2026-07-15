#!/usr/bin/env python3
"""Measure current fixed-gate coverage on an already frozen triples corpus.

This is a retrospective derivation-set coverage measurement, not a held-out
accuracy evaluation. It emits aggregate counts and hashes only; no private
triple text is written to the repository.

Reproduce from the repository root with an existing private corpus. The
published aggregate is reproduced only when the input SHA-256 matches the
receipt:

    python3 evals/gate-coverage/runner.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hermeneutic import compile as hcompile  # noqa: E402
from hermeneutic.gates import regex as gate_regex  # noqa: E402
from hermeneutic.triples import Triple  # noqa: E402

ORIGINAL_SIX = frozenset({
    "completion_with_number",
    "completion_with_all_quantifier",
    "subagent_passthrough",
    "unhedged_certainty",
    "scope_expansion",
    "fluent_summary_no_evidence",
})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def measure(corpus: Path) -> dict:
    triples = [
        Triple.from_json(line)
        for line in corpus.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    specs = [(rule_id, severity) for rule_id, severity, _pattern, _description in gate_regex._RAW_PATTERNS]
    rule_rows: Counter[str] = Counter()
    rule_matches: Counter[str] = Counter()
    multiplicity: Counter[int] = Counter()
    pair_rows: Counter[tuple[str, str]] = Counter()
    bucket_rows: Counter[str] = Counter()
    bucket_covered: Counter[str] = Counter()

    covered = 0
    original_six_covered = 0
    for triple in triples:
        hits = gate_regex.risk_score(triple.prior_assistant)
        unique_ids = sorted({hit.rule_id for hit in hits})
        if unique_ids:
            covered += 1
        if ORIGINAL_SIX.intersection(unique_ids):
            original_six_covered += 1
        multiplicity[len(unique_ids)] += 1
        rule_rows.update(unique_ids)
        rule_matches.update(hit.rule_id for hit in hits)
        pair_rows.update(combinations(unique_ids, 2))

        bucket_result = hcompile.bucket_for(triple.user_correction)
        bucket = bucket_result[0] if bucket_result else "unbucketed"
        bucket_rows[bucket] += 1
        if unique_ids:
            bucket_covered[bucket] += 1

    n = len(triples)
    gate_path = ROOT / "src" / "hermeneutic" / "gates" / "regex.py"
    return {
        "schema_version": 1,
        "measurement": "retrospective_derivation_set_gate_coverage",
        "corpus": {
            "sha256": _sha256(corpus),
            "triples": n,
            "private_text_emitted": False,
        },
        "gate": {
            "source": "src/hermeneutic/gates/regex.py",
            "source_sha256": _sha256(gate_path),
            "rule_count": len(specs),
            "language_scope": "fixed English surface patterns",
        },
        "coverage": {
            "scanned_field": "prior_assistant",
            "covered_triples": covered,
            "missed_triples": n - covered,
            "coverage_rate": _pct(covered, n),
            "total_rule_matches": sum(rule_matches.values()),
        },
        "derivation_set_coverage": {
            "original_six_direct_hits": original_six_covered,
            "original_six_direct_rate": _pct(original_six_covered, n),
            "current_eight_direct_hits": covered,
            "current_eight_direct_rate": _pct(covered, n),
            "unique_rows_added_by_two_later_rules": covered - original_six_covered,
            "historical_approximately_65_percent": (
                "Category mapping on the separate 326-triple derivation run; not a direct regex execution result."
            ),
        },
        "per_rule": {
            rule_id: {
                "severity": severity,
                "triples_with_rule": rule_rows[rule_id],
                "raw_matches": rule_matches[rule_id],
                "triple_rate": _pct(rule_rows[rule_id], n),
            }
            for rule_id, severity in specs
        },
        "overlap": {
            "rules_per_triple": {str(k): multiplicity[k] for k in sorted(multiplicity)},
            "triples_with_multiple_rules": sum(rows for count, rows in multiplicity.items() if count > 1),
            "pair_rows": {
                f"{left}+{right}": count
                for (left, right), count in sorted(pair_rows.items())
            },
        },
        "correction_bucket_context": {
            bucket: {
                "triples": bucket_rows[bucket],
                "covered": bucket_covered[bucket],
                "coverage_rate": _pct(bucket_covered[bucket], bucket_rows[bucket]),
            }
            for bucket in sorted(bucket_rows)
        },
        "interpretation": {
            "demonstrates": (
                "How often the current eight-rule gate fires on prior assistant replies "
                "in the frozen correction corpus."
            ),
            "does_not_demonstrate": [
                "held-out recall",
                "precision or false-positive rate",
                "live fire rate",
                "severity calibration",
                "reduced downstream model misinterpretation",
            ],
        },
    }


def render_markdown(result: dict) -> str:
    corpus = result["corpus"]
    gate = result["gate"]
    coverage = result["coverage"]
    lines = [
        "# Current deterministic gate coverage\n\n",
        "This bounded measurement runs the shipped eight-rule English gate over "
        "the `prior_assistant` field of the already frozen 346-triple retrieval "
        "corpus. It does not re-mine private logs and writes no private text.\n\n",
        "## Identity\n\n",
        f"- Corpus SHA-256: `{corpus['sha256']}`\n",
        f"- Gate source SHA-256: `{gate['source_sha256']}`\n",
        f"- Triples: {corpus['triples']}\n",
        f"- Rules: {gate['rule_count']} fixed English surface-pattern rules\n\n",
        "## Result\n\n",
        f"The current gate fires on **{coverage['covered_triples']}/{corpus['triples']} "
        f"({coverage['coverage_rate']:.2%})** prior assistant replies and stays "
        f"silent on **{coverage['missed_triples']}/{corpus['triples']}**. This is "
        "retrospective derivation-set coverage, not held-out recall.\n\n",
        "| Rule | Severity | Triples | Raw matches | Triple rate |\n",
        "|---|---:|---:|---:|---:|\n",
    ]
    for rule_id, row in result["per_rule"].items():
        lines.append(
            f"| `{rule_id}` | {row['severity']} | {row['triples_with_rule']} | "
            f"{row['raw_matches']} | {row['triple_rate']:.2%} |\n"
        )

    lines.extend(["\n## Overlap\n\n", "| Distinct rules on one triple | Triples |\n", "|---:|---:|\n"])
    for count, rows in result["overlap"]["rules_per_triple"].items():
        lines.append(f"| {count} | {rows} |\n")
    lines.append(
        f"\n**{result['overlap']['triples_with_multiple_rules']}** triples fire more "
        "than one distinct rule. Pair counts are preserved in "
        "[`results.json`](results.json).\n\n"
    )

    derivation = result["derivation_set_coverage"]
    lines.extend([
        "## Derivation-set comparison\n\n",
        f"The original six-rule subset directly fires on **{derivation['original_six_direct_hits']}/"
        f"{corpus['triples']} ({derivation['original_six_direct_rate']:.2%})** rows in this frozen 346-triple "
        "corpus. The two later rules add "
        f"**{derivation['unique_rows_added_by_two_later_rules']}** uniquely covered rows. The historical "
        "`about 65%` statement was a category-mapping estimate on the separate 326-triple derivation "
        "run, not a direct regex execution result.\n\n",
    ])

    lines.extend([
        "## Interpretation boundary\n\n",
        "This result answers one narrow question: how much of the frozen correction "
        "corpus's prior assistant text has a surface form recognized by the current "
        "fixed gate? The corpus consists only of correction-bearing episodes and was "
        "involved in rule derivation, so the result cannot establish precision, "
        "false-positive rate, live trigger rate, severity calibration, or downstream "
        "effectiveness. Those remain unmeasured for v0.1.7.\n",
    ])
    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path.home() / ".hermeneutic" / "triples.jsonl",
        help="Existing frozen triples corpus (default: ~/.hermeneutic/triples.jsonl).",
    )
    args = parser.parse_args()
    if not args.corpus.is_file():
        print(f"ERROR: frozen corpus not found: {args.corpus}", file=sys.stderr)
        return 1

    result = measure(args.corpus)
    output_dir = Path(__file__).resolve().parent
    (output_dir / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output_dir / "RESULTS.md").write_text(render_markdown(result), encoding="utf-8")
    coverage = result["coverage"]
    print(
        f"current gate coverage: {coverage['covered_triples']}/{result['corpus']['triples']} "
        f"({coverage['coverage_rate']:.2%})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
