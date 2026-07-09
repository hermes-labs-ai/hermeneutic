# AGENTS.md — using hermeneutic from a coding agent

This file is for AI coding agents (Claude Code, Cursor, Cline, etc.) that want
to use `hermeneutic` as a tool.

## What this tool does

Pre-flight gate for assistant-generated drafts. Catches surface patterns
historically associated with user corrections (post-completion overclaiming,
subagent passthrough, unhedged certainty, scope expansion, fluency tells).

## When to invoke it

Run `hermeneutic gate` on any assistant draft *before* you send it to the user
when:

- The draft contains numeric claims (file counts, test counts, percentages, ms).
- The draft summarizes work completed by a subagent.
- The draft uses completion language ("done", "shipped", "all green").
- The draft contains universal quantifiers ("every", "all", "always").
- You want a cheap second-opinion gate that doesn't require an LLM call.

If `hermeneutic gate` returns nonzero, **do not ship the draft as-is**. Either:
1. Add the missing evidence (run the verification commands, paste the output).
2. Hedge the claim ("appears to" / "based on N samples").
3. Cut the unverifiable text.

## Programmatic use

```python
from hermeneutic import Router, PressureProbe

probe = PressureProbe(judge=your_llm_call)  # callable: prompt -> str

def repair(request, draft, reason):
    return your_llm_call(f"Revise: {reason}\n\n{draft}")

router = Router(probe=probe, repairer=repair)
result = router.gate(request=user_request, draft=your_draft)
if result.repaired:
    log(f"hermeneutic caught drift: {result.summary()}")
final = result.final_output
```

## Calibration

`PressureProbe` ships with a generic "rigorous-skeptic" calibration. To make it
match your team's standards, pass your own calibration text:

```python
my_calibration = """
You are reviewing drafts for a security-critical product.
Bias toward HOLD when:
- Any security claim lacks a CVE or vendor-confirmed citation.
- Code changes touch authentication or crypto without a test diff.
"""
probe = PressureProbe(judge=your_llm_call, calibration=my_calibration)
```

## Mining your own logs

To extend the regex gate, mine your own chat logs and look for new drift modes:

```bash
hermeneutic mine ~/your/log/dir --format claude-code --out triples.jsonl
hermeneutic bucket triples.jsonl
```

Then add new patterns to `src/hermeneutic/gates/regex.py`.

## What this tool is NOT

- Not a model evaluator. Scores individual drafts, not aggregate quality.
- Not foresight. Catches drift modes seen before; novel drifts pass through.
- Not a replacement for human review. It's a floor-raiser.
