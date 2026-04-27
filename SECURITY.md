# Security Policy

## Supported versions

Only the latest released version receives security fixes.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Reporting a vulnerability

Please do **not** open a public GitHub issue for security reports.

Email `rbosch@lpci.ai` with subject `[security] scaffold-lint`. Expect an acknowledgement within 5 business days.

Include:

- a minimal reproducer (input prompt + command)
- affected version
- observed vs expected behavior
- your disclosure timeline preference

## Attack surface

This package:

- reads a text file (or stdin) from disk
- runs regex-based heuristics over its content
- writes a JSON or plain-text report to stdout

It does **not**:

- make network requests
- execute user-provided code
- shell out to subprocesses
- read or write files beyond the explicit argument
- handle credentials, tokens, or secrets

Realistic threat model: (a) regex pathological inputs (ReDoS), (b) memory pressure on very large inputs. The package has no privileged state.

## Supply chain

- The repository carries a staged [hermes-seal](https://hermes-labs.ai) v1 manifest at `.hermes-seal.yaml`. Signed out-of-band by the Hermes Labs internal sealing toolchain.
- SBOM at `sbom.cdx.json` (CycloneDX 1.5).
- Zero runtime dependencies — the SBOM lists only the package itself.

## History

No security vulnerabilities have been disclosed against this project.
