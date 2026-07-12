# Integrations

hermeneutic gates AI responses wherever they're produced. Every integration
is **advisory by default** — it flags, it never blocks.

| Harness | Status | Path |
|---|---|---|
| **Claude Code** | ✅ native, one command — or plugin | [`claude-code.md`](claude-code.md) · `hermeneutic install-hook` or `/plugin install hermeneutic-gate@hermeneutic` |
| **Codex CLI** | ✅ native — Stop hook, plugin, or sentinel | [`codex.md`](codex.md) |
| **Cursor** | ✅ recipe — also loads Claude Code hooks directly | [`cursor.md`](cursor.md) |
| **Windsurf / Cascade** | ✅ recipe (one payload field unverified — flagged) | [`windsurf.md`](windsurf.md) |
| **Cline** | ✅ recipe (one payload field unverified — flagged) | [`cline.md`](cline.md) |
| **OpenHands** | ◐ preamble-only (no response-bearing hook exists there yet) | [`openhands.md`](openhands.md) |
| **Anything else** | pipe it | `echo "$response" \| hermeneutic gate` (exit 1 = RISK) · Python API |

### Next wave (tracked, not yet shipped)

- **MCP server** (`hermeneutic mcp-serve`) — next release. One listing covers
  Goose, Zed, Warp, Kiro, Copilot, Antigravity, and every other MCP host.
- **GitHub Copilot CLI plugin** — open `plugin.json` + `hooks.json` format,
  GA since Feb 2026; next release.
- **Gemini CLI:** sunset for individual users on 2026-06-18 in favor of
  Google's closed-source **Antigravity CLI**, which keeps hooks/plugins/MCP.
  We'll target Antigravity's plugin format once its docs stabilize (current
  third-party descriptions are unverified). **Qwen Code** (Gemini CLI fork,
  Apache-2.0) keeps the legacy hooks/extensions model — a recipe there is
  near-free and tracked.
- **OpenCode** npm plugin shim — tracked.

Recipes marked "unverified" carry the exact field-level caveat inline —
we ship what we verified against vendor docs and flag what we couldn't,
rather than inventing schema fields. Corrections welcome via PR.

Log **readers** (for `mine`/`harvest`) are a separate axis: Claude Code
JSONL, Codex CLI session rollouts, OpenAI ChatCompletion JSON — plus a
pluggable `LogReader` protocol for anything else (see README Extensibility).
