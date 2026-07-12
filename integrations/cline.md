# hermeneutic × Cline — advisory completion-claim gate

**Prereqs:** `pip install hermeneutic`; Cline ≥ v3.36 (hooks), macOS/Linux.

Cline has no hook that carries the chat response text; its `TaskComplete`
hook fires *after* completion and its payload contains no message content.
The honest interception point is `PreToolUse` on `attempt_completion` —
the completion claim, checked before it lands.

Create an executable file named exactly `PreToolUse` (no extension) at
`.clinerules/hooks/PreToolUse` (project) or
`~/Documents/Cline/Rules/Hooks/PreToolUse` (global):

```bash
#!/usr/bin/env bash
input=$(cat)
tool=$(echo "$input" | jq -r '.tool_name')
[ "$tool" != "attempt_completion" ] && { echo '{"cancel":false}'; exit 0; }
text=$(echo "$input" | jq -r '.tool_input.result')  # UNVERIFIED key — see note
if ! echo "$text" | hermeneutic gate >/dev/null 2>&1; then
  echo '{"cancel":false,"errorMessage":"[hermeneutic] RISK: possible overclaim in completion claim (advisory)"}'
else
  echo '{"cancel":false}'
fi
```

`cancel:false` keeps it advisory (hermeneutic's default stance); the
`errorMessage` surfaces in Cline's per-hook UI indicator. Set `cancel:true`
only if you deliberately want a hard block.

> **UNVERIFIED:** the `tool_input.result` key name comes from a cached copy
> of docs.cline.bot/features/hooks/hook-reference (the live page would not
> render for our fetcher). Echo the stdin payload once to confirm the key in
> your Cline version.

Uninstall: `rm .clinerules/hooks/PreToolUse`.

Sources: docs.cline.bot/customization/cline-rules · cline.bot/blog/cline-v3-36-hooks (fetched 2026-07-12).
