# Theory and design boundary

## Corrections are useful evidence

When a user corrects an assistant, the surrounding turns form a compact local record:

```text
(original prompt, prior assistant reply, user correction, next assistant reply)
```

Hermeneutic calls this a correction triple. A collection of triples can show recurring correction categories and provide examples to retrieve when a similar prompt appears later. The user is evidence about what was unacceptable in that interaction—not an infallible oracle about every factual claim.

## Three mechanisms, not one learning gate

Hermeneutic keeps three mechanisms separate:

1. **Mining** uses fixed readers and correction markers to produce triples.
2. **Retrieval** uses optional local embeddings to select relevant prior corrections and a deterministic template to render context.
3. **The gate** uses eight fixed English regex rules over an outgoing draft.

Personal data changes the first two results. It does not generate new regex rules. That separation keeps the default gate cheap, inspectable, and testable while allowing the local evidence corpus to evolve.

## Why keep a deterministic stage

Surface checks can cheaply flag a small set of recurring shapes: numeric completion claims, universal quantifiers, relayed authority, unhedged certainty, scope expansion, and unsupported quality adjectives. They need no model or network call and produce exact rule IDs and match spans.

The trade-off is substantial. Regexes cannot determine whether a claim is true, can miss semantic drift, and can fire on harmless language. The fixed contrast guard handles one known partial-progress shape, but it is not a general semantic parser.

The current direct measurement illustrates the boundary: the eight-rule gate fires on 115/346 (33.24%) prior assistant replies in the available correction corpus. Because this is a correction-only retrospective derivation-set run involved in development, it is neither held-out recall nor a precision estimate.

## Why optional retrieval exists

A fixed gate cannot encode every user's standing instructions or domain-specific corrections. The compile layer retrieves warnings from the user's own corpus instead. It embeds the original prompt, selects up to two matches per correction bucket above a threshold, applies a global cap, and renders category advice without a generation call.

The current production-path leave-one-out measurement finds the held-out correction's category in 88/104 prompts at CLI/hook defaults and 94/104 at Python-library defaults. That demonstrates selection behavior on one frozen corpus and index. It does not show that another user's corpus behaves the same or that a model follows the injected context.

## Why the Router is separate

Some applications need semantic review or repair. The Python `Router` can conditionally compose:

```text
draft → fixed regex stage
            ↓ when configured threshold fires
        optional hermes-rubric
            ↓ when configured and not passed
        optional caller-supplied PressureProbe
            ↓ revise/hold, if caller supplied one
        optional caller-supplied repairer
```

This is a library construction, not the `hermeneutic gate` CLI. External stages introduce provider-specific latency, cost, privacy, and failure modes. The caller chooses the backend and decides whether a `GateResult` warns, holds, replaces, or sends a draft.

## The review loop

Opt-in telemetry records gate and compile events locally. Harvest replays the current fixed gate over supported logs and creates three review categories:

- `confirmed_catch`: gate fired and the next user turn was correction-shaped;
- `possible_false_positive`: gate fired and the next user turn was not correction-shaped;
- `missed_drift`: the next user turn was correction-shaped and the gate stayed silent.

A human accepts or rejects queue rows. Promotion appends accepted correction-bearing rows to the triples corpus, where they can affect later retrieval after re-indexing. It does not automatically add or tune gate rules.

## Evidence and open questions

The original derivation receipt covers one heavy user's 1,423 sessions and 326 corrections. The private triples are not shipped. A separate later frozen 346-triple corpus and embedding index support aggregate current measurements, but do not constitute a representative benchmark.

Open questions include:

- precision and false-positive rate on a bounded ordinary-prompt set;
- generalization across users and domains;
- stable embedding reproduction with a pinned model artifact;
- whether retrieved warnings reduce downstream model misinterpretation;
- whether a repair should be gated again before a caller accepts it.

Until those are measured, Hermeneutic should be treated as a transparent review aid, not a reliability guarantee.
