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
if ! tool=$(printf '%s' "$input" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_name", ""))' 2>/dev/null); then
  echo '{"cancel":false,"errorMessage":"[hermeneutic] hook could not parse the Cline event (advisory unavailable)"}'
  exit 0
fi
[ "$tool" != "attempt_completion" ] && { echo '{"cancel":false}'; exit 0; }
if ! text=$(printf '%s' "$input" | python3 -c 'import json,sys; d=json.load(sys.stdin); v=d.get("tool_input", {}).get("result", ""); print(v if isinstance(v, str) else "")' 2>/dev/null); then
  echo '{"cancel":false,"errorMessage":"[hermeneutic] hook could not parse completion text (advisory unavailable)"}'
  exit 0
fi
[ -z "$text" ] && { echo '{"cancel":false,"errorMessage":"[hermeneutic] completion text was absent (check the documented Cline payload key)"}'; exit 0; }
verdict=$(printf '%s' "$text" | hermeneutic gate 2>&1)
case "$verdict" in
  RISK*) echo '{"cancel":false,"errorMessage":"[hermeneutic] RISK: possible overclaim in completion claim (advisory)"}' ;;
  PASS*) echo '{"cancel":false}' ;;
  *) echo '{"cancel":false,"errorMessage":"[hermeneutic] gate unavailable; inspect the hook environment"}' ;;
esac
```

`cancel:false` keeps it advisory (hermeneutic's default stance); the
`errorMessage` surfaces in Cline's per-hook UI indicator. Set `cancel:true`
only if you deliberately want a hard block.

The recipe uses the same Python 3.10+ interpreter required by hermeneutic; it
has no separate `jq` dependency. It keys on the printed `RISK` verdict because
low-severity advisory hits intentionally exit 0.

> **UNVERIFIED:** the `tool_input.result` key name comes from a cached copy
> of docs.cline.bot/features/hooks/hook-reference (the live page would not
> render for our fetcher). Echo the stdin payload once to confirm the key in
> your Cline version.

Uninstall: `rm .clinerules/hooks/PreToolUse`.

Sources: docs.cline.bot/customization/cline-rules · cline.bot/blog/cline-v3-36-hooks (fetched 2026-07-12).
