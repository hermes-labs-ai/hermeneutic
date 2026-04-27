# hermeneutic

**Your AI overclaims. You correct it. Now your AI gets gated.**

> Mined 326 corrections across 1,423 chat sessions. 44% were post-completion overclaiming — the dominant drift mode. 5 regex rules now catch ~65% of that distribution before the next response ships. Three stages, fail-cheap to fail-expensive. Free, MIT, zero dependencies.

[![tests](https://img.shields.io/badge/tests-26%20passing-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hermes Labs](https://img.shields.io/badge/by-Hermes%20Labs-black)](https://hermes-labs.ai)

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
pip install hermeneutic

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

Your AI was about to overclaim. It can't anymore.

---

## What you actually get

| | |
|---|---|
| **Mine** | Walk any chat-log directory (Claude Code, OpenAI), extract correction triples |
| **Bucket** | See your AI's actual drift modes — not what someone else thinks they are |
| **Gate** | Run the 3-stage pre-flight on any outgoing draft |
| **Library** | Full Python API. Plug into your pipeline in 4 lines. |

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

1. **The role** — a critic that forces structured output: verdict + flip-condition + evidence pointer
2. **The priors** — *whose* judgment, *what* red flags, *what* severity calibration

We ship the role as `PressureProbe`. You bring your own calibration. **The architecture does the work even when the calibration is generic** — your users can't game *"what would falsify this?"* by being lazy.

| Audience | What you do | What you get |
|---|---|---|
| **Solo dev** | Use the default rigorous-skeptic prior | Instant gate on your AI's worst drafts |
| **Team** | Drop in your own calibration text | Codified house style, every commit |
| **Enterprise** | Swap in your domain priors (security, medical, legal) | Private calibration, public-tested architecture, ship to every team |

One library. Every audience.

### Extensibility

Both pluggable surfaces are `typing.Protocol` interfaces — no subclassing required, no framework lock-in:

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

Default judge calibration is `rigorous-skeptic`; default readers cover Claude Code JSONL and OpenAI ChatCompletion JSON.

---

## The receipts

This isn't a thought experiment. The risk patterns ship with `hermeneutic` because we mined a real corpus first:

- **1,423 sessions** of one heavy AI user
- **326 corrections** extracted as `(drift, steer, repair)` triples
- **44%** were post-completion overclaiming — the dominant drift mode
- **5 regex rules** cover ~65% of the corpus

Every pattern in `gates/regex.py` traces to corrections caught in the wild. **Your distribution will look different — that's the point.** Run the miner on your own logs and *your* gate writes itself.

---

## Free, forever, MIT

`hermeneutic` is free and will stay free. No tier. No telemetry. No auth wall. No "open core" bait.

It's part of the **Hermes Labs audit stack** — small, sharp, free OSS for teams shipping AI in production:

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

---

## Docs

- [`docs/THEORY.md`](docs/THEORY.md) — why this works, and where it doesn't
- [`examples/before_after.md`](examples/before_after.md) — one drift caught and repaired, end-to-end
- [`AGENTS.md`](AGENTS.md) — how a coding agent should use this tool
- [`llms.txt`](llms.txt) — machine-readable summary

---

## License

MIT. Use it, fork it, ship it. If you build something interesting on top, [tell us](mailto:rbosch@lpci.ai).

---

Built by [Hermes Labs](https://hermes-labs.ai). We make AI auditable.
