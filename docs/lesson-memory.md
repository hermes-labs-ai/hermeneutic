# Scoped lesson memory

Hermeneutic can preserve a correction once, keep an attributable lesson, and
return that lesson as context for a later task. The host decides how to apply
it. Retrieval does not execute a task, decide semantic applicability, or change
the assistant's hidden state.

The default `learn` path does not require retyping a correction as a separate
rule. It copies a bounded verbatim excerpt of the selected correction into an
inspectable **candidate**, using its original task as a retrieval example. The
candidate cannot appear in context until explicitly confirmed. This is source
preservation, not model interpretation or inferred operational meaning.

A user or host that has interpreted the correction can instead supply
`--lesson` and representative `--when` examples. That explicit interpretation
is stored as active and attributed as `host_supplied`. Neither path promotes
raw logs automatically. Mining, selecting evidence, confirming a candidate,
and inserting context are explicit operations.

## Try the fictional kitchen example

These commands export a packaged fictional session, mine the correction, and
prepare a candidate without restating the correction:

```sh
demo_dir="$(mktemp -d)"
demo_dir="$(cd "$demo_dir" && pwd -P)"
hermeneutic demo --scenario dishes --out "$demo_dir/session"
hermeneutic mine "$demo_dir/session" --format openai --glob '*.json' \
  --out "$demo_dir/triples.jsonl"
learned="$(hermeneutic learn --triples "$demo_dir/triples.jsonl" \
  --evidence triple-id-1 --scope home/kitchen --memory "$demo_dir/lessons.json")"
printf '%s\n' "$learned"
lesson_id="$(printf '%s' "$learned" | python3 -c 'import json, sys; print(json.load(sys.stdin)["lesson"]["id"])')"
hermeneutic lessons --memory "$demo_dir/lessons.json"
```

Inspect the source correction, attribution, scope, and example before activating
the candidate:

```sh
hermeneutic confirm "$lesson_id" --memory "$demo_dir/lessons.json"
hermeneutic context 'Wash the dishes after supper.' \
  --scope home/kitchen --memory "$demo_dir/lessons.json"
```

The later instruction does not repeat the rule about table plates. It shares
task vocabulary with the original instruction, so the selector returns the
confirmed correction. The host can insert the returned `context`, check that
the kitchen scope still applies, and use that correction when deciding how to
carry out the later instruction. These commands demonstrate storage and
retrieval; they do not perform washing or prove how a model will act.

Disable retrieval for an invocation, or revoke the lesson:

```sh
hermeneutic context 'Wash the dishes after supper.' \
  --scope home/kitchen --memory "$demo_dir/lessons.json" --disabled
hermeneutic revoke "$lesson_id" --memory "$demo_dir/lessons.json"
```

`--disabled` returns empty context without opening the memory. Revocation
preserves the lesson and original evidence as a tombstone, excluding it from
later retrieval. Repeating `learn` or `confirm` cannot silently reactivate the
revoked identity. To supersede a lesson, revoke it and teach a new interpretation;
the old evidence remains inspectable.

## Supply an interpreted meaning once

The default candidate is verbatim source data. A host can explicitly interpret
the operational meaning and supply additional task examples:

```sh
hermeneutic learn --triples "$demo_dir/triples.jsonl" --evidence triple-id-1 \
  --scope home/kitchen --memory "$demo_dir/lessons.json" \
  --lesson 'Washing up includes collecting and washing dirty plates on the table, not only dishes already in the sink.' \
  --when 'wash the dishes' --when 'wash up after supper'
hermeneutic context 'Wash up after supper.' \
  --scope home/kitchen --memory "$demo_dir/lessons.json"
```

This path records a `host_supplied` interpretation as active. Omitted `--when`
uses the original prompt; omitted `--lesson` uses the source candidate path.
If a legacy episode lacks an original prompt, the caller must supply a task
example. Teaching does not add a gate rule, invoke an LLM, or alter the original
correction corpus.

## What the selector does

Scope is a required opaque label, matched exactly. Retrieval considers active
lessons in that scope and compares the later instruction with the supplied or
source-derived `when` examples. It does **not** search lesson text or the
correction snapshot. Tokens are case-folded Unicode letter sequences of at least
three characters, with a fixed list of common task and function words removed.

A match normally needs two shared informative terms. If either term set has
only one term, that shared term is sufficient. Both cases require coverage of
at least half of both the instruction's and the example's informative term
sets. Results expose `matched_when`, `shared_terms`, `query_coverage`,
`example_coverage`, and `weak_match` (true for single-term overlaps). Ranking
uses the smaller coverage, then the shared-term count, then stable lesson ID.
These are transparent selection signals, not probabilities or proof of meaning.

Sparse matches need particular host review: a cue such as `Do the dishes` can
retrieve for both `Dishes after supper` and the inapplicable task `Buy dishes`.
That is an exposed retrieval false match; the host must reject the lesson's
applicability to a buying task. No hidden negation or task-intent heuristic
silently turns lexical selection into an application decision.

There is no synonym expansion, stemming, embedding, or language-model call.
An unseen paraphrase such as `Wash up after supper` can abstain when only
`Wash the dishes` was learned. Supplying a representative alternate example is
an explicit host choice. Longer unrelated requests, weak overlap, a different
scope, candidates, revoked lessons, and disabled retrieval produce no selected
context. Do not treat this lexical baseline as general natural-language
understanding.

The returned context tells the host to check applicability and conflicts.
Current explicit instructions take precedence: a later request limited to sink
dishes overrides an older lesson about collecting table plates for that task.
Multiple matching lessons remain visible with evidence; the selector does not
silently resolve incompatible instructions. Hosts should clarify conflicts or
explicitly revoke and replace stale lessons. There is no automatic feedback
from context or model output into memory and no recursive conditioning loop.

## Python API and JSON output

```python
from hermeneutic import (
    confirm_lesson,
    inspect_lessons,
    learn_lesson,
    render_context,
    revoke_lesson,
)

candidate = learn_lesson(
    triples="triples.jsonl", evidence="triple-id-1",
    scope="project/parser", memory="lessons.json",
)
inspection = inspect_lessons(memory="lessons.json")
# After the host has inspected the candidate:
confirm_lesson(candidate["id"], memory="lessons.json")
result = render_context(
    "Repair the request parser today.",
    scope="project/parser", memory="lessons.json",
)
# The host chooses whether to insert result["context"].
revoke_lesson(candidate["id"], memory="lessons.json")
```

`learn_lesson(*, triples, evidence, scope, memory, lesson=None, when=None)` returns
the lesson record. `confirm_lesson(id, *, memory)` and
`revoke_lesson(id, *, memory)` return its resulting record.
`recall_lessons(instruction, *, scope, memory, limit=3, disabled=False)` returns
bounded matches. `render_context` takes the same arguments and returns
`schema_version`, `enabled`, `scope`, `context`, `matches`, and `usage`.
`inspect_lessons(*, memory, limit=20)` returns `schema_version`, `total`, and
bounded `lessons`, including candidates and revoked records.

CLI success output is one JSON object. `learn`, `confirm`, and `revoke` wrap the
record as `{"schema_version": 1, "lesson": ...}`. `lessons` and `context` return
their API objects. Input and storage errors exit `2`, with a static stderr
diagnostic and no raw private content or exception body.

Stored records contain `id`, `version`, `status`, `interpretation`, `scope`,
`lesson`, `when`, and `provenance`. Status is `candidate`, `active`, or `revoked`;
interpretation is `source_verbatim` or `host_supplied`. The stable ID hashes the
version, attribution, scope, lesson, examples, and provenance. Confirming or
revoking changes status without changing that identity. Exact repeated teaching
is idempotent; changing the source corpus fingerprint or interpreted content
creates a different identity. A source-verbatim candidate with a truncated
correction snapshot cannot be confirmed: omitted text could contain a scope
exception. The caller must review the original source and supply an explicit
interpretation instead.

Provenance includes the positional `triple-id-N` identifier (counting nonempty
JSONL records), SHA-256 of the original corpus bytes, SHA-256 of the selected
raw JSONL line including its line ending, a bounded original `episode` snapshot,
and per-field `truncated` flags. Snapshot fields are `session`, `timestamp`,
`orig_prompt`, `prior_assistant`, `user_correction`, and `next_assistant`. They
are copied from the selected source, not generated from the interpretation.
These fingerprints establish identity against retained source bytes; they are
not signatures or proof that an interpretation is correct.

## Bounds and local storage

Memory and evidence paths must be explicit. No default home directory, parent
directory, corpus, index, model, telemetry sink, or hook is created. A missing
memory file means empty memory for inspection and context; learning creates it
only in an existing parent directory. Inputs must use physical directory paths:
symlinks in path components are rejected, including macOS `/var` and `/tmp`
aliases. Resolve an existing temporary directory with `pwd -P` or Python's
`Path.resolve()` before constructing its file paths.

The store is bounded to one MiB and at most 100 lessons, including tombstones.
The source corpus is bounded to 16 MiB, with a one-MiB record limit. Lesson text
is bounded to 1200 characters; there can be up to eight task examples of 240
characters each. Later instructions are bounded to 4000 characters. Context
returns at most five matches; inspection returns at most 100 records. The
original snapshot uses separate field caps and explicit truncation flags.
Bounds reject oversized inputs instead of silently discarding stored lessons.

New memory files and replacement files use owner-only permissions. Updates use
an exclusive temporary lock, identity/change checks, a synced temporary file,
and atomic replacement. Readers reject non-regular files, multiple hard links,
symlinks, malformed or duplicate-key JSON, unsupported schemas, invalid record
identities, and files changed during reading. A stale lock causes a visible
failure rather than an automatic takeover. Writers cooperating with this API
serialize updates; this is a local file store, not a hostile-writer database.

Evidence and inspection output contain private text. Context omits raw episode
text from its rendered string but its separate `matches` include provenance
snapshots for review. Treat returned JSON and the memory file as private. The
library performs no network access and never modifies the source corpus.
