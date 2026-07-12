# Security Policy

## Supported versions

Only the latest released version receives security fixes.

| Version | Supported |
|---------|-----------|
| 0.1.7   | ✅        |
| < 0.1.7 | ❌        |

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security reports.

Email `roli@hermes-labs.ai` with subject `[security] hermeneutic`. Expect an acknowledgement within 5 business days.

Include:

- a minimal reproducer (input prompt + command)
- affected version
- observed vs expected behavior
- your disclosure timeline preference

## Attack surface

Honest inventory — this package is more than a pure text filter, and the
surface differs by subcommand:

**Always (gate, mine, bucket, harvest, promote):**

- reads text files / stdin from paths you pass
- runs regex heuristics over their content
- writes reports to stdout or to output paths you pass

**Compile layer (`compile`, `compile-index`):**

- makes HTTP requests to a **local** Ollama instance at `127.0.0.1:11434`
  (embeddings). No other network destination exists in the codebase; nothing
  is sent off-machine.
- reads/writes the local index under `~/.hermeneutic/`

**Hook installer (`install-hook`, opt-in command):**

- writes a hook script into `~/.claude/hooks/`
- edits `~/.claude/settings.json` to register it

**Audit log (opt-in via `HERMENEUTIC_TELEMETRY`):**

- appends JSONL to the local file path you set; in `raw` context mode that
  file contains draft text windows — treat it with the sensitivity of the
  logs it derives from. Off by default; never transmitted.

It does **not**:

- make network requests to anything other than localhost Ollama (and none at
  all unless you use the compile layer)
- execute user-provided code
- handle credentials, tokens, or secrets

Realistic threat model: (a) regex pathological inputs (ReDoS), (b) memory
pressure on very large inputs, (c) a hostile local process reading an opt-in
`raw`-mode audit log, (d) the hook installer modifying `~/.claude/settings.json`
— review the diff it prints before accepting.

## Supply chain

- SBOM at `sbom.cdx.json` (CycloneDX 1.5).
- Zero runtime dependencies — the SBOM lists only the package itself.

## History

No security vulnerabilities have been disclosed against this project.
