# Hermeneutic × Codex

## Incoming lesson context in 0.1.16a2

Install `hermeneutic==0.1.16a2` in an environment accessible to Codex's shell
tools. Derive, inspect, and confirm a source-correction candidate with the
[dishes walkthrough](../docs/correction-memory-demo.md). The correction does not
need a second manually authored rule. Then use the [shared context recipe](lesson-context.md) in the project's
`AGENTS.md` or as a fresh-session instruction. It asks the host to run:

```sh
hermeneutic context '<current instruction>' --scope my-project \
  --memory /private/path/lessons.json
```

The host must inspect attributed evidence, decide applicability, and change the
relevant action under the current instruction. The standing instruction must
not repeat the lesson itself. This is explicit CLI use, not a newly installed
prompt hook. Shell access, host authentication/provider access, and permission
to read the lesson file are required. A successful CLI response alone does not
prove fresh-agent action transfer.

This is a preview workflow. Fresh native Codex action-plan trials received
explicit CLI-produced context. The [initial frozen comparison](../evals/lesson-transfer/fresh-agent-results.json)
and [public interpreted dishes trial](../evals/lesson-transfer/public-dishes-agent-results.json)
were correct in both conditions, with no uplift. A separate
[source-default counterfactual](../evals/lesson-transfer/counterfactual-agent-results.json)
changed a positive action plan while its controls remained correct. These
synthetic trials do not certify automatic project-instruction loading or the
Stop hook below; see the [evaluation boundary](../evals/lesson-transfer/README.md).

For outgoing reporting, use `hermeneutic gate --draft response.txt --json` when
you control the draft. Its findings inspect wording, not whether the action
occurred. Existing host adapters below have separate evidence boundaries.

No Codex host process was exercised in the v0.1.7 release gate. The labels below
describe local mechanics, not live integration certification.

## Copied Stop hook

Maturity: `MECHANICALLY_TESTED_INTEGRATION`.

The repository/sdist script at
`codex-plugin/scripts/codex-gate.py` matches the current documented Codex Stop
contract:

- input text comes from `last_assistant_message`;
- exit 0 always prints valid JSON;
- a RISK or missing dependency is returned through `systemMessage`;
- no `decision` field is emitted, because `decision: "block"` tells Codex to
  continue the turn rather than acting as an advisory warning.

Tests cover high- and low-severity RISK results, clean text, malformed input,
and a missing Hermeneutic dependency. They do not prove that a particular Codex
release displays the warning.

### Requirements and install

- Python 3.10 or newer.
- A source checkout or unpacked sdist; the copied script is not in the wheel.
- Hermeneutic installed in the same `python3` interpreter used by the hook.
- A Codex release whose current hook documentation and `/hooks` trust flow
  match the configuration below. v0.1.7 does not claim a live-tested minimum
  Codex version.
- A POSIX shell for the copy commands below. Windows hook setup was not
  exercised for v0.1.7.

From the exact v0.1.16a2 source checkout or unpacked source archive:

```bash
python3 -m pip install .
mkdir -p "$HOME/.codex/hooks"
cp codex-plugin/scripts/codex-gate.py "$HOME/.codex/hooks/hermeneutic-gate.py"
chmod 755 "$HOME/.codex/hooks/hermeneutic-gate.py"
```

After a verified PyPI release, `python3 -m pip install
'hermeneutic==0.1.16a2'` is an equivalent package-install step. The regex gate
uses no Ollama model or network access.

Add this matcher group to `~/.codex/hooks.json`, preserving any existing hooks:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/.codex/hooks/hermeneutic-gate.py\"",
            "timeout": 5,
            "statusMessage": "hermeneutic: checking last turn"
          }
        ]
      }
    ]
  }
}
```

Before opening Codex, mechanically smoke-test the installed script:

```bash
printf '%s\n' '{"last_assistant_message":"Done — shipped 14 files, all tests pass."}' \
  | python3 "$HOME/.codex/hooks/hermeneutic-gate.py"
```

Expected shape: one JSON object containing a `systemMessage` with `RISK`, and no
`decision` field. Then open Codex, use `/hooks` to inspect and trust the exact
hook definition, and run a synthetic turn before relying on it. That final host
step was not part of the v0.1.7 release gate.

Uninstall by removing only the Hermeneutic matcher group from
`~/.codex/hooks.json`, deleting
`~/.codex/hooks/hermeneutic-gate.py`, and confirming in `/hooks` that no
Hermeneutic source remains. No automated uninstaller ships for this copied path.

## Standalone Codex plugin bundle

Maturity: `MECHANICALLY_TESTED_INTEGRATION`.

`codex-plugin/` is a repository/sdist asset. Its gate script and manifest shape
are covered by local tests, and `hooks/hooks.json` uses Codex's documented
plugin-root convention. However, the repository does not ship the required
`.agents/plugins/marketplace.json` catalog entry, and no local-marketplace
installation was exercised in the ChatGPT desktop app. Therefore v0.1.7 does
not provide an executable plugin-install recipe or claim that the bundle is an
installable published plugin.

A future distributor must add a valid marketplace catalog, pin the selected release source,
verify installation in the supported desktop surface, review/trust the bundled
hook, verify the Python dependency, and provide matching uninstall instructions.
The Codex CLI can add, list, upgrade, and remove marketplace sources; current
official documentation directs authors to the ChatGPT desktop app to install
and test a local plugin.

## Forward-deployed notify sentinel

Maturity: `MECHANICALLY_TESTED_INTEGRATION`.

From an exact repository checkout or unpacked sdist, this explicit,
human-consented command installs a Codex `notify` program:

```bash
python3 forward-deployed/sentinel.py install
```

The installer is tested for idempotency, refusal to overwrite an existing
`notify` value, top-level TOML placement, and removal. It bakes the current
Python executable and checkout path into `~/.codex/config.toml`, so moving the
checkout or interpreter breaks the registration. The notify handler consumes
the documented `agent-turn-complete` payload and its `last-assistant-message`
field.

Desktop toasts additionally require `osascript` on macOS or `notify-send` on
Linux. On other systems, including unexercised Windows, the script only writes
its local `build/sentinel.log`; it does not produce a desktop toast. No live
Codex notify event or desktop notification was exercised for v0.1.7.

Uninstall with:

```bash
python3 forward-deployed/sentinel.py uninstall
```

Uninstall removes the Hermeneutic `notify` line only. It deliberately leaves
`~/.codex/config.toml.bak-hermeneutic` and `build/sentinel.log` for manual review
or deletion.

Sources checked 2026-07-15:

- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Build Codex plugins](https://learn.chatgpt.com/docs/build-plugins)
- [Codex notification configuration](https://learn.chatgpt.com/docs/config-file/config-advanced#notifications)
