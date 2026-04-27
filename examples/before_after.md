# One drift, caught and repaired

Real shape, sanitized. Watch the gate work end-to-end: draft in → 5 hits in zero milliseconds → PressureProbe verdict → repair → ship-ready output.

## Input

**User request:**
```
Build the bridge module and report what you got working.
```

**Assistant draft (before gate):**
```
Done — built 4 modules and shipped 26 tests, all green. The agents converged
on a comprehensive solution. The implementation is production-ready.
```

## Stage 1 — regex risk

```
$ echo "<draft>" | hermeneutic gate
RISK — highest severity: high
  [high] completion_with_number: 'Done — built 4'
  [high] completion_with_number: 'shipped 26'
  [high] completion_with_all_quantifier: 'Done — built 4 modules and shipped 26 tests, all'
  [high] subagent_passthrough: 'agents converged'
  [low]  fluent_summary_no_evidence: 'comprehensive'
  [low]  fluent_summary_no_evidence: 'production-ready'
```

Five hits. Three high-severity. The draft would not pass.

## Stage 3 — PressureProbe verdict

```
VERDICT: revise
REASON: Numeric claims ("4 modules", "26 tests") and "all green" lack tool-call provenance in the same turn; "agents converged" passes through subagent output without verification.
FLIP: Show the test runner output and the convergence-check command output.
```

## Repair pass output

```
Built the bridge module. Concretely:

  - bridge/router.py, bridge/probe.py, bridge/regex.py, bridge/triples.py — 4 files
  - 26 tests in tests/, all 26 passing on this run (output below)

  $ pytest tests/ -v | tail -3
  tests/test_triples.py::test_triple_to_json_roundtrip PASSED  [100%]
  ============================== 26 passed in 0.02s ==============================

The agent-convergence check ran with 3 reviewer subagents; their outputs are at
audit/convergence-2026-04-25.json. I have not independently verified each
subagent's claim — flag if you want me to spot-check.
```

## What just happened

- **5 surface tells caught** in ~0ms — zero LLM cost.
- Every numeric claim now carries **evidence**.
- *"Agents converged"* became an honest hedge with a pointer to the audit file and an offer to verify.
- *"Comprehensive"* and *"production-ready"* — gone. Fluency tells with no measurable referent.

The repaired draft is longer. It ships safer. The user can act on it without doing the verification work themselves.

**This is what `hermeneutic` does on every draft, every time, by default.**
