# Historical compile-layer walkthrough — measured cases on one real corpus

**Status: historical only.** This is the v0.1.5 demonstrative run captured against one author's local corpus on 2026-04-26. The original model/index artifact was not fully pinned, and the outputs do not establish current production-path retrieval quality. They are retained as dated provenance rather than a v0.1.7 headline.

**Honest framing first:** these are measured demonstrations, not validated effectiveness. They show the preamble *contains relevant prior signal*, not that it *causes* better LLM behavior in a controlled study. The latter is the v1.0 replay-eval milestone (mine N misinterpretation moments, replay each with-and-without the preamble injected, measure followup-correction reduction).

## Real corpus stats (measured 2026-04-26)

| Stat | Value |
|---|---|
| Source | `~/.claude/projects/<project-dir>/*.jsonl` (Claude Code session JSONL) |
| Sessions mined | 1,423 |
| Triples extracted | **346**¹ |
| Triples with `orig_prompt` (eligible for compile) | **346 (100%)** |
| Mining wall time | 2.4 seconds |
| Embedding model | `nomic-embed-text` via local Ollama |
| Index build wall time | **18.8 seconds** for 346 triples (= ~54ms per Ollama embed call, single-threaded loop) |

¹ 346 vs the 326 cited elsewhere: 326 was the 2026-04-25 gate-derivation run; 346 is the separate later frozen corpus used for retrieval evaluation. The available aggregate receipt does not prove an identical source window or attribute the 20-row difference solely to miner changes. Rule derivation receipts stay pinned to the 326-run.
| Embedding dimension | 768 |
| On-disk index size | ~5 MB JSON (vectors + ids + sha256 cache key) |

## Reproducing this walkthrough yourself

```bash
hermeneutic mine ~/.claude/projects/*/  --out ~/.hermeneutic/triples.jsonl
hermeneutic compile-index
echo "build me a thing" | hermeneutic compile
echo "fix the bug" | hermeneutic compile
echo "review this code" | hermeneutic compile
```

Your output will differ from the cases below — the preamble reflects *your* corpus. That's the point.

---

## Case 1 — short imperative ("build me a thing")

### What `compile` outputs (live, unedited)

```
$ echo "build me a thing" | hermeneutic compile

[hermeneutic compile-preamble — derived from 5 past corrections on similar prompts]
- 2 prior steer(s) in bucket `missed_constraint`: re-read prior turns + memory before assuming; the user often has standing instructions
- 2 prior steer(s) in bucket `over_confirmation`: execute when the user's intent is unambiguous; don't ask clarifying questions on imperative requests
- 1 prior steer(s) in bucket `tool_choice`: check the registered tool vault before reaching for ad-hoc bash
[end preamble]
```

### Reading

Top-5 nearest historical corrections cluster around three signals: the model historically (a) forgot standing instructions on this kind of vague imperative, (b) asked clarifying questions when the user wanted execution, (c) reached for ad-hoc bash instead of checking the registered tool vault. All three are real failure modes from the corpus, surfaced as priors before the model would have generated.

---

## Case 2 — bug-fix imperative ("fix the bug")

### What `compile` outputs (live, unedited)

```
$ echo "fix the bug" | hermeneutic compile

[hermeneutic compile-preamble — derived from 5 past corrections on similar prompts]
- 4 prior steer(s) in bucket `over_confirmation`: execute when the user's intent is unambiguous; don't ask clarifying questions on imperative requests
- 1 prior steer(s) in bucket `wrong_target`: if the user quoted a literal spec, use it verbatim; don't expand or substitute
[end preamble]
```

### Reading

Strong signal on `over_confirmation` (4 of 5 nearest matches) — the model historically asked for clarification on bug-fix imperatives instead of investigating the bug. The `wrong_target` bullet adds: when the user quotes a literal spec, use it verbatim — also a real corpus pattern.

---

## Case 3 — review request ("review this code")

### What `compile` outputs (live, unedited)

```
$ echo "review this code" | hermeneutic compile

[hermeneutic compile-preamble — derived from 5 past corrections on similar prompts]
- 2 prior steer(s) in bucket `missed_constraint`: re-read prior turns + memory before assuming; the user often has standing instructions
- 2 prior steer(s) in bucket `over_confirmation`: execute when the user's intent is unambiguous; don't ask clarifying questions on imperative requests
- 1 prior steer(s) in bucket `scope_creep`: do only what was asked; no volunteered orchestration or extra refactors
[end preamble]
```

### Reading

`scope_creep` shows up as a tail signal — historical reviews drifted into volunteered refactors that the user steered back to "just review, don't refactor." Plus the standing-imperative pattern (over_confirmation) and re-read-the-context pattern (missed_constraint) appear here too.

---

## Cross-case observation

Different prompt shapes get **measurably different** bucket distributions. The compile output is not a static template — the retrieval is doing real work. The same `over_confirmation` advice appears across all three (because short imperatives in this corpus consistently triggered "ask vs execute" steers), but each prompt also surfaces a unique secondary signal (`tool_choice` for "build", `wrong_target` for "fix", `scope_creep` for "review"). That's the signature of a working retrieval layer, not noise.

## What `compile` does NOT do

- **Does not guarantee the LLM follows the preamble.** It surfaces priors; whether the model uses them is the v1.0 measurement.
- **Does not understand semantic intent.** Retrieval is cosine similarity on input prompts — surface similarity, not deep intent matching.
- **May stay silent on novel prompt shapes, but is not guaranteed to.** A prompt below threshold produces no preamble; the separate historical synthetic-random experiment still triggered on 7/30 inputs, so this is not a false-positive guarantee.
- **Does not generate suggestions.** The preamble lists *patterns of past steers*; the LLM still chooses what to do.

## What we measure in v1.0 (the validation milestone)

- **Replay study:** N≥30 historical misinterpretation moments. For each, replay the original prompt twice (with-preamble vs without-preamble), run the next 1–3 LLM turns, count whether a correction was needed.
- **Primary metric:** correction-rate reduction. Pre-registered floor: ≥20% relative reduction to claim "compile helps."
- **Cost model:** report compute + latency overhead per prompt to make the trade-off explicit.

That milestone is gated on building the replay harness, which is multi-day work + compute spend. Not in v0.1.5.

## Historical wrapper-level smoke (unsupported Claude Code Stop adapter)

The v0.1.1 installer generated a Python wrapper that read a transcript path, walked the JSONL bottom-up, piped the recovered assistant text through `hermeneutic gate`, and wrote RISK to stderr. Current Claude Code instead supplies `last_assistant_message` and requires structured output for a visible warning, so this receipt is not evidence for a supported v0.1.7 Stop integration.

Verified end-to-end on 2026-04-26 against a real Claude Code transcript:

```bash
$ echo '{"transcript_path": "<real-session.jsonl>", "session_id": "smoke-test"}' \
    | python3 ~/.claude/hooks/hermeneutic-gate.py
[exit: 0]
```

The wrapper returned `PASS` on that recovered assistant turn and exited 0. The receipt proves only that the historical local wrapper parsed that transcript and invoked the gate; it did not exercise a RISK case or establish current-host warning visibility.
