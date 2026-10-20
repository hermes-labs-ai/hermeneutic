# Changelog

All notable changes to Hermeneutic are documented here. The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.16a1] — Candidate, unreleased

### Experimental language fixes

- Integrate the advisory policy and independent simulated evaluation from #57.
  Mapped-only findings no longer trigger CLI rejection, Router review/repair
  or Gemini/Qwen retry; raw canonical English enforcement is retained.
  None of the four independently evaluated adapters met both quality targets.

- Route sparse Korean technical assertions with mapped completion/universal
  vocabulary through the Korean adapter even when Latin identifiers dominate.
  Counters alone do not select Korean.
- Map the Korean contrast ending `-했는데` and next-step marker `다음은` into
  the canonical gate's existing partial-progress guard. English rules are unchanged.
- Replay the frozen synthetic language corpora and negative controls: Korean
  auto catch changes from 111/180 to 116/180; explicit catch stays 116/180;
  clean false fires change from 4/135 to 2/135. The other seven language results
  and the separate negative/affirmative relay controls are unchanged.
- This is an opt-in alpha prerelease. Korean still misses 64/180 authored drift
  drafts and flags two clean drafts. The other authored sets catch 14–16/20
  drift drafts each. No fresh held-out, native-speaker or real-use coverage is established.
- Keep the original #57 candidate and consumed evaluation immutable. A separate
  current-source regression receipt reports severity-specific TP/FN and any-hit
  FP/TN on the exposed cases, with uncertain adjudication explicitly unmeasured.
  This replay does not qualify a language for enforcement or establish a new holdout.

## [0.1.15] — 2026-10-20

### Changed

- Lead onboarding with installed offline correction recall; correct stale claims
  about Ollama requirements and shipped language adapters. Clarify the audience,
  native alternatives and evidence boundary.
- Add a public synthetic retrieval set with frozen labels, published misses and
  optional local embedding comparisons. Keep the retrieval algorithm unchanged.
- Validate evaluation labels, query IDs and corpus row references before scoring;
  run the offline public retrieval regression floor in pytest.

## [0.1.14] — 2026-10-20

### Added

- Add `recall` for bounded original correction evidence with offline keyword
  search by default, optional local semantic/hybrid modes, and private-corpus
  development evaluation receipts.
- Add a packaged synthetic correction-memory demo and reproducible presenter guide;
  local Ollama is required only for embedding retrieval.
- Add `inspect` for read-only, bounded correction previews with provenance and
  complete JSONL validation before indexing. No network or model is required.

## [0.1.13] — 2026-10-09

### Added

- Add experimental Korean, Chinese, Japanese, Turkish, German, French, Spanish,
  and Portuguese trigger adapters around the unchanged English gate. CLI
  `--lang auto` or an explicit code and `Router(lang=...)` opt in; response hooks
  normalize automatically. Gate hits retain original-draft spans. Synthetic
  fixtures, per-language results, and replay methodology live in `evals/languages/`.
- Add an OpenClaw native `reply_payload_sending` plugin that checks visible
  reply text with the local deterministic gate and appends an advisory on
  medium/high findings. It strips telemetry settings from the child process,
  discards stderr, bounds runtime and input size, and fails open on errors.
  Adapter mechanics and isolated OpenClaw v2026.9.5 hook registration are
  tested; Gateway/channel reply delivery is not claimed.
- Add a native Qwen Code extension. A root `qwen-extension.json` points at a
  Qwen-only `Stop` hook config, because Qwen's Gemini converter copies
  `hooks/hooks.json` without translating event names and therefore drops
  `AfterAgent`. The gate requests one evidence-focused revision on the first
  risky response and then allows with a visible warning.

Qwen Code 0.23.2 sends `stop_hook_active: true` on the first `Stop` of a turn,
so the adapter ignores that flag and bounds itself with a per-session marker
file that carries no response text. The next Stop for that session consumes the marker; concurrent first calls
that already observed no marker share the atomic claim and both block; old markers for other sessions are pruned after 30 minutes.
The marker lives in a private directory owned by the current user. It is created
exclusively with mode `0600` and never written through a symlink.
When the adapter cannot key or write its marker it warns instead of blocking,
because an unbounded blocking hook loops. Both response adapters now share one decision-text module,
so no adapter restates a gate rule. Clean, risky-repair, and still-risky bounded
turns were exercised through Qwen Code 0.23.2; the exact boundary is recorded in
`evals/qwen-code/RESULTS.md`.

### Fixed

- Guard negative relay, certainty, completion/pass, request and inability
  vocabulary before affirmative substitutions. Chinese/Japanese completion
  assertion forms and their limits are documented with review regressions.
- Keep source coordinates in compressed segments, without rebuilding untouched
  mappings. Preserve full-draft scans and original-text snippets.
- Atomically publish eval receipts; interrupted writes preserve the prior JSON.
- Require multilingual host tests to observe the actual evidence advisory.

## [0.1.12] — 2026-09-02

### Added

- Add a native Gemini CLI `AfterAgent` extension that runs the deterministic
  drift gate on the proposed response and requests one bounded automatic retry
  when medium- or high-risk patterns are present.

The extension is fail-open on malformed hook input or internal errors and does
not claim that a clean result proves correctness. Its source-distribution and
copied-install contracts are exercised in CI.

## [0.1.11] — 2026-09-02

### Added

- Add an opt-in Hermes Agent pip plugin that runs the deterministic gate on
  Hermes Agent's native final-output transform hook before delivery.

Clean and low-severity responses remain unchanged. Medium/high findings append
a bounded evidence advisory; the plugin does not call a model, read personal
correction logs, block output, or claim that a pass proves correctness.

## [0.1.10] — 2026-09-02

### Added

- Cite the exact correction-corpus rows supporting each compiled advice bullet.
- Add a deterministic `hermeneutic --version` command.

### Fixed

- Refuse to compile against an index whose recorded corpus hash no longer
  matches the current corpus, preventing stale positional references from
  citing the wrong correction rows.

### Changed

- Harden release and CI workflows and publish the canonical product links.

## [0.1.9] — 2026-08-17

### Changed

- Advance release metadata for the Apache-2.0 successor release.

No gate rule, mining, retrieval, Router, CLI, or integration behavior changed.

## [0.1.8] — 2026-08-04

### Changed

- Exercise the installed wheel and exact source distribution in CI and the
  release workflow before publication.
- Update GitHub Actions maintenance versions and add the package Documentation
  link.
- Pin release actions immutably and reject release tags that do not match the
  package version.

No gate rule, mining, retrieval, Router, CLI, or integration behavior changed.

## [0.1.7] — 2026-07-15

### Publication truth corrections

- Reframed the product around its actual distinct surfaces: personal correction mining, optional personal retrieval, a fixed deterministic English gate, and a separately configured Python Router.
- Replaced the Claude compile hook's user-visible `systemMessage` with the documented `UserPromptSubmit` `hookSpecificOutput.additionalContext` contract. The installer now registers an exec-form command bound to the running Python interpreter, handles paths with spaces, migrates or cleans its exact legacy registration, preserves unrelated hooks, and avoids destructive malformed-settings behavior.
- Added exact compile-hook contract coverage for success JSON, empty/missing results, unavailable Ollama, malformed input/state, compiler failures, timeouts, idempotency, foreign-file protection, legacy cleanup, coexistence, and uninstall.
- Replaced the leave-one-out evaluator's duplicated selection approximation with calls through the shipped `compile_prompt()` production path. Current same-bucket results on the frozen 346-triple corpus are 88/104 (84.6%) at CLI/hook defaults and 94/104 (90.4%) at Python defaults.
- Added a privacy-safe current gate-coverage receipt: 115/346 (33.24%) prior assistant replies in the frozen correction corpus fire at least one current rule. This is retrospective derivation-set coverage, not held-out accuracy.
- Moved the prior 83.7% leave-one-out and 98/100 discrimination figures into historical-only framing because their evaluators did not match the shipped selection path.
- Classified every integration by evidence maturity. The Claude compile hook, Codex plugin mechanics, and forward-deployed tooling are mechanically tested; Cursor/OpenHands are design sketches; current Claude Stop, Cline, and Windsurf adapters are removed from the ready-support matrix.
- Synchronized README, package description, machine-readable summary, examples, theory/intent docs, citation metadata, Zenodo metadata, plugin descriptions, installation commands, optional dependencies, privacy boundaries, and author display.

### Added and hardened

- Eight fixed English stage-one rules with a partial-progress contrast guard.
- Correction mining for Claude Code, Codex rollout, and OpenAI-style message logs; loud zero-parse diagnostics; multi-directory input; nested output-directory creation.
- Optional local-Ollama compile index and deterministic bucket-aware warning preambles.
- Local opt-in telemetry, reviewable audit modes, `stats`, harvest classification, human review, and accepted-record promotion.
- Wheel-built Claude compile-hook installer plus repository/sdist standalone plugin assets and integration documentation.
- Forward-deployed environment/boot/harvest/report/gate tooling, report leak checks, tamper-evident mission state, and optional Codex notification sentinel.
- Trusted-publishing GitHub Actions workflow, wheel/sdist checks, exact-sdist tests, typed-package smoke, release metadata, and software citation files.

### Boundaries

- Core library and CLI have zero required Python runtime dependencies.
- Stage-one checks are fixed English surface patterns. Mining and promotion do not generate regex rules.
- Live Ollama, live response-hook hosts, external Router backends, Windows, false-positive rate on ordinary prompts, and downstream model effectiveness are not certified by this release.
- The wheel contains the core, CLI, type marker, and built-in hook installers. Evaluations, standalone plugins, integration docs, and forward-deployed tooling require the repository or extracted sdist.

## [0.1.6] — 2026-07-08

### Added

- Opt-in local JSONL gate/compile telemetry with context labels and best-effort failure isolation.
- Audit modes `none`, `hash`, and `raw`, plus draft fingerprints and matched-context windows.
- `stats`, `harvest`, `harvest --sanitized`, and `promote` review-loop commands.
- Codex rollout reader and forward-deployed validation tooling.
- Two additional fixed English rule shapes and a contrastive partial-progress guard, bringing the rule count to eight.

### Changed

- Declared the fixed gate's English-only boundary.
- Improved loud failure for missing inputs, unsupported log shapes, corrupt harness state, and invalid explicit session paths.

## [0.1.5+bucket-aware] — 2026-04-27

Local-only retrieval iteration on the v0.1.5 compiler. It introduced per-bucket selection and recorded the historical 83.7% leave-one-out and 98/100 versus 7/30 discrimination experiments. Those values remain provenance receipts, not current production-path claims; the original embedding artifact was not fully pinned and the evaluators later proved behaviorally different from `compile_prompt()`.

## [0.1.5] — 2026-04-26

### Added

- `orig_prompt` in correction triples with backward-compatible loading.
- Local Ollama `nomic-embed-text` index stored under `~/.hermeneutic/`.
- `compile-index`, `compile`, deterministic preamble synthesis, and an initial Claude prompt hook.

## [0.1.1] — 2026-04-26

### Added

- Additional log-reader resilience, CLI error reporting, and packaging metadata.

## [0.1.0] — 2026-04-25

### Added

- Correction-triple mining and bucketing.
- Fixed regex gate and programmable three-stage Router.
- Python library and `hermeneutic` CLI under the MIT License.
