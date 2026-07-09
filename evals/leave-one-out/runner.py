#!/usr/bin/env python3
"""Leave-one-out retrieval recall@K eval (Measurement A from v0.9 plan).

For each triple in the corpus:
  1. Embed its orig_prompt (one Ollama call per trial — corpus stays embedded).
  2. Score against all index vectors EXCEPT the trial's own (boolean mask).
  3. Take top-K matches, look up their buckets via bucket_for(user_correction).
  4. Hit if the held-out triple's own bucket appears in top-K.
  5. Also report exact-hit (would the trial's own triple have been top-1
     if not masked).

Triples whose user_correction doesn't match any bucket are excluded from
the denominator (with explicit count reported).

Produces:
  - results.json (machine-readable)
  - RESULTS.md (human-readable summary)

Reproduce:
  python3 evals/leave-one-out/runner.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Allow running from repo root without install.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hermeneutic import compile as hcompile  # noqa: E402
from hermeneutic.triples import Triple  # noqa: E402

K_VALUES = [1, 3, 5, 10]
N_PER_BUCKET = 2          # v0.9 default — matches compile.DEFAULT_N_PER_BUCKET
THRESHOLD = 0.5           # v0.9 default — matches compile.DEFAULT_SIM_THRESHOLD


def main() -> int:
    home = hcompile.home_dir()
    triples_path = home / "triples.jsonl"
    if not triples_path.is_file():
        print(f"ERROR: {triples_path} not found. Run `hermeneutic mine ... --out {triples_path}` first.", file=sys.stderr)
        return 1

    idx = hcompile.load_index(home)
    if idx is None:
        print(f"ERROR: no index at {home}. Run `hermeneutic compile-index` first.", file=sys.stderr)
        return 1

    triples = [Triple.from_json(line) for line in triples_path.read_text().splitlines() if line.strip()]
    n_total = len(triples)

    # Map index position -> triple index (in the source jsonl).
    pos_to_triple = idx.triple_indices  # list[int]

    # Compute true bucket for each triple in the index (skip if no bucket match).
    bucket_per_pos: list[str | None] = []
    for ti in pos_to_triple:
        b = hcompile.bucket_for(triples[ti].user_correction)
        bucket_per_pos.append(b[0] if b else None)

    eligible_positions = [p for p, b in enumerate(bucket_per_pos) if b is not None]
    n_eligible = len(eligible_positions)
    n_skipped_unbucketed = len(idx.vectors) - n_eligible

    print(f"Corpus: {n_total} triples; index has {len(idx.vectors)} eligible-orig-prompt entries.", file=sys.stderr)
    print(f"Bucketed (eligible for recall): {n_eligible}; skipped (no bucket match): {n_skipped_unbucketed}.", file=sys.stderr)
    print(f"Running {n_eligible} leave-one-out trials (zero Ollama calls — reuse existing index vectors as queries)...", file=sys.stderr)

    bucket_hits = {k: 0 for k in K_VALUES}
    bucket_aware_hits = 0     # v0.9 metric: top-N per bucket (above threshold)
    exact_hits = {k: 0 for k in K_VALUES}
    t0 = time.time()
    fails = 0

    for trial_n, trial_pos in enumerate(eligible_positions, 1):
        if trial_n % 50 == 0:
            print(f"  [{trial_n}/{n_eligible}] elapsed={time.time()-t0:.1f}s", file=sys.stderr)
        triple_idx = pos_to_triple[trial_pos]
        true_bucket = bucket_per_pos[trial_pos]

        # Leave-one-out: the index already contains embed(orig_prompt) at trial_pos.
        # Query with that exact vector and mask out trial_pos. Zero new Ollama calls.
        q = idx.vectors[trial_pos]

        # Score against all positions except trial_pos
        scored: list[tuple[float, int]] = []
        for pos, vec in enumerate(idx.vectors):
            if pos == trial_pos:
                continue
            s = sum(x * y for x, y in zip(q, vec, strict=False))
            scored.append((s, pos))
        scored.sort(key=lambda x: -x[0])

        # Legacy global top-K bucket-hit (for comparison with v0.9 bucket-aware)
        for k in K_VALUES:
            top = scored[:k]
            top_buckets = {bucket_per_pos[p] for _, p in top if bucket_per_pos[p] is not None}
            if true_bucket in top_buckets:
                bucket_hits[k] += 1

        # v0.9 bucket-aware metric: top-N per bucket above threshold
        # (matches compile_prompt's actual behavior post-tweak)
        from collections import defaultdict as _dd
        by_bucket_local: dict[str, list[float]] = _dd(list)
        for sim, pos in scored:
            if sim < THRESHOLD:
                continue
            b = bucket_per_pos[pos]
            if b is None:
                continue
            by_bucket_local[b].append(sim)
        # A bucket is "surfaced" only if it has ≥N_PER_BUCKET candidates above
        # threshold — this is the actual constraint compile_prompt applies.
        # n=1 is degenerate (every non-empty bucket surfaces); n=2 is the
        # measured sweet spot per evals/leave-one-out/test_bucket_aware.py.
        surfaced_buckets = {b for b, sims in by_bucket_local.items() if len(sims) >= N_PER_BUCKET}
        if true_bucket in surfaced_buckets:
            bucket_aware_hits += 1

        # Same-session sanity check
        for k in K_VALUES:
            top_session_ids = {triples[pos_to_triple[p]].session for _, p in scored[:k]}
            if triples[triple_idx].session in top_session_ids:
                exact_hits[k] += 1

    elapsed = time.time() - t0
    n_run = n_eligible - fails

    # Random-retrieval baseline: for each trial, sample K positions uniformly at
    # random (excluding self), check if true bucket is in their buckets.
    import random as _random
    rng = _random.Random(42)
    random_bucket_hits = {k: 0 for k in K_VALUES}
    random_trials = 1000  # average over many random samplings per trial
    for trial_pos in eligible_positions:
        true_bucket = bucket_per_pos[trial_pos]
        candidate_positions = [p for p in range(len(idx.vectors)) if p != trial_pos]
        for k in K_VALUES:
            hits = 0
            for _ in range(random_trials // n_run + 1):
                sample = rng.sample(candidate_positions, min(k, len(candidate_positions)))
                if true_bucket in {bucket_per_pos[p] for p in sample if bucket_per_pos[p] is not None}:
                    hits += 1
            random_bucket_hits[k] += hits / (random_trials // n_run + 1)
    random_baseline_rate = {k: random_bucket_hits[k] / n_run for k in K_VALUES}

    # Per-bucket breakdown of cosine retrieval (where does it succeed/fail?)
    bucket_hit_breakdown: dict[str, dict[int, list[int]]] = {}  # bucket -> K -> [hits, total]
    for trial_pos in eligible_positions:
        true_bucket = bucket_per_pos[trial_pos]
        if true_bucket not in bucket_hit_breakdown:
            bucket_hit_breakdown[true_bucket] = {k: [0, 0] for k in K_VALUES}
        # Re-score for breakdown
        q = idx.vectors[trial_pos]
        scored = sorted(
            ((sum(x*y for x,y in zip(q, idx.vectors[p], strict=False)), p)
             for p in range(len(idx.vectors)) if p != trial_pos),
            key=lambda x: -x[0],
        )
        for k in K_VALUES:
            top_buckets = {bucket_per_pos[p] for _, p in scored[:k] if bucket_per_pos[p] is not None}
            bucket_hit_breakdown[true_bucket][k][1] += 1
            if true_bucket in top_buckets:
                bucket_hit_breakdown[true_bucket][k][0] += 1

    # v0.9 bucket-aware per-bucket breakdown
    bucket_aware_breakdown: dict[str, list[int]] = {b: [0, 0] for b in set(bucket_per_pos) if b}
    for trial_pos in eligible_positions:
        true_b = bucket_per_pos[trial_pos]
        q = idx.vectors[trial_pos]
        from collections import defaultdict as _dd2
        bb: dict[str, list[float]] = _dd2(list)
        for pos, vec in enumerate(idx.vectors):
            if pos == trial_pos: continue
            s = sum(x * y for x, y in zip(q, vec, strict=False))
            if s >= THRESHOLD and bucket_per_pos[pos] is not None:
                bb[bucket_per_pos[pos]].append(s)
        bucket_aware_breakdown[true_b][1] += 1
        if true_b in bb and len(bb[true_b]) >= N_PER_BUCKET:
            bucket_aware_breakdown[true_b][0] += 1

    out = {
        "n_total_triples": n_total,
        "n_indexed": len(idx.vectors),
        "n_eligible_for_recall": n_eligible,
        "n_skipped_unbucketed": n_skipped_unbucketed,
        "n_trials_attempted": n_eligible,
        "n_trials_succeeded": n_run,
        "n_trials_failed": fails,
        "v09_bucket_aware": {
            "method": f"top-N per bucket above threshold {THRESHOLD} (n_per_bucket={N_PER_BUCKET})",
            "hits": bucket_aware_hits,
            "rate": round(bucket_aware_hits/n_run, 4),
            "per_bucket": {b: {"hits": v[0], "total": v[1],
                               "rate": round(v[0]/v[1], 4) if v[1] else 0}
                           for b, v in bucket_aware_breakdown.items()},
        },
        "legacy_global_topk": {
            "method": "top-K global cosine (pre-v0.9 baseline)",
            "bucket_hits": bucket_hits,
            "bucket_hit_rate": {k: round(bucket_hits[k]/n_run, 4) for k in K_VALUES},
            "random_baseline_rate": {k: round(random_baseline_rate[k], 4) for k in K_VALUES},
        },
        "same_session_hits": exact_hits,
        "per_bucket_breakdown_topk": {
            b: {str(k): {"hits": v[k][0], "total": v[k][1],
                         "rate": round(v[k][0]/v[k][1], 4) if v[k][1] else 0}
                for k in K_VALUES}
            for b, v in bucket_hit_breakdown.items()
        },
        "k_values": K_VALUES,
        "wall_seconds": round(elapsed, 1),
        "model": idx.model,
        "dim": idx.dim,
    }

    out_dir = Path(__file__).resolve().parent
    (out_dir / "results.json").write_text(json.dumps(out, indent=2))

    md = ["# Leave-one-out retrieval recall — measured (v0.9)\n"]
    md.append(f"**Corpus:** {n_total} mined triples, {len(idx.vectors)} indexed (have orig_prompt), "
              f"{n_eligible} eligible (user_correction matches a bucket).\n")
    md.append("**Method:** boolean-mask leave-one-out — for each eligible triple, query with its own cached vector and mask out self.\n")
    md.append(f"**Trials succeeded:** {n_run}/{n_eligible}. "
              f"**Wall time:** {elapsed:.1f} s. **Embed model:** {idx.model} (dim={idx.dim}).\n")
    md.append(f"\n## v0.9 headline: bucket-aware retrieval (n_per_bucket={N_PER_BUCKET}, threshold={THRESHOLD})\n")
    md.append(f"**Overall recall:** {bucket_aware_hits}/{n_run} = **{bucket_aware_hits/n_run*100:.1f}%**\n\n")
    md.append("Per-bucket recall:\n\n")
    md.append("| true bucket | n | recall |\n|---|---|---|\n")
    for b in sorted(bucket_aware_breakdown.keys(), key=lambda x: -bucket_aware_breakdown[x][1]):
        v = bucket_aware_breakdown[b]
        md.append(f"| `{b}` | {v[1]} | {v[0]/v[1]*100 if v[1] else 0:.1f}% |\n")
    md.append("\n## Legacy comparison: global top-K (pre-v0.9 baseline)\n")
    md.append("Held-out triple's bucket appears in top-K returned matches:\n\n")
    md.append("| K | Cosine retrieval | Random-retrieval baseline | Δ |\n|---|---|---|---|\n")
    for k in K_VALUES:
        rate = bucket_hits[k] / n_run if n_run else 0
        rand = random_baseline_rate[k]
        delta = rate - rand
        sign = "+" if delta >= 0 else ""
        md.append(f"| {k} | **{rate*100:.1f}%** ({bucket_hits[k]}/{n_run}) | {rand*100:.1f}% | {sign}{delta*100:.1f} pp |\n")
    md.append("\n**Reading:** if Δ is positive, cosine retrieval is doing better than random sampling K from the corpus. If Δ is near zero or negative, the embedding signal is not adding value over a uniform sample.\n")
    md.append("\n## Per-bucket breakdown of cosine retrieval (K=5)\n")
    md.append("Where retrieval succeeds and fails, by held-out triple's true bucket:\n\n")
    md.append("| true bucket | n | bucket-hit@5 |\n|---|---|---|\n")
    for b in sorted(bucket_hit_breakdown.keys(), key=lambda x: -bucket_hit_breakdown[x][5][1]):
        v = bucket_hit_breakdown[b][5]
        md.append(f"| `{b}` | {v[1]} | {v[0]/v[1]*100 if v[1] else 0:.1f}% |\n")
    md.append("\n## Same-session sanity check\n")
    md.append("Top-K matches contain at least one triple from the same source session as the held-out triple (signal that prompts within a session cluster):\n\n")
    md.append("| K | Hits | Rate |\n|---|---|---|\n")
    for k in K_VALUES:
        rate = exact_hits[k] / n_run if n_run else 0
        md.append(f"| {k} | {exact_hits[k]}/{n_run} | {rate*100:.1f}% |\n")
    md.append("\n## Honest caveats\n")
    md.append("- Bucket-hit measures whether retrieval finds a *similar-class* historical correction. ")
    md.append("It does NOT measure whether the *exact* held-out correction would have been the top match (that would be circular — it was masked out).\n")
    md.append("- The bucket-hit floor is the corpus-wide most-common-bucket rate. ")
    md.append("If retrieval is no better than chance, bucket-hit@K=1 ≈ max-bucket-share. ")
    md.append("A meaningfully-higher rate than the chance floor indicates retrieval is doing prompt-specific work.\n")
    md.append(f"- Skipped {n_skipped_unbucketed} index entries because their user_correction text didn't match any of the 8 buckets — these are the unbucketed-rest from the v0.1 corpus study.\n")

    (out_dir / "RESULTS.md").write_text("".join(md))
    print(f"\nDone. Results: {out_dir}/results.json + RESULTS.md", file=sys.stderr)
    print(f"\nHeadline: bucket-hit@5 = {bucket_hits[5]/n_run*100:.1f}% (n={n_run})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
