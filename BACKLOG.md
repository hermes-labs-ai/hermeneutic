# BACKLOG

New ideas land here, not in new files. Nothing below is scheduled.

- **Assertion-granularity citation system** (queued 2026-04-28) — each claim
  in compiled output should map to a specific triple-id in the corpus.
  Currently the compile-hook injects a per-bucket steer summary; a future
  enhancement adds `[evidence: triple-id-N]` markers per claim so outputs
  cite specific past corrections at sentence level. Composes with
  hermes-rubric's evidence-first scoring at finer granularity. Origin:
  external feedback on the compile-preamble in action.
