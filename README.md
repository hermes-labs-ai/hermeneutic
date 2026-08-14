# hermeneutic

**Catch recurring AI drift using corrections already present in your chat logs.**

[![PyPI](https://img.shields.io/pypi/v/hermeneutic.svg)](https://pypi.org/project/hermeneutic/)
[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-3776AB)](https://www.python.org/)
[![CI](https://github.com/hermes-labs-ai/hermeneutic/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/hermes-labs-ai/hermeneutic/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-2ea44f)](https://github.com/hermes-labs-ai/hermeneutic/blob/main/LICENSE)

Many AI workflow failures are not failures of model capability. They are failures of interpretation:

- what “done” meant;
- what evidence counted;
- which constraint still applied;
- when confidence was unjustified;
- which earlier correction should govern the next task.

Hermeneutic recovers what prior corrections reveal about the user’s meaning, then examines what the system’s next answer commits it to.

Your work logs already contain a trace of those failures:

```text
assistant output → user correction → repaired output
```

Hermeneutic makes that trace reusable.

It works on both sides of an AI interaction:

- **Hermeneutic memory** carries prior corrections forward into similar tasks.
- **The epistemic gate** checks what an outgoing answer claims before you trust it.

```text
past corrections
      ↓
hermeneutic memory
      ↓
relevant context for a similar task
      ↓
generated draft
      ↓
epistemic gate
      ↓
PASS or RISK
```

The memory layer adapts to your history. The gate remains fixed and transparent.

## Related research

[*Precise Records, Unstable Meanings*](https://doi.org/10.5281/zenodo.21652316)
examined a two-day stream of Hermeneutic v0.1.7 verdicts as unvalidated
instrument outputs. The study did not evaluate Hermeneutic's correction mining,
retrieval, integrations, or downstream effectiveness.

## See the full loop

### 1. Carry prior meaning forward

Hermeneutic can recover a correction from an earlier Claude Code session and surface it when a similar task appears later.

The trace below is real, taken from the author’s own Claude Code logs and abridged only for length. The assistant had classified parts of a retrieval system as “fully generic” without running anything:

```text
Earlier Claude Code session

Assistant (abridged):
Honest breakdown:

**What's fully generic (works for any harness out of the box):**
- `/store`, `/recall`, `/recall_b` endpoints — zero corpus assumptions
- RRF decomposition — pure tokenization + vector math, no domain knowledge
[…]
The pipeline itself is generic.

User correction (verbatim, typos preserved):
wait... recall,_b at 60%+ is gerneric? are you sure/ please verify

Repaired response:
Let me actually verify rather than assert. Let me look at *why* recall_b
is hitting on the cases it hits:
```

The durable lesson is interpretive: for this user, a capability or completion claim is not acceptable until it cites direct evidence.

When a later prompt resembles that situation:

```text
Would this retrieval strategy work for other harnesses too, or is it customized to ours? Can we say it is generic?
```

Hermeneutic memory retrieves the relevant prior lesson as advisory context. This is the unedited `hermeneutic compile` output for that prompt against the author’s 346-correction corpus — the correction above is the highest-similarity match behind the first line:

```text
[hermeneutic compile-preamble — derived from 5 past corrections on similar prompts]
- 2 prior steer(s) in bucket `over_completion`: default to citing evidence (file:line, command output) when claiming completion
- 2 prior steer(s) in bucket `over_confirmation`: execute when the user's intent is unambiguous; don't ask clarifying questions on imperative requests
- 1 prior steer(s) in bucket `wrong_target`: if the user quoted a literal spec, use it verbatim; don't expand or substitute
[end preamble]
```

This is the adaptive side of Hermeneutic: it recovers what prior corrections reveal about the user’s standards, constraints, and intended meaning, then brings that evidence forward into similar work.

It does not rewrite the model or silently convert personal corrections into global rules.

### 2. Check claims on the way out

After the system produces a draft, the fixed epistemic gate examines what the wording commits the system to.

The following reproducible example deliberately contains two claims that deserve verification:

```bash
printf '%s\n' 'Done — shipped 14 files, all tests pass.' | hermeneutic gate
```

Hermeneutic flags:

- **“Done — shipped 14”** because it combines a completion claim with a precise count. That count should come from tool output or another verifiable source.
- **“all tests pass”** because “all” claims complete coverage. The caller should confirm that the full relevant test set actually ran.

```text
RISK — highest severity: high
  [high] completion_with_number: 'Done — shipped 14'
    why: Completion verb co-occurs with a numeric claim — verify the number is tool-derived.
  [high] completion_with_all_quantifier: 'Done — shipped 14 files, all'
    why: Completion claim with universal quantifier — confirm scope coverage.
```

The gate is not declaring the sentence false. It is identifying wording that creates an evidence obligation.

## Quick start

Hermeneutic requires Python 3.10 or newer.

```bash
pip install hermeneutic
```

Check a saved draft:

```bash
hermeneutic gate --draft response.txt
```

Or pipe generated output into the gate:

```bash
generate-response | hermeneutic gate
```

The standalone gate works offline, requires no model or private logs, and has zero required Python runtime dependencies.

Its exit codes are designed for scripts and hooks:

- `0`: no match, or only a low-severity advisory;
- `1`: at least one medium- or high-severity match;
- `2`: invalid input, such as a missing file or non-UTF-8 text.

Using multiple Python installations? Install with:

```bash
python3 -m pip install hermeneutic
```

## Hermeneutic memory

Hermeneutic memory recovers correction evidence from supported AI work logs and surfaces relevant prior guidance when a similar task appears.

```text
logs → correction episodes → local corpus → relevant prior guidance
```

### Mine correction episodes

Hermeneutic recognizes correction-shaped user turns and records the surrounding exchange when available:

```text
prompt → assistant reply → user correction → repaired reply
```

Mine Claude Code logs:

```bash
hermeneutic mine ~/.claude/projects \
  --format claude-code \
  --glob '**/*.jsonl' \
  --out ~/.hermeneutic/triples.jsonl
```

Inspect recurring categories:

```bash
hermeneutic bucket ~/.hermeneutic/triples.jsonl
```

Supported readers:

| Format | Expected input |
|---|---|
| `claude-code` | Claude Code session JSONL |
| `codex` | Codex rollout JSONL |
| `openai` | JSON containing a `messages` list, or a top-level message list |

Mining writes local JSONL records. It does not change the epistemic gate or send the corpus anywhere.

Missing directories, unmatched globs, and wholly unreadable input fail loudly rather than being reported as zero corrections.

### Retrieve relevant prior corrections

Personalized retrieval is optional. It uses the local correction corpus and an Ollama embedding service with `nomic-embed-text`.

Build the index:

```bash
ollama pull nomic-embed-text
hermeneutic compile-index --triples ~/.hermeneutic/triples.jsonl
```

Retrieve prior guidance for a new prompt:

```bash
hermeneutic compile 'Finish the release and report what passed.'
```

When relevant matches clear the configured threshold, Hermeneutic emits deterministic advisory context such as:

```text
[hermeneutic compile-preamble — derived from 2 past corrections on similar prompts]
- 2 prior steer(s) in bucket `over_completion`: default to citing evidence (file:line, command output) when claiming completion
[end preamble]
```

Ollama produces embeddings. It does not generate the guidance text.

No corpus, index, relevant match, or available embedding service means no preamble.

After changing the corpus, rebuild the index.

Diagnose an empty result with:

```bash
hermeneutic compile --verbose 'Finish the release and report what passed.'
```

See the [compile walkthrough](https://github.com/hermes-labs-ai/hermeneutic/blob/main/evals/compile-walkthrough.md) for a complete example.

## Epistemic gate

The epistemic gate examines what an outgoing draft commits the system to.

It runs eight fixed English surface-pattern checks covering patterns such as:

- completion claims combined with precise counts;
- universal coverage claims such as “all” or “every”;
- subagent or authority output relayed as verified;
- unhedged certainty;
- volunteered expansion beyond the requested scope;
- quality claims without a measurable referent.

It returns `PASS` or `RISK` together with any matched rules.

The gate identifies claims that deserve verification. It does not determine whether a statement is true, understand its full semantic meaning, or prove that a response is safe to send.

Mining and retrieval never rewrite gate rules. New gate behavior requires a deliberate code change and a later release.

Use the Python API directly:

```python
from hermeneutic import risk_score

for hit in risk_score("Done — shipped 14 files, all tests pass."):
    print(hit.rule_id, hit.severity, hit.description)
```

The caller decides whether to warn, hold, revise, or send the draft.

## How the layers differ

| Layer | Uses your history? | Output |
|---|---:|---|
| Hermeneutic memory: mining | Yes | Local correction records |
| Hermeneutic memory: retrieval | Yes | Advisory context for a new prompt |
| Epistemic gate | No | `PASS` or `RISK` for a draft |
| Python Router | Caller-controlled | Composed review behavior |

The distinction is intentional:

- memory adapts to your correction history;
- the gate remains fixed across users;
- retrieval acts before or during a task;
- the gate acts on the outgoing draft;
- the Router is an advanced composition API, not the default workflow.

## Optional integrations

The standalone CLI and Python API are the portable core paths.

The package also includes an installer for an optional Claude Code `UserPromptSubmit` hook:

```bash
hermeneutic install-compile-hook
hermeneutic uninstall-compile-hook
```

On a relevant match, the hook returns structured prompt context. Empty results and compiler errors fail open with no hook output.

The Claude hook is mechanically tested. A live authenticated Claude turn was not part of the v0.1.7 release gate.

Codex plugin and sentinel assets are also included with narrower mechanically tested boundaries.

See the [integration guides](https://github.com/hermes-labs-ai/hermeneutic/tree/main/integrations) for configuration, maturity, dependencies, and uninstall instructions.

## Advanced Python Router

The optional [Python Router](https://github.com/hermes-labs-ai/hermeneutic/blob/main/docs/THEORY.md) can compose the fixed gate with caller-supplied stages such as:

- rubric-based review;
- model criticism;
- probing;
- repair.

It is not part of the default CLI workflow.

External stages inherit the caller’s credentials, cost, network behavior, privacy boundaries, and failure modes.

## Evidence

Hermeneutic was derived from a single author’s working corpus rather than a synthetic benchmark alone.

| Measurement | Result | Boundary |
|---|---:|---|
| Historical mining derivation | 326 corrections from 1,423 Claude Code sessions; 143/326 were post-completion overclaim corrections | Private triples are not distributed |
| Fixed-gate coverage | 115/346 direct hits | Retrospective correction-corpus coverage, not held-out accuracy |
| Retrieval profile | 88/104 same-category hits at CLI/hook defaults; 94/104 at Python defaults | One frozen single-user corpus using cached vectors |

The mining derivation was a 2026-04 run that produced 326 corrections. The gate-coverage and retrieval measurements use a separate, later frozen 346-correction corpus; the receipts do not attribute the 20-row difference to one cause.

The gate result is not a precision, false-positive-rate, held-out-recall, or live-fire claim.

The retrieval result measures whether guidance from the same correction category was surfaced. It does not measure advice quality, cross-user generalization, model compliance, or downstream improvement.

Downstream effectiveness remains unmeasured.

Reproduction details:

- [Mining derivation receipt](https://github.com/hermes-labs-ai/hermeneutic/blob/main/evals/triple-mining-receipts.md)
- [Gate coverage](https://github.com/hermes-labs-ai/hermeneutic/blob/main/evals/gate-coverage/RESULTS.md)
- [Retrieval evaluation](https://github.com/hermes-labs-ai/hermeneutic/blob/main/evals/leave-one-out/RESULTS.md)

## Privacy

Mining reads only the paths supplied by the caller.

Triples and embedding indexes default to `~/.hermeneutic/`.

Core mining, bucketing, gating, and local review commands make no network calls.

The optional retrieval compiler sends prompt text to its configured Ollama endpoint, which defaults to localhost.

Telemetry is disabled unless `HERMENEUTIC_TELEMETRY` is configured.

No private corpus, embedding index, or session content is distributed.

Triples, telemetry, embeddings, and injected context may contain sensitive text. Review local artifacts before sharing them and apply the retention policy of any configured host.

See the [security and data-handling policy](https://github.com/hermes-labs-ai/hermeneutic/blob/main/SECURITY.md).

## Limitations

- The epistemic gate checks English surface patterns, not full semantic meaning.
- `PASS` means only that no shipped pattern matched.
- Rules can produce false positives and miss real failures.
- Gate rules do not learn automatically.
- Mining uses deliberately narrow correction markers and log readers.
- Retrieval quality is not downstream effectiveness.
- Current evidence comes from one heavy user’s private corpus and deterministic fixtures.
- Windows, live host interfaces, external Router backends, and downstream effectiveness were not release-gate verified.
- Human review remains necessary.

Do not use Hermeneutic as a security boundary, factuality guarantee, moderation system, policy engine, or substitute for domain review.

## Documentation

- [Worked before/after example](https://github.com/hermes-labs-ai/hermeneutic/blob/main/examples/before_after.md)
- [Theory and advanced Router](https://github.com/hermes-labs-ai/hermeneutic/blob/main/docs/THEORY.md)
- [Integration guides](https://github.com/hermes-labs-ai/hermeneutic/tree/main/integrations)
- [Evaluation receipts](https://github.com/hermes-labs-ai/hermeneutic/tree/main/evals)
- [Forward-deployed verification tooling](https://github.com/hermes-labs-ai/hermeneutic/blob/main/FORWARD-DEPLOYED-HARNESS.md)
- [Changelog](https://github.com/hermes-labs-ai/hermeneutic/blob/main/CHANGELOG.md)
- [Security](https://github.com/hermes-labs-ai/hermeneutic/blob/main/SECURITY.md)
- [Contributing](https://github.com/hermes-labs-ai/hermeneutic/blob/main/CONTRIBUTING.md)
- [Citation metadata](https://github.com/hermes-labs-ai/hermeneutic/blob/main/CITATION.cff)
- [MIT License](https://github.com/hermes-labs-ai/hermeneutic/blob/main/LICENSE)

For CLI reference:

```bash
hermeneutic --help
hermeneutic <command> --help
```

Hermeneutic is maintained by [Hermes Labs](https://github.com/hermes-labs-ai).
