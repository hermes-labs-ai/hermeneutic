# Independent synthetic holdout, candidate v1

**Decision: fails the preregistered accuracy acceptance. Do not activate this candidate on the operational root under that acceptance.**

The fixtures and labels were authored before candidate inspection. Their SHA256 is `733c0656cc6fa2ffb9c50854d26ee88cfebcb12815110aee7b71552ce38f8069`; the freeze metadata is in `holdout-preregistration.json`. The candidate is commit `eecc2adc05848524e4f4203c6cfe1d267e61d59f`; installed wheel and wrapper hashes are in `holdout-candidate-freeze.json`. The source was not inspected by the evaluator. The documented APIs and pinned installed wrapper were invoked against synthetic data only.

| Criterion | Frozen candidate observation | Acceptance | Result |
|---|---:|---:|---|
| Mining correction recovery | 3/24 (12.5%) | >=80% | FAIL |
| Mining noncorrection false positives | 1/24 (4.17%) | <=5% | PASS |
| Strict recall target hit in top 3, API and wrapper | 21/24 (87.5%) | >=85% | PASS |
| Strict irrelevant recall, API and wrapper | 8/24 (33.33%) | <=5% | FAIL |
| Warm in-process keyword API p95/p99, 200 calls | 0.1741/0.1802 ms | <=30/50 ms | PASS |
| Cold full wrapper-command p95/p99, 50 processes | 119.4699/124.1893 ms | <=150/250 ms | PASS |

The warm timing calls `recall()` in the evaluator process after package import and corpus construction. It excludes interpreter startup and the parent/worker wrapper. The cold timing launches the full pinned wrapper command, including its worker process. No persistent host process was measured, so the warm API distribution is not an end-to-end Codex command latency claim.

`holdout-results.json` preserves the candidate measurements with the local interpreter path redacted. The exact unredacted result and pre-redaction scripts remain privately retained; the redaction does not alter metrics or labels. `holdout-baseline-results.json` records the same fixtures against the isolated origin/main `4f357b7` export: mining recovery 3/24, mining false positives 1/24, default keyword target hit 23/24, irrelevant recall 13/24. Candidate strict matching reduced irrelevant matches while losing some relevant matches; it did not meet the fixed irrelevant-recall threshold.

Observed failure categories: correction wording outside the miner's recognized shapes was missed, including declarative clarification of meaning and scope. The noncorrection false positive was ordinary weather text beginning with "No". The irrelevant recall failures were six quoted-only requests and two unrelated meanings of shared vocabulary. These observations describe the fixed fixture behavior; they do not establish a general cause in the implementation.

Output-control observations in `holdout-results.json`: maximum observed stdout was 1052 UTF-8 bytes; no session/timestamp keys, private temporary paths, synthetic canary, or created shell canary was observed; the historical-data notice and match limit were present. Missing, empty, malformed, oversized, or directory corpus; absent, failed, slow, and noisy interpreter; and oversized prompt returned empty evidence with status 0 within the 500 ms bound in the tested runs. The slow interpreter probe took 394.2069 ms. Those checks demonstrate the tested formatting/failure behavior, not universal privacy or host continuation guarantees. Irrelevant correction snippets were still returned in the accuracy failures above.

`holdout-lifecycle-results.json` records local-helper mechanics checked through staged-only install/disable/enable/uninstall calls. The external switch helper is not shipped with this evaluator; its exact SHA256 is recorded in that result. Checks cover exact synthetic configuration restoration, mode preservation, idempotence, unrelated-state preservation, and refusal of concurrent edits, wrong targets, invalid replacement counts, or damaged snapshots. Real operational AGENTS configuration was not read or changed by this evaluator.

To rerun the frozen package evaluation, use its installed interpreter to invoke `holdout-evaluate.py --fixtures holdout-fixtures.json --wrapper PINNED_WRAPPER --python INSTALLED_INTERPRETER --output NEW_RESULT.json`. To rerun staged lifecycle checks, supply the compatible local helper and its expected scoped command: `holdout-lifecycle.py --manager LOCAL_MANAGER --existing-command EXISTING_SCOPED_COMMAND --output NEW_LIFECYCLE_RESULT.json`. The command value appears only in synthetic temporary input and is omitted from results.

This result uses synthetic English cases. It does not establish real private-log recovery, additional-language coverage, or native Codex invocation/delivery. The fixture wording was disclosed after this evaluation; these fixtures are now exposed development evidence and must not be called an unexposed holdout for later candidates. The original labels and failed v1 result remain unchanged.
