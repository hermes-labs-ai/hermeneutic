---
name: hermeneutic-gate
description: >-
  Run the hermeneutic deterministic English drift gate on an assistant draft
  before sending it when the draft contains numeric claims, completion language,
  universal quantifiers, or a summary of delegated work.
---

# Hermeneutic gate

Use the installed `hermeneutic` CLI as a cheap, zero-LLM pre-flight check for
assistant drafts. It catches fixed English surface patterns associated with
completion overclaiming, relayed authority, unhedged certainty, scope
expansion, and unsupported quality adjectives.

## Workflow

1. Identify the exact draft that is about to be sent.
2. Run `hermeneutic gate` with the draft on standard input, for example:

   ```bash
   printf '%s' "$DRAFT" | hermeneutic gate
   ```

3. Inspect the printed verdict as well as the exit code. A low-severity
   `RISK` is advisory and exits 0; medium- and high-severity `RISK` exits 1.
4. If the draft is held, add the missing evidence, hedge the claim, or remove
   the unverifiable text before sending it.

The gate is advisory and does not edit the draft or call an LLM. Do not treat a
pass as proof that a draft is correct, complete, safe, or free of novel drift.
It checks English surface patterns only and does not replace human review.

Use this skill especially when the draft contains numeric claims, says that
work is done or shipped, uses words such as “every” or “always”, or summarizes
work completed by another agent.
