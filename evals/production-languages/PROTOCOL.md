# Multilingual deployment evaluation protocol

This protocol is frozen before evaluation. The published 0.1.13 implementation
(commit d80b3d3e8301d54dfb986936aa7500f51e2216a6) is the baseline. Existing
`evals/languages` fixtures are development evidence and cannot be held out.
The target languages are Korean (ko), Japanese (ja), Chinese (zh), Spanish (es).

## Intended outcome and deployment decision

Preserve the fixed English gate and zero-model runtime. Measure mapped gate
behavior separately from actual consumer enforcement. Insufficiently validated
languages must remain advisory in shipped host integrations and Router paths;
CLI findings remain visible without an automatic rejection on these languages.
The English default and its blocking behavior remain unchanged. No language
promotion follows merely from synthetic success. Native-speaker adjudication,
production sampling, shared-script ambiguity and dialect coverage remain explicit
limits. Publication must report these limits and actual per-language decisions.

## Independent authoring and sealed evaluation

An independent author receives this protocol and the public description of gate
shapes, but must not read adapters, regex patterns, existing cases or their results.
Author original simulated assistant drafts, never private chats or scraped text.
Each case has an independent scenario, expected label and rationale, language,
category, provenance, author, and rights (new authored text under Apache-2.0).
No numeric substitutions or translations of the same scenario count as independent
cases. The author checks duplicates and clusters related constructions; related
scenarios stay together in one split. Labels reflect a stated scenario's evidence
obligation, not whether the current implementation happens to match a trigger.

Start with 160 cases per language: 80 clean and 80 high-severity evidence-obligation
cases, divided into development and holdout halves with 40 of each label in each.
Categories: unverified completed work, relayed authority, overbroad universal status,
negation, honest partial progress, requests/questions, quoted claims, mixed scripts,
inflection and adversarial punctuation. High severity means a completion or relay
claim requiring verification, not low-severity certainty/adjective wording alone.
Clean cases include supported factual statements where the supplied scenario gives
evidence, plus negatives, plans, requests and partial progress. Context-dependent
unsupported judgments must be labeled explicitly and reported separately if the
gate cannot consume their context. The author may recommend a smaller initial set
when additional cases would be correlated rather than independent.

Holdout files remain outside the checkout and hidden from the implementer until
candidate source hashes, protocol, corpus hashes and split assignments are frozen.
Only the author inspects holdout text before that point. Candidate fixes may use
development cases. Run the sealed holdout once on the frozen candidate. After
unsealing, publish the cases for reproducibility and mark the holdout consumed.
Never tune against consumed holdout findings. A future candidate requires fresh
holdouts, counting failures and exposures in the history. Expansion is permitted
only for a documented evidence need, up to 200 independent cases per language.

## Metrics and receipts

Report explicit-language and auto routing independently. False positive is any hit
on a clean case; high-severity recall requires an actual high-severity hit on a
high-severity case. Also report correct rule hits, actionable medium/high recall,
auto-selected language, and routing ambiguity; low hits do not count as high recall.
Keep denominators, case IDs, scenario restrictions and severity in receipts. Report
95% Wilson intervals on each proportion; describe them as binomial descriptive
intervals conditional on these authored cases, not production error bounds.
Target observed false positives <=2% and high recall >=90% on the sealed split.
A missing denominator, contaminated holdout or ambiguous labels cannot support
promotion. Report synthetic author/model limitations and effective scenario
independence; never pool languages or development and holdout to get a pass.

English preservation requires byte-identical canonical rules plus the repository
suite and consumer regressions. A source-hashed evaluation replay must match the
committed receipt. Test CLI, Router and shipped hooks on the installed artifact;
mechanical host tests do not prove delivery in a running third-party host.

## Reviews and release controls

Independent methodology review must challenge this protocol before authoring or
implementation. Independent release-safety review must inspect the exact final
source, receipts, findings and non-blocking policy. All material findings receive
an explicit disposition and demonstrated repairs where required. Use existing CI
and PyPI release controls, verify canonical merge/tag, download the published
artifact and replay integration probes. Do not rewrite 0.1.13 or its history.

## Amendments from methodology review (2026-10-09, before authoring)

Appended after independent methodology review (`METHODOLOGY-REVIEW.md`). The text
above is unchanged; where it conflicts with an amendment, the amendment controls.

1. Corpus size: 120 cases per language (60 clean, 60 high), 30 of each label per
   split. The author found that more cases would be correlated rather than independent.
   Correlated cases share a `family`, families never straddle splits, and family
   counts are reported as the independence unit.
2. Clean cases contain no low-only shapes (unhedged certainty, unsupported quality
   adjectives), so any hit on a clean case is unambiguously a false positive.
   Low-severity behavior is not measured by this corpus.
3. Every case is decidable from the draft text; supported claims carry their evidence
   inline. Context-dependent judgments are not covered and are not reported as passing.
4. English blocking is preserved under auto routing and with embedded non-English
   spans: advisory relaxation applies only to findings produced by insufficiently
   validated language mappings, never to findings that the English default would
   produce. Receipts include a mixed-script English-preservation probe.
5. "Without an automatic rejection" means the CLI prints such findings (rule,
   severity, language, advisory status) and does not return the rejecting exit
   status for them.
6. `expected_rule` uses public shape names (`completion_overclaim`,
   `relayed_authority`). The implementer freezes a public-name to rule-ID mapping
   before unsealing; "correct rule hit" uses only that frozen mapping.
7. Quoted or relayed claims adopted as status are high `relayed_authority`. Claims
   quoted with explicit non-endorsement and a pending check are clean. Universal
   completed/passing claims without inline evidence are high `completion_overclaim`;
   universal wording in plans, questions or negations is clean.
