# Hermeneutic × Qwen Code

Maturity: `LIVE_VERIFIED_INTEGRATION`. Adapter decisions, bounding, and
manifest/hook wiring are covered by `tests/test_qwen_code_extension.py`. The
host contract below was checked against the published
`@qwen-code/qwen-code` 0.23.2 bundle, and clean, risky-repair, and bounded-risky
turns were exercised through that CLI. See the
[live receipt](../../evals/qwen-code/RESULTS.md).

## Why Qwen Code needs its own manifest and hook config

Qwen Code recognizes a Gemini-origin checkout and converts
`gemini-extension.json` into `qwen-extension.json` on install, but the converter
copies `hooks/hooks.json` **without translating event names**. Gemini's
`AfterAgent` is not a Qwen event, so the converted install registers nothing.
Qwen's native final-response event is `Stop`.

The root `qwen-extension.json` therefore ships as a native Qwen manifest and
points at a Qwen-specific hook config:

```json
{ "hooks": "integrations/qwen-code/hooks.json" }
```

Qwen prefers a root `qwen-extension.json` over `gemini-extension.json`, so
installing this repository into Qwen Code takes the native path and no
conversion happens. The Gemini manifest and `hooks/hooks.json` are untouched and
keep working in Gemini CLI.

Inside an external hooks file Qwen substitutes only `${CLAUDE_PLUGIN_ROOT}` —
`${extensionPath}` and `${/}` are hydrated in the manifest, not in a referenced
hook config — so the Stop command uses `${CLAUDE_PLUGIN_ROOT}`.

## Behavior

- A clean response is allowed.
- The first risky response is blocked once with a single evidence-focused repair
  reason, which Qwen feeds back to the model as the continuation prompt.
- The repaired response is allowed. If it is still risky, the allow carries a
  visible `systemMessage` warning.
- A malformed payload, a missing `last_assistant_message`, or any internal error
  fails open on exit 0 with a warning.

## Why `stop_hook_active` is ignored

Qwen Code 0.23.2's final-response dispatch hardcodes `stop_hook_active: true` in
the `Stop` input, including on the first call of a turn. The flag cannot
distinguish a first response from a repaired one. Reading it as "already
retried" would suppress every repair request; reading it the other way would
loop. The adapter ignores it.

## The bounded repair marker

Bounding instead uses one small marker file per session:

- Location: `$HERMENEUTIC_QWEN_STATE_DIR`, else `hermeneutic-qwen-stop/` under
  the OS temporary directory.
- Name: `hermeneutic-qwen-stop-<first 32 hex characters of sha256(session_id)>.marker.json`.
  The session id itself never appears in a path.
- Body: `{"schema": 1, "blocked_at": "<the host's event timestamp>"}`. No
  response text, no prompt, no session id, no working directory.
- Lifecycle: written when the adapter blocks; always consumed and deleted by the
  next `Stop` of the same session, whether that response is clean or risky and
  regardless of marker age. So one response gets at most one repair request and
  even a long repair cannot trigger a second block.
- Cleanup TTL: each run removes markers older than 30 minutes for other
  sessions. Only files matching the owned name above are eligible, so pointing
  `$HERMENEUTIC_QWEN_STATE_DIR` at a directory shared with other tools never
  deletes JSON this hook did not write. The current session's marker is never
  expired before consumption,
  because that would reintroduce a loop. If a blocked turn is cancelled or
  abandoned, the next response in that same session is therefore allowed once;
  this is the deliberate fail-open edge. The following response starts a fresh
  bounded attempt.

If the adapter cannot key or write a marker — no usable `session_id`, or an
unwritable state directory — it does not block. It allows the response with a
warning that it could not record a bounded repair attempt. A hook that blocks
without bounded state loops, so the unbounded case must fail open.

To clear all state by hand, delete the directory above; nothing else persists.

## Install from an exact source checkout

```bash
qwen extensions install . --consent
qwen extensions list
```

Or install an exact remote ref that contains `qwen-extension.json` (the file is
not present in the `v0.1.12` tag):

```bash
qwen extensions install https://github.com/hermes-labs-ai/hermeneutic \
  --ref <git-ref-containing-qwen-extension.json> --consent
```

After the change reaches `main` or a later tag, the explicit `--ref` can be
omitted.

Exercise the adapter directly, without a model call:

```bash
printf '%s\n' '{"hook_event_name":"Stop","session_id":"demo","stop_hook_active":true,"last_assistant_message":"Done — shipped 14 files, all tests pass.","timestamp":"2026-09-10T00:00:00.000Z"}' \
  | python3 integrations/qwen-code/hermeneutic_stop.py
```

The first invocation prints a `block` decision; a second invocation with the
same `session_id` prints the bounded allow with its warning.

Uninstall with:

```bash
qwen extensions uninstall hermeneutic
```

The extension runs the source bundled in its own checkout. It does not read the
optional personal correction corpus, call a model, or send response text over
the network. The regex rules come from `hermeneutic.gates.regex` and the shared
decision text from `hermeneutic.response_gate`; this adapter restates neither.
Hermeneutic flags surface wording; it does not establish whether a claim is true.
