# hermeneutic × OpenHands — compile-preamble nudge (not a response gate)

**Honest limitation first:** as of the July-2026 docs, no OpenHands hook
exposes the assistant's final response text (available events:
`pre_tool_use`, `post_tool_use`, `user_prompt_submit`, `stop`,
`session_start` — payloads carry tool names/inputs, not chat text). So a
true after-the-fact gate is not currently possible here. The closest honest
integration is **preventive**: inject hermeneutic's overclaim-avoidance
context before generation via `user_prompt_submit`.

**Prereqs:** `pip install hermeneutic`.

`.openhands/hooks.json` at the repo root:

```json
{
  "user_prompt_submit": [
    {
      "matcher": "*",
      "hooks": [
        { "command": ".openhands/hooks/hermeneutic_preamble.sh", "timeout": 10 }
      ]
    }
  ]
}
```

`hermeneutic_preamble.sh` runs `hermeneutic compile` on the prompt (or, with
no local corpus, emits the static overclaim-avoidance rules) and prints
`{"additionalContext": "<preamble>"}` — injected into the agent's context
each turn. Preventive, not detective: no RISK notice fires afterward,
because no hook can see the reply.

If OpenHands adds a response-bearing hook, a true gate recipe will replace
this file — watch the CHANGELOG.

Uninstall: delete `.openhands/hooks.json`.

Sources: docs.openhands.dev · docs.openhands.dev/openhands/usage/customization/hooks (fetched 2026-07-12).
