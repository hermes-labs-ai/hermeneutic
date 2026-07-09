# Leave-one-out retrieval recall — measured (v0.9)
**Corpus:** 346 mined triples, 346 indexed (have orig_prompt), 104 eligible (user_correction matches a bucket).
**Method:** boolean-mask leave-one-out — for each eligible triple, query with its own cached vector and mask out self.
**Trials succeeded:** 104/104. **Wall time:** 0.6 s. **Embed model:** nomic-embed-text (dim=768).

## v0.9 headline: bucket-aware retrieval (n_per_bucket=2, threshold=0.5)
**Overall recall:** 87/104 = **83.7%**

Per-bucket recall:

| true bucket | n | recall |
|---|---|---|
| `over_confirmation` | 59 | 91.5% |
| `missed_constraint` | 29 | 86.2% |
| `wrong_target` | 6 | 50.0% |
| `over_completion` | 4 | 75.0% |
| `scope_creep` | 3 | 33.3% |
| `tool_choice` | 3 | 33.3% |

## Legacy comparison: global top-K (pre-v0.9 baseline)
Held-out triple's bucket appears in top-K returned matches:

| K | Cosine retrieval | Random-retrieval baseline | Δ |
|---|---|---|---|
| 1 | **16.3%** (17/104) | 11.5% | +4.8 pp |
| 3 | **41.3%** (43/104) | 29.7% | +11.6 pp |
| 5 | **56.7%** (59/104) | 44.5% | +12.2 pp |
| 10 | **66.3%** (69/104) | 64.8% | +1.5 pp |

**Reading:** if Δ is positive, cosine retrieval is doing better than random sampling K from the corpus. If Δ is near zero or negative, the embedding signal is not adding value over a uniform sample.

## Per-bucket breakdown of cosine retrieval (K=5)
Where retrieval succeeds and fails, by held-out triple's true bucket:

| true bucket | n | bucket-hit@5 |
|---|---|---|
| `over_confirmation` | 59 | 81.4% |
| `missed_constraint` | 29 | 37.9% |
| `wrong_target` | 6 | 0.0% |
| `over_completion` | 4 | 0.0% |
| `scope_creep` | 3 | 0.0% |
| `tool_choice` | 3 | 0.0% |

## Same-session sanity check
Top-K matches contain at least one triple from the same source session as the held-out triple (signal that prompts within a session cluster):

| K | Hits | Rate |
|---|---|---|
| 1 | 22/104 | 21.2% |
| 3 | 29/104 | 27.9% |
| 5 | 34/104 | 32.7% |
| 10 | 49/104 | 47.1% |

## Honest caveats
- Bucket-hit measures whether retrieval finds a *similar-class* historical correction. It does NOT measure whether the *exact* held-out correction would have been the top match (that would be circular — it was masked out).
- The bucket-hit floor is the corpus-wide most-common-bucket rate. If retrieval is no better than chance, bucket-hit@K=1 ≈ max-bucket-share. A meaningfully-higher rate than the chance floor indicates retrieval is doing prompt-specific work.
- Skipped 242 index entries because their user_correction text didn't match any of the 8 buckets — these are the unbucketed-rest from the v0.1 corpus study.
