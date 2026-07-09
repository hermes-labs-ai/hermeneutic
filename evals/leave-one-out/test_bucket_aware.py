#!/usr/bin/env python3
"""Test ONE methodological tweak: bucket-aware top-K retrieval.

Hypothesis: rare-bucket triples are semantically similar to majority-bucket
triples (rank 60+ in global cosine), so global top-K crowds them out.
Fix: return top-2 PER bucket (above threshold), not top-K globally.

This guarantees rare buckets surface if any same-bucket match clears
threshold, regardless of global rank.

Compares:
  - Baseline: top-K=5 global cosine (current compile-prompt behavior)
  - Tweak:    top-2 per-bucket above threshold=0.4

Reports recall@K rates for the OVERALL corpus AND for the rare-bucket subset.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from collections import defaultdict

from hermeneutic import compile as hcompile
from hermeneutic.triples import Triple

home = hcompile.home_dir()
triples_path = home / "triples.jsonl"
idx = hcompile.load_index(home)
triples = [Triple.from_json(l) for l in triples_path.read_text().splitlines() if l.strip()]
bucket_per_pos = []
for ti in idx.triple_indices:
    b = hcompile.bucket_for(triples[ti].user_correction)
    bucket_per_pos.append(b[0] if b else None)

eligible_positions = [p for p, b in enumerate(bucket_per_pos) if b is not None]

THRESHOLD = 0.4
N_PER_BUCKET = 2     # tweak param

def baseline_topk(query_pos: int, k: int) -> set[str]:
    """Current behavior: top-K across all triples above threshold."""
    q = idx.vectors[query_pos]
    scored = []
    for p, vec in enumerate(idx.vectors):
        if p == query_pos: continue
        s = sum(x*y for x,y in zip(q, vec, strict=False))
        if s >= THRESHOLD:
            scored.append((s, p))
    scored.sort(key=lambda x: -x[0])
    return {bucket_per_pos[p] for _, p in scored[:k] if bucket_per_pos[p] is not None}

def bucket_aware(query_pos: int, n_per_bucket: int) -> set[str]:
    """Tweak: top-N per bucket above threshold."""
    q = idx.vectors[query_pos]
    by_bucket: dict[str, list] = defaultdict(list)
    for p, vec in enumerate(idx.vectors):
        if p == query_pos: continue
        b = bucket_per_pos[p]
        if b is None: continue
        s = sum(x*y for x,y in zip(q, vec, strict=False))
        if s >= THRESHOLD:
            by_bucket[b].append((s, p))
    # Take top-N from each bucket
    surfaced_buckets = set()
    for b, lst in by_bucket.items():
        lst.sort(key=lambda x: -x[0])
        if lst[:n_per_bucket]:
            surfaced_buckets.add(b)
    return surfaced_buckets

# Compare on all eligible
RARE = {"wrong_target", "over_completion", "scope_creep", "tool_choice"}

baseline_hits_all = 0
tweak_hits_all = 0
baseline_hits_rare = 0
tweak_hits_rare = 0
n_rare = 0

for trial_pos in eligible_positions:
    true_b = bucket_per_pos[trial_pos]
    base_buckets = baseline_topk(trial_pos, k=5)
    tweak_buckets = bucket_aware(trial_pos, N_PER_BUCKET)
    base_hit = true_b in base_buckets
    tweak_hit = true_b in tweak_buckets
    baseline_hits_all += int(base_hit)
    tweak_hits_all += int(tweak_hit)
    if true_b in RARE:
        n_rare += 1
        baseline_hits_rare += int(base_hit)
        tweak_hits_rare += int(tweak_hit)

n_all = len(eligible_positions)
print(f"Bucket-aware retrieval (top-{N_PER_BUCKET} per bucket above threshold {THRESHOLD}) vs baseline (top-5 global)\n")
print(f"OVERALL  (n={n_all}):")
print(f"  baseline  recall: {baseline_hits_all}/{n_all} = {baseline_hits_all/n_all*100:.1f}%")
print(f"  tweak     recall: {tweak_hits_all}/{n_all} = {tweak_hits_all/n_all*100:.1f}%  Δ = {(tweak_hits_all-baseline_hits_all)/n_all*100:+.1f}pp")
print()
print(f"RARE-BUCKET subset (n={n_rare}):")
print(f"  baseline  recall: {baseline_hits_rare}/{n_rare} = {baseline_hits_rare/n_rare*100:.1f}%")
print(f"  tweak     recall: {tweak_hits_rare}/{n_rare} = {tweak_hits_rare/n_rare*100:.1f}%  Δ = {(tweak_hits_rare-baseline_hits_rare)/n_rare*100:+.1f}pp")
print()
# Also check: how many buckets does tweak surface on average?
total_tweak_buckets = 0
for trial_pos in eligible_positions:
    total_tweak_buckets += len(bucket_aware(trial_pos, N_PER_BUCKET))
print(f"Avg buckets surfaced per query (tweak): {total_tweak_buckets/n_all:.2f}")
