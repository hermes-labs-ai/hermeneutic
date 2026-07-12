# hermeneutic × Windsurf (Cascade) — advisory response gate

**Prereqs:** `pip install hermeneutic`; Windsurf with Cascade hooks enabled.

`.windsurf/hooks.json` at the workspace root:

```json
{
  "hooks": {
    "post_cascade_response_with_transcript": [
      {
        "command": "bash -c 'python3 .windsurf/hooks/hermeneutic_gate.py'",
        "show_output": true
      }
    ]
  }
}
```

Cascade post-hooks architecturally **cannot block** — which matches
hermeneutic's advisory stance exactly: by the time the hook fires the
response has already reached you, and the gate's job is to flag it.
`hermeneutic_gate.py` reads the stdin JSON, extracts the last assistant
message from the transcript, pipes it to `hermeneutic gate`, and on exit 1
prints `[hermeneutic] RISK <rule-ids> — advisory, already sent` to stderr
(visible in the Cascade UI via `show_output: true`).

> **UNVERIFIED field:** the docs promise the `_with_transcript` variant
> carries the full transcript, but do not name the JSON key. Confirmed base
> fields: `agent_action_name`, `trajectory_id`, `timestamp`, `model_name`.
> Dump the stdin payload once (`cat > /tmp/cascade-payload.json`) to find
> the transcript key in your Windsurf version before relying on this.

Uninstall: delete `.windsurf/hooks.json`.

Sources: docs.windsurf.com/windsurf/cascade/hooks (→ docs.devin.ai/desktop/cascade/hooks), fetched 2026-07-12.
