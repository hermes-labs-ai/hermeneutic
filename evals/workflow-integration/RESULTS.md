# Scoped correction-recall integration: installation held

The candidate recovers the motivating correction in a native staged Codex session,
but does **not** meet the preregistered installation criteria. The existing
operational workspace command remains unchanged. No new operational integration
is enabled, and no release is published by this work.

## Host and baseline

Codex is the owner's normal operational entry point, established by its current
project instructions, actual correction rollout, and earlier native entrypoint
probes in the storage-transition receipt. The selected supported extension is a
project `AGENTS.md` instruction calling an on-demand offline command. It adds no
automatic startup scan or global hook. See the [integration recipe](../../integrations/codex.md).

The installed release miner reproduced **zero triples from the reported
31-turn prefix**. The source had continued to 36 parsed turns when snapshotted;
that snapshot also produced zero. Private raw evidence, identifiers, original
text, and derived correction memory remain outside Git. The candidate mines one
seed episode. This is development evidence from one failure, not a mining-recall
estimate. See [baseline.json](baseline.json).

[Native checks](native-checks.json) distinguish delivery from quality: a fresh
Codex session followed the old instruction and reported unavailable; staged
sessions using the installed candidates invoked the new command and recovered
the intended historical meaning. A missing-package session returned the expected
continuation response, and package reinstall succeeded. Staging restoration
preserved the prior instruction bytes. These isolated checks do not prove a
general agent-behavior or productivity improvement.

## Independent evaluation

[Acceptance](acceptance.json) was committed before implementation. Fixture authors
did not inspect candidate source or private evidence before freezing labels.
Runtime identities and fixture hashes accompany the receipts. The seed and
implementation tests never count as holdout cases.

| Set and candidate | Corrections recovered | Noncorrections mined | Recall targets in top three | Irrelevant queries returning evidence |
| --- | ---: | ---: | ---: | ---: |
| Initial baseline | 3/24 | 1/24 | 23/24 | 13/24 |
| Initial candidate | 3/24 | 1/24 | 21/24 | 8/24 |
| Fresh baseline | 2/24 | 4/28 | 24/24 | 20/24 |
| Fresh final candidate | 2/24 | 4/28 | 24/24 | 1/24 |

Initial evidence: [baseline](holdout-baseline-results.json),
[candidate](holdout-results.json), [report](holdout-report.md).
Fresh evidence: [receipt](fresh-receipt.json), [per-case results](fresh-cases.json),
[fixtures](fresh-fixtures.json), [latency samples](fresh-latency.json).
The [same-fixture baseline comparison](fresh-baseline-comparison.json) separates
the final recall improvement from the pre-existing mining misses and false
positives. The candidate does not improve mining on either independent set.

The initial set was exposed after its failed evaluation and became development
evidence for one bounded remediation. A separate evaluator authored the fresh
set with different wording and situations, froze it before the final candidate,
and evaluated without label changes or retries. No source tuning followed the
fresh results. Both sets are now exposed regression evidence. They are small,
synthetic sets, not estimates of real-language or population-level performance.

Reproduce the fresh set with the matching installed candidate and wrapper:

```bash
python3 evals/workflow-integration/fresh-evaluate.py \
  --python /absolute/path/to/candidate-venv/bin/python \
  --wrapper /absolute/path/to/recall.py \
  --fixtures evals/workflow-integration/fresh-fixtures.json \
  --safety-fixtures evals/workflow-integration/fresh-safety-fixtures.json \
  --reference-receipt evals/workflow-integration/fresh-receipt.json \
  --out /absolute/private/path/to/new-evaluation-directory
```

The output directory must not exist. Exact raw outputs stay in its private run
subdirectory. Hash validation rejects a different fixture or wrapper; use a new
receipt rather than relabeling a changed candidate as this frozen evaluation.

The final candidate meets the fresh recall floors, but mining misses the
required 80% recovery and exceeds the 5% false-positive ceiling. Narrow lexical
steer markers do not cover the tested range of contextual corrections. This
work does not add a semantic miner or alias subsystem to hide that limitation.

## Latency, failure handling, privacy, and restoration

The [fresh receipt](fresh-receipt.json) records API warm p95/p99 of
0.255/0.298 ms over 200 calls, full cold-command p95/p99 of 121.175/122.887 ms
over 50 processes, and repeated full-command p95/p99 of 116.825/120.217 ms over
200 invocations. API timing excludes Python and wrapper startup. The actual
on-demand command starts processes on each call; its repeated-call latency
exceeds the 30/50 ms warm budgets. No threshold was waived.

Tested bounded-output, fail-open, immutable-store, canary, and inert hostile-data
checks passed; the fresh maximum output was 626 UTF-8 bytes. This is finite
instrumented evidence, not a guarantee about arbitrary hostile memory or model
compliance. Corpus data is returned as JSON historical evidence, never executed.
The wrapper requires no network, model, telemetry, or embedding service.

[Lifecycle evidence](holdout-lifecycle-results.json) covers staged install,
idempotence, disable, uninstall, restoration, and refusal of concurrent edits or
damaged snapshots. Independent review additionally checked missing parent/runtime
guards and cancellation through the actual launcher shape. The local switch and
launcher remain private installation aids, not a shipped general installer.

[Native checks and build receipts](checks.json) record the test suite, lint,
wheel/sdist build, installed CLI smoke, and unchanged canonical gate. Hermes Gate
fast/review returned `NOT_CONFIGURED`; this unadopted repository was not modified
to manufacture a Gate pass.

## Delivery disposition

Deliver the bounded source improvements and reproducible evaluation as an
experimental draft PR. Keep operational activation held for mining accuracy,
false positives, and repeated-command latency. The real workspace's prior
configuration is preserved; only private staging copies were enabled and then
restored. Any future attempt requires a new frozen evaluation rather than reuse
of these exposed cases as holdout evidence.
