# hermeneutic

hermeneutic mines your chat logs for the moments you corrected your AI, turns those corrections into rules, and checks every outgoing response against them before it ships. A drift gate, built from your own evidence.

**Your AI overclaims. You correct it. Now your AI gets gated.**

> Mined 326 corrections across 1,423 chat sessions. 44% were post-completion overclaiming - the dominant drift mode. 8 regex rules ship; the original 6 covered ~65% of that distribution (8-rule coverage not yet re-measured). **131 tests** covering the gate, the compile layer, the audit log, the harvester, the forward-deployed harness, the plugin gate scripts, and a doc-consistency CI check. Three stages, fail-cheap to fail-expensive. Free, MIT, zero dependencies.

> **Validation status (measured 2026-04-27):** bucket-aware retrieval lifts leave-one-out recall from 56.7% → **83.7%** on n=104 trials, including 50%/75%/33%/33% on the four rare buckets that the global-top-K baseline missed entirely. In-corpus prompts trigger compile 98/100 vs synthetic-random 7/30 (Fisher's exact p=2.6e-17). Trade-off: 3× wider preamble (1.4 → 4.2 buckets per query). That validates hermeneutic **as a retrieval system** (frozen embedding-index snapshot; see the Reproducibility note under Eval evidence). Effectiveness (does compile actually reduce LLM misinterpretation?) is the pre-registered v1.0 milestone — **not yet measured**.

[![CI](https://github.com/hermes-labs-ai/hermeneutic/actions/workflows/ci.yml/badge.svg)](https://github.com/hermes-labs-ai/hermeneutic/actions/workflows/ci.yml)
[![tests](https://img.shields.io/badge/tests-131%20passing-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hermes Labs](https://img.shields.io/badge/by-Hermes%20Labs-black)](https://hermes-labs.ai)

![hermeneutic gate catching an overclaim](docs/demo.gif)

---

## The shift

Every chat log you've ever produced contains a hidden, labeled dataset:

```
prior_assistant   ← the drift
       ↓
user_correction   ← you, doing the work
       ↓
next_assistant    ← the repair
```

Most teams throw it away. **`hermeneutic` mines it, classifies the drift, and runs it as a pre-flight gate on the next outgoing response.**

```
draft → regex (~0ms)         most ship here
           ↓ if hit
       hermes-rubric          many ship here
           ↓ if fail
       PressureProbe          ship | revise | hold
           ↓ if revise
       repair pass            ship
```

Cheap-to-expensive. Most drafts pass stage 1 untouched. The stage that costs you an API call only fires on the ~10–20% that look risky.

---

## 30 seconds

```bash
git clone --depth 1 https://github.com/hermes-labs-ai/hermeneutic
cd hermeneutic && pip install .
# after the PyPI release is verified, this is equivalent: pip install hermeneutic

hermeneutic mine ~/.claude/projects/*/  --out triples.jsonl
hermeneutic bucket triples.jsonl
echo "Done — shipped 14 files, all tests pass." | hermeneutic gate
```

That last line returns:

```
RISK — high
  completion_with_number: 'Done — shipped 14'
  completion_with_all_quantifier: 'Done — shipped 14 files, all'
```

### Real-time gating in Claude Code (one command)

```bash
# after installing with one of the commands above:
hermeneutic install-hook
# Restart Claude Code. Done.
```

Every assistant turn now passes through the gate; if a RISK fires, you'll see a one-line `[hermeneutic] RISK — high ...` notice in the Claude Code UI. **Advisory mode** - the hook never blocks the assistant, just flags the drift. Remove with `hermeneutic uninstall-hook`.

The install is idempotent (safe to re-run), preserves any other hooks you have configured, and refuses to overwrite files it didn't create.

### Compile your prompts ahead of the LLM (Layer 2, v0.1.5)

The output gate above is half the loop. The other half is a **compiler** that runs *before* the LLM sees your prompt: it retrieves past moments where similar prompts were misinterpreted, and injects a "watch out for X" preamble so the model is calibrated up front.

**Prerequisite:** the compile layer embeds locally via [Ollama](https://ollama.com) (`ollama pull nomic-embed-text`). If Ollama is unreachable the preamble is skipped silently — the gate keeps working, compile just stays quiet.

```bash
hermeneutic mine ~/.claude/projects/*/  --out ~/.hermeneutic/triples.jsonl
hermeneutic compile-index            # one-time: embed the corpus (Ollama + nomic-embed-text)
echo "build me a thing" | hermeneutic compile
# [hermeneutic compile-preamble — derived from N past corrections on similar prompts]
# - 12 prior steer(s) in bucket `over_confirmation`: execute when the user's intent is unambiguous; ...
# [end preamble]
```

To wire compile into Claude Code as a UserPromptSubmit hook (one command):

```bash
hermeneutic install-compile-hook
# Restart Claude Code. Every prompt now gets a past-corrections preamble injected silently.
```

Same advisory stance as the gate - never blocks, only injects context. Same idempotency + foreign-file protection. Remove with `hermeneutic uninstall-compile-hook`.

**Two loops, one corpus:**

```
user prompt → [Layer 2 compile]  → LLM → [Layer 1 gate] → response
                ↑                              ↑
                └──── shared (drift, steer, repair) corpus ────┘
```

See [`evals/compile-walkthrough.md`](evals/compile-walkthrough.md) for two demonstrative cases. Honest framing: the compile layer surfaces *relevant past signal*, not validated effectiveness. The replay-study measurement is the v1.0 milestone.

The draft was about to overclaim. The gate flagged it before you trusted it.

### What we explicitly do NOT claim

1. **No effectiveness measurement yet.** Everything above is validated as a *retrieval* system; whether compile actually reduces LLM misinterpretation is the replay study — the v1.0 milestone (N≥30 historical drift moments, ≥20% relative correction-rate reduction floor pre-registered, two backends, blind LLM-judge coding).
2. **Rare-bucket recall (50%/75%/33%/33%) is real but uneven** - `scope_creep` and `tool_choice` have N=3 triples each, so a single hit/miss moves their rate by 33pp.
3. **The 3× preamble width** trade-off may turn out to be too noisy for downstream LLMs — v1.0 measures whether wider preambles help or hurt.
4. **The random baseline is synthetic** (word recombiner). The v1.0 upgrade is real out-of-distribution prompts.

Full context under [Eval evidence](#eval-evidence-local-iteration-2026-04-27) below.

---

## What you actually get

| | |
|---|---|
| **Mine** | Walk any chat-log directory (Claude Code, Codex CLI, OpenAI), extract correction triples |
| **Bucket** | See your AI's actual drift modes - not what someone else thinks they are |
| **Gate** | Run the 3-stage pre-flight on any outgoing draft |
| **Audit** | Opt-in local log of every fire, with reviewable before/after context |
| **Stats** | `hermeneutic stats` - fire rates, rule distribution, human-vs-agent split |
| **Harvest** | Replay the gate over months of logs into a labeled review queue - no hand-reading |
| **Deploy** | Forward-deployed harness: an agent in *your* environment verifies the install end-to-end and leaves a sanitized report |
| **Library** | Full Python API. Plug into your pipeline in 4 lines. |

The PyPI wheel contains the CLI, Python library, and built-in Claude Code hook
installer. The forward-deployed harness, standalone plugin bundles, integration
recipes, and eval receipts are repository/source-distribution assets; clone the
tag when you need those surfaces.

### Where it plugs in

| | Claude Code | Codex CLI | Cursor | Windsurf | Cline | OpenHands | MCP hosts | anything |
|---|---|---|---|---|---|---|---|---|
| gate every response | verified hook | validated local plugin + sentinel | [documented recipe](integrations/cursor.md) | [documented recipe](integrations/windsurf.md) | [documented recipe](integrations/cline.md) | [preamble only](integrations/openhands.md) | planned | pipe to `hermeneutic gate` |

Details, honest caveats, and uninstall paths: [`integrations/`](integrations/).

---

## See it working: the audit log

A gate you can't inspect is a gate you can't trust. Turn on the local audit
log and every fire becomes reviewable on your own machine - which rule fired,
on what text, in what surrounding context:

```bash
export HERMENEUTIC_TELEMETRY=~/.hermeneutic/telemetry.jsonl   # off unless set
export HERMENEUTIC_TELEMETRY_CONTEXT=raw                      # none | hash | raw

echo "Done — shipped 14 files and all 92 tests pass." | hermeneutic gate
hermeneutic stats
```

`stats` summarizes the sink: PASS/RISK split, per-rule fire counts, severity
distribution, and a human-vs-agent segmentation (agent sessions fire
differently than interactive ones). Add `--json` for dashboards.

Context modes are a privacy dial: `none` (default) logs verdicts and rule ids
only; `hash` stores SHA-256 fingerprints of the matched windows - enough to
correlate repeated content without storing the text; `raw` stores the
before/matched/after windows themselves for full local review. In every mode
the log is a plain JSONL file on your disk. Hermeneutic's telemetry code does
not transmit it.

False positives are the point: when a rule misfires, the audit entry is the
labeled counter-example you tune it with.

### Close the loop: harvest → review → promote

Hand-reading chats to find corrections doesn't scale. The harvester replays
the gate (it's a pure function) over any log directory and classifies every
assistant turn by what the user *actually did next*:

```bash
hermeneutic harvest ~/.claude/projects/my-project --out queue.jsonl
#   confirmed_catch           gate fired, user corrected - the gate proved itself
#   possible_false_positive   gate fired, user moved on   - tune rules against these
#   missed_drift              gate silent, user corrected - new rules come from here

# flip "status" to accepted/rejected in queue.jsonl, then:
hermeneutic promote queue.jsonl --out ~/.hermeneutic/triples.jsonl
hermeneutic compile-index
```

Months of logs reduce to a few hundred classified rows; accepted records feed
straight back into your corpus. Zero LLM calls end to end.

---

## Deploy it where you can't see: the forward-deployed harness

Shipping a tool into an environment you will never see is itself a
completion claim — so it gets gated too. `FORWARD-DEPLOYED-HARNESS.md` is an
executable mission for the agent already living in the adopter's
environment: a deterministic step-machine (`forward-deployed/harness.py`)
drives ENV → BOOT → HARVEST → REPORT → GATE, verifies every step from
artifacts on disk before the next unlocks, and records progress as a
tamper-evident hash chain.

```bash
python3 forward-deployed/harness.py    # prints exactly one next action; repeat until MISSION COMPLETE
```

The agent can't declare the deployment done — `forward-deployed/gate.py`
declares it, and only when boot evidence is fresh and green, the suite
passes *in that environment*, the zero-LLM and privacy invariants hold
mechanically, and the report passes a bounded leak-linter. The linter screens
common path, email, and pasted-text shapes; it is not an anonymity proof, so a
human must review the report before deciding whether to send it. This repository
tests the harness mechanics locally; an adopter's own receipt is the evidence
that a particular deployment worked in that environment.

---

## Library use

```python
from hermeneutic import Router, PressureProbe

probe = PressureProbe(judge=your_llm)   # any callable: prompt -> str

router = Router(
    probe=probe,
    repairer=lambda req, draft, why: your_llm(f"Revise: {why}\n\n{draft}"),
)

result = router.gate(request="Build me a thing", draft=your_draft)
print(result.summary())          # shipped@repair risk=high(2) twin=revise REPAIRED
print(result.final_output)       # the safer, ship-ready version
```

That's it. No subclassing, no config file, no provider lock-in.

---

## The breakthrough: ship the role, keep the priors

A reviewer-twin has two layers:

1. **The role** - a critic that forces structured output: verdict + flip-condition + evidence pointer
2. **The priors** - *whose* judgment, *what* red flags, *what* severity calibration

We ship the role as `PressureProbe`. You bring your own calibration. **The architecture does the work even when the calibration is generic** - your users can't game *"what would falsify this?"* by being lazy.

| Audience | What you do | What you get |
|---|---|---|
| **Solo dev** | Use the default rigorous-skeptic prior | Instant gate on your AI's worst drafts |
| **Team** | Drop in your own calibration text | Codified house style, every commit |
| **Enterprise** | Swap in your domain priors (security, medical, legal) | Private calibration, public-tested architecture, ship to every team |

One library. Every audience.

### What changes for you immediately

After `pip install hermeneutic` and one mining pass on your existing logs:

- Every outgoing draft gets a free pre-flight check - most pass in microseconds, only the risky ones cost a downstream LLM call.
- Confident "Done - shipped 14 files, all green" claims get caught before they ship, with the specific drift pattern named (`completion_with_number`).
- Subagent-passthrough text ("the agents converged on…") gets flagged so you don't propagate unverified summaries.
- You build a labeled dataset of *(my draft, gate verdict, your acceptance)* every time the gate fires - that's your data flywheel for the next round of rules.
- Your team's house style gets codified as a `PressureProbe` calibration string instead of living in tribal Slack messages.

The gate doesn't make your AI smarter. It stops the most common drift modes from reaching the user.

### Extensibility

Both pluggable surfaces are `typing.Protocol` interfaces - no subclassing required, no framework lock-in:

```python
from typing import Protocol

# Plug in any LLM as the critic — OpenAI, Anthropic, Ollama, your own twin.
class LLMJudge(Protocol):
    def __call__(self, prompt: str) -> str: ...

# Plug in any chat-log format by subclassing LogReader (registered in READERS dict).
from hermeneutic.triples import LogReader, READERS

class MyFormatReader(LogReader):
    name = "my-format"
    def iter_turns(self, path):
        # yield (role, text, timestamp) tuples
        ...

READERS["my-format"] = MyFormatReader()
```

Default judge calibration is `rigorous-skeptic`; default readers cover Claude Code JSONL, Codex CLI session rollouts, and OpenAI ChatCompletion JSON.

---

## Eval evidence (local iteration, 2026-04-27)

We separated "does retrieval work as a retrieval system" from "does compile actually change LLM behavior" and only claim the first. The second is the v1.0 milestone.

### Measurement A - leave-one-out recall (`evals/leave-one-out/`)

For each of 346 mined triples (a re-mine of the same corpus behind the 326-triple derivation study — reader improvements picked up 20 more; see [`evals/triple-mining-receipts.md`](evals/triple-mining-receipts.md)), hide it from the index, query its `orig_prompt`, check if its bucket appears in the bucket-aware top-N-per-bucket retrieval (n=2, threshold=0.5). Compare to a global-top-K baseline and a uniform-random-retrieval baseline.

| Configuration | Overall recall | Rare-bucket recall (n=16) | Avg buckets surfaced/query |
|---|---|---|---|
| **Bucket-aware (current default)** | **83.7%** (87/104) | **50%** (avg of 50/75/33/33) | 4.2 |
| Prior global top-K=5 baseline | 56.7% (59/104) | **0%** | 1.4 |
| Random-retrieval baseline | 44.5% | n/a | n/a |

Per-bucket recall under bucket-aware retrieval:

| true bucket | n eligible | recall |
|---|---|---|
| `over_confirmation` | 59 | 91.5% |
| `missed_constraint` | 29 | 86.2% |
| `over_completion` | 4 | 75.0% |
| `wrong_target` | 6 | 50.0% |
| `scope_creep` | 3 | 33.3% |
| `tool_choice` | 3 | 33.3% |

The rare-bucket lift came from a single methodological tweak: instead of top-K globally (where rare-bucket matches were getting outranked at median-rank-62 by majority-bucket triples), we take top-N per bucket above threshold. Diagnosis run + measurement at [`evals/leave-one-out/diagnose_minority.py`](evals/leave-one-out/diagnose_minority.py) and [`test_bucket_aware.py`](evals/leave-one-out/test_bucket_aware.py).

**Reproducibility note (2026-07-12):** these numbers are properties of the frozen 2026-04 embedding index (receipts committed in [`results.json`](evals/leave-one-out/results.json)). Re-running against a freshly rebuilt local index of the same 346-triple corpus reproduces the baseline at 52.9% (55/104) rather than 56.7%, and the bucket-aware headline at 81.7% (85/104) rather than 83.7% — small index-state drift: the local embedding model was updated between builds (`nomic-embed-text` is a moving tag), per-bucket corpus counts are bit-identical, and repeated runs on the rebuilt index are fully deterministic. Treat retrieval numbers as specific to the committed index state, not as embedder-version-independent constants. Future frozen receipts will pin a corpus hash + embedder digest at generation time.

### Measurement B - input discrimination (`evals/bucket-discrimination/`)

Compile 100 in-corpus prompts vs 30 deterministic random word-recombiner prompts, measure how often each group produces a non-empty preamble.

| Group | Triggered | Silent | Trigger rate |
|---|---|---|---|
| in-corpus prompts | 98 | 2 | **98%** |
| synthetic-random word-soup | 7 | 23 | **23%** |

**Fisher's exact (2-tailed): odds ratio = 161, p = 2.6 × 10⁻¹⁷.** Compile reliably distinguishes real prompts from noise at the trigger-rate level.

Bucket-shape conditional on trigger: χ² = 3.80, dof = 5, p = 0.58. Once both groups produce a non-empty preamble, the bucket distributions look similar - meaning the discrimination signal is at the *trigger* level, not at the *bucket-mix* level. Honest limitation, not a defect.

### What we explicitly do NOT claim

1. **No effectiveness measurement.** This iteration measures the retrieval system; it does not measure whether compile actually reduces LLM misinterpretation. The replay study is the v1.0 milestone (N≥30 historical drift moments, ≥20% relative correction-rate reduction floor pre-registered, two backends, blind LLM-judge coding).
2. **The 50% / 75% / 33% / 33% rare-bucket recall** is real but uneven - `scope_creep` and `tool_choice` only have N=3 triples each, so a single hit/miss moves their rate by 33pp. v1.0 requires more rare-bucket triples in the corpus to stabilize.
3. **The 3× preamble width** trade-off may turn out to be too noisy for downstream LLMs. v1.0 will measure whether wider preambles help or hurt actual behavior change.
4. **Random baseline is synthetic** (word recombiner from `/usr/share/dict/words`). v1.0 baseline upgrade is real out-of-distribution prompts (Tatoeba / public chat corpus).


---

## The receipts

This isn't a thought experiment. The risk patterns ship with `hermeneutic` because we mined a real corpus first:

- **1,423 sessions** of one heavy AI user
- **326 corrections** extracted as `(drift, steer, repair)` triples
- **44%** (143/326) were post-completion overclaiming - the dominant drift mode
- **8 regex rules** ship; the original 6 covered ~65% of the corpus (8-rule coverage not yet re-measured)

Every pattern in `gates/regex.py` traces to corrections caught in the wild. Methodology, bucket distribution, and pattern derivation are documented in [`evals/triple-mining-receipts.md`](evals/triple-mining-receipts.md). The 326 triples themselves are not shipped (private session content). **Your distribution will look different - that's the point.** Run the miner on your own logs and *your* gate writes itself.

### Verify the gate yourself

The gate should catch its own announcement language. If the demo below ships zero hits, the rules are broken:

```bash
git clone https://github.com/hermes-labs-ai/hermeneutic && cd hermeneutic
pip install -e .
bash evals/self_test.sh
# PASS — gate correctly flagged the deliberately drift-shaped draft.
```

Then run `hermeneutic mine` against your own chat logs to bucket your distribution and see which rules apply most.

---

## Free, forever, MIT

`hermeneutic` is free and will stay free. No tier. No phoning home (the opt-in audit log is a local file, off by default). No auth wall. No "open core" bait.

It's part of the **Hermes Labs audit stack** - small, sharp, free OSS for teams shipping AI in production:

| Tool | Catches |
|---|---|
| [`scaffold-lint`](https://github.com/hermes-labs-ai/scaffold-lint) | Bad prompt structure (static) |
| [`hermes-rubric`](https://github.com/hermes-labs-ai/hermes-rubric) | Vibes-based scoring (evidence-first judge) |
| [`agent-convergence-scorer`](https://github.com/hermes-labs-ai/agent-convergence-scorer) | Multi-agent disagreement |
| [`hermes-seal`](https://github.com/hermes-labs-ai/hermes-seal) | Tampered or unverified artifacts |
| **`hermeneutic`** | **Drifted responses, before they ship** |

Static linters catch the prompt. `hermeneutic` catches the response. You get both. Free.

---

## Who this is for

- You ship an AI feature and your users say *"wait, are you sure?"* too often.
- You run agents and want a cheap pre-flight gate before responses go out.
- You build LLM apps and don't have time for another evaluation framework.
- You audit AI systems and want a tool that grounds in evidence, not vibes.

## When not to use it

- **Your AI never drifts.** If users don't push back on outputs, there's no signal to mine and the gate has nothing to enforce.
- **You need foresight, not memory.** The gate catches drift modes already corrected in your logs. Genuinely novel drift modes pass through silently until you re-mine.
- **You want aggregate model evaluation.** This scores individual outgoing drafts. For benchmarks, use a benchmark suite.
- **You expect it to replace human review.** It raises the floor on the worst drafts; the top of your distribution is unaffected.
- **You can't afford one extra LLM call on the ~10–20% of drafts that look risky.** Stage 1 (regex) is free; stage 3 (PressureProbe) costs one API call per gated draft.
- **Your sessions aren't in English.** The stage-1 regex rules match English surface patterns only. An overclaim written in Korean or Japanese passes stage 1 silently — confirmed by direct test, not a hypothetical. Multilingual enforcement is not shipped; treat non-English drafts as ungated.

---

## Docs

- [`docs/THEORY.md`](docs/THEORY.md) - why this works, and where it doesn't
- [`examples/before_after.md`](examples/before_after.md) - one drift caught and repaired, end-to-end
- [`AGENTS.md`](AGENTS.md) - how a coding agent should use this tool
- [`llms.txt`](llms.txt) - machine-readable summary

---

## License

MIT. Use it, fork it, ship it. If you build something interesting on top, [tell us](mailto:roli@hermes-labs.ai).

---

Built by [Hermes Labs](https://hermes-labs.ai). We make AI auditable.

## About Hermes Labs

Hermes Labs is building the reliability stack for the agent era — Epistemic Engineering: applied epistemology and hermeneutics for AI systems. The technical thesis: the model is the substrate, language is the operations layer; reliability is a question of linguistic infrastructure, not model tuning. hermeneutic is the overclaim gate in that stack. Founded by Rolando (Roli) Bosch.
