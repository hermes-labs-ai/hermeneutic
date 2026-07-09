#!/usr/bin/env python3
"""Diagnose why rare buckets hit 0% recall@K=5.

Runs the leave-one-out eval again, but breaks down per rare-bucket triple:
  - What is the true bucket?
  - What are the top-10 nearest non-self triples by cosine?
  - At what rank does the FIRST same-bucket match appear?
  - Is it filtered out by threshold=0.4, or just outranked by majority-class?

Outputs a per-rare-triple report so we can see exactly where retrieval fails.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from collections import Counter

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

# Count buckets among bucketed triples
bucket_counts = Counter(b for b in bucket_per_pos if b)
print(f"Bucket counts in eligible set: {dict(bucket_counts.most_common())}\n")

RARE_BUCKETS = {"wrong_target", "over_completion", "scope_creep", "tool_choice"}
print(f"Diagnosing {sum(1 for b in bucket_per_pos if b in RARE_BUCKETS)} rare-bucket triples:\n")
print(f"{'true_bucket':20s} {'rank_first_same':>16s} {'sim_first_same':>16s} {'top1_bucket':20s} {'top1_sim':>10s}")
print("-" * 90)

for trial_pos, true_b in enumerate(bucket_per_pos):
    if true_b not in RARE_BUCKETS:
        continue
    q = idx.vectors[trial_pos]
    # Score against all non-self
    scored = []
    for p, vec in enumerate(idx.vectors):
        if p == trial_pos: continue
        s = sum(x*y for x,y in zip(q, vec, strict=False))
        scored.append((s, p))
    scored.sort(key=lambda x: -x[0])

    # Find rank of first same-bucket match
    rank_first_same = None
    sim_first_same = None
    for rank, (sim, pos) in enumerate(scored, 1):
        if bucket_per_pos[pos] == true_b:
            rank_first_same = rank
            sim_first_same = sim
            break
    top1_sim, top1_pos = scored[0]
    top1_b = bucket_per_pos[top1_pos] or "(none)"
    rfs = str(rank_first_same) if rank_first_same else "NEVER"
    sfs = f"{sim_first_same:.3f}" if sim_first_same is not None else "n/a"
    print(f"{true_b:20s} {rfs:>16s} {sfs:>16s} {top1_b:20s} {top1_sim:.3f}")

print("\n## Distribution of `rank_first_same`")
print("Where does the FIRST same-bucket match show up in the ranking, for rare-bucket queries?")

ranks = []
for trial_pos, true_b in enumerate(bucket_per_pos):
    if true_b not in RARE_BUCKETS: continue
    q = idx.vectors[trial_pos]
    scored = sorted(((sum(x*y for x,y in zip(q, idx.vectors[p], strict=False)), p)
                     for p in range(len(idx.vectors)) if p != trial_pos), key=lambda x: -x[0])
    for rank, (_, pos) in enumerate(scored, 1):
        if bucket_per_pos[pos] == true_b:
            ranks.append(rank)
            break
    else:
        ranks.append(None)

found = [r for r in ranks if r is not None]
not_found = sum(1 for r in ranks if r is None)
print(f"\nFound at rank: min={min(found) if found else 'na'} median={sorted(found)[len(found)//2] if found else 'na'} "
      f"max={max(found) if found else 'na'}")
print(f"Never found: {not_found}/{len(ranks)}")

# Rate at top-5, top-10, top-20, top-50, top-100, top-200
print("\nRecall@K for rare-bucket queries:")
for k in [1, 3, 5, 10, 20, 50, 100, 200, len(idx.vectors)]:
    hits = sum(1 for r in ranks if r is not None and r <= k)
    print(f"  K={k:>4d}: {hits}/{len(ranks)} = {hits/len(ranks)*100:.1f}%")
