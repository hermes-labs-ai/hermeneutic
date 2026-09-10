# Integrations

The current repository has live-verified ingestion and Qwen response-hook paths,
several adapters whose local mechanics are tested, and several ideas that are
intentionally not presented as runnable integrations. Release-specific claims
remain bound to their cited release or receipt.

## Maturity vocabulary

- `LIVE_VERIFIED_INTEGRATION`: exercised against real host or source data, with
  a committed public receipt.
- `MECHANICALLY_TESTED_INTEGRATION`: adapter behavior or packaging is covered by
  local tests and checked against current vendor documentation, but the live
  host was not exercised for the cited release or repository state.
- `SELF_CONTAINED_RECIPE`: every required project-owned asset and command is
  present, but the host path has no release-gate execution evidence.
- `EXPERIMENTAL_RECIPE`: runnable only with explicit experimental caveats.
- `DESIGN_SKETCH`: a direction, not an installable integration; required assets
  or host behavior are still missing.
- `PLANNED`: no implementation or runnable recipe ships in the current repository.
- `REMOVE`: not a ready surface because its documented runtime contract
  is known to be wrong. Compatibility code may remain, but it is unsupported.

## Outgoing-text and prompt-context surfaces

| Surface | Maturity | What the current repository supports |
|---|---|---|
| Hermes Agent final-output plugin | `MECHANICALLY_TESTED_INTEGRATION` | The pip entry point registers Hermeneutic's deterministic gate on Hermes Agent's native `transform_llm_output` hook. Medium/high findings append an advisory before delivery; clean and low-severity outputs are unchanged. See [Hermes Agent](hermes-agent.md). |
| Claude Code compile hook | `MECHANICALLY_TESTED_INTEGRATION` | The corrected `UserPromptSubmit` wrapper emits `hookSpecificOutput.additionalContext`; installer, output shape, fail-soft behavior, and uninstall mechanics are tested. Live Claude Code was not exercised. See [Claude Code](claude-code.md). |
| Claude Code built-in Stop gate | `REMOVE` | Current Claude Code recommends `last_assistant_message` and requires structured JSON for a user-visible warning. The retained adapter parses a transcript and writes stderr while exiting 0. Do not advertise or newly install it. |
| Claude Code standalone Stop plugin | `REMOVE` | The plugin has the same unsupported runtime warning path as the built-in Stop adapter. Its bundle may remain for compatibility, but it is not a supported integration. |
| Codex copied Stop hook | `MECHANICALLY_TESTED_INTEGRATION` | The shipped script consumes `last_assistant_message`, always returns valid JSON on exit 0, and uses `systemMessage` without a continuation decision. Script mechanics are tested; live Codex was not. See [Codex](codex.md). |
| Codex plugin bundle | `MECHANICALLY_TESTED_INTEGRATION` | Script and manifest shape are tested. The repository does not ship a Codex marketplace catalog, and plugin installation was not exercised live. |
| Codex notify sentinel | `MECHANICALLY_TESTED_INTEGRATION` | Install/refusal/uninstall and decision mechanics are tested. Live notifications and Windows were not exercised. |
| Gemini CLI `AfterAgent` gate | `MECHANICALLY_TESTED_INTEGRATION` | The native response-bearing hook requests one evidence-focused retry and then fails open with a warning. Manifest, hook output, bounded retry, and local host loading are tested. See [Gemini CLI](gemini-cli/README.md). |
| Qwen Code native `Stop` gate (unreleased) | `LIVE_VERIFIED_INTEGRATION` | A native `qwen-extension.json` points at a Qwen-only `Stop` hook config, because Qwen's Gemini converter copies hooks without translating event names and drops `AfterAgent`. The gate requests one evidence-focused revision, then allows with a visible warning. Qwen 0.23.2 hardcodes `stop_hook_active: true` on the first `Stop`, so bounding uses a per-session marker file instead of that flag. Clean, risky-repair, and still-risky bounded turns ran through the published 0.23.2 CLI; see the [receipt](../evals/qwen-code/RESULTS.md) and [Qwen Code guide](qwen-code/README.md). |
| Cursor via imported Claude hooks | `REMOVE` | Cursor's compatibility mechanism exists, but importing the unsupported Hermeneutic Claude Stop adapter does not make that adapter ready. See [Cursor](cursor.md). |
| Cursor native two-hook concept | `DESIGN_SKETCH` | The former recipe referenced two absent helpers and returned the wrong `stop` result shape. No executable recipe ships. |
| Windsurf / Cascade response hook | `REMOVE` | The former recipe referenced an absent helper and relied on `show_output` where current Windsurf docs say it does not apply. See [Windsurf](windsurf.md). |
| Cline completion hook | `REMOVE` | The former recipe used obsolete payload keys, an obsolete global path, and a non-visible advisory result. See [Cline](cline.md). |
| OpenHands prompt preamble | `DESIGN_SKETCH` | The host hook direction is plausible, but the helper is absent and the claimed no-corpus fallback does not exist. See [OpenHands](openhands.md). |
| Generic stdin / Python API adapter | `SELF_CONTAINED_RECIPE` | Pipe text to `hermeneutic gate` or call the library directly; no host-owned assets are required. |
| Forward-deployed harness | `MECHANICALLY_TESTED_INTEGRATION` | The repository/sdist kit's state machine, boot checks, report linter, final gate, and sentinel mechanics are tested. A real adopter receipt is still required for any deployment claim. See [`FORWARD-DEPLOYED-HARNESS.md`](../FORWARD-DEPLOYED-HARNESS.md). |

The forward-deployed harness is not a wheel workflow. It assumes a writable
source tree with the repository layout intact, the `dev` extra (including
pytest), and Bash for `evals/self_test.sh`. It writes mission state, boot
evidence, a local build queue or skip receipt, and a root report. A missing real
log corpus may be recorded as `not_exercised` or explicitly skipped while the
package-controlled checks still complete, so MISSION COMPLETE is not evidence
that real log harvesting ran. Native Windows execution was not exercised, and
the kit has no single reset/cleanup command.

The generic CLI verdict contract is not binary by exit status alone:

```bash
printf '%s\n' "$response" | hermeneutic gate
```

The command prints `PASS` or `RISK`. Exit 1 means a high- or medium-severity
RISK; exit 0 means either PASS or a low-severity advisory RISK; exit 2 means an
input error. A caller that must observe every RISK must inspect the printed
verdict or use the Python result, not only `$?`.

## Ingestion surfaces

Log readers are a separate axis from outgoing-response hooks.

| Reader surface | Maturity | Evidence boundary |
|---|---|---|
| Claude Code JSONL reader | `LIVE_VERIFIED_INTEGRATION` | The committed triple-mining receipt records a real 1,423-session Claude Code derivation run using the public miner. |
| Codex rollout reader | `MECHANICALLY_TESTED_INTEGRATION` | Parser and nested-log behavior are tested. The v0.1.7 public release packet does not include a standalone live-reader receipt. |
| OpenAI ChatCompletion JSON reader | `MECHANICALLY_TESTED_INTEGRATION` | Synthetic parser tests cover the documented JSON shape; no external live-log receipt ships. |
| Custom `LogReader` subclass | `SELF_CONTAINED_RECIPE` | The extension protocol and registration point ship in the library; the adopter supplies and tests its own reader. |

## Planned, not shipped

| Surface | Maturity | Current repository state |
|---|---|---|
| MCP server, including Goose/Zed/Warp/Kiro/Copilot/Antigravity hosts | `PLANNED` | No `hermeneutic mcp-serve` command, server implementation, or manifest ships. |
| GitHub Copilot CLI plugin | `PLANNED` | No plugin assets ship. |
| Antigravity plugin | `PLANNED` | No plugin assets ship. |
| OpenCode npm shim | `PLANNED` | No npm package or shim ships. |

## Distribution boundary

The wheel contains the library, CLI, and the built-in Claude hook installers.
Standalone plugin bundles, host recipes, the forward-deployed kit, and eval
receipts are repository/source-archive assets. Installing an sdist through pip
builds an installed wheel; it does not turn those repository assets into
site-packages resources. Clone the exact release tag or unpack the exact sdist
when a repository-only surface is required.

The earlier integration host contracts were checked against vendor documentation
on 2026-07-15. Qwen Code was checked independently against its published 0.23.2
bundle and live host on 2026-09-10; see its receipt for the exact boundary.
