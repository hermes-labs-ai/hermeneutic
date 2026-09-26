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
python -m pip install hermeneutic==0.1.12
printf '%s\n' 'Done — shipped 14 files, all tests pass.' | hermeneutic gate
```

The gate reports `RISK` for the precise completion and “all tests” claims and exits `1`. Try `printf '%s\n' 'Draft ready for review.' | hermeneutic gate` to see a `PASS` (exit `0`). For a real draft, use `hermeneutic gate --draft response.txt`. Unreadable or non-text input exits `2`.

The check highlights English wording that needs a closer look. It cannot tell whether a claim is true. You decide whether to revise, verify, or send the draft.

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
