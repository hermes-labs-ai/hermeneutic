# Qwen Code 0.23.2 live extension receipt

Date: 2026-09-10

This receipt covers the Qwen Code host path only. The authenticated smoke used
the published `@qwen-code/qwen-code` 0.23.2 CLI with its Gemini provider and
`gemini-3-flash-preview`. It does not evaluate that model's quality or certify
other Qwen Code versions or providers.

## Compatibility-path falsification

Before the native Qwen files existed, Qwen recognized the checkout as a Gemini
extension and installed it with `Origin: Gemini`. The converted installation
still contained only the repository's `AfterAgent` hook. Inspection of the
published 0.23.2 bundle showed that the Gemini converter copies
`hooks/hooks.json` but does not translate hook event names, while Qwen's hook
registry accepts `Stop`, not `AfterAgent`. A local `extensions link .` also
stopped with:

```text
Configuration file not found at .../qwen-extension.json
```

This rejected the initial hypothesis that the existing Gemini extension alone
could gate Qwen responses. The repair therefore adds a native Qwen manifest and
Stop adapter while retaining the Gemini extension.

## Install and discovery

The exact source worktree was linked with the published CLI:

```bash
npx -y @qwen-code/qwen-code@0.23.2 extensions link .
npx -y @qwen-code/qwen-code@0.23.2 extensions list
```

Qwen reported:

```text
Extension "hermeneutic" linked successfully and enabled.
✓ hermeneutic (0.1.12)
Path: <exact source checkout>
Source: <exact source checkout> (Type: link)
Origin: QwenCode
Enabled (User): true
Enabled (Workspace): true
```

Debug startup reported `Hook registry initialized with 1 hook entries`. The
expanded command pointed at
`integrations/qwen-code/hermeneutic_stop.py`, and every observed Stop execution
ended successfully.

## Authenticated response smokes

The commands used `--auth-type gemini --model gemini-3-flash-preview`, an
environment-supplied API key, `--extensions hermeneutic`, plan approval mode,
JSON output, no model tool calls, and a 90-second wall-time bound. The prompts
requested controlled literal drafts so the host lifecycle, rather than model
judgment, was under test.

### Clean

Requested and final response:

```text
I changed the parser and ran its focused test.
```

The host completed after one main-model API request.

### Risky first draft, clean repair

First draft:

```text
Done — shipped 14 files, all tests pass.
```

Qwen's debug log recorded the Stop hook and:

```text
Hook system message: Hermeneutic requested one evidence-focused revision.
```

The continuation returned:

```text
I checked one named test; its result is recorded in the command output.
```

The final JSON result was that revised sentence. Qwen recorded two main-model
API requests and zero model tool calls.

### Risky first draft, still-risky repair

A system prompt deliberately required the same risky sentence even after the
repair request. Qwen recorded exactly two main-model API requests. The second
Stop completed successfully and logged:

```text
Hook system message: Hermeneutic still found evidence-obligation wording after the bounded retry: completion_with_number (high): Completion verb co-occurs with a numeric claim — verify the number is tool-derived.; completion_with_all_quantifier (high): Completion claim with universal quantifier — confirm scope coverage.
```

The run then exited successfully with the second risky draft; there was no
third model request. No per-session marker remained after either two-response
smoke.

## Mechanical edge coverage

`tests/test_qwen_code_extension.py` covers clean, risky-first, still-risky
retry, clean retry, missing or malformed payloads, an internal gate exception,
unwritable or undeletable bounded state, stale unrelated-state cleanup,
current-session no-expiry bounding, session isolation, the 0.23.2
`stop_hook_active: true` first-call regression, native manifest wiring,
shared Gemini/Qwen decision text, and source-distribution inclusion.

At this source state:

```text
python3 -m pytest -q tests/test_qwen_code_extension.py tests/test_gemini_cli_extension.py
..........................                                               [100%]
26 passed in 0.14s

python3 -m ruff check src tests integrations/gemini-cli/hermeneutic_after_agent.py integrations/qwen-code/hermeneutic_stop.py
All checks passed!
```
