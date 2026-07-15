# Historical bucket-distribution experiment (seed=42, N_in_corpus=100, N_random=30)

**Status: historical only.** This runner uses legacy global top-K selection and asymmetric trigger definitions; it is not equivalent to the shipped bucket-aware `compile_prompt` path. It is retained for provenance, not a current product claim.

## B1: retrieval-trigger rate (in-corpus vs synthetic random)

How often does `compile` produce a non-empty preamble at threshold=0.5, K=10?

|  | triggered | silent | rate |
|---|---|---|---|
| in-corpus | 98 | 2 | 98% |
| random   | 7 | 23 | 23% |

**Fisher's exact (2-tailed):** odds ratio = 161.0, p = 2.63e-17.

## B2: bucket-shape discrimination (conditional on triggered)

Within prompts that produced a non-empty preamble, what bucket distribution did each group induce?

| bucket | in-corpus | random |
|---|---|---|
| `missed_constraint` | 68 | 3 |
| `over_completion` | 6 | 0 |
| `over_confirmation` | 235 | 4 |
| `scope_creep` | 14 | 0 |
| `tool_choice` | 14 | 1 |
| `wrong_target` | 15 | 0 |

**χ² test:** χ² = 3.801, dof = 5, p = 5.78e-01.

## Honest caveats

- **Random source is synthetic** (word-recombiner). Not real-user prompts. v1.0 baseline upgrade is real OOD prompts (Tatoeba, public chat corpus).
- **B1 is the more interpretable result.** It directly answers "does the retrieval system distinguish in-distribution from out-of-distribution prompts at all?" If B1 is significant, retrieval isn't returning the corpus-wide prior on every input.
- **B2 isolates the *shape* of bucket output once retrieval triggers**, removing the trigger-rate confound. If B1 is significant but B2 is not, retrieval triggers more often on in-corpus prompts but the bucket mix is similar — that's still a useful discriminator, just at the trigger level.
- **Significant ≠ useful.** This eval rules out the null (compile output is invariant to input). It does NOT validate the *quality* of the differentiation — that requires the v1.0 replay study.
