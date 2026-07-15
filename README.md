# hermeneutic

**Hermeneutic is a local-first Python toolkit that mines reusable correction evidence from AI chat logs, retrieves relevant past corrections when asked, and runs a fixed deterministic English drift check on outgoing drafts.**

[![Python ≥3.10](https://img.shields.io/badge/python-%E2%89%A53.10-3776AB)](https://www.python.org/) [![MIT](https://img.shields.io/badge/license-MIT-2ea44f)](LICENSE) [![Typed](https://img.shields.io/badge/typing-PEP%20561-blue)](src/hermeneutic/py.typed) [![Status: beta](https://img.shields.io/badge/status-beta-orange)](CHANGELOG.md)

AI systems can repeat mistakes that a user has already corrected. Hermeneutic gives engineers working with coding agents and chat systems a local evidence trail and a cheap review floor: mine correction triples, optionally retrieve similar warnings for a new prompt, and check a draft for eight recurring English surface patterns.

Mining personalizes the correction corpus and optional retrieval. It does **not** rewrite the default gate: the gate stays a fixed, reviewable rule set until a developer deliberately changes the code. Optional Python APIs can add deeper external checks. Hermeneutic can raise a reliability floor; it cannot make an AI generally reliable or prove that an answer is correct.

## One deterministic check

```bash
printf '%s\n' 'Done — shipped 14 files, all tests pass.' | hermeneutic gate
```

```text
RISK — highest severity: high
  [high] completion_with_number: 'Done — shipped 14'
    why: Completion verb co-occurs with a numeric claim — verify the number is tool-derived.
  [high] completion_with_all_quantifier: 'Done — shipped 14 files, all'
    why: Completion claim with universal quantifier — confirm scope coverage.
```

That path uses no private logs, model, network service, or host integration.

## Install v0.1.7

Hermeneutic requires Python 3.10 or newer. CI is configured for Python 3.10–3.13; package metadata intentionally permits newer Python versions rather than imposing an untested upper bound. The core package has **zero required Python runtime dependencies**.

Publication status: neither the PyPI 0.1.7 package nor the public `v0.1.7` tag exists during owner review. After the owner publishes them, these are the exact publication-state commands.

Install the exact package release from PyPI:

```bash
python3 -m pip install 'hermeneutic==0.1.7'
```

Get the repository-only assets—evaluations, standalone plugins, integration documents, and forward-deployed tooling—from the exact public tag:

```bash
git clone --branch v0.1.7 --depth 1 https://github.com/hermes-labs-ai/hermeneutic.git
cd hermeneutic
python3 -m pip install .
```

During pre-publication review, install the rebuilt exact local wheel instead:

```bash
python3 -m pip install ./dist/hermeneutic-0.1.7-py3-none-any.whl
```

The local-wheel command assumes the release working tree containing the rebuilt `dist/` artifacts. `dist/` is intentionally not committed.

### What each installation contains

| Form | Contains | Additional requirement |
|---|---|---|
| Wheel / normal `pip` install | Core library, `hermeneutic` CLI, type marker, supported Claude compile-hook installer, and an unsupported compatibility-only Claude Stop installer | None for mining, bucketing, gate, audit, harvest, review, or promotion |
| Source install | Wheel contents built from source | The build environment may need to obtain `hatchling>=1.24` |
| Extracted sdist or tagged repository checkout | Wheel contents plus tests, evaluation receipts, standalone plugin bundles, integration docs, and forward-deployed tooling | Keep the extracted directory or checkout; `pip install` alone does not expose these as browsable assets |
| Development install | Repository assets and test/lint tools | `python3 -m pip install -e '.[dev]'` |

Optional surfaces have their own dependencies:

- Personalized compile/retrieval needs a local [Ollama](https://ollama.com/) service and the `nomic-embed-text` model.
- Router stage two needs the separate `hermes-rubric` executable on `PATH`.
- Router stage three needs a caller-supplied model function; repair needs a caller-supplied repair function.
- Forward-deployed boot needs Bash and the `dev` extra (`pytest`) in addition to Python.
- Host recipes and plugins need their named host. Their maturity is listed below.

Release validation ran on macOS. CI is configured for macOS and Ubuntu; Windows is not release-gate verified.

## Five-minute quick start

Check a string:

```bash
printf '%s\n' 'Here are three options and their trade-offs.' | hermeneutic gate
```

```text
PASS — no risk patterns matched.
```

Check a file:

```bash
hermeneutic gate --draft response.txt
```

Exit behavior is deliberate:

- `0`: no hit, or only a low-severity advisory hit;
- `1`: at least one medium- or high-severity hit;
- `2`: invalid input, such as a missing draft file or non-UTF-8 text.

The command reports every hit even when it exits `0`. If a caller wants a hard pre-send check, it must decide how to handle the exit code and output before sending the draft. Post-response hooks can only advise after their host has already rendered the response.

## What learns and what stays fixed

| Surface | Uses your history? | Changes automatically? | Result |
|---|---:|---:|---|
| Mine | Yes | The corpus changes when you re-mine | Correction triples |
| Bucket | Yes | Counts change with the corpus | Category summary |
| Compile/retrieval | Yes | Retrieval changes with the corpus and index | Optional prompt context |
| Deterministic gate | No | No; eight English rules are shipped in code | `PASS` / `RISK` |
| Router | Only if the caller supplies personalized behavior | No default learning loop | Caller-controlled deeper review |
| Harvest/review/promote | Yes | Only accepted human review decisions change the corpus | Reviewed triples for future retrieval |

New mined corrections do not become regex rules. Adding a gate rule requires a code change, evidence, tests, review, and a new release.

## Mine and bucket corrections

The miner recognizes correction-shaped user turns, then records the preceding prompt, assistant reply, correction, and following assistant reply when present.

Supported readers:

| `--format` | Expected input | Typical command |
|---|---|---|
| `claude-code` | Claude Code session JSONL | `hermeneutic mine ~/.claude/projects --glob '**/*.jsonl' --out ~/.hermeneutic/triples.jsonl` |
| `codex` | Codex rollout JSONL | `hermeneutic mine ~/.codex/sessions --format codex --glob '**/rollout-*.jsonl' --out ~/.hermeneutic/triples.jsonl` |
| `openai` | JSON containing a `messages` list, or a top-level message list | `hermeneutic mine ./chat-exports --format openai --glob '*.json' --out ~/.hermeneutic/triples.jsonl` |

Then inspect correction categories:

```bash
hermeneutic bucket ~/.hermeneutic/triples.jsonl
```

`mine` writes JSONL records. `bucket` prints counts. Neither command edits the deterministic gate or sends data anywhere. A missing directory, unmatched glob, or wholly unreadable format fails loudly instead of pretending that zero corrections were found.

The supported readers are intentionally narrow. Add another format by implementing `LogReader` and registering it in `hermeneutic.triples.READERS`.

## Optional personalized compile and retrieval

Compile retrieves corrections from similar prior prompts and builds a deterministic text preamble. The corpus is personal; the retrieval and template are fixed. Ollama is used for local embeddings, not for preamble generation.

Prepare the local model and index:

```bash
ollama pull nomic-embed-text
hermeneutic compile-index --triples ~/.hermeneutic/triples.jsonl
```

Retrieve context for a prompt:

```bash
hermeneutic compile 'Finish the release and report what passed.'
```

If relevant matches clear the configured threshold, the command prints a preamble such as:

```text
[hermeneutic compile-preamble — derived from 2 past corrections on similar prompts]
- 2 prior steer(s) in bucket `over_completion`: default to citing evidence (file:line, command output) when claiming completion
[end preamble]
```

The output depends on your corpus. No corpus, no index, no match, an unavailable Ollama service, a model mismatch, or a vector-dimension mismatch produces no preamble. Diagnose the optional path with:

```bash
hermeneutic compile --verbose 'Finish the release and report what passed.'
```

The CLI uses `k=5` and threshold `0.4`; direct `compile_prompt()` callers default to `k=10` and threshold `0.5`. Both take up to two matches per bucket before applying the global `k` cap. After changing or promoting into the triples corpus, rerun `compile-index`; v0.1.7 does not automatically reject every stale same-length corpus/index pairing.

### Claude prompt-context hook

The wheel includes a mechanically tested `UserPromptSubmit` installer for the optional compile path:

```bash
hermeneutic install-compile-hook
```

It requires an existing `$HOME/.claude/` directory and installs an exec-form hook using the same Python interpreter that ran Hermeneutic. On a match it returns Claude's structured `hookSpecificOutput.additionalContext` for `UserPromptSubmit`; it does not use a user-visible `systemMessage` as model context. Empty results and compiler errors fail open with no hook output.

Remove it with:

```bash
hermeneutic uninstall-compile-hook
```

The installer is idempotent, preserves unrelated hooks, refuses to overwrite a foreign wrapper, and currently targets `$HOME/.claude` rather than `CLAUDE_CONFIG_DIR`. Its JSON contract is fixture-tested; a live authenticated Claude turn was not exercised in the v0.1.7 release gate.

## Deterministic English gate

`hermeneutic gate` calls `hermeneutic.gates.regex.risk_score`. It does not call Ollama, read the triples corpus, run `hermes-rubric`, invoke a model, or repair text.

The eight shipped rules are:

| Rule | Severity | Surface shape |
|---|---|---|
| `completion_with_number` | high | Completion verb followed by a numeric claim |
| `completion_with_all_quantifier` | high | Completion claim with `all`, `every`, or `each` |
| `number_then_completion` | high | Numeric claim followed by a completion verb |
| `subagent_passthrough` | high | Agent output relayed as verified |
| `authority_passthrough` | medium | Team sign-off relayed as verified |
| `unhedged_certainty` | medium | Absolute certainty language |
| `scope_expansion` | medium | Volunteered work beyond the ask |
| `fluent_summary_no_evidence` | low | High-fluency quality adjective without a measurable referent |

A fixed contrast guard suppresses completion hits in honest partial-progress language such as “finished 3, but 5 remain.” These patterns are English surface checks, not semantic proof.

Library use:

```python
from hermeneutic import risk_score

hits = risk_score("Done — shipped 14 files, all tests pass.")
for hit in hits:
    print(hit.rule_id, hit.severity, hit.description)
```

## Advanced Python Router

`Router` is a programmable library surface, not the behavior behind the `gate` CLI. It can compose up to three stages:

1. the fixed regex gate;
2. optional `hermes-rubric` scoring when that executable is available;
3. an optional caller-supplied `PressureProbe`, followed by an optional caller-supplied repairer.

A dependency-free stage-one-only call:

```python
from hermeneutic import Router

router = Router(use_rubric=False)
result = router.gate(
    request="Report the release status.",
    draft="Done — shipped 14 files, all tests pass.",
)

print(result.summary())
print([hit.rule_id for hit in result.risk_hits])
```

Without a probe, a triggered result records `twin-skipped`; it does not block anything. The caller owns the policy that turns `GateResult` into warn, hold, replace, or send behavior.

To add a probe, pass a callable that maps a prompt to model output:

```python
from hermeneutic import PressureProbe, Router

def my_judge(prompt: str) -> str:
    # Call the model/provider chosen by your application.
    return "VERDICT: hold\nREASON: claims lack evidence\nFLIP: attach test output\n"

router = Router(
    probe=PressureProbe(my_judge),
    use_rubric=False,
)
```

Provider packages, credentials, costs, data handling, and failure policy belong to the caller. The v0.1.7 release gate tested Router mechanics with deterministic doubles; it did not certify external rubric, judge, or repair backends.

## Audit, harvest, review, and promote

Telemetry is local, append-only, best-effort, and off by default:

```bash
export HERMENEUTIC_TELEMETRY="$HOME/.hermeneutic/telemetry.jsonl"
export HERMENEUTIC_TELEMETRY_CONTEXT=hash  # none | hash | raw
```

- `none` records classifications, rule IDs, lengths, and content fingerprints without text windows.
- `hash` adds hashes and lengths for matched/context windows.
- `raw` stores reviewable text windows. Use it only where local sensitive text is acceptable.

Summarize the sink:

```bash
hermeneutic stats
hermeneutic stats --json
```

Build a review queue by replaying the current fixed gate over local logs:

```bash
hermeneutic harvest ~/.claude/projects \
  --glob '**/*.jsonl' \
  --out queue.jsonl
```

Queue kinds are `confirmed_catch`, `possible_false_positive`, and `missed_drift`. Reviewers set each row's `status` to `accepted` or `rejected`. Promote only accepted correction-bearing rows:

```bash
hermeneutic promote queue.jsonl --out ~/.hermeneutic/triples.jsonl
hermeneutic compile-index --triples ~/.hermeneutic/triples.jsonl
```

Promotion updates the retrieval corpus. It does not auto-promote records or generate gate regexes. `harvest --sanitized` removes text and hashes session names for sharing review statistics, but this is data minimization—not a guarantee of anonymity—and sanitized queues cannot be promoted.

## Integrations by maturity

Maturity labels describe v0.1.7 evidence, not vendor endorsement.

| Surface | Classification | What is supported |
|---|---|---|
| CLI over stdin/file and Python API | `SELF_CONTAINED_RECIPE` | Portable fixed-gate entry points; the caller chooses whether a hit advises or blocks |
| Claude `UserPromptSubmit` compile hook | `MECHANICALLY_TESTED_INTEGRATION` | Structured optional retrieval-context injection; live authenticated turn unexercised |
| Claude built-in Stop gate | `REMOVE` | Compatibility command remains in the wheel but its current-host runtime contract is unsupported |
| Claude standalone Stop plugin | `REMOVE` | Repository/sdist bundle remains for compatibility but is not a supported v0.1.7 integration |
| Codex copied Stop hook | `MECHANICALLY_TESTED_INTEGRATION` | Script contract is fixture-tested; manual copy/configuration and live host remain unexercised |
| Codex plugin bundle | `MECHANICALLY_TESTED_INTEGRATION` | Repository/sdist script and manifest are tested; no installable marketplace catalog ships |
| Codex forward-deployed sentinel | `MECHANICALLY_TESTED_INTEGRATION` | Install/uninstall and local notification/audit mechanics tested; live deployment unexercised |
| Forward-deployed harness | `MECHANICALLY_TESTED_INTEGRATION` | Repository/sdist verification kit is tested with synthetic/empty inputs; no adopter deployment receipt |
| Cursor via imported Claude Stop hook | `REMOVE` | Importing the unsupported Claude adapter does not create a ready Cursor integration |
| Cursor native hook concept | `DESIGN_SKETCH` | Payload idea only; no complete shipped helper or supported ready recipe |
| OpenHands prompt-context concept | `DESIGN_SKETCH` | No complete shipped helper or verified current payload contract |
| Cline recipe | `REMOVE` | Removed from ready support because the documented payload/output contract drifted |
| Windsurf recipe | `REMOVE` | Removed from ready support because the documented payload/visibility contract drifted |

Log ingestion is a separate axis:

| Reader | Classification | Evidence boundary |
|---|---|---|
| Claude Code JSONL | `LIVE_VERIFIED_INTEGRATION` | Historical 1,423-session derivation receipt using the public miner |
| Codex rollout JSONL | `MECHANICALLY_TESTED_INTEGRATION` | Parser and nested-log fixtures; no standalone live-reader receipt |
| OpenAI-style message JSON | `MECHANICALLY_TESTED_INTEGRATION` | Synthetic parser fixtures; no external live-log receipt |
| Custom `LogReader` | `SELF_CONTAINED_RECIPE` | Extension protocol ships; adopters supply and test their reader |

See [`integrations/`](integrations/) for exact configuration, dependencies, expected result, uninstall path, and host/version caveats. Design sketches are deliberately excluded from ready-support claims.

The standalone `hermeneutic gate` CLI and Python API remain the portable integration points. Run the CLI before sending if you need caller-controlled blocking; run it after rendering only if an advisory is sufficient.

## Forward-deployed tooling

The repository and extracted sdist include a deployment-verification harness under [`forward-deployed/`](forward-deployed/) and the guide [`FORWARD-DEPLOYED-HARNESS.md`](FORWARD-DEPLOYED-HARNESS.md). It can:

- validate that required release files are present and unchanged;
- run local smoke/self-tests;
- inspect a supplied session-log path;
- produce a structured fit/adaptation report;
- install or remove the Codex notification sentinel.

These assets are not installed by the wheel. Boot requires Python 3.10+, Bash, and the `dev` extra because it runs pytest. Mechanics were exercised with synthetic/empty inputs; a real adopter's logs and live deployment were not.

## Evidence and historical experiments

### Corpus facts

The original 2026-04-25 derivation receipt covers one author's 1,423 Claude Code sessions and 326 mined corrections. It found 143/326 post-completion overclaim corrections. The private triples are not shipped. The historical “about 65%” figure described category mapping for the original six rules; it was not a direct regex hit rate or held-out score.

The available 346-triple dataset is a separate later frozen retrieval corpus. Its SHA-256 is `920bfcac721e0df2b18894461daf5d5fd8d847d90974a4572e7749322900172b`.

### Current deterministic gate coverage

Running the current eight-rule gate over `prior_assistant` in that 346-triple correction corpus produces:

- 115/346 direct hits (33.24%);
- 231/346 silent rows;
- 54 rows with more than one distinct rule.

This is retrospective derivation-set coverage on a correction-only corpus. It is not held-out recall, precision, false-positive rate, live fire rate, or evidence that the gate improves a model. Aggregate per-rule and overlap counts are in [`evals/gate-coverage/`](evals/gate-coverage/).

### Current production-path retrieval measurement

The current bounded evaluator masks each held-out triple and calls the shipped `compile_prompt()` selection path using its cached frozen query vector. It makes no live Ollama calls.

| Profile | Same-bucket recall | Mean surfaced buckets |
|---|---:|---:|
| CLI / compile-hook defaults (`k=5`, threshold `0.4`) | 88/104 (84.6%) | 3.29 |
| Python defaults (`k=10`, threshold `0.5`) | 94/104 (90.4%) | 4.93 |

This measures whether at least one warning from the held-out correction's category is surfaced on one single-user corpus. It does not measure advice quality, generalization, or whether a model follows the context. See [`evals/leave-one-out/`](evals/leave-one-out/).

### Historical-only retrieval receipts

The previously reported 83.7% leave-one-out result and 98/100 versus 7/30 discrimination result are retained as dated frozen experiments, not current production-path headlines. Their evaluators differed from the shipped per-bucket/global-cap path, and the original April model/index bytes were not fully pinned. The original aggregate receipts remain under [`evals/`](evals/).

Downstream effectiveness—whether the gate or compile context reduces later model misinterpretation—remains unmeasured.

## Limitations and when not to use it

- The fixed gate checks English surface patterns. It is not a multilingual or semantic verifier.
- Regex hits can be false positives, and many correction episodes do not match a shipped rule.
- A `PASS` means only that no current pattern matched; it is not proof of correctness.
- Mining uses fixed correction markers and can miss implicit corrections or unsupported log shapes.
- Personalized retrieval needs local Ollama and an index rebuilt after corpus changes.
- Post-response hooks advise after rendering; they do not prevent a response from reaching the user.
- The Router's external stages can add latency, cost, network transfer, and provider-specific failures.
- Current evidence comes from one heavy user's private corpus and deterministic fixtures; do not assume the same distribution for another user or team.
- Windows, live Ollama in the release gate, live host UIs, external Router backends, and downstream effectiveness are unexercised.

Do not use Hermeneutic as a security boundary, factuality guarantee, policy engine, moderation system, or substitute for domain review. It is most useful when you want a transparent local tripwire and a reviewable record of repeated correction shapes.

## Privacy and local data

- Mining reads paths you provide and writes where you direct it.
- Triples and embedding indexes default to `~/.hermeneutic/` and stay local.
- No private corpus, embedding, or session content ships in the package or repository.
- Core mining, bucketing, gate, harvest, review, and promotion make no network calls.
- The built-in compile path sends prompt text to localhost Ollama; Python callers can override that URL and then own the endpoint's data policy.
- Router model/provider calls occur only through tools or callables the application configures.
- Telemetry is off unless `HERMENEUTIC_TELEMETRY` is set.
- Raw telemetry, triples, and injected compile context may contain sensitive text. Claude stores injected `additionalContext` in its session transcript; apply the host's retention policy accordingly.

Review local files before sharing them. Hashing and `harvest --sanitized` reduce exposed text but do not prove anonymity.

## Documentation and project

- [Theory and design boundary](docs/THEORY.md)
- [Evaluation receipts](evals/)
- [Integration maturity and recipes](integrations/)
- [Forward-deployed harness](FORWARD-DEPLOYED-HARNESS.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of conduct](CODE_OF_CONDUCT.md)

If you use Hermeneutic in scholarly work, cite the metadata in [`CITATION.cff`](CITATION.cff). The software is authored by Rolando Bosch / Hermes Labs; scholarly metadata preserves the full family name and ORCID.

Hermeneutic is free software under the [MIT License](LICENSE).
