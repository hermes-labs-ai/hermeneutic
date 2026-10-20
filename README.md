<div align="center">

# Hermeneutic

<img src="https://raw.githubusercontent.com/hermes-labs-ai/hermeneutic/v0.1.16a2/assets/hermeneutic-banner.jpg" alt="Hermeneutic — understanding in between" width="900" />

**Carry the meaning of a correction into the next task.**

Preview: attributed, scoped correction memory for coding agents.

by [Hermes Labs](https://hermes-labs.ai)

[PyPI](https://pypi.org/project/hermeneutic/) · [Try correction memory](#try-correction-memory) · [Host workflow](#use-it-in-a-fresh-agent-session) · [Draft gate](#try-the-gate) · [Integrations](integrations/README.md)

</div>

You ask an agent to wash the dishes. It washes only the dishes in the sink. You
correct it: the dirty plates on the table belong to that task too. Later, a
fresh agent receives “wash the dishes after supper.” You should not have to
teach the same scope correction again.

Hermeneutic derives a reviewable lesson candidate from the original correction
and instruction. Inspect that attributed source and confirm it for the project's
scope. A fresh agent can then retrieve it for a later instruction, check whether
it applies, and change the relevant action. The current instruction controls
when it conflicts with historical context.

You correct the agent once; the default path does not ask you to rewrite that
correction into a second rule. It retains the source correction verbatim rather
than synthesizing a general rule with a model. The host supplies semantic
applicability judgment. Keep it in a workflow when corrected meaning needs to
survive sessions with evidence you can inspect, scope, confirm, and revoke.

## Try correction memory

Requires Python 3.10+. Install preview **0.1.16a2**:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install hermeneutic==0.1.16a2
```

The exact version pin selects this prerelease; no `--pre` flag is needed.
Stable **0.1.15** remains available. The lesson workflow is a preview with
bounded synthetic host evidence, not a demonstrated general improvement.

This packaged fictional episode needs no personal logs, model, account, or
server. Preserve the original correction and derive its candidate:

```sh
demo_dir="$(mktemp -d)"
demo_dir="$(cd "$demo_dir" && pwd -P)"
hermeneutic demo --scenario dishes --out "$demo_dir/sessions"
hermeneutic mine "$demo_dir/sessions" --format openai --glob '*.json' \
  --out "$demo_dir/triples.jsonl"
hermeneutic learn --triples "$demo_dir/triples.jsonl" --evidence triple-id-1 \
  --scope home/kitchen --memory "$demo_dir/lessons.json"
hermeneutic lessons --memory "$demo_dir/lessons.json"
```

The second shell line resolves the temporary directory to its physical path;
lesson inputs reject symlink path components. `learn` uses the original
correction as a verbatim candidate and the original instruction as its lexical
cue. It retains provenance and fingerprints. Candidates do not contribute
context until confirmed.

Inspect the candidate and its original episode. Copy its printed lesson ID
into the confirmation command; no rewriting of the correction is required:

```sh
hermeneutic confirm LESSON-ID --memory "$demo_dir/lessons.json"
hermeneutic context 'Wash the dishes after supper.' --scope home/kitchen \
  --memory "$demo_dir/lessons.json"
```

The later instruction contains no reminder about table plates. Give the
returned context and that instruction to a fresh agent. It must inspect the
attributed correction, check that the home/kitchen scope still applies, and
include collecting the dirty table plates in its action. Printing a matching
lesson alone does not demonstrate action transfer. The
[five-minute guide](docs/correction-memory-demo.md) adds a disabled-memory
comparison, false-transfer checks, and revocation.

The default selector uses conservative lexical overlap with the source
instruction, not arbitrary paraphrase understanding. For example, “wash up
after supper” can abstain without an explicit host-supplied cue. The host can
supply a richer interpretation and examples with `--lesson` and `--when`, but
that is an optional interpretation step. Sparse cues can return a `weak_match`
that needs particular scrutiny. A matching cue is still only a candidate for
applicability. For a standing instruction that needs no
provenance, a maintained AGENTS.md rule can be simpler.

## Use it in a fresh agent session

The host owns the loop from a correction to changed behavior:

1. Preserve the original episode with `mine` or another supported source.
2. Call `learn` with its evidence ID and integration-owned project scope.
   Inspect the source-derived candidate, then confirm it. Optional explicit
   interpretation is available when the source needs clarification.
3. Before a later task, call `context` with the new instruction and the same
   project scope. Supply that context to the fresh agent.
4. Have the agent check the source and applicability, then act under the current
   instruction. Inspect the resulting action, including cases where the lesson
   should not transfer.
5. Report the action and its evidence. The separate outgoing draft gate can flag
   overclaiming in that report; it does not prove the action occurred.

For a coding project, the standing AGENTS.md instruction should ask the agent to
run `hermeneutic context '<current instruction>' --scope <project> --memory
/private/lessons.json` and inspect applicable sources. It should not repeat the
lesson itself. No automatic global host hook is installed.

Use `hermeneutic lessons --memory /private/lessons.json` to inspect saved lessons,
`hermeneutic revoke LESSON-ID --memory /private/lessons.json` to retire one, and
`context ... --disabled` for a no-memory comparison. See the
[lesson-memory contract](docs/lesson-memory.md) for the Python API, matching,
provenance, limits, and failure behavior.

The initial [frozen Codex comparison](evals/lesson-transfer/fresh-agent-results.json)
completed its positive tasks 3/3 with memory and 3/3 without it: no measured
uplift. Its controls recorded no extra actions; the host rejected a retrieved
candidate when the current instruction explicitly narrowed scope.

A separate [frozen counterfactual](evals/lesson-transfer/counterfactual-agent-results.json)
recorded a changed action plan: the positive case went from 0/1 exact completion
without memory to 1/1 with a confirmed source correction, adding a nonobvious
ready-marker. Its narrower and unrelated controls were correct in both
conditions (2/2). This is a bounded synthetic demonstration with separate
denominators; it does not establish general effectiveness.

In separate public design trials, [Claude Code](evals/product-baseline/claude-path.json)
selected the correct objects with and without source-derived context.
[Hermes Agent](evals/product-baseline/hermes-path.json) included an unrelated
desk mug without context and selected only the sink bowl and table plate with
it. That is an observed scope-selection change, not recovery from sink-only
undercompletion. These are synthetic action plans supplied through explicit
host prompts, not physical chores or real repository changes. The
[evaluation guide](evals/lesson-transfer/README.md) separates public design,
frozen validation, and additional counterfactual evidence; inspect those
receipts before interpreting a transfer claim.

## Use your own corrections

Mine logs you own and keep the resulting corpus and lesson memory private.
For Codex:

```sh
umask 077
memory_dir="$(mktemp -d)"
hermeneutic mine "$HOME/.codex/sessions" --format codex --glob '**/*.jsonl' \
  --out "$memory_dir/triples.jsonl"
hermeneutic inspect "$memory_dir/triples.jsonl" --limit 3
hermeneutic recall 'Finish the release and report what passed.' \
  --triples "$memory_dir/triples.jsonl"
```

Claude Code (`--format claude-code`) and OpenAI message files (`--format openai`)
are also supported. Raw `recall` searches original episodes; it does not create
lesson candidates. Inspect an episode's meaning and scope before confirming one.
Mining detects explicit correction markers, so it misses some corrections. Retrieved text can contain irrelevant or malicious historical
instructions; it is evidence to inspect, not a command or higher authority.

The [public retrieval regression](evals/correction-memory/public/README.md)
exposes missed paraphrases and irrelevant candidates in raw episode search.
[Historical internal results](evals/correction-memory/RESULTS.md) and the
[0.1.15 fresh-session tool-use check](evals/correction-memory/fresh-session-0.1.15.json)
measure narrower behavior. Retrieval counts and successful tool calls do not
establish downstream lesson application or general improvement across users.

## Try the gate

The separate fixed offline gate inspects outgoing wording. It does not learn
from lesson memory. Requires Python 3.10+:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install hermeneutic==0.1.16a2
printf '%s\n' 'Done — shipped 14 files, all tests pass.' | hermeneutic gate
```

The gate reports `RISK` for the precise completion and “all tests” claims and exits `1`. Try `printf '%s\n' 'Draft ready for review.' | hermeneutic gate` to see a `PASS` (exit `0`). For a real draft, use `hermeneutic gate --draft response.txt`. Unreadable or non-text input exits `2`.

The gate flags fixed surface patterns such as completion overclaiming, relayed
authority, and unsupported certainty. It cannot establish whether a claim is
true. Review the finding, add evidence, or revise the draft.

## Structured draft reports

The optional structured interface uses the same gate without parsing terminal
prose:

```python
from hermeneutic import check_draft

report = check_draft("Draft ready for review.")
payload = report.to_dict()
if report.should_block:
    print("Review the findings before delivery:", payload["findings"])
```

`hermeneutic gate --draft response.txt --json` returns finding origins,
blocking decisions, and original-draft coordinates. Matched text is omitted by
default; `--include-text` or `to_dict(include_text=True)` opts into bounded
snippets. See the [report contract](docs/gate-json.md). The optional
[Python Router](docs/THEORY.md) composes caller-selected review and repair stages
and is separate from lesson memory and the offline gate.

## Experimental language mapping

This package is a preview; draft-gate language mapping also remains experimental.
Adapters for Korean (`ko`), Chinese (`zh`), Japanese (`ja`), Turkish (`tr`),
German (`de`), French (`fr`), Spanish (`es`), and Portuguese (`pt`) map vocabulary
into the fixed English rules. Use `hermeneutic gate --lang auto` or an explicit
code; English remains the CLI default.

Mapped findings remain advisory at any severity in shipped consumers. Raw
English medium/high findings retain enforcement, including in mixed drafts.
Automatic routing selects one adapter and can be ambiguous; diagnostic severity
alone does not imply blocking. These adapters do not interpret or learn lessons.

The [independent simulated evaluation](evals/production-languages/README.md)
shows the limits: frozen-candidate high-severity recall was Korean 2/30,
Japanese 0/30, Chinese 0/30, and Spanish 3/30 explicit or 2/30 auto. None met both
predeclared quality targets. These are model-authored simulations, not
native-speaker or production validation. The
[current-source regression replay](evals/production-languages/current-regression.json)
uses those now-exposed cases and is not a fresh holdout. Smaller
[synthetic development fixtures](evals/languages/README.md) do not establish
real-language coverage or justify enforcement.

[Lesson guide](docs/lesson-memory.md) · [Integration boundaries](integrations/README.md) · [Evaluation receipts](evals/) · [Roadmap](docs/ROADMAP.md) · [Privacy and security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

Apache-2.0. [Hermes Labs](https://hermes-labs.ai) builds agentic infrastructure for autonomous systems.
