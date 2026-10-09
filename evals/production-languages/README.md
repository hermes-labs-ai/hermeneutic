# Independent simulated multilingual deployment evaluation

This evaluation measures Korean, Japanese, Chinese and Spanish trigger mapping
against independently authored draft scenarios. It does not certify production
reliability. Experimental mappings remain advisory in CLI, Router and shipped
response adapters; canonical English findings retain existing enforcement,
including in mixed-language drafts.

## Corpus and independence

An independent Claude Opus author produced 120 original cases per language under
Apache-2.0: 60 clean and 60 high-severity evidence-obligation drafts. Each split
contains 30 of each label and 45 scenario families per language. Related pairs
share a family and never cross splits. Across both splits there are 90 families
per language, rather than 120 independent observations. The author rejected
expansion that would merely add correlated variants.

The author did not inspect the gate implementation, adapters, existing fixtures
or their results. The author performed duplicate and scenario-diversity checks,
including replacing mirrored scenarios across languages. Cases are simulations,
not scraped or private conversations. A single model author and methodology
reviewer is not native-speaker adjudication or independent human ground truth.
Dialect coverage, real-use prevalence, low-only advisory shapes and judgments
requiring context outside the draft are not established.

The [protocol](PROTOCOL.md), [methodology review](METHODOLOGY-REVIEW.md) and
[author manifest](manifest.json) record authoring and pre-exposure decisions.
The manifest is an immutable authoring snapshot: its sealed status describes
that earlier point in time. `candidate.json`, `holdout-exposure.json` and
`results.json` record subsequent freezing and consumption.

## Candidate development

[Development baseline](development-baseline.json) and
[final development replay](development-repair.json) preserve the same open
cases, labels and denominators. [Independent triage](DEVELOPMENT-TRIAGE.md)
identified misses beyond vocabulary mapping: unnumbered standalone completion
and human authority claims do not have the unchanged canonical high-severity
shape, and supported inline tool counts can still trigger the fixed English
gate. No canonical rule, label or denominator was changed to obtain a pass.

Bounded automated actor + affirmative report + explicit adopted status mappings
were retained. New universal-completion reordering was withdrawn before freeze
after independent probes reproduced false positives on conditional clauses.
[Clause review](CLAUSE-REPAIR-REVIEW.md) preserves findings, repairs and the
accepted binding. These probes are regression controls, not added quality cases.

## Metrics and replay

False positives count **any** hit on a clean draft. High-severity recall counts
only actual `high` hits on high-labeled drafts; medium or low hits cannot inflate
it. `results.json` separately records actionable recall, frozen public-shape to
rule-ID agreement, original spans, selected languages, case IDs, categories and
families. Development and held-out splits, and explicit and auto routing, are
reported separately. Targets are at most 2% observed false positives and at
least 90% observed high recall for each language.

Wilson 95% intervals describe binomial proportions conditional on these authored
cases. Family correlation and shared model authorship mean they are not
production confidence bounds. Even zero false positives among 30 clean cases
would have an upper Wilson bound above 11%; this sample cannot establish a 2%
population error rate.

After the first sealed evaluation, reproduce its exact frozen receipt with:

```bash
python3 evals/production-languages/run.py \
  --holdout evals/production-languages/holdout.json --replay
```

The runner verifies source, protocol, manifest, methodology and corpus hashes.
It records exposure before parsing. An incomplete first exposure is consumed,
not retryable; a replay requires an existing terminal receipt and unchanged
bindings. This holdout must never be used to tune a future candidate.

## Sealed results and deployment decisions

The first held-out run was consumed after the accepted source binding was frozen.
The committed holdout is byte-identical to the author's sealed file; exact receipt
replay passes. **No language meets both observed targets in either routing mode.**
All four therefore remain advisory. No source or case was tuned after exposure.

Cells show count/denominator, observed rate and Wilson 95% interval.

| Language | Routing | Held-out false positives | Held-out high recall | Targets met |
| --- | --- | --- | --- | --- |
| ko | explicit | 0/30 (0.0%; 0.0–11.4%) | 2/30 (6.7%; 1.8–21.3%) | No |
| ko | auto | 0/30 (0.0%; 0.0–11.4%) | 2/30 (6.7%; 1.8–21.3%) | No |
| ja | explicit | 0/30 (0.0%; 0.0–11.4%) | 0/30 (0.0%; 0.0–11.4%) | No |
| ja | auto | 0/30 (0.0%; 0.0–11.4%) | 0/30 (0.0%; 0.0–11.4%) | No |
| zh | explicit | 1/30 (3.3%; 0.6–16.7%) | 0/30 (0.0%; 0.0–11.4%) | No |
| zh | auto | 1/30 (3.3%; 0.6–16.7%) | 0/30 (0.0%; 0.0–11.4%) | No |
| es | explicit | 2/30 (6.7%; 1.8–21.3%) | 3/30 (10.0%; 3.5–25.6%) | No |
| es | auto | 0/30 (0.0%; 0.0–11.4%) | 2/30 (6.7%; 1.8–21.3%) | No |

The development split also misses both targets for every language/mode:

| Language | Routing | Development false positives | Development high recall |
| --- | --- | --- | --- |
| ko | explicit | 1/30 (3.3%; 0.6–16.7%) | 2/30 (6.7%; 1.8–21.3%) |
| ko | auto | 1/30 (3.3%; 0.6–16.7%) | 2/30 (6.7%; 1.8–21.3%) |
| ja | explicit | 2/30 (6.7%; 1.8–21.3%) | 3/30 (10.0%; 3.5–25.6%) |
| ja | auto | 2/30 (6.7%; 1.8–21.3%) | 3/30 (10.0%; 3.5–25.6%) |
| zh | explicit | 2/30 (6.7%; 1.8–21.3%) | 2/30 (6.7%; 1.8–21.3%) |
| zh | auto | 2/30 (6.7%; 1.8–21.3%) | 2/30 (6.7%; 1.8–21.3%) |
| es | explicit | 2/30 (6.7%; 1.8–21.3%) | 4/30 (13.3%; 5.3–29.7%) |
| es | auto | 2/30 (6.7%; 1.8–21.3%) | 3/30 (10.0%; 3.5–25.6%) |

This is strong bounded evidence of inadequate high-severity coverage on the
authored tasks, rather than evidence of production reliability. Explicit and auto
routing differ for Spanish; falling back to English can remove both false
positives and legitimate mapped findings. Neither mode is a validated language
classifier. Supported inline claims can still trigger canonical English patterns;
the advisory decision never suppresses a raw English finding.

## Consumer verification boundary

The source-hashed `scripts/verify-installed-languages.py` checks installed package
byte parity, isolated CLI advisory and mixed-English rejection, Router dispatch,
Hermes Agent output and simulated Gemini/Qwen hook payloads. The repository
suite covers state, concurrency and existing English contracts. Installed
mechanics do not prove delivery through a running third-party host or channel.
The canonical English regex remains byte-identical to the 0.1.13 baseline.
