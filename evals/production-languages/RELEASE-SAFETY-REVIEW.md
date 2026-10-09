# Independent pre-unseal release-safety source review

Reviewer: independent Codex decision/source-review session, 2026-10-09.
Scope: completed policy implementation, consumer tests, evaluation runner and
independent protocol. No authored development or sealed holdout corpus was read.
The corpus author was still working; corpus provenance, split/manifest binding,
quality results and final artifact receipts are explicitly pending.

## Verdict

**ACCEPT the repaired source for freezing and one sealed evaluation.** This is
not release acceptance, quality-target acceptance or verification in running
third-party hosts. Final receipt binding and installed/published artifact checks
must be reviewed after evaluation, without tuning against exposed holdout text.

The executable policy now preserves canonical raw-English findings independently
of mapping, keeps mapping-dependent evidence advisory, and applies each existing
consumer's threshold rather than a new common threshold. No runtime model call or
canonical regex change was introduced. The advisory deployment decision must
remain in force even if the authored point targets pass.

## Findings and demonstrated dispositions

| ID | Finding | Disposition |
| --- | --- | --- |
| S1 | Original correct-rule metric compared a public shape directly with internal rule IDs. | Repaired before unseal: `SHAPE_RULES` maps completion/relay public shapes to fixed ID sets and is included in the frozen binding. Inspected mappings against canonical findings. |
| S2 | Original source hash set omitted Gemini/Qwen and shipped plugin consumers. | Repaired before unseal: hashes cover package Python, runner, integration/plugin Python/MJS/JSON, hook JSON, package/extension manifests and installed smoke script. Direct inspection found no missing consumer among those checked. |
| S3 | Original exposure marker allowed another initial evaluation after a failed consumed attempt when no result receipt existed. | Repaired before unseal: existing exposure rejects incomplete attempts; replay requires a terminal receipt. An isolated dummy-path probe verified rejection before `load_cases`, without touching a real holdout. |
| S4 | Adding family counts made the metric-semantics test fail because its controls omitted family metadata. | Repaired by assigning distinct families to those test controls, preserving strict corpus validation. Focused suite then passed. |
| S5 | Mixed CLI output did not identify which findings were advisory. | Repaired: individual mapping-dependent hits carry `[language advisory]`; the advisory line carries selected code. Raw findings determine the existing medium/high exit threshold. English default output is preserved. |
| S6 | Qwen documentation said every next Stop consumes state despite the new advisory bypass. | Repaired: module contract, advisory guide and lifecycle/cleanup bullets now specify next applicable English/enforceable Stop or applicable run and explain the pending-marker association limit. |
| S7 | Agent guidance and installed smoke expectations did not prove the new exit/advisory contract. | Repaired: AGENTS distinguishes raw English medium/high exits from mapping advisories; smoke checks exit zero plus `ADVISORY` and selected code for mapping positives. Smoke execution on the final artifact remains pending. |
| S8 | Hermes Agent's mapped-only scorer could hide raw-English advisory evidence in mixed text. | Reproduced: the mapped-empty/raw-hit probe returned `None` from `check_outgoing_claims`. Repaired to use merged deployment findings with unchanged medium/high filter and advisory transform. Existing plugin tests and the new mixed/English regression passed. |

## Direct source and probe evidence

- `deployment_findings` always evaluates the raw canonical gate on original text;
  merging uses rule/span/severity identity and never changes severity or original
  coordinates. Unknown programmatic selectors still pass through to raw English.
  The public mapped `risk_score` remains unchanged for diagnostic quality scoring.
- The Korean-dominant partial-progress plus English completion probe documented
  in `DECISION-REVIEW.md` has no mapped hits but retains the raw high completion
  findings. CLI, Router and repairing hosts consume the raw enforcement list;
  Gemini/Qwen repair reasons summarize that list rather than mapped-only evidence.
- Mapping-only Router hits cannot call rubric, probe or repair. Raw hits retain
  the configured severity threshold. Gemini/Qwen retain their existing any-hit
  trigger contract, not the CLI medium/high threshold. Retry behavior and
  fail-open/security state controls remain covered by existing consumer tests.
- Clean Korean advisory output with absent state does not create a Qwen directory.
  With an English marker already present, clean and risky Korean advisory outputs
  preserve its bytes. The branch precedes resolving, sweeping, taking or writing
  state. Later applicable English output may consume that pending marker; lack of
  a host turn identifier leaves this documented association limit.
- Generated compatibility hooks now show medium/high diagnostics even when CLI
  returns zero. Existing Claude/Codex hooks recognize printed `RISK`, keep their
  advisory exit/envelopes, and receive merged CLI findings. Hermes Agent now also
  retains merged evidence without introducing blocking.
- Canonical `src/hermeneutic/gates/regex.py` is byte-identical to repository HEAD.
  Auto routing remains heuristic: Latin fallback, unsupported language, shared Han
  and mixed drafts are not proven language identity. Raw-English findings can
  still fire in an actually non-English draft; no broad message-language
  nonblocking guarantee is accepted.

Independent focused validation after the runner/consumer fixes:

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/test_language_deployment_policy.py tests/test_production_language_eval.py \
  tests/test_gemini_cli_extension.py tests/test_qwen_code_extension.py \
  tests/test_lang.py tests/test_router.py
115 passed in 2.19s
```

After the subsequent Hermes Agent repair, only its invalidated surface was checked:

```text
PYTHONPATH=src python3 -m pytest -q tests/test_hermes_agent_plugin.py \
  tests/test_language_deployment_policy.py::test_hermes_agent_preserves_raw_english_advisory_in_mapped_empty_draft
4 passed in 0.03s
```

These are local mechanics and metric-semantic checks. Full-suite, lint and wheel
checks reported by the lead are not counted as independent review execution here.

## Exact reviewed binding

The final installed-mechanics verifier was also inspected. It compares package
Python bytes with the supplied source, invokes CLI with isolated Python, probes
explicit/auto advisory and raw-English rejection, forbids a mapping-only Router
probe, checks Hermes Agent advisories and simulated Gemini/Qwen allow/block
decisions. Its output expressly excludes running-host delivery. It must be run
with the final installed artifact; source inspection is not execution evidence.

Runner `source_hashes()` contains 44 file hashes, including this verifier. Its
canonical compact sorted-JSON SHA-256 after the final source changes is:

```text
f6e335d9b6790ff9b20bf2772860b1906a8aa762ee7484d8fc907a55a2c25d8e
```

Compute as `sha256(json.dumps(source_hashes(), sort_keys=True,
separators=(',', ':')).encode())`. The freeze must preserve the complete dictionary,
not replace it with this review digest. Material file SHA-256 values:

| Path | SHA-256 |
| --- | --- |
| `src/hermeneutic/gates/regex.py` | `24a70e1239e36922f0fa5093dcd43b9a07f1bc18d23157b18e4aacea09072276` |
| `src/hermeneutic/lang/__init__.py` | `49ffc39341dd054cb29f15846609b85a44d66f12b3b7c534a53e9891ee7ec03e` |
| `src/hermeneutic/cli.py` | `508bdaff531e1917300ea26d9187920455e76a5070e8db96de3dac28ae685cba` |
| `src/hermeneutic/router.py` | `a1d7deff2cfd34f25c374ebaecc6f47a77b967220434cb9037b95d08ce482e75` |
| `src/hermeneutic/install_hook.py` | `025968130f951409623902bd377cc5513711912bd096a8af68ece41d4983b663` |
| `src/hermeneutic/hermes_agent_plugin.py` | `f28c735f99b143b6bd1cf1d13ae368bbb809d71e6cc071cb9a2060aadd56cd18` |
| `integrations/gemini-cli/hermeneutic_after_agent.py` | `05c09b677dad14e097ea9b04f7fba54fddc8597644df0c5de1c734d5990485a1` |
| `integrations/qwen-code/hermeneutic_stop.py` | `044ef466016469f3781f4d1a80390486316b1c8a1c5cecb4a7404c571b786cda` |
| `evals/production-languages/run.py` | `53392225b0d1b90a0fdd6c20a27464ddf36855cb55a67c2d55c50db27aae0bab` |
| `evals/production-languages/PROTOCOL.md` | `b669e979da1833f997275a28c2607b1ff0fdb0076ee3043eaa3d076c6ffbc498` |
| `tests/test_language_deployment_policy.py` | `60047e2f3ea1862c6f57365caef90e77e15f8ecf2e662e4b801005242918fb9b` |
| `tests/test_production_language_eval.py` | `4b79cb00057203d5944bf17f6356c2d7e1ac1e6ded4d4f9d10c6fcb5df013eed` |
| `scripts/smoke-installed-cli.sh` | `c808736fe88996021a8b135a23b53f464ac83a23c708061a58cdd1624f325a24` |
| `scripts/verify-installed-languages.py` | `634a6cb814a8975f3262e8a4c0a7b458aef249b6b04be3401c31b7f5797474e5` |

## Pending final evidence, before release acceptance

Verify the independent author manifest, corpus rights/provenance, scenario families,
language/label counts, actual split assignment and frozen development/holdout hashes.
Validate required public expected shapes and denominator completeness against the
authored corpus; loader schema checks alone do not adjudicate labels. Keep the
sealed text hidden until source, protocol and corpus bindings are frozen.

Inspect the consumed receipt and exact replay against this reviewed source set.
Report explicit and auto quality separately, actual severity, correct-rule hits,
denominators/case IDs, selected routing/ambiguity, intervals and failed targets.
The runner correctly scores mapped `risk_score`, not merged deployment evidence;
consumer enforcement is a separate receipt subject. A failed first exposure stays
consumed; do not retune this candidate against it.

Require final installed and published-artifact consumer readback, canonical
merge/tag/release verification, truthful publication text and explicit limits:
single synthetic author, no native-speaker adjudication, no production sampling,
thin dialect/shared-script coverage and omitted context-dependent/low-only cases.
Passing authored point targets must not be called production error bounds,
efficacy certification or validated blocking-language promotion.
