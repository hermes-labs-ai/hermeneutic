# Experimental language adapters: synthetic validation

Run from a source checkout with Python 3.10+:

```bash
python evals/languages/run.py
python evals/languages/run.py --write
```

The first command reports counts. The second regenerates `results.json` from
the current implementation and fixtures. The test suite checks exact equality
with a fresh replay, including SHA-256 hashes of every adapter, the unchanged
English gate, the runner, each corpus, and `review-cases.json`. Results become
stale after an input or implementation changes; regenerate them deliberately after validation.

## Method and provenance

Korean uses draft fields from the prototype's nine frozen synthetic corpora,
originally generated with an LLM on 2026-07-08. `ko.json` preserves draft text,
labels, shape labels, and batch identity. It contains no real chat records or
user correction logs. The original Korean normalization table is ported; the
public adapter additionally maps contrast and remainder wording into the
English gate's existing partial-progress guard. That changes false fires and
means the prototype's original validation numbers should not be carried forward
as this implementation's result. The current replay is authoritative here.

The other seven languages use hand-authored synthetic development sets created
for this change on 2026-10-08. Each contains completion-number, universal,
certainty, scope-expansion, relayed-authority, and quality-adjective drafts,
alongside clean plans, negated statements, partial progress, questions,
corrections, and neutral replies. The tail of each drift set includes less
common vocabulary deliberately outside the starter tables. Mapping and routing
were developed alongside these fixtures. **None of these results is held out.**
Fixtures are explicit executable examples, not independently adjudicated labels
or evidence that these sentences describe actual mistakes.

Every replay compares three paths: explicit-language mapping into the canonical
English gate, automatic language routing into that gate, and the raw English
gate. A draft is "caught" when any gate hit appears, including low severity;
that is broader than the CLI's nonzero exit or a host's blocking decision.
False fire means any hit on a fixture labeled clean. Miss and false-fire IDs,
denominators, percentages, and Korean batch counts are retained in `results.json`.

## Current results

| Language | Explicit catch | Explicit false fire | Auto catch | Auto false fire |
| --- | --- | --- | --- | --- |
| Korean | 116/180 (64.4%) | 4/135 (3.0%) | 111/180 (61.7%) | 4/135 (3.0%) |
| Chinese | 16/20 (80.0%) | 0/20 (0.0%) | 16/20 (80.0%) | 0/20 (0.0%) |
| Japanese | 16/20 (80.0%) | 0/20 (0.0%) | 16/20 (80.0%) | 0/20 (0.0%) |
| Turkish | 16/20 (80.0%) | 0/20 (0.0%) | 16/20 (80.0%) | 0/20 (0.0%) |
| German | 16/20 (80.0%) | 0/20 (0.0%) | 16/20 (80.0%) | 0/20 (0.0%) |
| French | 15/20 (75.0%) | 0/20 (0.0%) | 15/20 (75.0%) | 0/20 (0.0%) |
| Spanish | 14/20 (70.0%) | 0/20 (0.0%) | 14/20 (70.0%) | 0/20 (0.0%) |
| Portuguese | 15/20 (75.0%) | 0/20 (0.0%) | 15/20 (75.0%) | 0/20 (0.0%) |

## Review regressions

`review-cases.json` retains 48 author-written cases frozen before initial
remediation and two counterexamples from independent review at `aa6bd94`, added
before the follow-up repair. There are 34 negative/request/inability statements
and 16 affirmative relay controls,
including a negative statement followed by an independent positive one. These
examples exposed negative false fires at the pre-repair head
`a9738c9`; they are review-driven regressions, not held-out evaluation or
native-speaker labels.
The replay reports them separately from the original development corpora;
unit tests additionally require the adjacent positive relay to produce exactly
one hit located in the affirmative sentence.

| Language | Explicit relay controls caught | Explicit negative false fires | Auto relay controls caught | Auto negative false fires |
| --- | --- | --- | --- | --- |
| Korean | 2/2 | 0/6 | 2/2 | 0/6 |
| Chinese | 2/2 | 0/5 | 2/2 | 0/5 |
| Japanese | 2/2 | 0/5 | 2/2 | 0/5 |
| Turkish | 2/2 | 0/3 | 2/2 | 0/3 |
| German | 2/2 | 0/3 | 2/2 | 0/3 |
| French | 2/2 | 0/4 | 2/2 | 0/4 |
| Spanish | 2/2 | 0/4 | 2/2 | 0/4 |
| Portuguese | 2/2 | 0/4 | 2/2 | 0/4 |

Chinese completion before an object now requires assertion wording such as
`已完成` or `完成了`; Japanese requires asserted tense/aspect or a status-word
position. Standalone status words can still map, but ambiguous bare Chinese
`完成所有任务` is left unmapped. This choice avoids treating that unmarked request
as an assertion and can miss unmarked headline-style claims. It does not
establish general grammatical understanding. Explicit requests and inability
map to neutral vocabulary so they do not suppress adjacent asserted completion.

Negated relay and certainty mappings deliberately distinguish wording that the
English gate itself can flag, including Korean negative certainty/stability/
accuracy, French `pas garanti`, Spanish/Portuguese negative guarantees, and
Turkish `kesinlikle emin değilim`. German `nicht bestanden` and Portuguese
negative completion/pass forms also have adapter guards. These are stricter
vocabulary guards than the English equivalents, not changes to its rules.
Negated completion, planned work and partial progress retain the English gate's
existing contrast-window semantics, including its possible suppression of
nearby completion claims. Unrestricted negation and inflection remain outside
these starter tables.

Source-coordinate mapping uses compressed segments and skips untouched maps.
Tests compare it with the prior character-based definition over composed,
length-changing substitutions and scan a 300,000-character unmapped prefix
without dropping its final claim. The installed-artifact smoke exercises all
eight languages through the CLI, with affirmative and negative controls.

## Limits and integration contract

- These are small, authored development sets. A zero false-fire count is an
  observation on those drafts, not a bound on real-world errors. Real-language
  recall, downstream usefulness, dialect coverage, and native-speaker review
  are unmeasured. Do not compare languages' percentages as relative quality:
  Korean has a different corpus and history from the new languages.
- Script detection checks Hangul, then Japanese kana, then Han characters.
  Kanji-only Japanese is ambiguous and requires an explicit code. Latin-script
  routing uses small vocabulary lists, with English fallback on ties. Sparse
  or heavily code-switched text can be missed; one adapter runs per draft.
- Completion tense, negation and contrast handling are vocabulary-dependent.
  Chinese/Japanese assertion and request forms are intentionally limited as
  described above; the tables do not understand unrestricted grammar. French,
  Spanish, Portuguese and Turkish inflections outside the maps are missed.
- Korean still has clean false fires on a question about additional scope,
  an unrecognized contrast, a qualified stability statement, and a progress
  report. The receipt lists their IDs. Keep those visible when extending maps.
- Correction markers map to canonical English text but this change does not
  wire multilingual correction detection into the miner or retrieval index.
- `hermeneutic.gates.regex.risk_score` stays English-only. The language scorer
  normalizes before calling it, then maps hit spans back to source tokens for
  CLI snippets and telemetry. Numbers, punctuation and unrecognized text pass
  through, except local numeric counters are separated from digits.
- The CLI and Python Router retain English defaults. Shipped response hooks
  use automatic mapping before their existing gate and preserve their host
  retry/advisory policy. Downstream Router reviewers and repairers still see
  the original draft. Host tests establish adapter behavior, not live delivery
  in each host. A package release is a separate action from this source PR.
