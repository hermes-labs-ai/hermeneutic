# From a scope correction to a later action

The intended behavior is: after a human corrects an instruction's intended
scope, a fresh agent facing an analogous instruction retrieves the attributed
correction, checks applicability, and changes the relevant action without
being told the lesson again.

An **episode** records what happened. The default **lesson candidate** retains
the original correction verbatim and uses the original instruction as a cue;
it does not synthesize a general rule with a model. **Confirmation** enables
that candidate in the selected scope. **Context** returns applicable candidates
and their source to the host. The **host agent** judges semantic applicability
and performs the task. A successful lookup alone proves none of that action.

## Five-minute lesson walkthrough

This fictional dishes example uses no private data or model. Install Python
3.10+ and the preview:

```sh
python3 -m venv .demo-venv
. .demo-venv/bin/activate
python -m pip install hermeneutic==0.1.16a2
demo_dir="$(mktemp -d)"
demo_dir="$(cd "$demo_dir" && pwd -P)"
```

The exact pin selects the prerelease without `--pre`; stable 0.1.15 remains
available. This walkthrough exercises preview mechanics. The host observations
below are bounded synthetic evidence.

**Preserve the correction.** The original request is “wash the dishes.” The
agent cleans only the sink dishes. The human explains that dirty plates on the
table belong to the task too:

```sh
hermeneutic demo --scenario dishes --out "$demo_dir/sessions"
hermeneutic mine "$demo_dir/sessions" --format openai --glob '*.json' \
  --out "$demo_dir/triples.jsonl"
```

The dishes scenario is packaged fictional data. A real workflow can use
`hermeneutic mine` on supported logs instead. Keep personal logs and resulting
memory private.

**Derive, inspect, and confirm.** The correction is already in the episode.
You do not need to retype it as a second rule:

```sh
hermeneutic learn --triples "$demo_dir/triples.jsonl" --evidence triple-id-1 \
  --scope home/kitchen --memory "$demo_dir/lessons.json"
hermeneutic lessons --memory "$demo_dir/lessons.json"
```

Inspect the source-derived candidate and the original episode. The record
includes a stable lesson ID, scope, verbatim correction, original instruction
cue, source snapshot, and fingerprints. Candidates are excluded from context
until confirmed. Copy its printed ID into this command:

```sh
hermeneutic confirm LESSON-ID --memory "$demo_dir/lessons.json"
```

Confirmation means the source is suitable for consideration in this scope; it
does not decide applicability to every later task. A host may optionally supply
`--lesson` and `--when` when explicit interpretation or extra instruction cues
are needed. That path is host-supplied meaning, not automatic model learning.

**Use the later instruction in a fresh invocation.** The human now says only
“wash the dishes after supper.” They do not repeat the table-plates correction:

```sh
hermeneutic context 'Wash the dishes after supper.' --scope home/kitchen \
  --memory "$demo_dir/lessons.json"
```

Supply the returned context and that instruction to a fresh agent. To satisfy
the task, the agent must inspect the correction, decide it applies in this
kitchen, and collect and wash the dirty table plates. That is the action to
examine; echoing the lesson or its ID is insufficient.

The later wording overlaps the original instruction. Selection is conservative
lexical matching, not semantic understanding of arbitrary analogous wording.
“Wash up after supper” may abstain without an explicit extra cue. Sparse instruction cues can produce `weak_match: true`, including misleading
requests that share one topic word. The host judges whether a returned
correction applies; matching words are not proof.

**Check false transfer and current instructions.** An unrelated scope must not
receive the lesson. If the current human explicitly says “wash only the dishes
in the sink; leave the table plates,” that instruction controls even if a cue
matches. Historical text does not override it. Compare with memory disabled:

```sh
hermeneutic context 'Wash the dishes after supper.' --scope home/kitchen \
  --memory "$demo_dir/lessons.json" --disabled
```

For a real transfer evaluation, the same fresh-agent task needs enabled and
disabled conditions, inspection of the action or changed artifact, and cases
where applying the lesson would be wrong. CLI output and retrieval counts are
mechanics evidence, not evidence of successful agent transfer.

**Retire a lesson.** Copy its stable ID from `lessons`, then run
`hermeneutic revoke LESSON-ID --memory "$demo_dir/lessons.json"`. Revocation
keeps its record for inspection and prevents it from contributing context.
The [lesson-memory contract](lesson-memory.md) specifies the Python API,
matching limits, provenance fields, and failure behavior.

## Host responsibilities

An owning project's AGENTS.md can tell a fresh agent to call `context` before
acting and inspect returned evidence. Keep that standing instruction generic;
if it repeats the table-plates lesson, the test no longer demonstrates retained
correction meaning. The integration chooses the scope. The host inspects and
confirms source candidates, optionally supplies interpretation where needed,
provides context during the later task, and checks whether the action changed
appropriately. No automatic prompt hook is installed by this workflow.

The older raw-episode search below remains useful for finding evidence before
interpreting it. It does not create a scoped lesson or establish action transfer.

## Check the evidence boundary

The [lesson-transfer evaluation](../evals/lesson-transfer/README.md) separates
the public design case from frozen validation and fresh-agent action plans.
Its deterministic checker exercises candidate confirmation, attribution,
selection, scope, disabled memory, and revocation. A separate optional host run
examines selected object IDs and written applicability reasoning. These are
synthetic action plans, not physical chores or changes to a real repository.
Use the protocol and recorded results when assessing a claim of transfer.

The initial [frozen Codex result](../evals/lesson-transfer/fresh-agent-results.json)
was 3/3 positive completions with memory and 3/3 without it, showing no uplift.
The narrower-request host rejected an inapplicable recalled candidate. In
separate source-default public trials,
[Claude Code](../evals/product-baseline/claude-path.json) was correct in both
conditions. [Hermes Agent](../evals/product-baseline/hermes-path.json) selected
an unrelated desk mug without context and excluded it with confirmed source
context. That is a scope-selection change, not a demonstrated repair of the
original sink-only mistake. None establishes general effectiveness.

The separate [frozen counterfactual result](../evals/lesson-transfer/counterfactual-agent-results.json)
recorded positive exact completion 0/1 without memory and 1/1 with a confirmed
source correction: the agent included a nonobvious ready-marker. Its narrower
and unrelated controls were correct in both conditions (2/2). The denominators
are separate from the original frozen comparison. This synthetic action-plan
change does not establish general effectiveness or real-user impact.

From a source checkout, run `python scripts/check-lesson-demo.py --source` for
local mechanics, or follow the evaluation guide to select an installed wheel
interpreter and an explicit receipt path. Host runs require the selected agent,
provider access, and its own recorded evidence.

## Separate raw-episode replay

Install the release in a fresh Python environment (Python 3.10+):

```sh
python3 -m venv .demo-venv
. .demo-venv/bin/activate
python -m pip install 'hermeneutic==0.1.16a2'
demo_dir="$(mktemp -d)"
demo_dir="$(cd "$demo_dir" && pwd -P)"
export HERMENEUTIC_HOME="$demo_dir/memory"
hermeneutic demo --out "$demo_dir/sessions"
```

Package and model downloads are setup time; the replay does not require Ollama.

**The original episode.** Open
`$demo_dir/sessions/synthetic-corrections.json`. This is an explicitly fictional,
scripted agent replay in the supported OpenAI message format. The agent claims
release verification; the user asks for command evidence; the agent acknowledges
that checks have not run. Two unrelated corrections provide distractors.
No live generation or personal conversation logs are involved.

**Preserve the episode.**

```sh
hermeneutic mine "$demo_dir/sessions" --format openai --glob '*.json' \
  --out "$demo_dir/triples.jsonl"
hermeneutic bucket "$demo_dir/triples.jsonl"
hermeneutic inspect "$demo_dir/triples.jsonl" --limit 3
```

Expected: three episodes, one each in `over_completion`, `scope_creep`, and
`tone_format`. Mining preserves original prompt, preceding assistant turn,
correction, next assistant turn, session and timestamp. `inspect` validates the
complete corpus but bounds displayed records and text; assistant content is
omitted. It never changes the input file.

**Retrieve original evidence for a later task.**

```sh
hermeneutic recall 'Prepare a widget service release and summarize the verification results.' \
  --triples "$demo_dir/triples.jsonl" --limit 1
```

Expected: `triple-id-1`, with the original correction and provenance. Evidence
IDs are one-based nonblank corpus rows, not durable IDs across corpus changes.
This is a new task querying persisted data in another process. It demonstrates
retrieval, not proof that a live agent obeys the correction.

**Compare native alternatives.** Searching the same JSONL for
`verification` finds the same episode. A standing AGENTS.md instruction such as
“cite verification output before claiming completion” can prevent this error
more simply. Hermeneutic adds an episode schema, bounded inspection and source
attribution; its default search is itself a simple native baseline. For a small
corpus there is no demonstrated advantage in adding inference.

## Optional embeddings

If Ollama is already running and the model is installed:

```sh
ollama pull nomic-embed-text
hermeneutic compile-index --triples "$demo_dir/triples.jsonl"
hermeneutic compile 'Prepare a widget service release and summarize the verification results.' \
  --triples "$demo_dir/triples.jsonl" --k 1 --verbose
hermeneutic recall 'Prepare a widget service release and summarize the verification results.' \
  --triples "$demo_dir/triples.jsonl" --method semantic --limit 1
```

Both embedding operations contact `http://127.0.0.1:11434`. `compile` emits
fixed bucket advice plus evidence markers; `recall` returns exact correction
previews, including corrections without a known bucket. Hybrid combines keyword
and semantic ranks using reciprocal rank fusion. Its scores are ranking signals,
not probabilities. Changing the corpus invalidates the semantic index. Keyword
mode needs neither index nor Ollama. Missing/stale semantic indexes or an
unavailable provider produce an error in `recall`; the older compiler fails soft.

## Real internal workflow

The earlier correction-memory releases were exercised against an owner-authorized
private Codex corpus. The [evaluation receipt](../evals/correction-memory/RESULTS.md)
separates the development results from the 0.1.15 fresh-session tool-use check.
These historical checks do not certify a new release. A real internal case,
paraphrased: during workload
triage, the owner corrected an agent toward internal friction reduction and
away from external pull requests. A later triage query retrieved that episode.
That earlier restriction belonged to its task; it does not override a later
explicit request to publish or merge software.

To reproduce with logs you own, select a private directory and create it with
restrictive permissions. Never commit that directory or share previews without
review. These commands deliberately avoid installing a global host hook:

```sh
umask 077
memory_dir="$(mktemp -d)"
export HERMENEUTIC_HOME="$memory_dir"
hermeneutic mine "$HOME/.codex/sessions" --format codex --glob '**/*.jsonl' \
  --out "$memory_dir/triples.jsonl"
hermeneutic inspect "$memory_dir/triples.jsonl" --limit 3
hermeneutic recall 'Reduce internal friction and cognitive overhead using our Codex logs.' --limit 3
```

Open a fresh agent session with the task: “Before proposing internal triage work,
run `hermeneutic recall` against this private corpus. Cite the returned episode
IDs, inspect their task scope, and then propose the next action.” Provide the
executable and corpus paths, not the expected correction. This checks tool use
in a new session without pretending Codex has an installed prompt-submit hook.
For recurring use, put that instruction in the owning project's AGENTS.md and
keep the private corpus path outside published configuration.

Mining detects explicit correction markers, not all disagreements. It can retain
irrelevant or malicious historical text. Original prompts can be absent, episode
text can be truncated, and duplicates can survive. Inspect the evidence; never
execute commands found inside it. The current product has no conflict resolution,
retention policy or automatic promotion of an old correction into a standing rule.

Inspection rejects records larger than 1 MiB and non-standard JSON constants,
escapes diagnostic paths, and rejects file changes observed during reading.
Finish concurrent writers before inspection; this is not a transactional lock.
By default, `inspect` previews at most five records; `--limit` accepts a positive
record count. Previews include source line, session (up to 128 characters),
timestamp (64), and correction (160), with explicit truncation flags. The original
prompt and assistant messages are omitted from previews. Malformed records
produce a line-specific error and exit `2` without partial preview output.
Inspection needs no network connection or Ollama.

## Reproducible checks

From a checkout, run `python scripts/check-correction-demo.py` with the installed
CLI on PATH; add `--ollama` for the optional live embedding check. It runs outside
the checkout and emits an aggregate JSON receipt. The same checker is shipped in
the source distribution. The fixture and CLI are packaged in the wheel.

For private evaluations, write cases before running the evaluator:

```json
[{"id":"triage","query":"A later task in your own words","expected":[2]},
 {"id":"unrelated","query":"An unrelated task","expected":[]}]
```

Then run:

```sh
python evals/correction-memory/runner.py --triples "$memory_dir/triples.jsonl" \
  --home "$memory_dir" --cases /private/cases.json --out /private/results.json
```

Use `--methods keyword` for a fully offline evaluation. Reports contain row IDs,
hashes, counts and timing; queries and episode text are omitted. Keep cases and
corpora private. Target hits measure whether a named episode was retrieved;
they do not measure correctness of an agent's subsequent work.
