# Changelog

All notable changes to Hermeneutic are documented here. The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
