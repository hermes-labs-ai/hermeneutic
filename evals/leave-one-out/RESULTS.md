# Production-path leave-one-out retrieval measurement

This current bounded run masks each held-out triple and calls the shipped `hermeneutic.compile.compile_prompt` function. It reuses the frozen cached query vector, so the measurement exercises production filtering, per-bucket selection, global cap, and synthesis without calling a moving Ollama model.

## Frozen identity

- Corpus: 346 triples, SHA-256 `920bfcac721e0df2b18894461daf5d5fd8d847d90974a4572e7749322900172b`
- Index: 346 vectors, SHA-256 `d1477ef2384dacc46117337d5b4aff2a2398032ee7b4ce3de2c7c4cee496dda1`
- Compile source SHA-256: `502798af9c74d4944d66217fc6d349a9f203d3522723e05be5433207dc7501a5`
- Model tag recorded in index: `nomic-embed-text` (dimension 768; cached vectors, no live model call)
- Trials: 104 bucketed; 242 unbucketed entries excluded

## Current result

| Shipped profile | k | Threshold | Per bucket | Same-bucket recall | Triggered | Mean buckets | Mean matches |
|---|---:|---:|---:|---:|---:|---:|---:|
| cli and compile hook defaults | 5 | 0.4 | 2 | **88/104 (84.62%)** | 104/104 | 3.29 | 4.96 |
| python library defaults | 10 | 0.5 | 2 | **94/104 (90.38%)** | 102/104 | 4.93 | 8.25 |

The installed CLI and built-in compile hook use the first profile. Direct Python callers that omit `k` and `threshold` use the second. These are corpus-specific retrieval measurements, not model-effectiveness results.

## Per-bucket current recall

| Bucket | Trials | CLI/hook defaults | Python defaults |
|---|---:|---:|---:|
| `missed_constraint` | 29 | 27/29 (93.10%) | 27/29 (93.10%) |
| `over_completion` | 4 | 0/4 (0.00%) | 4/4 (100.00%) |
| `over_confirmation` | 59 | 59/59 (100.00%) | 55/59 (93.22%) |
| `scope_creep` | 3 | 0/3 (0.00%) | 2/3 (66.67%) |
| `tool_choice` | 3 | 0/3 (0.00%) | 2/3 (66.67%) |
| `wrong_target` | 6 | 2/6 (33.33%) | 4/6 (66.67%) |

## Historical experiments

The prior **83.7% (87/104)** leave-one-out result and **98/100 versus 7/30** discrimination result remain dated frozen experiments. They are not current production-path headlines: the former used a different bucket-surfacing rule and omitted the global cap; the latter used global top-K and asymmetric trigger definitions. Their original aggregate receipts remain in this repository for provenance.

## Interpretation boundary

Same-bucket recall asks whether the production retrieval function surfaces at least one warning from the held-out correction's category after the held-out item is removed. It does not measure generalization to other users, the quality of the warning, false positives on normal prompts, or whether an LLM follows the injected context. Downstream effectiveness remains unmeasured.
