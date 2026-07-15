# FORWARD-DEPLOYED HARNESS — instructions for the agent that executes it

**This file is the instructions. The harness itself is executable** —
`forward-deployed/harness.py`, a deterministic step-machine that drives the
mission and verifies each step from artifacts before the next unlocks. You
read this once for context; you RUN the harness.

You are an agent reading this inside the adopter's environment — an
environment the author of this package cannot see and deliberately never
will. Read this whole file before acting. When you finish it, you are the
**forward-deployed engineer** for hermeneutic here: verify that it works in
this harness, adapt it where it doesn't, and leave behind a sanitized report
of what you did. You know this environment better than the author ever
could — that asymmetry is the design, not a workaround.

## The concept (60 seconds)

Every chat log contains a discarded dataset: the moments the user corrected
the assistant — *"no, not that"*, *"still crashes"*, *"I said MySQL"*. Each
correction marks a drift: the assistant did Y when asked for X, did half and
called it done, or overclaimed ("Done — 14 files, all green") without the
receipts. hermeneutic mines those corrections into `(drift, steer, repair)`
triples and uses them twice:

1. **The gate** (`hermeneutic gate`) — a zero-LLM regex tripwire run on
   outgoing drafts. It catches announcement-shaped drift modes with a local,
   deterministic regex pass; every fire is explainable. It is a floor, not a
   guarantee.
2. **The compile layer** (`hermeneutic compile`) — optionally retrieves past
   corrections similar to the incoming prompt and prints a "watch out for X"
   preamble for a caller or supported context hook to inject.

## The map (what lives where)

| Path | What it is |
|---|---|
| `src/hermeneutic/gates/regex.py` | the 8 canonical rules — the gate itself |
| `src/hermeneutic/triples.py` | log readers (`claude-code`, `codex`, `openai` — registered in `READERS`) + the miner |
| `src/hermeneutic/harvest.py` | replay-classify loop (`confirmed_catch` / `possible_false_positive` / `missed_drift`), `promote`, sanitized output |
| `src/hermeneutic/compile.py` | embeddings (local Ollama, `nomic-embed-text`) + preamble builder |
| `src/hermeneutic/cli.py` | every command |
| `evals/` | self-test, current bounded receipts, and clearly labeled historical experiments |
| `tests/` | the suite — `python -m pytest -q` must stay green |
| `AGENTS.md` | the in-session protocol; meant to be copied into the human's own projects' `AGENTS.md` |

## Invariants — never break these, whatever you change

1. **The core gate stays zero-LLM.** Deterministic and local, every fire
   explainable by pointing at a rule and matched text. No LLM call on any
   default path, ever.
2. **Privacy is structural.** Nothing leaves this machine by default.
   Anything labeled sanitized carries zero message text — counts, rule ids,
   timestamps, hashes, lengths only. That is data minimization, not proof of
   anonymity; a human reviews the metadata before sharing it.
3. **Tense is load-bearing** in the rules: past-tense completion claims
   gate, planned future work does not. Naive stemming destroys the
   distinction.
4. **Honest partial progress is not drift.** Never "improve" recall by
   flagging "did X, but Y remains".
5. **Fail loud.** Zero-parse must exit 2 with an explanation, never emit
   silent zero output.
6. **Tests and evals gate every change.** The full suite green after every
   edit; every behavior you add gets a test.

## THE PROTOCOL — the harness drives, you execute

The mission is not self-reported. It is driven by a step-machine:

```bash
python3 forward-deployed/harness.py
```

Run it. Do exactly what it prints. Run it again. Repeat until it prints
**MISSION COMPLETE** with an attestation hash. Each step (ENV → BOOT →
HARVEST → REPORT → GATE) is verified mechanically from artifacts on disk
before the next unlocks — described-but-not-done work does not advance the
mission. Progress is a hash chain in `forward-deployed/mission-state.json`
(`python3 forward-deployed/harness.py verify` audits it). Honest scope: the
chain is tamper-evident against sloppy or accidental edits, not cryptographic
proof — a determined forger can recompute it. The attestation is a receipt
that disciplined work happened in order; what your human reviews and sends
is the report and artifacts, not the hash alone.

The sections below are your reference material for the steps the harness
will hand you.

## BOOT — what the harness runs first (~2 minutes)

```bash
python3 -m pip install -e '.[dev]'       # once — pytest ships in the dev extra, boot needs it
python3 forward-deployed/boot.py         # add --sessions DIR --format X if logs live elsewhere
```

It runs the whole verification sequence — test suite, gate self-test, the
gate smoke trio against documented expectations, and a
sanitized harvest probe over real logs — and writes
`forward-deployed/boot-report.json` (sanitized by construction; out-of-repo
paths are stripped before anything is stored). **Exit 0 / `fits-as-shipped`:**
all package-controlled checks passed; if no matching logs existed, the
real-log probe is labeled `not_exercised` rather than fabricated as a pass.
Tell your human, run the real sanitized harvest for them — write it to the
gitignored `build/` dir (e.g. `--out build/report.jsonl`) so the tree stays
pristine, and leave `promote` to your human unless they ask — then write the
report (below). **Exit 1 / `adaptation-needed`:** the failed steps are your work
queue, in the order they appear.

Manual equivalents, when you need to investigate a failure directly:

```bash
python3 -m pytest -q                     # expect: all green, 0 failed
bash evals/self_test.sh                  # expect: PASS
echo "Done — shipped 14 files, all tests pass." | hermeneutic gate            # → RISK
echo "Fixed 3 of the 14 failing tests; 11 still fail." | hermeneutic gate     # → PASS (honest partial progress)
echo "I will ship the remaining files tomorrow." | hermeneutic gate           # → PASS (a plan is not a claim)
hermeneutic harvest ~/.claude/projects --format claude-code --sanitized --out /tmp/hh-probe.jsonl
```

## Permitted adaptations (most likely first)

- **A. Log format mismatch** (harvest says ZERO EVENTS on real logs):
  subclass `LogReader` in `triples.py`, register it in `READERS`. Verify
  against ONE real session file, then add a test using synthetic fixture
  data only — never commit real log content.
- **B. Rule gaps** (drift your human corrects that the gate misses): add a
  bounded-window rule to `gates/regex.py` following the existing tuple
  pattern, with the mined evidence that justifies it and a test. Add rules,
  never loosen existing ones.
- **C. Correction-marker gaps** (real corrections invisible to the miner):
  extend the correction markers in `triples.py` the same way.
- **D. Path and layout differences**: prefer `--glob` flags over code edits.
- **E. Architectural adaptation**: allowed when A–D don't fit, if every
  invariant holds and tests + evals stay green. Prefer additive changes
  behind a flag. You are expected to harden this beyond what its author
  could do blind — that is the assignment, not an exception.

**Do not**: wire an LLM into a default path; weaken completion rules
globally to silence a known false-fire (note occurrences in your report
instead — rule changes need their own mined evidence); put any session
text, out-of-repo path, or personal identifier in anything you commit or
report.

## The report you leave behind

Copy `forward-deployed/REPORT-TEMPLATE.md` to `FORWARD-DEPLOYED-REPORT.md`
at the repo root and fill it in. It is sanitized by the same rule as
`--sanitized`: **counts, categories, and this repo's own code — never your
human's text.** The linter checks common leak shapes (paths, identifiers, long
quotes, long Hangul runs); it is deliberately not presented as an exhaustive
privacy or anonymity check. English prose and organization-specific identifiers
may evade it, so human review completes the process. Before handing the report over, run it and
resolve every flag:

```bash
python3 forward-deployed/check_report.py FORWARD-DEPLOYED-REPORT.md   # must print CLEAN
```

Structure:

1. **Environment** (categories only): OS family, Python `x.y`, package
   version, agent CLI + version (Claude Code / Codex / other).
2. **Boot results**: pass/fail per step; for failures, exception type +
   message with every out-of-repo path stripped.
3. **Adaptations**: per change — file, one-sentence reason (no session
   content), the diff of THIS repo's code, tests added, and
   `pytest` numbers before and after.
4. **Observed but not fixed**: known-false-fire counts, missed-drift shapes
   described generically ("uncommon completion verb, casual register") —
   never quoted.
5. **Open questions** for the author.

Your human reviews the report and sends it to roli@hermes-labs.ai. Nothing
sends itself; you have no network duties.

## Definition of package-controlled completion

The harness can establish that its package-controlled checks completed; it
cannot by itself establish that Hermeneutic is deployed and working on real
adopter logs. `gate.py` exit 0 closes the local verification chain with an
attestation:

```bash
python3 forward-deployed/gate.py       # exit 0 = package-controlled checks complete
python3 forward-deployed/harness.py    # advances to MISSION COMPLETE + attestation
```

It deterministically checks: boot evidence fresh and `fits-as-shipped`,
the test suite green **in this environment**, the zero-LLM and privacy
invariants mechanically intact, and the report present and
`check_report.py`-CLEAN — always: "no adaptations needed" is a valid report,
a skipped one is not. If the gate says NOT DONE, it lists
exactly what's missing; finish that, don't argue with it. Treat `MISSION
COMPLETE` as the harness's internal completion state. A live deployment claim
additionally needs a human-reviewed real-log/adopter receipt; `not_exercised`
is never evidence of live fit. (Yes: the drift gate ships with a drift gate for
its own verification chain.)

## Runtime sentinel (optional, human-consented)

After MISSION COMPLETE, offer your human one more layer — enforcement that
lives inside Codex's own loop, via its native `notify` (turn-ended) hook:

```bash
python3 forward-deployed/sentinel.py install     # reversible: sentinel.py uninstall
```

While any future mission is incomplete, a turn that *sounds* finished
triggers a desktop nudge ("harness says NOT DONE — next step: X"); and every
turn's last message is live-gated (zero-LLM, advisory — rule
ids only, never text). Install REFUSES if another notify hook exists (it
prints how to compose them by hand) and backs the config up first. This is
an explicit human decision — never install it silently.

## Escalation

If BOOT fails at the test suite or self-test stage, the defect is in the
package, not your environment: stop adapting, produce the diagnostic block
from `AGENTS.md` ("If something doesn't fit this harness") plus the report,
and have your human send both. That is a bug on the author's side and gets
fixed at the source.
