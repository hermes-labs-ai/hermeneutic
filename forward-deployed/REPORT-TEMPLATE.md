# FORWARD-DEPLOYED REPORT

<!-- Copy this file to the repo root as FORWARD-DEPLOYED-REPORT.md and fill
     it in. Sanitization rule, enforced by forward-deployed/check_report.py:
     counts, categories, and THIS repo's own code — never the human's text,
     paths, or identifiers. Only ~/.hermeneutic and ~/.codex/sessions may
     appear literally (they are this package's documented defaults);
     describe every other location generically ("the project workspace"). -->

## 1. Environment (categories only)

- OS family:
- Python:
- hermeneutic version:
- Codex CLI version:

## 2. Boot results

<!-- paste the "steps" summary from forward-deployed/boot-report.json -->

| step | status | detail |
|---|---|---|
|  |  |  |

## 3. Adaptations made

<!-- one block per change; diffs of THIS repo's code only.
     No adaptations? Write "None — fits as shipped." and delete the example
     block below. -->

### <file changed> — <one-sentence reason, no session content>

```diff
```

- tests added:
- pytest before/after:
- pytest count before/after (if rules changed):

## 4. Observed but not fixed

<!-- e.g. "known partial-progress false-fire shape: N occurrences over M
     sessions" — counts and generic shape descriptions, never quotes -->

## 5. Open questions for the author

## Send checklist (human)

- [ ] `python3 forward-deployed/check_report.py FORWARD-DEPLOYED-REPORT.md` → CLEAN
- [ ] manually review for organization-specific names, endpoints, identifiers,
      and sensitive metadata the bounded linter may not recognize
- [ ] send to roli@hermes-labs.ai
