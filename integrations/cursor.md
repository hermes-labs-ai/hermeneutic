# Hermeneutic × Cursor

## Imported Claude hook path

Maturity: `REMOVE`.

Cursor currently documents loading compatible Claude Code hooks when third-party
configuration import is enabled. That host feature does not make Hermeneutic's
retained Claude Stop adapter ready: the adapter reads a transcript rather than
the documented final-message field and uses an exit-0 stderr warning instead of
a supported structured user-message channel. No live Cursor run exercised it.

Do not advertise `hermeneutic install-hook` as a Cursor integration. If an older
recipe installed it only for this purpose, remove it with:

```bash
hermeneutic uninstall-hook
```

Disabling Cursor's global third-party-import setting also disables other imported
plugins, skills, rules, and configuration, so it is not a targeted Hermeneutic
uninstall.

## Native Cursor hook direction

Maturity: `DESIGN_SKETCH`.

No runnable native Cursor recipe ships in v0.1.7. The former documentation
referenced absent `hermeneutic-log.sh` and `hermeneutic-notify.sh` helpers.
Although current Cursor input for `afterAgentResponse` includes the assistant
text as `text`, that event is observe-only. Current `stop` output uses
`followup_message`; the former Claude-shaped `{ "decision": "block", "reason":
... }` result is not the Cursor contract and would not provide the claimed
advisory behavior.

A future implementation needs shipped helpers under `.cursor/hooks/`, robust
state cleanup, an explicit notification/user-visibility mechanism, dependency
checks, install and uninstall tests, and a live Cursor receipt. Until then,
there is no version claim, installation command, or supported payload/result
contract.

If the obsolete sketch was copied into a project, remove its two entries from
`.cursor/hooks.json` and delete `.cursor/.hermeneutic-risk` plus any locally
created helper copies. Review other entries before deleting the whole hooks
file.

Sources checked 2026-07-15:

- [Cursor hooks](https://cursor.com/docs/hooks)
- [Cursor third-party hook compatibility](https://cursor.com/docs/reference/third-party-hooks)
