# Independent source-remediation decision review

Reviewer: independent Codex decision-review session, 2026-10-09. This is a
pre-implementation decision review, not final-source acceptance or corpus
adjudication. Inputs: repository `AGENTS.md`, `CLAUDE.md`, protocol and methodology
review, language routing, CLI, Router, Gemini/Qwen adapters and their existing
consumer tests. No development or holdout corpus was read or authored.

## Verdict

**ACCEPT the refined decision below. REVISE the original selected-language-only
decision.** A non-English selection cannot make the canonical English gate's
findings advisory. Protocol amendment 4 and methodology finding M5 require
preserving those findings even when mapping removes them from its own result.

Accepted remedy: a central deployment-policy helper retains unchanged
`lang.risk_score` as the mapped diagnostic API, evaluates the unchanged canonical
English gate on the original draft, and returns visible merged findings plus the
separate canonical-English findings eligible for existing consumer enforcement.
Every mapping remains unvalidated and mapping-dependent findings remain advisory.
No promotion follows from this authored evaluation, even if its point targets pass.

## Reproduced discrepancy and preservation risk

On the inspected source, `5개 파일을 수정했습니다.` selects `ko` and produces
`number_then_completion` at high severity. Gemini returns `deny`; Qwen returns
`block`. These are real local adapter decisions on the known development sample,
not false-positive adjudication or a running-host delivery result.

The mixed-script draft below selects `ko`. The raw canonical English gate returns
high `completion_with_number` and `completion_with_all_quantifier` findings, while
`lang.risk_score` returns no findings because mapped partial-progress wording
changes the surrounding gate context:

```text
요청하신 변경은 아직 검증하지 않았습니다. 다음 단계에서 확인할 예정입니다. Done — shipped 14 files and all 92 tests pass.
```

Therefore even retaining raw-English hits only when mapped hits exist is
insufficient. Always evaluate raw English independently for deployment decisions.
This probe is an enforcement regression input; it is excluded from sealed quality
evaluation and makes no label or recall claim.

## Exact minimal implementation requirements

1. Put policy and route metadata in one package helper. Return requested selector,
   resolved routing code, mapped findings, raw-English findings and visible merged
   findings, or equivalent fields sufficient to expose these distinctions. Resolve
   `auto` consistently once. Keep `risk_score` signatures, hit severities, original
   coordinates and canonical regex source unchanged. Do not mutate hit objects to
   encode advisory status. Deduplicate only identical rule/span/severity findings;
   preserve raw findings whose spans differ or disappear after normalization.
2. CLI must retain visible `RISK`, rule and severity, and add selected language and
   advisory status for mapping-dependent evidence. Compute exit status from raw
   English findings with the existing medium/high threshold. Mapping-only high
   severity exits zero; raw-English low severity still exits zero. Default `en`
   behavior and input-error exit statuses stay unchanged. The exit change is
   warranted by the protocol's explicit consumer outcome; no new CLI flag or
   replacement of the diagnostic API is needed. Release notes and agent guidance
   must explain that diagnostic severity and automatic rejection now differ.
3. Router keeps original/final drafts and merged risk evidence. Only raw-English
   findings may trigger rubric, probe or repair, using the existing severity
   threshold. Mapping-only findings return without calls to those components.
   An additive policy field is reasonable if needed to identify advisory returns;
   replacing the existing result type or changing English stage labels is not.
4. Gemini/Qwen retain their existing English blocking criteria and retry envelope,
   including any-hit hook behavior rather than importing the CLI threshold.
   Mapping-only evidence permits output with an evidence advisory, never a repair
   instruction, denial/block or claimed retry. Mixed findings may block because of
   raw-English findings; the repair reason must identify those enforceable findings.
5. Qwen must classify the response before `_resolve_marker`, sweeping, consuming
   or writing markers. A non-English advisory response must not touch state, even
   with no findings, an existing marker or unavailable/hostile state storage.
   Preserve the English clean-retry marker-release behavior and existing concurrent
   blocking, fail-open, ownership and no-symlink controls. Update the marker contract
   description: an intervening advisory response leaves a pending English marker
   for the next applicable English/enforceable response. It can consequently spend
   that later response's repair opportunity; without a host turn identifier this is
   a known state-association limit, not grounds for a broader state rewrite here.
6. Keep the already-advisory hooks advisory. Do not modify adapters, canonical
   rules, thresholds or evaluation labels to obtain quality targets. Do not add
   runtime model calls or introduce a user override that silently promotes a map.

## Required acceptance evidence

- For each supported non-English code, explicit and auto selected routes with
  mapping-only high findings: visible CLI evidence with exit zero, original Router
  output with zero rubric/probe/repair calls, and allowing Gemini/Qwen envelopes.
  These are mechanics tests using development samples, never quality denominators.
- English default and explicit `en`: existing outputs, thresholds, hit details,
  Router escalation and hook retry behavior. For mixed-script auto and explicit
  non-English routes, raw-English medium/high findings retain the corresponding
  CLI/Router behavior and raw-English findings retain existing hook behavior.
  Include the reproduced mapped-empty/raw-hit case above and duplicate-hit merging.
- Unknown programmatic language selectors retain documented raw-gate pass-through;
  an unknown selector is not validated-language status. Auto Latin ties, short
  drafts, Han-only Japanese/Chinese and code switching have explicit route receipts.
- Qwen advisory calls neither create a state directory nor alter existing markers;
  cover risky and clean advisory output, existing/absent state and unsafe state.
  Existing English clean-retry, concurrency and state-security tests remain valid.
  The existing concurrency test currently uses Korean as its blocking input; change
  that mechanics input to raw-English evidence rather than deleting the invariant.
- Byte-identical canonical regex source, passing repository lint/suite and installed
  artifact consumer probes. Independent final-source review must inspect the exact
  diff, policy attribution, receipts and the Qwen branch order before release.
- Freeze candidate source, protocol, corpus and split hashes plus the public-shape
  mapping before unsealing. Report explicit/auto mapped-quality metrics separately
  from deployment enforcement and raw-English attribution. Do not substitute the
  merged deployment findings for `lang.risk_score` quality scoring without a separately
  named metric; that would change the tested subject. Publish failed targets as
  failures, consumed holdout status and synthetic/native/production limitations.

## Limits and scope disposition

Auto detection chooses a routing code, not a verified language identity. Latin ties
and unsupported languages fall back to `en`; shared Han can route Japanese as
Chinese; mixed messages can choose one map. The policy guarantees advisory status
for mapping-dependent findings, not that every actually non-English message has
zero blocking risk. Raw-English patterns can fire in a mixed or non-English draft,
and remain enforceable to preserve the existing English contract. State this limit
in customer-facing guidance and deployment receipts rather than claiming broad
non-English nonblocking coverage.

This remedy is appropriate containment of unvalidated mapping enforcement.
Observed false positives and high-severity recall on a sealed authored split are
a separate result. Passing them would not prove multilingual production
reliability; failing them does not justify changing rules after holdout exposure.
