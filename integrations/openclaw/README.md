# Hermeneutic × OpenClaw

Maturity: `MECHANICALLY_TESTED_INTEGRATION`. The plugin registers on
OpenClaw's native `reply_payload_sending` hook and checks visible reply text
with the local `hermeneutic gate` CLI before delivery. The plugin loaded in an
isolated OpenClaw v2026.9.5 state and runtime inspection confirmed the typed
hook registration. The actual Gateway/channel reply-delivery path was not
exercised.

## Install

Install Hermeneutic into an environment whose `hermeneutic` command is on the
OpenClaw Gateway's `PATH`, then link this plugin from an exact repository
checkout:

```bash
python3 -m pip install hermeneutic==0.1.12
openclaw plugins install --link ./integrations/openclaw --force --accept-capabilities
openclaw plugins enable hermeneutic
```

The install command explicitly accepts this hook's declared capability. Review
the plugin source before running it; native plugins execute in the Gateway
process.

Allow the plugin to use conversation hooks in `openclaw.json`:

```json
{
  "plugins": {
    "entries": {
      "hermeneutic": {
        "enabled": true,
        "hooks": { "allowConversationAccess": true }
      }
    }
  }
}
```

Merge those fields into the existing config. If `plugins.allow` is configured,
also add `hermeneutic` to that list. Inspect the loaded plugin with
`openclaw plugins inspect hermeneutic --runtime --json`.

Disable it with:

```bash
openclaw plugins disable hermeneutic
```

## Behavior and limits

- Clean and low-severity replies are unchanged.
- Medium/high findings append a short advisory naming up to three rule IDs.
- Only `payload.text` or, when that is absent, `payload.fallbackText.text` is
  checked. Media-only payloads are unchanged.
- The local CLI receives the text on stdin. The adapter uses no shell, has a
  2.5 second timeout and a 200 KB input limit, and fails open if the CLI is
  unavailable or returns an invalid result.
- The child process has both `HERMENEUTIC_TELEMETRY` settings removed from its
  environment. Stderr is discarded, and the plugin neither logs the response
  nor sends it over the network. The CLI's temporary stdout (which can include
  matched snippets) is parsed in memory for severity and rule IDs only.
- This is an advisory, not a fact-check: a clean result does not prove a claim
  true, and a finding does not prove it false. No model call or retry occurs.

The integration source is maintained by Hermes Labs. The OpenClaw adapter was
implemented with autonomous agent assistance; no production OpenClaw host or
channel was changed.
