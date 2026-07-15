# CLAUDE.md — working on hermeneutic

Read `AGENTS.md` first — it is the canonical in-session protocol for coding
agents using or modifying this repo, and everything there applies to Claude
Code sessions too.

Repo-specific rules for agents:

- **The core gate stays zero-LLM.** Never wire an LLM call into a default
  path. The optional compiler defaults to localhost Ollama; Python callers can
  override that URL, and caller-supplied Router components own their network
  and credential behavior.
- **Every behavior change gets a test**, and the full suite must stay green:
  `PYTHONPATH=src python -m pytest -q`. The README/CHANGELOG test count is
  enforced by `tests/test_docs_consistency.py` — update all surfaces together.
- **Never loosen an existing gate rule to silence a false positive.** Note it
  in the harvest queue instead; rule changes require mined evidence
  (see `evals/triple-mining-receipts.md` for the bar).
- **Honest partial progress is not drift** — don't "improve" recall by
  flagging "did X, but Y remains" (`_CONTRAST_GUARD` protects this; keep it).
- **Numbers in docs must trace to committed receipts** in `evals/`. No
  uncommitted benchmark claims.
- Lint with `ruff check src tests` before committing.

To verify a deployment of this tool in your own environment, run the
forward-deployed harness: `python3 forward-deployed/harness.py` (see
`FORWARD-DEPLOYED-HARNESS.md`).
