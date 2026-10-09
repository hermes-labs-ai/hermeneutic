# Methodology review — multilingual production evaluation (ko, ja, zh, es)

Reviewer/author: independent methodology and corpus session, model `claude-opus-5-5`,
2026-10-09. Inputs read: repository `AGENTS.md` and `evals/production-languages/PROTOCOL.md`
(sha256 before amendment `622e60159a544e58239de0266407ff028f16e0a340c46bf2d0c40c7eebddf141`).
Not read: language adapters, regex patterns, `evals/languages` or any other corpus,
any evaluation result. No native-speaker adjudication was performed and none is claimed.

## Verdict

**Proceed with narrow amendments, for an advisory-only decision.** The protocol is
adequate to measure mapped gate behavior on authored drafts and to support keeping
ko/ja/zh/es advisory. It is **not** adequate to support promoting any of these
languages to blocking: a single author model, no native adjudication, and no
production sampling cannot establish real-language coverage, whatever the sealed
numbers are. The amendments below were appended to `PROTOCOL.md` before authoring
("Amendments from methodology review"); the original frozen text is unchanged.

## Findings and dispositions

| ID | Challenge | Disposition | Reason |
|----|-----------|-------------|--------|
| M1 | 160 cases/language from one author model would mostly add re-phrasings of the same few constructions (done / passed / reviewer approved), inflating n without adding independent evidence. | **Accepted.** Corpus reduced to 120/language (60 clean, 60 high; 30/30 per split). | The protocol allows a smaller set when more cases would be correlated. 120 is the point past which the author could no longer produce new constructions/scenarios per language without template-like variation. |
| M2 | Minimal pairs (same scenario, evidence present vs absent) are correlated and could leak across splits. | **Accepted.** Every case has a `family`; families are split together; families, not cases, are the independence unit. | 30 two-case families + 60 singletons = 90 families/language (45 per split). |
| M3 | "False positive is any hit on a clean case" is ambiguous if clean cases contain low-severity shapes (unhedged certainty, quality adjectives), which the protocol says are not high severity. | **Accepted; protocol amended.** Clean cases were authored to avoid low-only shapes; no low-only cases were authored. | Keeps every label unambiguous under "any hit = FP"; the cost is that low-severity behavior is not measured by this corpus. |
| M4 | The gate reads the draft; labels that depend on scenario context the gate cannot see would score the gate on information it never had. | **Accepted.** Every case is decidable from draft text: supported clean claims paste their evidence inline. `context_dependent` is `false` for all 480 cases. | Context-dependent judgments are therefore **not covered**; that is a stated limitation, not a pass. |
| M5 | Auto routing can select a non-English language for a mostly-English draft with a Korean/Japanese/Chinese/Spanish quote. If advisory status follows the selected language, an English overclaim that blocks today could silently become advisory. | **Accepted; protocol amended.** English-default blocking must survive auto routing and embedded non-English spans; advisory relaxation applies only to findings from insufficiently validated mappings. Receipts must include a mixed-script English-preservation probe. | This is the most material safety risk of the advisory policy: a regression in English, which the protocol treats as invariant. |
| M6 | "CLI findings remain visible without an automatic rejection" does not say what the exit status is; hooks and scripts treat exit 1 as rejection. | **Accepted as clarification; protocol amended.** For insufficiently validated languages the CLI must print findings (rule, severity, language, advisory status) and must not return the rejecting exit status for them. | Without this, "advisory" is unenforced in any host that keys on exit code. The release-safety review must confirm the exact exit semantics. |
| M7 | Point thresholds at small n: with 30 clean holdout cases per language, `<=2%` means zero FPs; with 30 high cases `>=90%` means at least 27 hits; the Wilson 95% lower bound at 27/30 is about 0.74. | **Accepted as clarification; targets unchanged.** | The targets are diagnostics for an advisory decision, not promotion gates. Raising n to tighten intervals was **rejected**: it would need fabricated independence (see M1). |
| M8 | Author and implementer are likely the same model family; mappings may match the idioms this author prefers, inflating recall on its own drafts. Open dev cases also teach the implementer this author's style. | **Accepted as limitation.** Not fixable in this session. | Before any promotion: a second, unrelated author (ideally native speakers) and production samples. |
| M9 | Sealing in `/tmp` is procedural, not technical: same-UID processes can read it, and macOS periodic cleanup may remove files not accessed for several days. | **Partially accepted.** Directory is mode 0700; manifest commits to sha256 of holdout and of the sorted holdout ID list, so substitution is detectable. | Peeking cannot be detected, only deterred. Copying the holdout to a second location was **rejected** (more exposure). The lead should run the sealed evaluation promptly or move it to a durable sealed location and re-verify hashes. |
| M10 | Shared script (Han in ja/zh), zh simplified vs traditional, and es regional variants. | **Accepted as limitation.** Cases carry `variant` tags (`zh-Hans` default, some `zh-Hant`; `es-ES`/`es-419`/`es-neutral`). | Variant cases are few; no dialect coverage is claimed. Auto-routing ambiguity on kanji-heavy ja and on zh-Hant should be reported per case. |
| M11 | The author cannot see internal rule IDs, so "correct rule hit" needs a mapping. | **Accepted; protocol amended.** `expected_rule` uses public shape names from `AGENTS.md`: `completion_overclaim` or `relayed_authority`. The implementer must freeze a public-name→rule-ID mapping before unsealing. | Prevents the mapping from being chosen after seeing holdout results. |
| M12 | Quoted claims are ambiguous between relay and report. | **Accepted; labeling rule recorded.** Quoting or citing a claim and adopting it as the status = high `relayed_authority`. Quoting it with explicit non-endorsement and a pending check = clean. | Makes the evidence obligation, not the quote marks, decide the label. |
| M13 | "Overbroad universal status" can be a plan or question. | **Accepted; labeling rule recorded.** A universal claim of completed/passing state without inline evidence = high `completion_overclaim`; universal wording in a plan, question or negation = clean. | |
| M14 | Should the corpus include context-dependent or low-only cases to widen coverage? | **Rejected for this round.** | They would make labels or the FP definition ambiguous (M3, M4). They should be a separately reported set in a later round. |
| M15 | Is the advisory deployment policy itself sound? | **Accepted with notes.** Advisory is the right default for unvalidated languages: false blocks in hosts are costly and these languages lack adjudication. It fails open: real non-English overclaims will not be blocked. If the published 0.1.13 host paths currently block on mapped-language hits, moving them to advisory changes shipped behavior and needs a release note. | I did not inspect source, so I cannot say which case applies. |
| M16 | Labels are author-model judgments. | **Accepted as limitation.** No native-speaker adjudication; `rationale` records the reasoning for each label so a later adjudicator can audit it. | |

## Corpus produced

See `manifest.json` for counts, hashes and paths. Development cases are in
`development.json` (open). Holdout cases exist only in
`/tmp/hermeneutic-production-sealed-20261009/` and are disclosed here only through
sha256 and counts.

## Authoring controls actually applied

- Scenarios were written separately per language, using domains chosen for that
  language. No case is a translation of a case in another language, and none is a
  numeric substitution of another case. The author checked this by hand; it was
  not verified by a second party.
- Exact duplicate drafts were checked mechanically, and character-trigram similarity
  across different families was screened (results in `manifest.json`).
- Labels come from each scenario's evidence obligation. No detector was run, and
  no detector output was seen.
- No case contains private chat text or scraped text.

## Limitations (must accompany any publication of results)

1. Single synthetic author model (`claude-opus-5-5`): constructions, register and
   domain choices are correlated within and across languages; effective independence
   is lower than the family count suggests.
2. No native-speaker adjudication; idiomaticity and label correctness are unverified
   by native speakers.
3. No production sampling; drafts are short, clean, single-message texts.
4. Variant and dialect coverage is thin; shared-script routing is exercised only
   by a handful of cases.
5. Context-dependent judgments and low-severity shapes are not covered.
6. The holdout seal is procedural (same-UID readable, `/tmp` lifetime).
