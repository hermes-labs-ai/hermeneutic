# Current deterministic gate coverage

This bounded measurement runs the shipped eight-rule English gate over the `prior_assistant` field of the already frozen 346-triple retrieval corpus. It does not re-mine private logs and writes no private text.

## Identity

- Corpus SHA-256: `920bfcac721e0df2b18894461daf5d5fd8d847d90974a4572e7749322900172b`
- Gate source SHA-256: `24a70e1239e36922f0fa5093dcd43b9a07f1bc18d23157b18e4aacea09072276`
- Triples: 346
- Rules: 8 fixed English surface-pattern rules

## Result

The current gate fires on **115/346 (33.24%)** prior assistant replies and stays silent on **231/346**. This is retrospective derivation-set coverage, not held-out recall.

| Rule | Severity | Triples | Raw matches | Triple rate |
|---|---:|---:|---:|---:|
| `completion_with_number` | high | 65 | 76 | 18.79% |
| `completion_with_all_quantifier` | high | 5 | 5 | 1.45% |
| `number_then_completion` | high | 52 | 61 | 15.03% |
| `subagent_passthrough` | high | 17 | 27 | 4.91% |
| `authority_passthrough` | med | 0 | 0 | 0.00% |
| `unhedged_certainty` | med | 26 | 42 | 7.51% |
| `scope_expansion` | med | 17 | 19 | 4.91% |
| `fluent_summary_no_evidence` | low | 2 | 2 | 0.58% |

## Overlap

| Distinct rules on one triple | Triples |
|---:|---:|
| 0 | 231 |
| 1 | 61 |
| 2 | 41 |
| 3 | 11 |
| 4 | 2 |

**54** triples fire more than one distinct rule. Pair counts are preserved in [`results.json`](results.json).

## Derivation-set comparison

The original six-rule subset directly fires on **105/346 (30.35%)** rows in this frozen 346-triple corpus. The two later rules add **10** uniquely covered rows. The historical `about 65%` statement was a category-mapping estimate on the separate 326-triple derivation run, not a direct regex execution result.

## Interpretation boundary

This result answers one narrow question: how much of the frozen correction corpus's prior assistant text has a surface form recognized by the current fixed gate? The corpus consists only of correction-bearing episodes and was involved in rule derivation, so the result cannot establish precision, false-positive rate, live trigger rate, severity calibration, or downstream effectiveness. Those remain unmeasured for v0.1.7.
