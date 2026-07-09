# Theory

## Why mining corrections works

Every assistant turn that ends with the user saying "wait, are you sure?" or "no, that's not what I meant" is a labeled training example. The user is the oracle, the prior assistant turn is the model's drift, and the next assistant turn is the corrected version. We have:

```
(prior_assistant, user_correction, next_assistant)
   = (drift, steer, repair)
```

Most teams throw these away. They're a free, high-signal dataset of *exactly the things this user / team / domain considers wrong*.

## Why a regex stage works

When you actually look at 326 corrections from 1,423 sessions, the surface patterns repeat heavily:

- **143 / 326 (44%)** open with "wait, are you sure" or similar epistemic-check phrasing — and the prior assistant turn almost always contains a confident completion claim with a number.
- **26 / 326** are missed-prior-constraint corrections.
- **28 / 326** are over-confirmation corrections ("just go").
- **11 / 326** are wrong-target corrections quoting a literal spec.

The drift modes are loud and few. A handful of regexes catch most of them. Stage 1 is correct *most of the time* not because regex is smart, but because human steers cluster on a small number of failure modes.

## Why three stages instead of one LLM call

LLM-as-judge is expensive and slow. Running it on every assistant turn costs 1 API call per response — at scale that doubles your inference bill. Most drafts are fine. The 3-stage gate runs the cheap stage on everything and the expensive stage only on the ~10–20% that look risky.

```
draft → regex (~0ms) → most ship here
              ↓ if hit
         rubric (1 local call) → many ship here
              ↓ if fail
         twin (1 API call) → most ship, some revise
```

Cost amortizes across thousands of drafts, not per-draft.

## Why "ship the role, keep the priors"

A reviewer-twin's value comes from two layers:
- **Architecture** — forces structured output (verdict + evidence + flip-condition).
- **Calibration** — encodes a specific reviewer's red flags, severity rules, fluency-distrust.

The architecture is generic and ship-publishable. The calibration is what makes the twin specifically *yours* and is your edge — keep it private.

A user with poor epistemic hygiene who deploys `PressureProbe` with the default calibration still gets value from the architecture: they can't game *"what would falsify this?"* by being lazy. The structure does some work even when the priors are generic. They just don't get *your* priors.

## What this is not

**Not foresight.** The gate catches drift modes you've already seen corrected. Novel drifts pass through silently until you re-mine.

**Not a model evaluator.** It scores individual outgoing drafts, not aggregate model quality. A model that scores high on benchmarks can still produce drift-shaped drafts.

**Not a replacement for human review.** It's a floor-raiser — it lifts the worst drafts out of the bottom of the distribution. The top of the distribution is unaffected.

## When this approach degrades

- **Your domain rotates fast.** If users complain about new things every week, the regex stage gets stale quickly. Re-mine monthly, or rely more on the PressureProbe stage.
- **Your users are mostly silent.** If users don't push back when the model drifts (they just leave), there's no signal to mine. The gate degrades to whatever the default rules catch.
- **Your drift is structural, not surface.** If your model gives wrong answers in fluent, well-formatted, evidence-cited prose, the regex stage misses entirely. Stage 3 (LLM critic) is your only line.

## Open questions

- **Embedding-clustered patterns.** Do the 112 unbucketed corrections in the 326-triple study cluster into modes the regex stage doesn't catch? (Tentative answer: yes, but the clusters are domain-specific factual corrections — harder to generalize across users.)
- **Repair quality.** A one-shot repair pass sometimes produces a draft that itself triggers the gate. Should the router re-gate after repair? (Open.)
- **Calibration drift.** Does PressureProbe with a specific calibration become *more* aligned with that calibration over time, or does it stay anchored to the model's pretraining? Untested.
