---
name: hermeneutic
description: Use when an AI agent's draft response needs a pre-flight check for completion overclaiming, unsupported numeric claims, relayed authority, or unhedged certainty before it ships — or when past chat-log corrections should carry forward into a similar task. Deterministic, offline, zero-LLM gate plus a corrections-memory layer.
license: Apache-2.0
compatibility: Requires Python 3.10+; installs via `pip install hermeneutic`. Runs fully offline with zero model calls and zero dependencies.
---

# Hermeneutic

Hermeneutic mines corrections already present in an AI agent's chat logs to
catch recurring drift and overclaiming before the next response ships. It is
a cheap-to-expensive pre-flight gate (regex, then structured scoring, then a
pressure probe) plus a memory layer that carries past corrections into
similar future tasks. Zero LLM calls, zero network calls, zero dependencies.

## Use it for

- Gating an outgoing draft for completion overclaiming ("shipped 14 files,
  all tests pass" with no evidence), unsupported universal quantifiers, or
  unhedged certainty before it is sent
- Carrying forward a prior human correction (from `assistant output → user
  correction → repaired output` traces already in chat logs) into a similar
  later task so the same mistake is not repeated
- Running a deterministic, offline second-opinion check on an
  assistant-generated English draft

## Do not use it for

- Formal security guarantees or audited benchmark comparisons
- Replacing runtime containment or outbound tool controls
- Proving a model's underlying claim is factually true — it flags surface
  shapes (overclaiming, unhedged certainty, relayed authority), not ground
  truth

## Quickstart

```bash
pip install hermeneutic==0.1.12
printf '%s\n' 'Done — shipped 14 files, all tests pass.' | hermeneutic gate
```

The command above exits `1`, flagging the completion claim and the universal
quantifier.

## Output shape

- `hermeneutic memory`: retrieves relevant prior corrections for a similar
  task
- `hermeneutic gate`: checks an outgoing draft against corrections and
  epistemic-risk patterns, exits `PASS` or `RISK`
- Low-severity `RISK` findings are advisory (exit 0); medium/high `RISK`
  exits 1

## Common gotchas

- Hermeneutic flags surface patterns (overclaiming, missing evidence,
  hedging gaps) — it does not verify the underlying factual claim.
- It is not a runtime evaluator or a dynamic agent test; it operates on a
  single draft or a chat-log trace, offline.
- If it flags a claim, add direct evidence, hedge the claim, or remove the
  unverifiable wording — do not silently rewrite around the gate.

## More

Full docs and CLI reference: https://github.com/hermes-labs-ai/hermeneutic
