#!/usr/bin/env python3
"""Bounded leave-one-out evaluation through the production retrieval function.

For each bucketed triple, this runner reuses the triple's frozen cached vector
as the query, masks that triple out of the index, and calls
``hermeneutic.compile.compile_prompt``. That keeps the measured selection,
threshold, per-bucket limit, global cap, and synthesis path identical to the
shipped implementation while avoiding a moving live embedding-model call.

Reproduce from the repository root with the matching private corpus and frozen
index already under `~/.hermeneutic/`. The committed receipt publishes their
hashes, not their private contents:

    python3 evals/leave-one-out/runner.py
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hermeneutic import compile as hcompile  # noqa: E402
from hermeneutic.triples import Triple  # noqa: E402

# The CLI and built-in compile hook pass these parser defaults explicitly.
CLI_HOOK_PROFILE = {"k": 5, "threshold": 0.4, "n_per_bucket": 2}

# Direct Python callers that omit keyword arguments receive these library defaults.
LIBRARY_PROFILE = {
    "k": hcompile.DEFAULT_TOP_K,
    "threshold": hcompile.DEFAULT_SIM_THRESHOLD,
    "n_per_bucket": hcompile.DEFAULT_N_PER_BUCKET,
}

PROFILES = {
    "cli_and_compile_hook_defaults": CLI_HOOK_PROFILE,
    "python_library_defaults": LIBRARY_PROFILE,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _new_profile_result(config: dict) -> dict:
    return {
        "config": config,
        "same_bucket_hits": 0,
        "triggered": 0,
        "total_buckets_surfaced": 0,
        "total_matches_surfaced": 0,
        "per_bucket": {},
    }


def _parse_preamble(preamble: str) -> tuple[set[str], int]:
    buckets = set(re.findall(r"in bucket `([^`]+)`", preamble))
    match = re.match(r"\[hermeneutic compile-preamble — derived from (\d+)", preamble)
    return buckets, int(match.group(1)) if match else 0


def evaluate() -> dict:
    home = hcompile.home_dir()
    triples_path = home / "triples.jsonl"
    if not triples_path.is_file():
        raise FileNotFoundError(f"frozen corpus not found: {triples_path}")
    index_path = hcompile.index_path(home)
    if not index_path.is_file():
        raise FileNotFoundError(f"frozen index not found: {index_path}")

    index = hcompile.load_index(home)
    if index is None:
        raise RuntimeError(f"could not load frozen index: {index_path}")
    corpus_sha256 = _sha256(triples_path)
    if index.triples_sha256 != corpus_sha256:
        raise RuntimeError("frozen index does not match the frozen triples corpus")

    triples = [
        Triple.from_json(line)
        for line in triples_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    bucket_by_position: list[str | None] = []
    for triple_index in index.triple_indices:
        bucket = hcompile.bucket_for(triples[triple_index].user_correction)
        bucket_by_position.append(bucket[0] if bucket else None)

    eligible = [position for position, bucket in enumerate(bucket_by_position) if bucket]
    results = {name: _new_profile_result(config) for name, config in PROFILES.items()}
    original_load_index = hcompile.load_index

    try:
        for position in eligible:
            query = index.vectors[position]
            true_bucket = bucket_by_position[position]
            triple_index = index.triple_indices[position]
            masked_index = hcompile.EmbedIndex(
                triples_sha256=index.triples_sha256,
                model=index.model,
                dim=index.dim,
                vectors=index.vectors[:position] + index.vectors[position + 1 :],
                triple_indices=index.triple_indices[:position] + index.triple_indices[position + 1 :],
            )
            hcompile.load_index = lambda _home, masked=masked_index: masked

            for name, config in PROFILES.items():
                preamble = hcompile.compile_prompt(
                    triples[triple_index].orig_prompt,
                    triples_path,
                    home=home,
                    k=config["k"],
                    threshold=config["threshold"],
                    n_per_bucket=config["n_per_bucket"],
                    embedder=lambda _text, vector=query: vector,
                    model=index.model,
                )
                surfaced_buckets, surfaced_matches = _parse_preamble(preamble)
                profile = results[name]
                if preamble:
                    profile["triggered"] += 1
                profile["total_buckets_surfaced"] += len(surfaced_buckets)
                profile["total_matches_surfaced"] += surfaced_matches
                per_bucket = profile["per_bucket"].setdefault(
                    true_bucket,
                    {"hits": 0, "trials": 0},
                )
                per_bucket["trials"] += 1
                if true_bucket in surfaced_buckets:
                    profile["same_bucket_hits"] += 1
                    per_bucket["hits"] += 1
    finally:
        hcompile.load_index = original_load_index

    n_trials = len(eligible)
    for profile in results.values():
        profile["same_bucket_recall"] = _rate(profile["same_bucket_hits"], n_trials)
        profile["trigger_rate"] = _rate(profile["triggered"], n_trials)
        profile["mean_buckets_surfaced"] = round(profile.pop("total_buckets_surfaced") / n_trials, 4)
        profile["mean_matches_surfaced"] = round(profile.pop("total_matches_surfaced") / n_trials, 4)
        profile["per_bucket"] = {
            bucket: {
                **counts,
                "recall": _rate(counts["hits"], counts["trials"]),
            }
            for bucket, counts in sorted(profile["per_bucket"].items())
        }

    compile_path = ROOT / "src" / "hermeneutic" / "compile.py"
    bucket_counts = Counter(bucket for bucket in bucket_by_position if bucket)
    return {
        "schema_version": 2,
        "measurement": "production_path_leave_one_out_same_bucket_recall",
        "identity": {
            "corpus_sha256": corpus_sha256,
            "index_sha256": _sha256(index_path),
            "compile_source_sha256": _sha256(compile_path),
            "triples": len(triples),
            "indexed": len(index.vectors),
            "eligible_bucketed_trials": n_trials,
            "skipped_unbucketed": len(index.vectors) - n_trials,
            "model_tag_recorded_in_index": index.model,
            "embedding_dimension": index.dim,
            "private_text_emitted": False,
        },
        "method": {
            "production_function": "hermeneutic.compile.compile_prompt",
            "self_masked": True,
            "query_embedding": "held-out triple's cached frozen vector",
            "live_ollama_calls": 0,
            "bucket_counts": dict(sorted(bucket_counts.items())),
        },
        "current_results": results,
        "historical_receipts": {
            "leave_one_out_2026_04_27": {
                "reported": "87/104 (83.7%)",
                "status": "historical_only",
                "reason": (
                    "The former evaluator required at least n_per_bucket candidates before a bucket counted "
                    "as surfaced and omitted compile_prompt's global k cap, so it did not execute the exact "
                    "production selection path."
                ),
            },
            "bucket_discrimination_2026_04_27": {
                "reported": "98/100 in-corpus prompts triggered versus 7/30 synthetic-random prompts",
                "status": "historical_only",
                "reason": (
                    "The evaluator used a global-top-K path and asymmetric trigger definitions rather than "
                    "the shipped bucket-aware compile path."
                ),
            },
        },
        "interpretation": {
            "demonstrates": (
                "Current same-bucket retrieval behavior for two shipped default profiles on one frozen "
                "single-user corpus, with the held-out item excluded."
            ),
            "does_not_demonstrate": [
                "generalization to new users or out-of-distribution prompts",
                "embedding-model reproducibility beyond the frozen cached vectors",
                "quality of the retrieved advice",
                "reduced downstream model misinterpretation",
            ],
        },
    }


def render_markdown(result: dict) -> str:
    identity = result["identity"]
    profiles = result["current_results"]
    lines = [
        "# Production-path leave-one-out retrieval measurement\n\n",
        "This current bounded run masks each held-out triple and calls the shipped "
        "`hermeneutic.compile.compile_prompt` function. It reuses the frozen cached "
        "query vector, so the measurement exercises production filtering, per-bucket "
        "selection, global cap, and synthesis without calling a moving Ollama model.\n\n",
        "## Frozen identity\n\n",
        f"- Corpus: {identity['triples']} triples, SHA-256 `{identity['corpus_sha256']}`\n",
        f"- Index: {identity['indexed']} vectors, SHA-256 `{identity['index_sha256']}`\n",
        f"- Compile source SHA-256: `{identity['compile_source_sha256']}`\n",
        f"- Model tag recorded in index: `{identity['model_tag_recorded_in_index']}` "
        f"(dimension {identity['embedding_dimension']}; cached vectors, no live model call)\n",
        f"- Trials: {identity['eligible_bucketed_trials']} bucketed; "
        f"{identity['skipped_unbucketed']} unbucketed entries excluded\n\n",
        "## Current result\n\n",
        "| Shipped profile | k | Threshold | Per bucket | Same-bucket recall | "
        "Triggered | Mean buckets | Mean matches |\n",
        "|---|---:|---:|---:|---:|---:|---:|---:|\n",
    ]
    for name, profile in profiles.items():
        config = profile["config"]
        label = name.replace("_", " ")
        lines.append(
            f"| {label} | {config['k']} | {config['threshold']} | "
            f"{config['n_per_bucket']} | **{profile['same_bucket_hits']}/"
            f"{identity['eligible_bucketed_trials']} ({profile['same_bucket_recall']:.2%})** | "
            f"{profile['triggered']}/{identity['eligible_bucketed_trials']} | "
            f"{profile['mean_buckets_surfaced']:.2f} | {profile['mean_matches_surfaced']:.2f} |\n"
        )

    lines.extend([
        "\nThe installed CLI and built-in compile hook use the first profile. Direct "
        "Python callers that omit `k` and `threshold` use the second. These are corpus-specific "
        "retrieval measurements, not model-effectiveness results.\n\n",
        "## Per-bucket current recall\n\n",
        "| Bucket | Trials | CLI/hook defaults | Python defaults |\n",
        "|---|---:|---:|---:|\n",
    ])
    cli_rows = profiles["cli_and_compile_hook_defaults"]["per_bucket"]
    library_rows = profiles["python_library_defaults"]["per_bucket"]
    for bucket in sorted(cli_rows):
        cli = cli_rows[bucket]
        library = library_rows[bucket]
        lines.append(
            f"| `{bucket}` | {cli['trials']} | {cli['hits']}/{cli['trials']} "
            f"({cli['recall']:.2%}) | {library['hits']}/{library['trials']} "
            f"({library['recall']:.2%}) |\n"
        )

    lines.extend([
        "\n## Historical experiments\n\n",
        "The prior **83.7% (87/104)** leave-one-out result and **98/100 versus 7/30** "
        "discrimination result remain dated frozen experiments. They are not current production-path "
        "headlines: the former used a different bucket-surfacing rule and omitted the global cap; the "
        "latter used global top-K and asymmetric trigger definitions. Their original aggregate receipts "
        "remain in this repository for provenance.\n\n",
        "## Interpretation boundary\n\n",
        "Same-bucket recall asks whether the production retrieval function surfaces at least one warning "
        "from the held-out correction's category after the held-out item is removed. It does not measure "
        "generalization to other users, the quality of the warning, false positives on normal prompts, "
        "or whether an LLM follows the injected context. Downstream effectiveness remains unmeasured.\n",
    ])
    return "".join(lines)


def main() -> int:
    try:
        result = evaluate()
    except (FileNotFoundError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    output_dir = Path(__file__).resolve().parent
    (output_dir / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (output_dir / "RESULTS.md").write_text(render_markdown(result), encoding="utf-8")
    for name, profile in result["current_results"].items():
        print(
            f"{name}: {profile['same_bucket_hits']}/"
            f"{result['identity']['eligible_bucketed_trials']} "
            f"({profile['same_bucket_recall']:.2%})",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
