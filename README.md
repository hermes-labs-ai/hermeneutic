<div align="center">

# Hermeneutic

<img src="https://raw.githubusercontent.com/hermes-labs-ai/hermeneutic/v0.1.15/assets/hermeneutic-banner.jpg" alt="Hermeneutic — understanding in between" width="900" />

**Correction evidence your next agent session can inspect.**

Save agent correction episodes, retrieve their original evidence in a later task, and check outgoing claims before they ship.

by [Hermes Labs](https://hermes-labs.ai)

[PyPI](https://pypi.org/project/hermeneutic/) · [Try correction memory](#try-correction-memory) · [Try the gate](#try-the-gate) · [Use your corrections](#use-your-corrections) · [Integrations](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/integrations/README.md)

</div>

Your agent says a feature is done before it has checked the work. You correct it. A week later, another session makes the same claim. Hermeneutic gives you two ways to close that loop: a **fixed, fast draft gate** for risky wording, and **personal correction memory** that retrieves past guidance when a similar task comes up. Either part can be used on its own.

The default onboarding below uses stable **0.1.15**. The local 0.1.16a1
candidate is an opt-in experimental build; it has not been released.

## Try correction memory

For developers whose agents need evidence from earlier corrections across sessions.
Python 3.10+ is sufficient; this replay needs no account, logs, model or server:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install hermeneutic==0.1.15
demo_dir="$(mktemp -d)"
hermeneutic demo --out "$demo_dir/sessions"
hermeneutic mine "$demo_dir/sessions" --format openai --glob '*.json' \
  --out "$demo_dir/triples.jsonl"
hermeneutic recall 'Prepare a widget service release and summarize the verification results.' \
  --triples "$demo_dir/triples.jsonl" --limit 1
```

The scripted agent initially claims release verification. The user corrects it
and the agent acknowledges checks have not run. The later task retrieves
`triple-id-1`: the original correction, its prompt and session/timestamp
provenance. The [five-minute guide](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/docs/correction-memory-demo.md) shows inspection,
optional embeddings and the real internal example separately.

The default is transparent keyword search over saved prompts and corrections.
It can miss paraphrases and return irrelevant evidence; the agent must check the
original scope. For one standing rule, a maintained AGENTS.md instruction is
simpler. Hermeneutic helps when you want to retain and search the episode behind
the rule. It does not establish that the agent will obey it.

The [public retrieval check](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/evals/correction-memory/public/README.md) can be rerun
without private data: offline keyword search found its target in 15/18 tasks and
returned no evidence for 4/8 unrelated questions. Optional embeddings recovered
more paraphrases and returned more unrelated candidates. These are small,
synthetic regression cases; [real internal use and its narrower evidence](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/evals/correction-memory/RESULTS.md)
are reported separately.

## Try the gate

Requires Python 3.10+. This first check needs no account, model, logs, or configuration:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install hermeneutic==0.1.15
printf '%s\n' 'Done — shipped 14 files, all tests pass.' | hermeneutic gate
```

The gate reports `RISK` for the precise completion and “all tests” claims and exits `1`. Try `printf '%s\n' 'Draft ready for review.' | hermeneutic gate` to see a `PASS` (exit `0`). For a real draft, use `hermeneutic gate --draft response.txt`. Unreadable or non-text input exits `2`.

The check highlights English wording that needs a closer look. It cannot tell whether a claim is true. You decide whether to revise, verify, or send the draft.

## Experimental language support

**0.1.16a1 is an unreleased opt-in experimental candidate.** Mapped-language
findings are advisory in the CLI, Router and shipped response consumers. Raw
canonical English findings retain enforcement, including in mixed drafts.
The independent evaluation does not establish reliable general-language coverage.

The experimental API provides vocabulary adapters for Korean (`ko`), Chinese (`zh`),
Japanese (`ja`), Turkish (`tr`), German (`de`), French (`fr`), Spanish (`es`), and
Portuguese (`pt`) through **trigger mapping**. Local phrases map to the triggers
the same English gate already checks. This is not translation or a separate
set of risk rules, and it adds no model calls or runtime dependencies.

```bash
printf '%s\n' '5개 파일을 수정했습니다.' | hermeneutic gate --lang auto
hermeneutic gate --draft response.txt --lang zh
```

The CLI keeps its English default. Mapping-dependent findings print
`ADVISORY` and do not cause exit 1 or automatic Router review/repair. Raw English
medium/high findings still cause CLI exit 1. `--lang auto` uses script and vocabulary
hints; select a code explicitly for ambiguous or short text. Japanese kana is
checked before Chinese Han characters; kanji-only Japanese needs `--lang ja`.
Shared Spanish/Portuguese vocabulary may fall back to English. One adapter is
selected per draft, so multilingual mixtures may need explicit selection.
Shipped response hooks enable automatic mapping before the gate. Their existing
advisory/retry behavior remains host-specific.

For Python callers, `hermeneutic.lang.risk_score(text, lang="auto")` returns hits
with spans and matched snippets in the original draft.
`Router(lang="auto")` enables mapping at stage 1 while downstream reviewers and
repairers receive the original text. `hermeneutic.risk_score` and the default
Router remain English-only.

Synthetic development-set results, replayed with explicit language selection:

| Language | Drafts caught | Clean drafts flagged |
| --- | --- | --- |
| Korean | 116/180 (64.4%) | 2/135 (1.5%) |
| Chinese | 16/20 (80.0%) | 0/20 (0.0%) |
| Japanese | 16/20 (80.0%) | 0/20 (0.0%) |
| Turkish | 16/20 (80.0%) | 0/20 (0.0%) |
| German | 16/20 (80.0%) | 0/20 (0.0%) |
| French | 15/20 (75.0%) | 0/20 (0.0%) |
| Spanish | 14/20 (70.0%) | 0/20 (0.0%) |
| Portuguese | 15/20 (75.0%) | 0/20 (0.0%) |

A catch means any gate hit, including a low-severity advisory. These are small
synthetic development sets, not held-out measurements or real-use coverage
estimates. Automatic Korean routing catches 116/180 (64.4%) with 2/135 (1.5%)
false fires; the other fixture results match explicit routing. Korean still misses
64/180 labeled drift drafts and flags a scope question and qualified stability
statement. These results do not support stable general-language coverage. See the
[synthetic validation methodology](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.16a1/evals/languages/README.md) and
[replayable receipt](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.16a1/evals/languages/results.json) for misses and limitations.

The recovered [independent simulated evaluation](evals/production-languages/README.md)
is stronger evidence of the current limits than the development fixtures above.
At its frozen candidate, held-out high-severity recall was Korean 2/30,
Japanese 0/30, Chinese 0/30 and Spanish 3/30 explicit or 2/30 auto.
False positives were Korean/Japanese 0/30, Chinese 1/30, Spanish 2/30 explicit
or 0/30 auto. None met both predeclared targets; these are model-authored
simulations, not native-speaker or production validation. The current bounded
Korean repairs were developed against the older synthetic corpus, not this
consumed holdout. The original frozen receipt and denominators are retained.

## Use your corrections

Use logs you own and keep the resulting corpus private. For Codex:

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
are also supported; see `hermeneutic mine --help`. Mining reads only supplied
paths and preserves local JSONL episodes. It uses explicit correction markers,
so it does not capture every disagreement or change the fixed gate.

For subsequent agent sessions, put an instruction in the owning project's
AGENTS.md to run `hermeneutic recall '<current task>' --triples /private/triples.jsonl`,
cite relevant episode IDs, and check their original task scope. This explicit
tool workflow was [verified in a fresh Codex session](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/evals/correction-memory/fresh-session-0.1.15.json).
It does not install a global host hook.

Keyword recall needs no index or inference. Optional semantic/hybrid recall and
the older advice compiler use local [Ollama](https://ollama.com/) embeddings:

```sh
export HERMENEUTIC_HOME="$memory_dir"
ollama pull nomic-embed-text
hermeneutic compile-index --triples "$memory_dir/triples.jsonl"
hermeneutic recall 'Finish the release and report what passed.' \
  --triples "$memory_dir/triples.jsonl" --method semantic
hermeneutic compile 'Finish the release and report what passed.' \
  --triples "$memory_dir/triples.jsonl"
```

Ollama runs at `http://127.0.0.1:11434`; model download is a separate setup step.
The compiler emits fixed category advice with episode references; it does not
use Ollama to generate guidance. On the [small real-log development set](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/evals/correction-memory/RESULTS.md),
keyword retrieval performed better than the embedding modes. Those results are
not held out and do not establish improved agent behavior.

Inspection rejects records larger than 1 MiB and non-standard JSON constants,
escapes diagnostic paths, and rejects file changes observed during reading.
Finish concurrent writers before inspection; this is not a transactional lock.

Before indexing, `inspect` validates the complete existing JSONL file and emits
at most five preview records by default; `--limit` accepts a positive record
count. Each JSON preview includes its source line, session (up to 128
characters), timestamp (64), and correction (160), with explicit truncation
flags. Prior/next assistant messages and the original prompt are omitted.
Malformed records produce a line-specific error and exit `2` without partial
preview output. Inspection reads the file without modifying it and needs no
network connection or Ollama. Previews can still contain private text; review
them before sharing.

## Where it fits

| Part | Put it here | Output |
| --- | --- | --- |
| Correction memory | Before or during a similar future task | Advisory context from prior corrections |
| Draft gate | Before an agent sends its response | `PASS` or `RISK` with matched patterns |

Use the standalone CLI in any workflow you control. The [integration guides](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/integrations/README.md) cover optional Claude Code, Codex, Gemini CLI, Qwen Code, OpenClaw, Hermes Agent, and other host paths. Integration capabilities vary by host; check the individual guide before expecting automatic gating or blocking. The [Python Router](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/docs/THEORY.md) is available if you want to compose your own review stages.

Hermeneutic's gate matches fixed English surface patterns and can miss a mistake or flag an innocent phrase. Correction retrieval depends on the history you supply and has not been shown to improve downstream outcomes across users. It is a way to surface previous guidance and scrutinize a draft, not a security boundary or a factuality guarantee.

[Worked example](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/examples/before_after.md) · [Integration guides](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/integrations/README.md) · [Evaluation results](https://github.com/hermes-labs-ai/hermeneutic/tree/v0.1.15/evals) · [Privacy and security](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/SECURITY.md) · [Contributing](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.15/CONTRIBUTING.md) · [Changelog](https://github.com/hermes-labs-ai/hermeneutic/blob/v0.1.16a1/CHANGELOG.md)

Apache-2.0. [Hermes Labs](https://hermes-labs.ai) builds agentic infrastructure for autonomous systems.
