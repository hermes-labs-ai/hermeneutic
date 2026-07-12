# hermeneutic × Claude Code

Two paths; both advisory (never block), both reversible.

**Path 1 — one command (installs a Stop hook into `~/.claude/`):**

```bash
pip install hermeneutic
hermeneutic install-hook            # gate every assistant turn
hermeneutic install-compile-hook    # optional: past-corrections preamble on every prompt
# Restart Claude Code.
```

Idempotent, preserves your other hooks, refuses to overwrite files it didn't
create. Remove with `hermeneutic uninstall-hook` / `uninstall-compile-hook`.

**Path 2 — as a plugin (marketplace-managed, once the repo is public):**

```
/plugin marketplace add hermes-labs-ai/hermeneutic
/plugin install hermeneutic-gate@hermeneutic
/reload-plugins
```

The plugin (in [`claude-plugin/`](../claude-plugin/)) ships the same Stop-hook
gate, validated with `claude plugin validate --strict`. It still requires
`pip install hermeneutic` for the gate binary itself.

On a RISK, you see one line — `[hermeneutic] RISK — highest severity: high` —
with rule ids; the assistant is never blocked.
