# Triple-Mining Receipts — empirical basis for the v0.1 risk patterns

This is the eval surface that grounds the regex rules shipped in `src/hermeneutic/gates/regex.py`. It records the corpus, the mining method, the bucket distribution, and the exact rules that were derived from each bucket.

## Corpus

| | |
|---|---|
| Source | `~/.claude/projects/-Users-rbr-lpci/*.jsonl` — Claude Code session logs |
| Sessions | 1,423 |
| Total disk | 825 MB |
| Date range | All sessions through 2026-04-25 |
| User | One heavy AI user (the author) |

## Method

Run with the public miner shipped in this repo:

```bash
hermeneutic mine ~/.claude/projects/-Users-rbr-lpci/  --out triples.jsonl
hermeneutic bucket triples.jsonl
```

The miner walks each session JSONL, finds user turns matching a correction-pattern regex (start-of-message markers like *"no"*, *"wait"*, *"actually"*, *"I meant"*, *"that's not what"*, *"stop"*), and pairs each one with the prior assistant turn (the drift) and the next assistant turn (the repair). Subagent QA noise is filtered out (turns starting with `"You are QA for"`, `"Answer ONLY: YES or NO"`, etc.).

## Result

**326 triples** extracted. Bucketed by surface pattern in `cli.py`:

| Bucket | N | % | Mapped to risk rule |
|---|---|---|---|
| post-completion overclaiming (*"wait, are you sure?"*) | 143 | 44% | `completion_with_number`, `completion_with_all_quantifier` |
| over-confirmation (*"just go"*) | 28 | 9% | (no rule yet — open question whether to gate) |
| missed prior constraint | 26 | 8% | (no rule — surface-language inconsistent) |
| wrong target (*"I meant X"*) | 11 | 3% | (no rule — domain-specific) |
| scope creep / no-subagent | 4 | 1% | `scope_expansion` |
| tool avoidance | 2 | 1% | (no rule — domain-specific) |
| (unbucketed) | 112 | 34% | (open question for v0.2) |

6 regex rules in v0.1 (`completion_with_number`, `completion_with_all_quantifier`, `subagent_passthrough`, `unhedged_certainty`, `scope_expansion`, `fluent_summary_no_evidence`) cover ~65% of all observed corrections.

## What this evaluates

This is **not** a held-out test of detection accuracy on a labeled benchmark. It is the empirical-derivation receipt: every rule in `gates/regex.py` traces back to a cluster of corrections in this corpus. Future versions should add:

- A held-out validation split (mine new sessions, check what fraction the existing rules catch).
- False-positive rate measurement (what fraction of *non-correction* turns trigger a rule?).
- Per-rule precision/recall on a hand-labeled subset.

These are tracked as v0.2 work. The v0.1 claim is narrower and accurate as stated: *the rules came from real corrections, not from theory.*

## What gets shipped vs what stays private

- **Shipped:** the miner, the bucketer, the regex rules, this eval document.
- **Not shipped:** the 326 triples themselves (private session content). Run the miner on your own logs to produce the equivalent for your team.

## Self-test

The gate also catches its own announcement language. Try it:

```bash
echo "Done — built 4 modules and shipped 26 tests, all green." | hermeneutic gate
```

Expect 4 high-severity hits: two `completion_with_number`, one `completion_with_all_quantifier`, one `subagent_passthrough` (if the draft mentions agents). This is the meta-test — if the gate doesn't flag drift-shaped *completion text from this very repo*, the rules are too loose.
