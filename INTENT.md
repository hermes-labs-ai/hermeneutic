# hermeneutic — Intent

Catches drift in outgoing assistant drafts before it ships, using the corrections you've already made as the training signal. Two-loop architecture: a miner that turns chat-log corrections into `(drift, steer, repair)` triples, and a router that runs those patterns as a 3-stage pre-flight gate (zero-LLM regex → optional rubric → generic LLM critic with bring-your-own-calibration).

## Accepts

- Mines `(prior_assistant, user_correction, next_assistant)` triples from any chat-log directory (Claude Code JSONL, OpenAI ChatCompletion JSON; pluggable via `LogReader` subclass).
- Runs a 3-stage gate on outgoing drafts: stage 1 zero-LLM regex (~0ms, evidence-derived patterns), stage 2 optional `hermes-rubric` adapter, stage 3 `PressureProbe` (LLM-as-critic with bring-your-own calibration).
- Returns a structured `GateResult` audit trail: which stage shipped the draft, which risk patterns matched, the LLM verdict, and whether a repair pass ran.
- Treats the architecture as public and the calibration as private — `PressureProbe` is BYO, the default `rigorous-skeptic` calibration is generic and replaceable.

## Refuses

- No new drift detection beyond patterns mined from real corrections. Risk regexes ship with empirical justification (the 326-triple study) — extension PRs require the contributor to provide their own mined evidence.
- No model evaluation. Scores individual outgoing drafts, not aggregate model quality.
- No replacement for human review. The gate raises the floor; it does not raise the ceiling.
- No silent foresight claim. The gate catches drift modes already seen corrected; novel drifts pass through until you re-mine.

## Three guarantees

1. **Stage 1 is cheap.** Risk regex runs in ~0ms per draft. Most outputs pass through stage 1 untouched. Stage 2 and 3 fire only on drafts that match a high-severity pattern.
2. **Calibration is replaceable.** `PressureProbe(judge, calibration)` accepts any callable LLM and any calibration string. The architecture forces structured output (verdict + flip-condition + evidence pointer) regardless of who supplies the priors.
3. **The audit trail is the product.** Every `GateResult` records: matched risk hits, rubric score (if used), twin verdict (if used), whether a repair fired, and the original draft alongside the final output. Persist this and you have a labeled dataset of (gate fired, was it right?) — that is how the gate gets smarter without architectural changes.

## Provenance

Risk patterns derived empirically from one heavy AI user's corpus: 1,423 Claude Code sessions mined for 326 user corrections. 44% of corrections were post-completion overclaiming (the dominant drift mode). 8 regex rules cover ~65% of the corpus. Your distribution will look different — re-mine your own logs and `your` gate writes itself.

The 326 triples themselves are not shipped (private session content). The miner that produces equivalent triples from your own logs is shipped, and is the entire point.
