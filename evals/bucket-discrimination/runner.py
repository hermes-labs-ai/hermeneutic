#!/usr/bin/env python3
"""Historical bucket-distribution discrimination experiment.

This runner uses a legacy global-top-K approximation, not the shipped
bucket-aware `compile_prompt` path. Its committed output is provenance only.

Two metrics, deliberately separated to avoid the degenerate-χ² trap where
random prompts mostly produce empty preambles and χ² fires for the wrong
reason.

  B1: retrieval-trigger rate. For 100 in-corpus orig_prompts vs 30
      synthetic random prompts, count how many produce a non-empty
      preamble at threshold=0.5. Fisher's exact test on a 2x2 contingency.

  B2: bucket-shape discrimination CONDITIONAL on retrieval triggered.
      Within prompts that DID produce a non-empty preamble, tabulate
      bucket counts. χ² on the 8-bucket distribution.

Random source: deterministic word-recombiner from /usr/share/dict/words
with fixed seed=42. 3-6 random words joined with spaces. Documented
limitation: synthetic, not real-user prompts. v1.0 upgrades to real OOD.
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hermeneutic import compile as hcompile  # noqa: E402
from hermeneutic.triples import Triple  # noqa: E402

try:
    from scipy.stats import chi2_contingency, fisher_exact
except ImportError:
    print("ERROR: scipy required. pip install scipy", file=sys.stderr)
    sys.exit(1)


SEED = 42
N_IN_CORPUS = 100   # cached — zero Ollama calls
N_RANDOM = 30       # live — N Ollama calls; reduced to fit a budget when Ollama is contended
WORDS_FILE = "/usr/share/dict/words"


def random_prompts(n: int, seed: int = SEED) -> list[str]:
    """Synthetic baseline: deterministic word-recombiner."""
    rng = random.Random(seed)
    with open(WORDS_FILE) as f:
        words = [w.strip().lower() for w in f if w.strip().isalpha() and 3 <= len(w.strip()) <= 12]
    out: list[str] = []
    for _ in range(n):
        k = rng.randint(3, 6)
        out.append(" ".join(rng.sample(words, k)))
    return out


def main() -> int:
    home = hcompile.home_dir()
    triples_path = home / "triples.jsonl"
    if not triples_path.is_file():
        print(f"ERROR: {triples_path} not found.", file=sys.stderr)
        return 1
    idx = hcompile.load_index(home)
    if idx is None:
        print(f"ERROR: no index at {home}.", file=sys.stderr)
        return 1

    triples = [Triple.from_json(line) for line in triples_path.read_text().splitlines() if line.strip()]
    rng = random.Random(SEED)

    # Sample N_IN_CORPUS positions from the index (cached embeddings)
    indexed_positions = list(range(len(idx.vectors)))
    in_corpus_positions = rng.sample(indexed_positions, min(N_IN_CORPUS, len(indexed_positions)))

    # Random baseline prompts — must be embedded live
    random_baseline = random_prompts(N_RANDOM)

    print(f"In-corpus: {len(in_corpus_positions)} (cached embeddings)", file=sys.stderr)
    print(f"Random baseline: {len(random_baseline)} (live Ollama embeds)", file=sys.stderr)

    THRESHOLD = 0.5     # historical experiment setting
    K = 10              # historical global cap

    def score_query_vec(q: list[float]) -> list[str]:
        """Return bucket names from top-K matches above threshold (cached scoring)."""
        scored = []
        for vec, ti in zip(idx.vectors, idx.triple_indices, strict=False):
            s = sum(x*y for x,y in zip(q, vec, strict=False))
            if s >= THRESHOLD:
                scored.append((s, ti))
        scored.sort(key=lambda x: -x[0])
        bucket_names: list[str] = []
        for _, ti in scored[:K]:
            b = hcompile.bucket_for(triples[ti].user_correction)
            if b:
                bucket_names.append(b[0])
        return bucket_names

    # In-corpus: use cached vectors
    in_buckets: list[str] = []
    in_triggered = 0
    for n, pos in enumerate(in_corpus_positions, 1):
        if n % 25 == 0:
            print(f"  [in-corpus] {n}/{len(in_corpus_positions)}", file=sys.stderr)
        # exclude self by mask
        q = idx.vectors[pos]
        scored = []
        for p, vec in enumerate(idx.vectors):
            if p == pos: continue
            s = sum(x*y for x,y in zip(q, vec, strict=False))
            if s >= THRESHOLD:
                scored.append((s, idx.triple_indices[p]))
        scored.sort(key=lambda x: -x[0])
        if scored:
            in_triggered += 1
            for _, ti in scored[:K]:
                b = hcompile.bucket_for(triples[ti].user_correction)
                if b: in_buckets.append(b[0])

    # Random: live embed
    rand_buckets: list[str] = []
    rand_triggered = 0
    rand_failed = 0
    for n, p in enumerate(random_baseline, 1):
        if n % 5 == 0:
            print(f"  [random] {n}/{len(random_baseline)}", file=sys.stderr)
        try:
            q = hcompile._normalize(hcompile.ollama_embed(p, timeout=120.0))
        except hcompile.OllamaUnavailable as e:
            rand_failed += 1
            if rand_failed <= 2:
                print(f"  ollama failure on random[{n}]: {e}", file=sys.stderr)
            continue
        if len(q) != idx.dim:
            rand_failed += 1
            continue
        names = score_query_vec(q)
        if names:
            rand_triggered += 1
            rand_buckets.extend(names)

    n_random_succeeded = len(random_baseline) - rand_failed
    if n_random_succeeded == 0:
        print("ERROR: all random embed calls failed (Ollama down?). Cannot run B.", file=sys.stderr)
        return 1

    # B1: 2x2 retrieval-trigger contingency
    in_silent = len(in_corpus_positions) - in_triggered
    rand_silent = n_random_succeeded - rand_triggered
    b1_table = [[in_triggered, in_silent], [rand_triggered, rand_silent]]
    b1_odds, b1_p = fisher_exact(b1_table)

    # B2: bucket distribution conditional on triggered
    bucket_universe = sorted(set(in_buckets) | set(rand_buckets))
    in_counts = Counter(in_buckets)
    rand_counts = Counter(rand_buckets)
    if bucket_universe and (in_buckets or rand_buckets):
        b2_table = [
            [in_counts.get(b, 0) for b in bucket_universe],
            [rand_counts.get(b, 0) for b in bucket_universe],
        ]
        # Drop columns where both rows are zero (chi2 needs nonzero marginals)
        b2_table_nonzero = [
            [r[i] for i in range(len(bucket_universe)) if b2_table[0][i] + b2_table[1][i] > 0]
            for r in b2_table
        ]
        nonzero_buckets = [b for i, b in enumerate(bucket_universe) if b2_table[0][i] + b2_table[1][i] > 0]
        if len(nonzero_buckets) >= 2:
            try:
                chi2, b2_p, dof, _ = chi2_contingency(b2_table_nonzero)
                b2_chi2 = round(float(chi2), 3)
                b2_p_val = float(b2_p)
                b2_dof = int(dof)
            except ValueError as e:
                b2_chi2, b2_p_val, b2_dof = None, None, None
                b2_error = str(e)
            else:
                b2_error = None
        else:
            b2_chi2, b2_p_val, b2_dof, b2_error = None, None, None, "fewer than 2 nonzero buckets — test undefined"
    else:
        b2_chi2, b2_p_val, b2_dof, b2_error = None, None, None, "no triggered prompts in either group"

    out = {
        "status": "historical_only",
        "production_path_equivalent": False,
        "known_mismatch": (
            "Uses legacy global top-K selection and asymmetric in-corpus/random trigger definitions; "
            "does not execute the shipped bucket-aware compile_prompt path."
        ),
        "seed": SEED,
        "n_in_corpus": len(in_corpus_positions),
        "n_random": n_random_succeeded,
        "n_random_failed": rand_failed,
        "threshold": THRESHOLD,
        "K": K,
        "B1_retrieval_trigger": {
            "in_corpus_triggered": in_triggered,
            "in_corpus_silent": in_silent,
            "random_triggered": rand_triggered,
            "random_silent": rand_silent,
            "fisher_odds_ratio": round(float(b1_odds), 3),
            "fisher_p": float(b1_p),
        },
        "B2_bucket_shape_conditional": {
            "in_corpus_bucket_counts": dict(in_counts),
            "random_bucket_counts": dict(rand_counts),
            "chi2": b2_chi2,
            "p": b2_p_val,
            "dof": b2_dof,
            "error": b2_error,
        },
        "random_source": "deterministic word-recombiner from /usr/share/dict/words, 3-6 words per prompt, seed=42",
    }

    out_dir = Path(__file__).resolve().parent
    (out_dir / "results.json").write_text(json.dumps(out, indent=2))

    md = [f"# Historical bucket-distribution experiment (seed={SEED}, N_in_corpus={len(in_corpus_positions)}, N_random={n_random_succeeded})\n\n"]
    md.append("**Status: historical only.** This runner uses legacy global top-K selection and asymmetric trigger definitions; it is not equivalent to the shipped bucket-aware `compile_prompt` path. Retained for provenance, not a current product claim.\n\n")
    if rand_failed > 0:
        md.append(f"_Note: {rand_failed} random-prompt embed calls failed (Ollama contention) — N_random reduced from {N_RANDOM} to {n_random_succeeded}._\n\n")
    md.append("## B1: retrieval-trigger rate (in-corpus vs synthetic random)\n\n")
    md.append(f"How often does `compile` produce a non-empty preamble at threshold={THRESHOLD}, K={K}?\n\n")
    md.append("|  | triggered | silent | rate |\n|---|---|---|---|\n")
    md.append(f"| in-corpus | {in_triggered} | {in_silent} | {in_triggered/len(in_corpus_positions)*100:.0f}% |\n")
    md.append(f"| random   | {rand_triggered} | {rand_silent} | {rand_triggered/n_random_succeeded*100 if n_random_succeeded else 0:.0f}% |\n\n")
    md.append(f"**Fisher's exact (2-tailed):** odds ratio = {round(float(b1_odds),3)}, p = {b1_p:.2e}.\n\n")
    md.append("## B2: bucket-shape discrimination (conditional on triggered)\n\n")
    md.append("Within prompts that produced a non-empty preamble, what bucket distribution did each group induce?\n\n")
    md.append("| bucket | in-corpus | random |\n|---|---|---|\n")
    for b in bucket_universe:
        md.append(f"| `{b}` | {in_counts.get(b,0)} | {rand_counts.get(b,0)} |\n")
    md.append("\n")
    if b2_chi2 is not None:
        md.append(f"**χ² test:** χ² = {b2_chi2}, dof = {b2_dof}, p = {b2_p_val:.2e}.\n\n")
    else:
        md.append(f"**χ² test:** undefined — {b2_error}.\n\n")
    md.append("## Honest caveats\n\n")
    md.append("- **Random source is synthetic** (word-recombiner). Not real-user prompts. v1.0 baseline upgrade is real OOD prompts (Tatoeba, public chat corpus).\n")
    md.append("- **B1 is the more interpretable result.** It directly answers \"does the retrieval system distinguish in-distribution from out-of-distribution prompts at all?\" If B1 is significant, retrieval isn't returning the corpus-wide prior on every input.\n")
    md.append("- **B2 isolates the *shape* of bucket output once retrieval triggers**, removing the trigger-rate confound. If B1 is significant but B2 is not, retrieval triggers more often on in-corpus prompts but the bucket mix is similar — that's still a useful discriminator, just at the trigger level.\n")
    md.append("- **Significant ≠ useful.** This eval rules out the null (compile output is invariant to input). It does NOT validate the *quality* of the differentiation — that requires the v1.0 replay study.\n")

    (out_dir / "RESULTS.md").write_text("".join(md))
    print(f"\nDone. Results: {out_dir}/results.json + RESULTS.md", file=sys.stderr)
    print(f"B1 trigger rate: in-corpus {in_triggered}/{len(in_corpus_positions)} vs random {rand_triggered}/{n_random_succeeded}, Fisher p={b1_p:.2e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
