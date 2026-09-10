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

## Source-branch publication revalidation

Immediately before opening the public integration pull request on 2026-09-10,
the published Qwen Code 0.23.2 CLI installed the pushed source branch directly:

```bash
qwen extensions install https://github.com/hermes-labs-ai/hermeneutic \
  --ref codex/qwen-compat-20260910 --consent
```

Qwen identified the installation as `Origin: QwenCode`. Authenticated session
`3369294c-3e75-4fc6-9169-124967d4ed06` then repeated the risky-first,
clean-repair smoke above. The final result was the clean repair, the main model
made exactly two API requests, and model tools made zero calls.

After the final import-failure and state-file ownership hardening, authenticated
session `37717c72-d80a-4219-a542-eb8ce2fb1270` exercised the repaired local
checkout in Qwen's normal headless mode. The deliberately still-risky repair was
allowed after exactly two main-model requests with zero tool calls, confirming
that the hardened adapter still blocks once and does not loop.

## Marker contract observation

The documented marker contract was observed by driving the hook script itself,
as Qwen does, with a fresh `HERMENEUTIC_QWEN_STATE_DIR`. The script below ran
from the source checkout with `python3`:

```python
import hashlib, json, os, subprocess, sys, tempfile, time
from pathlib import Path

hook = "integrations/qwen-code/hermeneutic_stop.py"
state = Path(tempfile.mkdtemp()) / "state"
env = {**os.environ, "HERMENEUTIC_QWEN_STATE_DIR": str(state)}

def stop(session, message):
    payload = {"hook_event_name": "Stop", "session_id": session, "stop_hook_active": True,
               "last_assistant_message": message, "timestamp": "2026-09-10T00:00:00.000Z"}
    out = subprocess.run([sys.executable, hook], input=json.dumps(payload),
                         env=env, text=True, capture_output=True, check=True).stdout
    return json.loads(out)

print("decision:", stop("receipt-session", "Done — shipped 14 files, all tests pass.")["decision"])
(marker,) = state.iterdir()
digest = hashlib.sha256(b"receipt-session").hexdigest()[:32]
print("name matches prefix + sha256[:32] + suffix:",
      marker.name == f"hermeneutic-qwen-stop-{digest}.marker.json")
print("body:", marker.read_text())
print("modes:", oct(state.stat().st_mode & 0o777), oct(marker.stat().st_mode & 0o777))

bystander = state / "some-other-tool.json"
bystander.write_text('{"not": "ours"}')
for path, age in ((marker, 1801), (bystander, 1801)):
    os.utime(path, (time.time() - age, time.time() - age))
fresh = state / f"hermeneutic-qwen-stop-{'0' * 32}.marker.json"
fresh.write_text('{"schema": 1, "blocked_at": null}')
os.utime(fresh, (time.time() - 1799, time.time() - 1799))
print("other-session clean run:", stop("another-session", "I ran the focused test."))
print("remaining:", sorted(p.name for p in state.iterdir()))
```

Output:

```text
decision: block
name matches prefix + sha256[:32] + suffix: True
body: {"schema": 1, "blocked_at": "2026-09-10T00:00:00.000Z"}
modes: 0o700 0o600
other-session clean run: {'continue': True}
remaining: ['hermeneutic-qwen-stop-00000000000000000000000000000000.marker.json', 'some-other-tool.json']
```

Here is what each line shows. The marker is named from the first 32 hex
characters of SHA-256 of the session id. Its body is schema `1` plus the host
timestamp. The state directory is `0700` and the marker is `0600`. A later run
from another session swept the owned marker that was 1801 seconds old. It kept
the owned marker that was 1799 seconds old, which brackets the 1800-second
(30-minute) TTL. It also kept the equally old non-owned `some-other-tool.json`,
because only the owned name shape is eligible for cleanup.

## Mechanical edge coverage

`tests/test_qwen_code_extension.py` covers clean, risky-first, still-risky
retry, clean retry, missing or malformed payloads, an internal gate exception,
unwritable or undeletable bounded state, a hostile pre-existing marker symlink
(rejected, target unmodified), partial-marker cleanup after a failed write,
private default state and marker modes, unsafe
override state directories, stale unrelated-state cleanup,
current-session no-expiry bounding, session isolation, the 0.23.2
`stop_hook_active: true` first-call regression, native manifest wiring,
shared Gemini/Qwen decision text, and source-distribution inclusion.

At this source state:

```text
python3 -m pytest -q tests/test_qwen_code_extension.py tests/test_gemini_cli_extension.py
.................................                                        [100%]
33 passed in 0.19s

python3 -m ruff check src tests integrations/gemini-cli/hermeneutic_after_agent.py integrations/qwen-code/hermeneutic_stop.py
All checks passed!
```
