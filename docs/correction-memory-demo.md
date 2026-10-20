# Correction memory: developer demonstration and internal use

Hermeneutic saves correction episodes and retrieves their original evidence for
later tasks. `recall` defaults to offline keyword retrieval. Optional semantic
and hybrid modes require local Ollama (`nomic-embed-text`); neither generates
advice with a language model. Retrieved corrections are historical evidence:
check their original scope against the current user's instructions.

## Five-minute public replay

Install the release in a fresh Python environment (Python 3.10+):

```sh
python3 -m venv .demo-venv
. .demo-venv/bin/activate
python -m pip install 'hermeneutic==0.1.14'
demo_dir="$(mktemp -d)"
export HERMENEUTIC_HOME="$demo_dir/memory"
hermeneutic demo --out "$demo_dir/sessions"
```

Before publication, install the exact checked-out source with `python -m pip
install .` instead of the version pin. Package/model downloads are setup time;
the presentation does not require Ollama.

**0:00–1:00 — agent gets corrected.** Open
`$demo_dir/sessions/synthetic-corrections.json`. This is an explicitly fictional,
scripted agent replay in the supported OpenAI message format. The agent claims
release verification; the user asks for command evidence; the agent acknowledges
that checks have not run. Two unrelated corrections provide distractors.
No live generation or personal conversation logs are involved.

**1:00–2:00 — preserve the episode.**

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

**2:00–3:00 — subsequent task retrieves evidence.**

```sh
hermeneutic recall 'Prepare a widget service release and summarize the verification results.' \
  --triples "$demo_dir/triples.jsonl" --limit 1
```

Expected: `triple-id-1`, with the original correction and provenance. Evidence
IDs are one-based nonblank corpus rows, not durable IDs across corpus changes.
This is a new task querying persisted data in another process. It demonstrates
retrieval, not proof that a live agent obeys the correction.

**3:00–4:00 — compare native alternatives.** Searching the same JSONL for
`verification` finds the same episode. A standing AGENTS.md instruction such as
“cite verification output before claiming completion” can prevent this error
more simply. Hermeneutic adds an episode schema, bounded inspection and source
attribution; its default search is itself a simple native baseline. For a small
corpus there is no demonstrated advantage in adding inference.

**4:00–5:00 — optional embeddings and limits.** If Ollama is already running
and the model is installed:

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

The release was exercised against an owner-authorized private Codex corpus.
The [evaluation receipt](../evals/correction-memory/RESULTS.md) states the bounded
results and limitations. A real internal case, paraphrased: during workload
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

## Public explanation

Hermeneutic turns agent corrections into inspectable evidence for later tasks.
We used it internally on owner-authorized Codex logs and checked retrieval in a
fresh session. The public demo uses fictional data so anyone can reproduce the
workflow without sharing conversations. In our small exploratory evaluation,
simple keyword retrieval performed better than the optional local embedding
modes. The release packages capture, bounded inspection and evidence recall;
it does not establish improved agent behavior or current upstream adoption.
