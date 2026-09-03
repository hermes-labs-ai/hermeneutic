# Hermeneutic × Gemini CLI

Maturity: `MECHANICALLY_TESTED_INTEGRATION` until a live Gemini turn and tagged
public gallery discovery are recorded.

Gemini CLI's native `AfterAgent` hook supplies the final `prompt_response` and
can reject it with a reason that becomes an automatic repair prompt. The root
`gemini-extension.json` and `hooks/hooks.json` register Hermeneutic's fixed,
offline epistemic gate on that lifecycle.

The adapter permits clean responses. On the first risky response it requests
one evidence-focused revision. If the retry is also risky,
`stop_hook_active` bounds the loop: the response is allowed with a visible
warning. Malformed input and internal errors fail open with a warning.

From an exact source checkout, validate and install locally:

```bash
gemini extensions validate .
gemini extensions link .
gemini extensions list
```

Exercise the adapter directly without a model call:

```bash
printf '%s\n' '{"prompt_response":"Done — shipped 14 files, all tests pass.","stop_hook_active":false}' \
  | python3 integrations/gemini-cli/hermeneutic_after_agent.py
```

Uninstall the linked extension with:

```bash
gemini extensions uninstall hermeneutic
```

The extension uses the source bundled in its own checkout and does not read the
optional personal correction corpus, call a model, or send response text over
the network. Hermeneutic flags surface wording; it does not establish whether a
claim is true.
