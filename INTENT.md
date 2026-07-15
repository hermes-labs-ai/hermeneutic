# Hermeneutic intent

Hermeneutic makes user corrections reusable without pretending that one mechanism does every job.

## Public surfaces

1. **Mine and bucket:** supported local chat logs become correction triples and aggregate categories.
2. **Compile and retrieve:** an optional local Ollama embedding index retrieves relevant prior corrections and renders a deterministic prompt preamble.
3. **Deterministic gate:** eight fixed English regex rules check outgoing text. Mining does not rewrite them.
4. **Programmable Router:** callers may compose the fixed gate with an optional `hermes-rubric` executable, a caller-supplied `PressureProbe`, and a caller-supplied repairer.
5. **Audit and review:** opt-in local telemetry plus harvest/review/promote mechanics create a reviewable correction loop.

## Accepts

- Transparent local evidence and deterministic behavior where possible.
- Personalization in the corpus and retrieval layer.
- Explicit caller ownership of blocking, external providers, repair policy, privacy, latency, and cost.
- New fixed gate rules only when a code change includes evidence, tests, and review.

## Refuses

- No claim that the gate writes itself.
- No claim that a `PASS` proves correctness or that a hook prevents every response.
- No multilingual claim; the fixed gate is English-only.
- No default model-evaluation, moderation, security-boundary, or factuality guarantee.
- No downstream-effectiveness claim without a direct measurement.

## Evidence boundary

The historical derivation receipt covers 326 corrections from 1,423 sessions belonging to one heavy user. A separate later frozen 346-triple corpus supports current aggregate gate and retrieval measurements, but neither corpus is a representative multi-user benchmark. Private triples are not distributed.

Current direct gate coverage on the frozen 346-triple corpus is 115/346 (33.24%). Current production-path same-bucket retrieval is 88/104 (84.6%) at CLI/hook defaults and 94/104 (90.4%) at Python defaults. These are single-corpus mechanism measurements, not precision, generalization, or evidence that a model follows the warning.

The project raises a review floor. Human and domain review remain responsible for the ceiling.
