# Product release contract

The product invariant is: after a human corrects an instruction's intended
scope, a fresh agent facing an analogous instruction must retrieve the attributed
correction, check its applicability, and change the relevant action without
being told the lesson again. Separately, the output gate checks the claims in
the resulting draft. Neither plane substitutes for the other.

The release endpoint is executable:

- Native lint and tests pass, with the canonical English rules unchanged.
- The built wheel and source distribution install and run the offline
  teach-and-transfer mechanics and structured-report regressions.
- A source-verbatim candidate is derived from an attributed correction and
  confirmed before use; optional user/host interpretation is explicit. Exact
  scope and task cues govern retrieval. A fresh invocation receives bounded context.
  Inspection, explicit revocation and disabled/missing-memory behavior work.
- The separate transfer evaluation records actual fresh host action proposals,
  successful transfers, retrieval false matches and action overgeneralization.
  The public dishes design example is separate from frozen validation cases.
- Default JSON omits matched text, identifies original source coordinates and
  raw-English/mapped origin, and separates severity from blocking policy.
- Codex, Claude Code and Hermes Agent paths state whether invocation is explicit
  or automatic and distinguish source mechanics from live host observations.
- Version surfaces agree with `release.json`. Fresh independent review and CI
  must apply to the release head before a separate controller merges it.

Run from an installed checkout or extracted source distribution:

```sh
python scripts/check-release.py
python scripts/check-product-baseline.py
python scripts/check-lesson-demo.py
bash scripts/smoke-installed-cli.sh
python scripts/check-correction-demo.py
```

CI runs these against the built artifact. `results.json` records the installed
API/CLI output-check development replay. The separate `evals/lesson-transfer/`
protocol freezes transfer jobs before execution. Release assurance and synthetic
usability observations are recorded separately from those task outcomes.

[`release-assurance.json`](release-assurance.json) records local source, wheel,
and source-distribution checks. Live host trials used an unpublished build
identified as `0.1.16`. The receipt compares that wheel with the `0.1.16a2`
preview: the package file sets match, and only the version assignment changed.
Preview deterministic mechanics were repeated; the live trials were not rerun
or relabeled. Exact committed-head CI and published-artifact readback remain
separate release requirements.

## What the cases establish

`cases.json` records the provenance of each exposed control. Hermeneutic's
rejected universal-clause transformations show why a conditional phrase must
not be presented as affirmative completion. The prior deployment review shows
why a high diagnostic severity must not imply language enforcement. LintLang's
[priority-order review](https://github.com/hermes-labs-ai/lintlang/pull/89#discussion_r3998561548)
shows the opposite hazard: broad negation suppression can erase a valid signal.
The transferred control here checks that unrelated negative instructions do not
hide a raw-English completion finding. This is design evidence, not proof that
the products have the same accuracy.

These controls are synthetic or taken from already-public development/review
examples. They are deliberately available to implementation authors. Passing
them demonstrates the stated mechanical contract, not independent validation,
real-language accuracy, user preference, or downstream reliability. They exercise
only the outgoing report plane. They cannot establish correction transfer.

Historical language corpus, frozen candidate and consumed evaluation receipts
under `evals/production-languages/` remain preserved. They must not be relabeled
as new held-out evidence. The public correction-retrieval set is likewise a
regression surface. The separate bounded-recall experiment in PR #63 failed its
operational acceptance and is outside this release.
