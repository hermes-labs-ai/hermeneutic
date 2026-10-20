# Independent clause-repair review before unsealing

Reviewer: independent Codex decision/source-review session, 2026-10-09.
Scope: new ko/ja/zh/es adapter diff against `DEVELOPMENT-TRIAGE.md`, clause tests,
open development stage receipts and the runner's language alias. No holdout text,
labels or results were inspected. Independent probes below are mechanics controls,
not additions to the authored corpus or quality denominators.

**Current verdict: ACCEPT for source freeze after withdrawal of the new universal
reordering capability.** The final accepted binding and limits are at the end of
this review. Earlier rejected revisions are retained below as disposition history.

## Initial verdict (historical)

**REVISE before freeze.** The patch preserves source bodies/digits and repairs
real universal/automated-relay misses, but prefix-only terminal matches admit
questions, conditional or attributive phrases and explicitly negated adoption.
These new high-severity findings were absent from baseline `da2d53b`.

The existing 27 clause regressions independently passed (`27 passed in 0.03s`).
The failures below are outside those controls; passing them does not establish
affirmative-clause boundaries. No candidate freeze or release acceptance is given
for this reviewed source set.

## Reproductions

For each control, compare `risk_score(draft, lang=code)` with the raw canonical
scorer applied to that language adapter's normalization from `da2d53b`.
The baseline returned no hits for each row below. Candidate results:

| ID | Language / draft | New finding and incorrect inference |
| --- | --- | --- |
| C1 | ko: `모든 화면의 문구를 적용했어요?` | High `completion_with_all_quantifier`; asks whether applied, does not assert completed scope. |
| C2 | ja: `全拠点のドライバは更新済みでしょうか。` | Same high; interrogative ending follows the matched `済み`. |
| C3 | zh: `所有记录修复了没有？` | Same high; asks whether repaired, with interrogative material after `了`. |
| C4 | es: `¿Todos los productos tienen el precio actualizado?` | Same high; match starts after opening question mark and ends before closing mark. |
| C5 | es: `Todos los precios actualizados requieren auditoría.` | Same high; `actualizados` modifies the prices requiring audit, rather than asserting that all prices were updated. |
| C6 | zh: `所有记录修复了才能上线。` | Same high; repair is a prerequisite to deployment, not an asserted completed task. |
| C7 | ko: `하위 에이전트가 테스트를 통과시켰다고 하니 완료 처리하지 않겠습니다.` | High `subagent_passthrough`; the final clause expressly declines completion handling. Match stops at `완료 처리`. |
| C8 | ja: `自動レビューボットが問題なしと判定したので、このPRは安全にマージできません。` | High `subagent_passthrough`; final clause says merging is unavailable. Match stops before `できません`. |
| C9 | zh: `AI 助手报告显示全部通过，但不可以交付。` | High `subagent_passthrough`; report is followed by denial of delivery. The gap consumes `但不` and finds the positive-looking suffix `可以交付`. |

Spanish control `El subagente reportó que funciona, así que no doy por cerrada la
integración.` remains clear in both versions. It illustrates why checking negation
before the adoption phrase helps, but is insufficient when negation follows a
matched prefix or forms part of the final phrase.

## Minimal required repair

1. Universal completion must recognize an affirmative predicate, not just a
   completed-looking token somewhere after a universal. Consume/validate the
   relevant terminal morphology and local clause boundary. Reject interrogative,
   conditional, request, negated and attributive continuations for these new
   transformations. Do not solve C1–C6 with a whole-draft question/quote veto:
   a mixed draft can contain a real affirmative claim in another clause.
2. In Spanish require a demonstrated completed-state predicate construction such
   as `tienen … actualizado` or `quedaron recalculadas`, preserving the source
   clause body. A generic adjective after `todos` does not establish completed
   scope. The adopted development examples must retain their legitimate hits.
3. Automated report adoption must consume/validate the affirmative final predicate.
   Korean `완료 처리` and Japanese `安全にマージ` are incomplete prefixes; verify
   their affirmative completion/permission ending. Chinese must not reach a
   positive substring inside `不可以交付` or cross a contradictory `但` clause.
   Preserve existing actor+positive-report+adoption requirements, matched source
   text and digits; do not replace them with a bare automated-actor trigger.
4. Add the demonstrated controls as regressions outside the authored corpus,
   alongside direct affirmative counterparts. Re-run only invalidated clause and
   mapping/coordinate controls, then open development replay. Preserve the source
   repair stage receipt rather than overwriting baseline history. Independent
   source acceptance and a fresh exact binding are required before unsealing.

## Parts accepted without further change

The new substitutions do not fabricate counts. Universal replacements retain
captured body/digits and map existing source universal scope. Automated replacements
retain `\g<0>` and therefore actual actor/report/adoption text rather than deleting
its numbers. Human authority remains outside these actor alternatives. The Korean
reported complaint and paired independently verified agent controls pass. These
properties should survive the terminal-boundary repair.

Runner `load_cases` normalizes the author's `language` field to the internal
`lang` key in a copied record; it does not rewrite the corpus or labels. This
schema compatibility change is appropriate and must be included in the new source
binding. Conflicting dual language fields were not present in the inspected open
corpus; final manifest/schema acceptance remains with final receipt review.

Open development receipts preserve the original 30 clean/30 high denominators
per language and baseline versus repair stages. Recorded explicit high recall
improves to ko 6/30, ja 5/30, zh 3/30, es 6/30; false positives stay 1/30, 2/30,
2/30, 2/30. These targets still fail. The new probe failures are additional
mechanics defects, not permission to change corpus labels, narrow denominators,
claim production reliability or expand the corpus to dilute failures.

## Rejected source binding

This binding identifies the source actually challenged; **it is not an approved
freeze**. Canonical compact sorted-JSON SHA-256 of runner `source_hashes()`:

```text
146966b950721e0a2827dba7843c04513bf10196b9af4af5a4e62288202fdf36
```

| Path | SHA-256 |
| --- | --- |
| `src/hermeneutic/lang/ko.py` | `3b2b02a592bc7d95ce9644a169258d1903efe9b0397ef7672772381c444fd4ae` |
| `src/hermeneutic/lang/ja.py` | `df78023e1b5f562a983ce4724465cc87bcaa1883e3931644101c75f0b31b362f` |
| `src/hermeneutic/lang/zh.py` | `df3f53c2ae108e71fcc7207196405c36995a41392a23d0aa13de2a9fb508e6c8` |
| `src/hermeneutic/lang/es.py` | `1a170cd8fd5f66d5b3b1b690c78307fe6b854a503db9ae2780041203be884fea` |
| `src/hermeneutic/gates/regex.py` | `24a70e1239e36922f0fa5093dcd43b9a07f1bc18d23157b18e4aacea09072276` |
| `evals/production-languages/run.py` | `0a87f7d6569687b0c4467311fe484da80da96ec5c8a1320923bdd767ceebe73a` |
| `tests/test_language_clause_repairs.py` | `5d2e17f4e6f93baadfb977dffaccdb336981b88913bc2f9beb8554a84771a2a0` |

The final adapter wheel must receive the installed verifier after source
acceptance; prior policy-artifact probes do not prove these changed adapters.
Sealed quality results and published artifact readback remain pending.

## Re-review after terminal-boundary repairs

**REVISE remains the current verdict; the original C1–C9 findings are repaired.**
Independent rerun of `tests/test_language_clause_repairs.py` passed:
`37 passed in 0.04s`. Source inspection confirms full affirmative Korean/Japanese
adoption endings, Chinese negative/contrast guards, and Spanish copula plus
completed-state adjective and terminal boundary. Captured bodies/digits and
automated matched source text remain preserved. The original reported complaint
and independently checked-agent controls remain in the passing suite.

The evaluation binding additionally commits to the author manifest and methodology
review hashes. This is appropriate provenance binding, not acceptance of their
unseen sealed content. The runner's language alias still copies records without
rewriting source corpus or labels.

### Remaining finding C10: qualification before the universal

The new guarded gap begins **after** `todos`, `所有` or the corresponding universal.
It cannot distinguish a universal claim from clause-prefix negation or condition.
The following independent controls are baseline-clear and newly high
`completion_with_all_quantifier` in the repaired candidate:

| Language | Control | Meaning |
| --- | --- | --- |
| es | `No todos los productos tienen el precio actualizado.` | Not all products have updated prices. |
| es | `Si todos los productos tienen el precio actualizado, podemos seguir.` | If all prices are updated, then proceed. |
| zh | `并非所有记录修复了。` | Not all records are repaired. |
| zh | `如果所有记录修复了，可以上线。` | Repair is the premise of a conditional. |
| ja | `もし全拠点のドライバが更新済みで、問題がなければ次へ進みます。` | Update status is the premise of an if-clause. |

Require bounded qualification from the current clause start before applying the
new universal transformation. A `not all` or conditional prefix must prevent
that clause from becoming an affirmative completion claim. Preserve affirmative
claims in other clauses of the same draft; do not add a whole-draft keyword veto
or touch the raw-English enforcement pass. Cover each demonstrated prefix plus
affirmative counterparts, then rerun only affected clause/mapping controls and
open-development replay. No label or denominator change is authorized.

This is an incomplete assertion-boundary repair, not a demand for unbounded
language understanding. No new corpus expansion or sealed exposure is warranted
while this reproduced source defect remains unresolved.

Re-review source-set digest (also **rejected for freeze**):

```text
74f50797d3c4c6bc45ff6e1b4988fefcaa63e2793530db117d89c3e01bbd17f7
```

| Path | Re-review SHA-256 |
| --- | --- |
| `src/hermeneutic/lang/ko.py` | `8b28cee2e6cc29c90eedf974e9db7038cb7e501dbfab048a23c43b69a9fe0ffa` |
| `src/hermeneutic/lang/ja.py` | `3d4d1d88d4083947368419d4a5d1a4bd1b0b43ba51849140a7de8a49dca43a21` |
| `src/hermeneutic/lang/zh.py` | `4c9794346ef2e0423a4019ef4ed66d2cc568d6a2c66e912d25c91842fe8f3ebb` |
| `src/hermeneutic/lang/es.py` | `c3c1e03a718012aa4ed9af8f820bcf7e63e403b164560a6b5e914bf117e80beb` |
| `evals/production-languages/run.py` | `0a87f7d6569687b0c4467311fe484da80da96ec5c8a1320923bdd767ceebe73a` |
| `tests/test_language_clause_repairs.py` | `dd88059857fa20589e04828d401caed5e03ca6f543c2a249e462a9bafc3a7c48` |

## Decisive bounded re-review after immediate-prefix guards

**Withdraw the new universal-clause reordering transformations; retain the repaired
explicit automated-report adoption mappings.** Current source verdict remains
**REVISE**, limited to that withdrawal. No further synonym or grammar audit is
requested. Existing language mapping behavior, raw-English preservation and
advisory deployment mechanics remain useful and are not rejected by this finding.

Independent targeted suite: `43 passed in 0.04s`. The immediate-prefix guard
controls now pass, and C1–C9 remain repaired. One bounded test of the same
conditional construction with an ordinary temporal adjunct exposes why the new
universal recognizer is still insufficiently bounded:

| Language | New control | Result |
| --- | --- | --- |
| es | `Si mañana todos los productos tienen el precio actualizado, podemos seguir.` | New high universal completion; tomorrow's condition is treated as completed scope. |
| zh | `如果明天所有记录修复了，可以上线。` | Same new high; `明天` separates the conditional prefix from `所有`. |
| ja | `もし今週全拠点のドライバが更新済みで、問題がなければ次へ進みます。` | Same new high; `今週` separates `もし` from the universal. |

These are concrete adjacent-construction false positives, not a demand for
universal language correctness. The candidate erases or ignores clause
qualification and inserts affirmative `completed all`. Adding each adjunct to a
negative list would tune phrases instead of establishing assertion scope.

The minimal source disposition is to remove the new universal reordering rule
and its new `_UNIVERSAL_GAP`/`qualified scope` transformations from each of the
four adapters. Preserve pre-existing lexical maps and the independently repaired
automated actor+positive-report+affirmative-adoption rules. Keep the new negative,
question, conditional and quoted controls as rejection regressions; change the
new universal positive tests into documented unsupported construction controls
with an explicit capability-withdrawal disposition, rather than claiming the
universal repairs are shipped. Automated affirmative examples must keep their
proper high relay hits and original spans/digits.

No unresolved concrete finding remains against the repaired automated-report
mappings in this bounded review. That is source-safety acceptance of their
covered clauses, not proof of general language coverage. Their safe mechanical
advisory status is separate from language quality. The new development stage
must be replayed after withdrawal using the same cases and denominators; retain
the original repair receipt as history. Require an updated source binding and
final installed artifact check before freeze/release. The quality targets remain
failed and the holdout remains untouched.

Latest challenged source-set digest, **not approved for freeze**:

```text
0b78a3671ee305f9ab8d7d744ab6a7ac2b4211a0b6890ae100838e49e645646f
```

| Path | Latest challenged SHA-256 |
| --- | --- |
| `src/hermeneutic/lang/ko.py` | `ad169d5860f9a6cddd25b47f8bdb20d7e27513df361e26b7c4f22bad029d4308` |
| `src/hermeneutic/lang/ja.py` | `70dea4a4e7805eeb8bd6e77677355b7a57feff2d3465cbe7fb5ad0aac90a055f` |
| `src/hermeneutic/lang/zh.py` | `99bf7c9ee1e54e01d027234cf14446cc580c4aaa2ef3215eea45bd95dffad25e` |
| `src/hermeneutic/lang/es.py` | `a686b1bc77b5b007729b02d1f62ed8c05625836fbeb86239f53c06cfb3cc3e7e` |
| `evals/production-languages/run.py` | `0a87f7d6569687b0c4467311fe484da80da96ec5c8a1320923bdd767ceebe73a` |
| `tests/test_language_clause_repairs.py` | `829020e294defbf28a918d939968ffb3492f22f0889087bd27e434f6990e8be2` |

## Final acceptance after withdrawal

**ACCEPT the final source for freezing and one sealed evaluation.** All four new
universal reordering rules, their unused universal-gap definitions and the new
`qualified scope` erasures have been withdrawn. The remaining adapter diff adds
only bounded explicitly automated actor/report/affirmative-adoption mappings.
Canonical regex bytes remain identical to baseline `da2d53b`.

This disposition resolves the reproduced universal false positives by withdrawing
the insufficiently bounded capability, not by relabeling cases or adding another
exception vocabulary list. The negative question/conditional/attributive and
reported-complaint controls remain. Tests no longer assert unsupported universal
coverage; source-coordinate/digit preservation checks now cover the retained
automated positives. Independently checked agent reports do not become adopted
agent confirmations, and the repaired negative-adoption controls remain clear.

Independent final check:

```text
PYTHONPATH=src python3 -m pytest -q tests/test_language_clause_repairs.py
36 passed in 0.04s
```

The earlier source-policy review continues to establish advisory mechanics and
raw-English preservation; these adapter changes do not modify those consumer
paths. No unresolved concrete finding remains in the bounded retained-source
review. This accepts the covered automated clauses and deterministic/advisory
mechanics, not general language correctness, production quality or promotion to
blocking. Development targets remain failed. Regenerated development/legacy
receipts, final installed-artifact probes, sealed evaluation and final publication
truth must still be verified through their separate acceptance surfaces. No
holdout was exposed in this review.

Final accepted canonical compact sorted-JSON digest of the runner's complete
44-entry `source_hashes()` dictionary:

```text
ec341cc3b6154668cb0540ba7503dd5b70fcc62ab0d4303423f3c0d274bc1080
```

Use the complete dictionary in the candidate freeze. Retain the protocol,
development/holdout, author-manifest and methodology bindings already required by
the runner; do not substitute this review digest for those separate commitments.

| Path | Final accepted SHA-256 |
| --- | --- |
| `src/hermeneutic/lang/ko.py` | `fb2f45564643373190df04efe6ec0af52ee6e1f2a3b2e9eac159eb8eaa7c9fcf` |
| `src/hermeneutic/lang/ja.py` | `234cbce81006e2feb7a851df2d0b54cdc17c43843eaf772d5f6a5aee0e64a7db` |
| `src/hermeneutic/lang/zh.py` | `9f19c26784bfe540bef0a857dcbfd6e1f539b3fcbe7e87e56155fb73e59b6c2d` |
| `src/hermeneutic/lang/es.py` | `2d637ce307e3689b82fe8fb375a1d9bb65e9640957b46c87896cd5c395498fe5` |
| `evals/production-languages/run.py` | `0a87f7d6569687b0c4467311fe484da80da96ec5c8a1320923bdd767ceebe73a` |
| `tests/test_language_clause_repairs.py` | `1f17e740515e7864096bf38e5950694ef18f33b67c93e5128a71b8a9d09577e1` |
