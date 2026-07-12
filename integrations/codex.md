# hermeneutic × Codex CLI

Three paths, all advisory. Codex's hooks engine (stable since v0.124) is
deliberately compatible with Claude Code's hook taxonomy, and its `Stop`
payload carries `last_assistant_message` directly — no transcript parsing.

**Path 1 — Stop hook (recommended):** `~/.codex/hooks.json`

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python3 \"$HOME/.codex/hooks/hermeneutic-gate.py\"", "timeout": 5, "statusMessage": "hermeneutic: checking last turn" } ] }
    ]
  }
}
```

Copy [`../codex-plugin/scripts/codex-gate.py`](../codex-plugin/scripts/codex-gate.py)
to `~/.codex/hooks/hermeneutic-gate.py`. First run: approve the hook via
`/hooks` (one-time trust review). Two Codex-specific rules the script
already honors: Stop hooks **must print valid JSON** on exit 0, and
advisory-only means **never emitting a `decision` field** — on Codex Stop,
`"decision": "block"` does not block; it auto-continues the turn with your
reason as a new prompt.

**Path 2 — as a plugin:** [`codex-plugin/`](../codex-plugin/) ships the same
hook plugin-packaged. Add via a marketplace entry pointing at this repo,
then `/plugins` inside Codex to enable.

> Flag: the docs describe the enable step through the ChatGPT desktop app;
> CLI `/plugins` parity for local marketplace sources is not fully
> documented — test live before relying on it.

**Path 3 — notify hook (what the forward-deployed harness uses):**
`python3 forward-deployed/sentinel.py install` wires the desktop-notification
sentinel into `notify` in `~/.codex/config.toml` (parallel mechanism, not
superseded; reversible with `sentinel.py uninstall`).

Log mining works regardless: `hermeneutic mine ~/.codex/sessions --format codex`.
