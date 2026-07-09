# Compile-layer walkthrough — measured cases on a real corpus

This is the v0.1.5 demonstrative eval. **All numbers below are measured, not illustrative** — captured by running `hermeneutic compile-index` and `hermeneutic compile` against the author's actual mining corpus on 2026-04-26.

**Honest framing first:** these are measured demonstrations, not validated effectiveness. They show the preamble *contains relevant prior signal*, not that it *causes* better LLM behavior in a controlled study. The latter is the v0.2.0 replay-eval milestone (mine N misinterpretation moments, replay each with-and-without the preamble injected, measure followup-correction reduction).

## Real corpus stats (measured 2026-04-26)

| Stat | Value |
|---|---|
| Source | `~/.claude/projects/-Users-rbr-lpci/*.jsonl` (Claude Code session JSONL) |
| Sessions mined | 1,423 |
| Triples extracted | **346** |
| Triples with `orig_prompt` (eligible for compile) | **346 (100%)** |
| Mining wall time | 2.4 seconds |
| Embedding model | `nomic-embed-text` via local Ollama |
| Index build wall time | **18.8 seconds** for 346 triples (= ~54ms per Ollama embed call, single-threaded loop) |
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

- **Does not guarantee the LLM follows the preamble.** It surfaces priors; whether the model uses them is the v0.2.0 measurement.
- **Does not understand semantic intent.** Retrieval is cosine similarity on input prompts — surface similarity, not deep intent matching.
- **Does not work on novel prompt shapes.** If a user asks something the corpus has never seen, the preamble is empty (silent skip — no false-positive injection).
- **Does not generate suggestions.** The preamble lists *patterns of past steers*; the LLM still chooses what to do.

## What we measure in v0.2.0 (the validation milestone)

- **Replay study:** N≥30 historical misinterpretation moments. For each, replay the original prompt twice (with-preamble vs without-preamble), run the next 1–3 LLM turns, count whether a correction was needed.
- **Primary metric:** correction-rate reduction. Pre-registered floor: ≥20% relative reduction to claim "compile helps."
- **Cost model:** report compute + latency overhead per prompt to make the trade-off explicit.

That milestone is gated on building the replay harness, which is multi-day work + compute spend. Not in v0.1.5.

## Wrapper-level smoke test (Claude Code Stop hook integration)

The v0.1.1 install-hook generates a Python wrapper that reads Claude Code's Stop hook stdin JSON, walks the transcript JSONL bottom-up to find the last assistant turn, pipes that text through `hermeneutic gate`, and surfaces RISK to stderr.

Verified end-to-end on 2026-04-26 against a real Claude Code transcript:

```bash
$ echo '{"transcript_path": "<real-session.jsonl>", "session_id": "smoke-test"}' \
    | python3 ~/.claude/hooks/hermeneutic-gate.py
[exit: 0]
```

Gate returned `PASS` on the last assistant turn (no completion-claim drift in that specific turn), so no stderr notice surfaced — exactly the advisory-mode contract. When the gate fires on a drift-shaped turn, the wrapper writes one `[hermeneutic] RISK — high ...` line to stderr and Claude Code surfaces it in the UI.
