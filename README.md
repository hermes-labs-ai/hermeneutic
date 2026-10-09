<div align="center">

# Hermeneutic

<img src="assets/hermeneutic-banner.jpg" alt="Hermeneutic — understanding in between" width="900" />

**Stop correcting the same agent mistake twice.**

Mine corrections from your AI work logs, bring relevant lessons into the next task, and check outgoing claims before they ship.

by [Hermes Labs](https://hermes-labs.ai)

[PyPI](https://pypi.org/project/hermeneutic/) · [Try the gate](#try-the-gate) · [Use your corrections](#use-your-corrections) · [Integrations](integrations/README.md)

</div>

Your agent says a feature is done before it has checked the work. You correct it. A week later, another session makes the same claim. Hermeneutic gives you two ways to close that loop: a **fixed, fast draft gate** for risky wording, and **personal correction memory** that retrieves past guidance when a similar task comes up. Either part can be used on its own.

## Try the gate

Requires Python 3.10+. This first check needs no account, model, logs, or configuration:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install hermeneutic==0.1.13
printf '%s\n' 'Done — shipped 14 files, all tests pass.' | hermeneutic gate
```

The gate reports `RISK` for the precise completion and “all tests” claims and exits `1`. Try `printf '%s\n' 'Draft ready for review.' | hermeneutic gate` to see a `PASS` (exit `0`). For a real draft, use `hermeneutic gate --draft response.txt`. Unreadable or non-text input exits `2`.

The check highlights English wording that needs a closer look. It cannot tell whether a claim is true. You decide whether to revise, verify, or send the draft.

## Experimental language support

From this source branch, the draft gate supports Korean (`ko`), Chinese (`zh`),
Japanese (`ja`), Turkish (`tr`), German (`de`), French (`fr`), Spanish (`es`), and
Portuguese (`pt`) through **trigger mapping**. Local phrases map to the triggers
the same English gate already checks. This is not translation or a separate
set of risk rules, and it adds no model calls or runtime dependencies.
The pinned PyPI release above does not include these adapters yet.

```bash
python -m pip install -e .
printf '%s\n' '5개 파일을 수정했습니다.' | hermeneutic gate --lang auto
hermeneutic gate --draft response.txt --lang zh
```

The CLI keeps its English default. `--lang auto` uses script and vocabulary
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
| Korean | 116/180 (64.4%) | 4/135 (3.0%) |
| Chinese | 16/20 (80.0%) | 0/20 (0.0%) |
| Japanese | 16/20 (80.0%) | 0/20 (0.0%) |
| Turkish | 16/20 (80.0%) | 0/20 (0.0%) |
| German | 16/20 (80.0%) | 0/20 (0.0%) |
| French | 15/20 (75.0%) | 0/20 (0.0%) |
| Spanish | 14/20 (70.0%) | 0/20 (0.0%) |
| Portuguese | 15/20 (75.0%) | 0/20 (0.0%) |

A catch means any gate hit, including a low-severity advisory. These are small
synthetic development sets, not held-out measurements or real-use coverage
estimates. Automatic Korean routing catches 111/180 (61.7%) with 4/135 (3.0%)
false fires; the other fixture results match explicit routing. See the
[validation methodology](evals/languages/README.md) and
[replayable receipt](evals/languages/results.json) for misses and limitations.

## Use your corrections

If you have Claude Code session logs, mine correction episodes, group the recurring types, and build a local retrieval index:

```bash
hermeneutic mine ~/.claude/projects --format claude-code \
  --glob '**/*.jsonl' --out ~/.hermeneutic/triples.jsonl
hermeneutic bucket ~/.hermeneutic/triples.jsonl
ollama pull nomic-embed-text
hermeneutic compile-index --triples ~/.hermeneutic/triples.jsonl
hermeneutic compile 'Finish the release and report what passed.'
```

The last two commands need [Ollama](https://ollama.com/) running locally. If your logs contain a relevant correction, `compile` can return a short advisory preamble grounded in those past episodes. An empty result is possible when no match clears the threshold. The [worked example](evals/compile-walkthrough.md) shows the full path from a real correction to retrieved guidance. Codex and OpenAI message logs are also supported; see `hermeneutic mine --help` for the input formats.

Mining reads the paths you supply and stores local JSONL records. It does not silently teach new rules to the fixed gate. Retrieval uses local embeddings; it does not use Ollama to generate the guidance text.

## Where it fits

| Part | Put it here | Output |
| --- | --- | --- |
| Correction memory | Before or during a similar future task | Advisory context from prior corrections |
| Draft gate | Before an agent sends its response | `PASS` or `RISK` with matched patterns |

Use the standalone CLI in any workflow you control. The [integration guides](integrations/README.md) cover optional Claude Code, Codex, Gemini CLI, Qwen Code, OpenClaw, Hermes Agent, and other host paths. Integration capabilities vary by host; check the individual guide before expecting automatic gating or blocking. The [Python Router](docs/THEORY.md) is available if you want to compose your own review stages.

Hermeneutic's gate matches fixed English surface patterns and can miss a mistake or flag an innocent phrase. Correction retrieval depends on the history you supply and has not been shown to improve downstream outcomes across users. It is a way to surface previous guidance and scrutinize a draft, not a security boundary or a factuality guarantee.

[Worked example](examples/before_after.md) · [Integration guides](integrations/README.md) · [Evaluation results](evals/) · [Privacy and security](SECURITY.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

Apache-2.0. [Hermes Labs](https://hermes-labs.ai) builds agentic infrastructure for autonomous systems.
