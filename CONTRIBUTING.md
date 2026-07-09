# Contributing

Thanks for your interest in `hermeneutic`. This document describes how to propose changes.

## Scope

`hermeneutic` is a focused tool: it mines correction triples from chat logs and gates outgoing assistant drafts. It is **not** a general-purpose evaluation framework, nor a model benchmarker, nor an LLM router for production traffic.

**In-scope:** new chat-log readers, new evidence-based risk patterns, calibration recipes for `PressureProbe`, bug fixes, docs, test coverage.

**Out-of-scope:**

- Aggregate model evaluation — use a benchmark suite.
- Static analysis of prompt scaffolds — that belongs in [scaffold-lint](https://github.com/hermes-labs-ai/scaffold-lint).
- Agent-config structural analysis — that belongs in [lintlang](https://github.com/hermes-labs-ai/lintlang).
- Anything that adds a mandatory runtime dependency. Stage 2 (hermes-rubric) and stage 3 (your LLM) stay optional and pluggable.

Open an issue first if you're unsure.

## Development setup

```bash
git clone https://github.com/hermes-labs-ai/hermeneutic
cd hermeneutic
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running the checks

```bash
ruff check .
pytest -ra
```

CI runs the same commands on Python 3.10–3.13.

## Adding a new risk pattern

Patterns must be **evidence-based**: derived from real corrections you've mined.

1. Add the pattern to `_RAW_PATTERNS` in `src/hermeneutic/gates/regex.py` with `(rule_id, severity, regex, description)`.
2. Add a test in `tests/test_regex.py` covering both a draft it should flag and one it should not.
3. In the PR description, include: how many corrections in your mined corpus matched this pattern, and a sanitized example.
4. Update `CHANGELOG.md` under `[Unreleased]`.

Severity guide: `high` = strong drift signal that almost always warrants a downstream check. `med` = often associated with drift but more false positives. `low` = stylistic tell only.

## Adding a new chat-log reader

1. Subclass `LogReader` in `src/hermeneutic/triples.py`.
2. Implement `iter_turns(path) -> Iterator[(role, text, timestamp)]`.
3. Register your reader in the `READERS` dict.
4. Add a round-trip test in `tests/test_triples.py`.

## Pull request checklist

- [ ] `ruff check .` passes
- [ ] `pytest -ra` passes
- [ ] No new mandatory runtime dependency added
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] New rules / readers have tests
- [ ] No backward-incompatible API change without a major-version bump

## Filing issues

Minimum useful report: Python version, OS, exact command, draft text (or a minimal reproducer), observed output, expected output.

For mining-related issues, please include a sanitized example log entry that reproduces the problem.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

By contributing, you agree that your contributions are licensed under the MIT License (see [LICENSE](LICENSE)).
