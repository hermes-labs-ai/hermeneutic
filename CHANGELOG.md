# Changelog

All notable changes to hermeneutic are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.7] — 2026-07-14

### Fixed
- `mine` accepts multiple log directories, so the documented
  `hermeneutic mine ~/.claude/projects/*/` glob form works instead of dying
  on the second expanded path; a nonexistent directory argument fails loud
  (exit 2) instead of being silently skipped.
- `--out` targets for `mine`, `harvest`, and `promote` create missing parent
  directories, so the forward-deployed harness's printed
  `--out build/report.jsonl` command works in a fresh clone.
- `forward-deployed/harness.py verify` fails loudly on missing, corrupt, or
  empty mission state instead of passing vacuously with "0 step(s)", and
  recomputes recorded artifact digests so changed or deleted evidence cannot
  retain a passing attestation.
- Codex plugin manifest matches the schema the Codex plugin validator
  accepts (no top-level `hooks` field; complete `interface` object) — the
  plugin previously failed validation at install time.
- 21 new tests; **131 tests** total.
- `gate` input failures are loud and clean: a missing `--draft` file or
  non-UTF-8 input prints a one-line ERROR and exits 2 instead of dumping a
  traceback. Log readers tolerate stray non-UTF-8 bytes (replacement
  decoding). 2 new tests; **110 tests** total.
- Install instructions use the current source checkout until PyPI publication
  is verified; rule-count references reconciled (8 shipped rules).
- Internal development notes removed from the tree.

### Added
- **Integrations for the 2026 agent-harness landscape** (`integrations/`):
  first-class Claude Code plugin (`claude-plugin/`, `claude plugin validate
  --strict` clean, installable via `/plugin marketplace add
  hermes-labs-ai/hermeneutic`) and Codex CLI Stop-hook plugin
  (`codex-plugin/`, structured-JSON advisory output, honors Codex's
  no-decision-field advisory semantics), plus verified recipes for Cursor
  (also loads Claude Code hooks directly), Windsurf/Cascade, Cline, and an
  honestly-scoped OpenHands preamble (no response-bearing hook exists
  there). Unverifiable schema fields are flagged inline rather than
  invented. **4 new tests** on the plugin gate scripts.
- **PyPI distribution**: a trusted-publishing release workflow
  (`.github/workflows/release.yml`, OIDC, no stored PyPI token) builds the
  wheel and source distribution, checks their metadata, smoke-tests the
  wheel, and runs the suite from the exact sdist before publishing.
- **Demo GIF** (`docs/demo.gif`, re-recordable via `demo.tape`), CI badge,
  dependabot config, and a root `CLAUDE.md` companion to `AGENTS.md`.
- **Forward-deployed harness** (`FORWARD-DEPLOYED-HARNESS.md` +
  `forward-deployed/`): an executable deployment mission for the agent
  inside an adopter's environment the author never sees. A deterministic
  step-machine (`harness.py`) drives ENV → BOOT → HARVEST → REPORT → GATE,
  verifying each step from artifacts on disk before the next unlocks;
  progress is a tamper-evident hash chain. Ships a boot verifier
  (`boot.py`: import, suite, self-test, gate smoke trio, sanitized harvest
  probe), a report leak-linter (`check_report.py`: flags out-of-repo paths,
  emails, long quotes before a report leaves the machine), the mission's own
  drift gate (`gate.py`: the deployment cannot be declared done — it must
  prove it), and an optional consented runtime sentinel (`sentinel.py`,
  Codex notify hook: reversible, advisory, rule-ids-only). Local tests verify
  the harness mechanics; each adopter's report is the evidence for that
  environment. **10 new tests.**
- **Codex CLI log reader** (`--format codex`): parses OpenAI Codex session
  rollouts (`~/.codex/sessions/**/rollout-*.jsonl` — `response_item` message
  payloads with `input_text`/`output_text` blocks), skipping injected
  environment/permissions wrappers. Schema verified against live Codex
  sessions, and `mine`/`harvest` run end-to-end on real Codex logs.
- **`harvest --sanitized`**: emits the review queue with ALL text stripped —
  kinds, rule ids, severities, timestamps, content fingerprints and text
  lengths only, session names hashed. This is data minimization, not
  anonymization; review the remaining metadata before sharing it.
  **3 new tests**.
- **Loud-fail zero-parse** in `mine` and `harvest`: pointing the miner at an
  unsupported log format used to produce silent zero output,
  indistinguishable from "no corrections found". Now it probes the reader,
  distinguishes "could not parse any turns" (exit 2, with an issue-filing
  pointer) from "parsed fine, genuinely nothing found" (exit 0), and says
  which it was. **3 new tests.**
- **Two new gate shapes + a false-fire guard**, all discovered by testing the
  gate against non-English input and finding the failures were
  language-neutral: `number_then_completion` (order-insensitive completion
  claims — "14 files shipped"; verb-final languages hit this constantly,
  English drifts this way too), `authority_passthrough` (human-team sign-off
  relayed as verified — "the QA team approved it"; med severity), and a
  **contrastive-partial guard** that suppresses completion fires on honest
  partial-progress reports ("finished 3, but 5 remain" — every false fire in
  the 2026-07-08 eval was this one shape). 8 rules total. **5 new
  tests**; total **91 tests**.
- **Reject-mining harvester — `hermeneutic harvest` + `hermeneutic promote`**
  (`src/hermeneutic/harvest.py`). Replays the (pure) regex gate over any
  session-log directory and classifies every assistant turn by the user's
  *actual next reaction*: gate fired + user corrected → `confirmed_catch`
  (corpus-ready, the gate proved itself); gate fired + no correction →
  `possible_false_positive` (the reviewable over-steer set); gate silent +
  user corrected → `missed_drift` (the false-negative set new rules come
  from). Output is a labeled JSONL review queue — flip `status` to
  accepted/rejected in batch instead of re-reading chats, then
  `hermeneutic promote` appends accepted correction-bearing records to the
  triples corpus. Duplicate turns dedup by content fingerprint; when a
  telemetry sink is supplied (`--telemetry` / `$HERMENEUTIC_TELEMETRY`),
  replayed records matching a live fire's `draft_sha256` are marked
  `live_fire`. Zero LLM calls end to end.
- **12 new tests** (`tests/test_harvest.py`): all three classifications,
  clean-exchange and trailing-turn skips, cross-session dedup, live-fire
  cross-referencing, promote filtering (accepted-only, correction-bearing
  kinds only), and CLI queue/promote round-trips. Total **86 tests**.
- **Audit log — reviewable before/after context on gate fires**
  (`HERMENEUTIC_TELEMETRY_CONTEXT`). Verdict + rule_ids alone make a false
  positive unreviewable; with this set, each gate record carries an `audit`
  list — per hit, the matched text plus a 120-char window of surrounding
  draft text. Modes: unset/`none` (no draft content logged — prior behavior),
  `hash` (SHA-256 of each window + lengths — proves *what* fired on *which*
  content without storing text), `raw` (the text windows themselves, for
  local review and demos). Whenever the draft is available, records carry a
  `draft_sha256`/`draft_len` fingerprint in every mode; compile records gain
  a prompt fingerprint (+ excerpt in `raw` mode). Local-only, opt-in, never
  raises into the gate path.
- **`hermeneutic stats`** — zero-LLM summary of the telemetry sink: gate
  fires with PASS/RISK split + risk rate, severity distribution, per-rule
  fire counts, human-vs-agent context segmentation, audit coverage, compile
  injection rate + bucket distribution. `--json` for machine-readable output;
  malformed lines are skipped and counted, never fatal.
- `RiskHit` records the match span (`start`/`end`) in the scanned draft
  (backwards-compatible: hand-constructed hits default to −1 and the audit
  layer falls back to locating `matched_text`).
- **9 new tests**: audit modes (none/hash/raw), the no-text guarantee in
  `hash` mode, span fallback, compile fingerprinting, and `stats` end-to-end
  through real gate fires. Total **74 tests**.
- **Opt-in fire telemetry** (`src/hermeneutic/telemetry.py`). A structured
  JSONL sink for the gate and compile paths, enabled only when the
  `HERMENEUTIC_TELEMETRY` env var names a writable path. Off by default →
  public behavior is byte-identical unless explicitly turned on. Records the
  gate verdict (PASS/RISK), severity, and matched `rule_ids`; the compile
  `injected` flag, matched `buckets`, and match count. Each record is tagged
  with a human-vs-agent **context** label (derived from `CLAUDE_CODE_CHILD_SESSION`
  / `AI_AGENT` / `CLAUDECODE`) plus the raw markers, so over-steering /
  false-positive rate can finally be measured and segmented by session type.
  This is the prerequisite the advisory gate lacked: its RISK verdict went to
  stderr and it always exits 0, so the chain-of-custody receipt layer (which
  hashes stdout) could not distinguish RISK from PASS.
- **10 new tests** (`tests/test_telemetry.py`): off-by-default no-op,
  never-raises-on-bad-path, gate/compile record shape, append semantics, and
  human-vs-agent context detection. Total **65 tests**.

## [0.1.6] — 2026-07-08

### Added
- **Opt-in fire telemetry** (`src/hermeneutic/telemetry.py`). A structured
  JSONL sink for the gate and compile paths, enabled only when the
  `HERMENEUTIC_TELEMETRY` env var names a writable path. Off by default →
  public behavior is byte-identical unless explicitly turned on. Records the
  gate verdict (PASS/RISK), severity, and matched `rule_ids`; the compile
  `injected` flag, matched `buckets`, and match count. Each record is tagged
  with a human-vs-agent **context** label (derived from `CLAUDE_CODE_CHILD_SESSION`
  / `AI_AGENT` / `CLAUDECODE`) plus the raw markers, so over-steering /
  false-positive rate can finally be measured and segmented by session type.
  This is the prerequisite the advisory gate lacked: its RISK verdict went to
  stderr and it always exits 0, so the chain-of-custody receipt layer (which
  hashes stdout) could not distinguish RISK from PASS.
- **10 new tests** (`tests/test_telemetry.py`): off-by-default no-op,
  never-raises-on-bad-path, gate/compile record shape, append semantics, and
  human-vs-agent context detection. Total **65 tests**.
- Citation/DOI metadata: ORCID and abstract in `CITATION.cff`, plus a
  `.zenodo.json` deposit manifest.

### Changed
- README declares the **English-only stage-1 limitation** explicitly
  (confirmed by direct test: an identical overclaim in Korean passes while
  English flags RISK-high). Honest limitation over silent hole; multilingual
  enforcement is tracked R&D.
- Docs corrected: rule count 5 → 6; import hygiene in evals scripts; fixed an
  undefined `N_PER_GROUP` in the bucket-discrimination runner.

## [0.1.5+bucket-aware] — 2026-04-27 (local-only iteration; not pushed publicly)

> The work below was local iteration on the v0.1.5 substrate while the public
> release stayed at v0.1.0; effectiveness validation is the v1.0 milestone
> before any PyPI bump above 0.1.x.

### Changed — bucket-aware retrieval (the `compile_prompt` upgrade)

After the earlier v0.1.5 leave-one-out eval surfaced 0% recall on the four rare buckets (`wrong_target`, `over_completion`, `scope_creep`, `tool_choice`), we diagnosed the failure (rare-bucket matches existed at cosine 0.46–0.62, above threshold, but at median rank 62 — crowded out by majority-bucket triples in global top-K) and shipped the fix in this iteration.

- **`compile_prompt` now uses bucket-aware retrieval**: top-N per bucket above threshold (defaults: `n_per_bucket=2`, `threshold=0.5`, hard cap `k=10`).
- **Measured lift on leave-one-out (n=104):** overall recall 56.7% → **83.7%** (+27pp). Rare-bucket recall 0% → **avg ~50%** (per-bucket: over_completion 75%, wrong_target 50%, scope_creep 33%, tool_choice 33%).
- **Measured input-discrimination (B):** in-corpus prompts trigger compile 98/100; synthetic-random word-soup triggers 7/30. Fisher's exact p = 2.6 × 10⁻¹⁷ (was 1.2 × 10⁻⁶ at the v0.4 threshold).
- **Measured trade-off:** preamble width grows from ~1.4 buckets per query to ~4.2. Documented as the honest cost.
- **Diagnosis runner:** [`evals/leave-one-out/diagnose_minority.py`](evals/leave-one-out/diagnose_minority.py) — for each rare-bucket triple, reports the rank at which the first same-bucket match appears in the global cosine ranking. Median = 62. This is the receipt for *why* the tweak was needed.
- **Tweak sweep:** [`evals/leave-one-out/test_bucket_aware.py`](evals/leave-one-out/test_bucket_aware.py) — measures recall + width across 7 (n_per_bucket × threshold) variants. Establishes the n=2 @ 0.5 sweet spot vs n=1 @ 0.5 (degenerates to global prior) vs higher thresholds (recall collapses).
- **Latency preflight:** p50 = 51 ms cached / 123 ms with live Ollama embed. Well under any interactive-hook budget.
- **C-prelim qualitative replay (N=5):** 0 counter-aligned, 2 aligned (case 5 strong), 3 neutral / mild-aligned.
- **Honest scope:** measures the retrieval system, not the effectiveness on LLM behavior. Effectiveness validation is the v1.0 milestone (N≥30 replay study with pre-registered ≥20% relative correction-rate reduction floor).

### Cross-session congruence note (2026-04-27 reconciliation)

The eval material above was originally drafted under a "v0.9" working label mid-iteration and later reconciled to the public versioning (v0.1.0 public, v0.1.5 local). Some eval artifacts kept the v0.9 label as historical receipts.

## [0.1.5] — 2026-04-26 (initial Layer 2 build, foundation for the 04-27 bucket-aware iteration above)

### Added — Layer 2: input compiler

The architectural completion. v0.1.x covered Layer 1 (gate the output); v0.1.5 adds Layer 2 (compile the input before the LLM generates), closing the original misinterpretation framing.

- **`Triple.orig_prompt`** field — the user turn that produced the drift. Backwards-compatible: v0.1.x triples without this field load fine, are skipped from compile-index with a clear warning.
- **`hermeneutic compile-index`** subcommand — embeds all eligible triples via local Ollama (`nomic-embed-text`). Stores at `~/.hermeneutic/embeddings.json`. Idempotent: re-runs are no-ops if the source `triples.jsonl` hasn't changed (sha256 cache key).
- **`hermeneutic compile <prompt>`** subcommand — embeds the prompt, retrieves top-K nearest historical corrections (cosine similarity), groups by bucket, emits a deterministic template-based preamble. Returns empty string if no matches clear the threshold (silent skip — no false-positive injection).
- **`hermeneutic install-compile-hook`** + **`uninstall-compile-hook`** subcommands — wires the compile layer as a Claude Code `UserPromptSubmit` hook with the same idempotency + foreign-wrapper protection patterns as v0.1.1's `install-hook`. Hook runs `compile`, injects the preamble via the `systemMessage` channel.
- **`evals/compile-walkthrough.md`** — two demonstrative cases showing compile output on real (sanitized) misinterpretation moments from the author's mining corpus, with explicit "would the preamble have helped" framing.
- **14 new tests** covering: triple backcompat, index build/cache/legacy-handling, retrieval threshold filter, preamble determinism, bucket routing, end-to-end mine→index→compile, install-compile-hook idempotency + others-preservation.
- **3 doc-consistency tests** (`tests/test_docs_consistency.py`) — pytest assertions that fail CI if README opener / CHANGELOG entry / pytest collection count drift apart. Ported from sister-repo gate.
- Total **55 tests**.
- README "Compile your prompts ahead of the LLM" section + two-loops diagram.
- Planned with a pre-committed rubric and blind grading (plan document kept out of the distribution).

### Notes

- **Effectiveness validation is deferred to v1.0.** v0.1.5 ships demonstrative evidence (compile retrieves relevant past signal) but not measured effectiveness (does compile actually reduce misinterpretation rate?). The v1.0 replay study is the validation milestone.
- **Embeddings are derived from private session content** and stay local at `~/.hermeneutic/`. Nothing public ships with embeddings — every user mines their own.
- **Cold-start latency:** measured on the author's corpus (346 triples, MacBook M1, Ollama + nomic-embed-text) — **18.8 seconds total = ~54 ms per Ollama embed call**. One-time per re-mine; subsequent `compile-index` calls are no-ops while the source `triples.jsonl` is unchanged (sha256 cache key).
- **Live end-to-end smoke test:** mine 1,423 sessions → 346 triples → index → `compile` on 3 real prompts → 3 distinct bucket distributions returned with non-trivial top-K matches. See `evals/compile-walkthrough.md` for the unedited compile output on each prompt.
- **Stop-hook wrapper smoke test:** wrapper executed end-to-end against a real Claude Code transcript JSONL via `{"transcript_path": "...", "session_id": "..."}` stdin input — correctly extracted the last assistant turn, piped through `hermeneutic gate`, returned exit 0 (advisory mode).

## [0.1.1] — 2026-04-26

### Added
- `hermeneutic install-hook` subcommand — installs a Claude Code Stop hook (advisory mode) that gates every assistant turn through the regex risk gate. Real-time drift notifications surface in the Claude Code UI.
- `hermeneutic uninstall-hook` subcommand — clean removal that preserves the user's other Stop hook entries and refuses to delete wrapper files it didn't create.
- Python wrapper script at `~/.claude/hooks/hermeneutic-gate.py` (auto-generated, marker-tagged for safe identification).
- 12 new tests covering install/uninstall idempotency, foreign-wrapper protection, malformed-settings handling, missing-claude-dir failure mode, and wrapper edge cases (missing transcript, malformed JSONL).
- "Real-time gating in Claude Code" section in README.

### Changed
- Total test count: 26 → 38, all passing.

### Notes
- Hook stdin pattern verified against real Claude Code Stop and PostToolUse hook implementations — receives `{"transcript_path", "session_id"}` JSON on stdin, not env vars.
- Idempotency fingerprint is the substring `hermeneutic-gate.py` in any Stop hook entry's `command` field; running `install-hook` twice never duplicates the entry.

## [0.1.0] — 2026-04-25

### Added
- Triples miner (`hermeneutic.triples`) supporting Claude Code JSONL and OpenAI ChatCompletion formats.
- Stage 1 regex risk gate (`hermeneutic.gates.regex`) with 6 patterns derived from a 326-triple study.
- Stage 2 hermes-rubric adapter (`hermeneutic.gates.rubric`) — optional, used if `hermes-rubric` is on PATH.
- Stage 3 PressureProbe (`hermeneutic.gates.twin`) — generic LLM critic with bring-your-own calibration. Default: rigorous-skeptic.
- 3-stage Router (`hermeneutic.router`) with one-shot repair pass.
- CLI: `hermeneutic mine|bucket|gate`.
- 26 tests covering miner, regex gate, router, CLI.

### Notes
- Risk patterns are evidence-based: derived from 326 real user corrections across 1,423 sessions.
- The gate is correct only on drift modes already seen corrected. Re-mine periodically.
