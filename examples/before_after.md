# One deterministic drift check

This example exercises the default `hermeneutic gate` CLI. It does not use a private corpus, Ollama, `hermes-rubric`, `PressureProbe`, or a repair model.

## Draft

```text
Done — built 4 modules and shipped 26 tests, all green. The agents converged on a comprehensive solution. The implementation is production-ready.
```

## Command

```bash
printf '%s\n' 'Done — built 4 modules and shipped 26 tests, all green. The agents converged on a comprehensive solution. The implementation is production-ready.' \
  | hermeneutic gate
```

## Captured output

```text
RISK — highest severity: high
  [high] completion_with_number: 'Done — built 4'
    why: Completion verb co-occurs with a numeric claim — verify the number is tool-derived.
  [high] completion_with_number: 'shipped 26'
    why: Completion verb co-occurs with a numeric claim — verify the number is tool-derived.
  [high] completion_with_all_quantifier: 'Done — built 4 modules and shipped 26 tests, all'
    why: Completion claim with universal quantifier — confirm scope coverage.
  [high] number_then_completion: '4 modules and shipped'
    why: Numeric claim precedes a completion verb — verify the number is tool-derived.
  [high] number_then_completion: '26 tests, all green'
    why: Numeric claim precedes a completion verb — verify the number is tool-derived.
  [high] subagent_passthrough: 'agents converged'
    why: Subagent output summarized — confirm the subagent actually performed the action.
  [low] fluent_summary_no_evidence: 'comprehensive'
    why: High-fluency adjective with no measurable referent.
  [low] fluent_summary_no_evidence: 'production-ready'
    why: High-fluency adjective with no measurable referent.
```

The command exits `1` because at least one medium/high rule fired. It reports eight matches; overlapping completion rules are intentional and visible.

## What happens next

The CLI does not edit the draft. A human or calling application decides whether to warn, hold, or rewrite. A defensible rewrite would replace unsupported completion, count, sign-off, and quality claims with the exact artifacts or command output that establish them—or remove the claims when that evidence is absent.

The optional Python `Router` can call a caller-supplied critic and repairer, but that behavior must be configured explicitly. It is not the default CLI path, and v0.1.7 has not measured whether model-generated repairs reduce later misinterpretation.
