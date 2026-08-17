# Security Policy

## Supported versions

Security fixes target the current maintained 0.1.x line.

| Version | Supported |
|---------|-----------|
| 0.1.9   | ✅        |
| 0.1.8   | ✅        |
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

- makes HTTP requests for embeddings to Ollama. The built-in CLI defaults to
  `127.0.0.1:11434`; Python callers can override the `ollama_embed()` URL and
  must assess that endpoint's transport and data policy.
- reads/writes the local index under `~/.hermeneutic/`

**Hook installers (`install-compile-hook` and compatibility-only `install-hook`, opt-in commands):**

- writes a hook script into `~/.claude/hooks/`
- edits `~/.claude/settings.json` to register it

**Audit log (opt-in via `HERMENEUTIC_TELEMETRY`):**

- appends JSONL to the local file path you set; in `raw` context mode that
  file contains draft text windows — treat it with the sensitivity of the
  logs it derives from. Off by default; never transmitted.

The built-in CLI defaults do **not**:

- make remote network requests; only the compile commands make HTTP requests,
  and their built-in endpoint is localhost Ollama
- handle credentials, tokens, or secrets

The core CLI does not execute text from the mined corpus. The optional Python
`Router` deliberately calls the rubric executable, judge, and repair functions
configured by the embedding application. Those components may use networks or
credentials and must be assessed separately.

Realistic threat model: (a) regex pathological inputs (ReDoS), (b) memory
pressure on very large inputs, (c) a hostile local process reading an opt-in
`raw`-mode audit log, (d) the hook installer modifying `~/.claude/settings.json`
without printing a preview, and (e) sensitive compile context being retained in
a host transcript. Back up and review host settings and local logs according to
your environment's policy.

## Supply chain

- SBOM at `sbom.cdx.json` (CycloneDX 1.5).
- Zero required Python runtime dependencies — the SBOM lists only the package
  itself. Optional external tools and caller-supplied Router backends are outside
  that dependency claim.

## History

No security vulnerabilities have been disclosed against this project.
