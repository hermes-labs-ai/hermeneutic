# hermeneutic × Cursor — advisory response gate

**Easiest path (verified):** Cursor loads Claude Code hooks directly.
Enable *"Include third-party Plugins, Skills, and other configs"* in Cursor,
then:

```bash
pip install hermeneutic
hermeneutic install-hook     # writes the Claude Code Stop hook
```

Cursor's `Stop`↔`stop` mapping picks the hook up from `~/.claude/settings.json`
automatically — no Cursor-specific config needed. Remove with
`hermeneutic uninstall-hook`.

**Native alternative** — `.cursor/hooks.json` at the project root:

```json
{
  "version": 1,
  "hooks": {
    "afterAgentResponse": [
      { "command": "./hooks/hermeneutic-log.sh" }
    ],
    "stop": [
      { "command": "./hooks/hermeneutic-notify.sh", "loop_limit": 3 }
    ]
  }
}
```

`afterAgentResponse` is the only Cursor hook that receives the assistant's
final text (`.text` on stdin JSON), but it is fire-and-forget — it cannot
alert the user by itself. So the log script pipes `.text` to
`hermeneutic gate` and on exit 1 writes a flag file
(`.cursor/.hermeneutic-risk`); the `stop` hook checks the flag and emits
`{"decision":"block","reason":"[hermeneutic] RISK <rule-ids> — advisory"}`,
which Cursor translates into a visible follow-up message. Advisory by
design: the response has already rendered.

Uninstall: delete the two entries (or the file) and the flag file.

Sources: cursor.com/docs/hooks · cursor.com/docs/agent/third-party-hooks
(fetched 2026-07-12).
