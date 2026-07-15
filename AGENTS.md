# AGENTS.md — using hermeneutic from a coding agent

This file is for AI coding agents and host applications that want to call the
standalone `hermeneutic` CLI or Python library.

## What this tool does

A fixed deterministic English drift check for assistant-generated drafts. It
flags eight surface shapes including completion overclaiming, relayed authority,
unhedged certainty, scope expansion, and unsupported quality adjectives. It
does not read the personal correction corpus or run the optional Router.

## When to invoke it

Run `hermeneutic gate` on any assistant draft *before* you send it to the user
when:

- The draft contains numeric claims (file counts, test counts, percentages, ms).
- The draft summarizes work completed by a subagent.
- The draft uses completion language ("done", "shipped", "all green").
- The draft contains universal quantifiers ("every", "all", "always").
- You want a cheap second-opinion gate that doesn't require an LLM call.

Inspect the printed verdict as well as the exit code: low-severity `RISK` is
advisory and exits 0; medium/high `RISK` exits 1. A caller that chooses to hold a
draft should either:
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

Mine your own chat logs to build a personal corpus and look for candidate drift
modes:

```bash
hermeneutic mine ~/your/log/dir --format claude-code --out triples.jsonl
hermeneutic bucket triples.jsonl
```

Mining does not change the gate. A developer may deliberately add a new pattern
to `src/hermeneutic/gates/regex.py` only with evidence, tests, review, and a new
release. The personal corpus can affect optional compile retrieval after
`compile-index` is rerun.

## What this tool is NOT

- Not a model evaluator. Scores individual drafts, not aggregate quality.
- Not foresight. Catches drift modes seen before; novel drifts pass through.
- Not a replacement for human review. It's a floor-raiser.
- Not multilingual. The fixed rules check English surface patterns.
- Not proof that a caller's external Router backends or repair behavior are safe.
