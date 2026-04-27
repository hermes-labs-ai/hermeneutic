# Changelog

All notable changes to hermeneutic are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-04-25

### Added
- Triples miner (`hermeneutic.triples`) supporting Claude Code JSONL and OpenAI ChatCompletion formats.
- Stage 1 regex risk gate (`hermeneutic.gates.regex`) with 6 patterns derived from a 326-triple study.
- Stage 2 hermes-rubric adapter (`hermeneutic.gates.rubric`) — optional, used if `hermes-rubric` is on PATH.
- Stage 3 PressureProbe (`hermeneutic.gates.twin`) — generic LLM critic with bring-your-own calibration. Default: rigorous-skeptic.
- 3-stage Router (`hermeneutic.router`) with one-shot repair pass.
- CLI: `hermeneutic mine|bucket|gate`.
- 26 tests covering miner, regex gate, router, CLI.

### Notes
- Risk patterns are evidence-based: derived from 326 real user corrections across 1,423 sessions.
- The gate is correct only on drift modes already seen corrected. Re-mine periodically.
