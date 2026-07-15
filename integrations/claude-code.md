# Hermeneutic × Claude Code

## Prompt-context compile hook

Maturity: `MECHANICALLY_TESTED_INTEGRATION`.

This is the supported Claude Code surface in v0.1.7. The corrected
`UserPromptSubmit` hook reads the submitted `prompt`, runs `hermeneutic
compile`, and, when retrieval produces a preamble, returns:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "<retrieved past-correction guidance>"
  }
}
```

That is the current documented Claude Code context-injection channel. Installer,
wrapper-output, malformed-input, missing-result, subprocess-failure, foreign-file
protection, and uninstall mechanics are tested locally. The v0.1.7 release gate
did not exercise a live Claude Code process, so this is not live-verified.

### Requirements

- Python 3.10 or newer.
- Claude Code initialized once so `~/.claude/` exists.
- Hermeneutic installed in the Python interpreter that runs the installer;
  the generated exec-form hook records that exact interpreter and passes the
  wrapper path separately in `args`.
- A local correction corpus and embedding index.
- Local Ollama with `nomic-embed-text` for index construction and prompt
  retrieval. Ollama is optional for Hermeneutic's deterministic gate, but it is
  required for this compile hook to inject anything.
- Release validation ran on macOS; Windows hook installation and execution were
  not exercised for v0.1.7.

Before PyPI publication is independently verified, install from the exact source
checkout or exact wheel artifact:

```bash
python3 -m pip install .
# or: python3 -m pip install /path/to/hermeneutic-0.1.7-py3-none-any.whl
```

After the v0.1.7 PyPI upload and clean public install are verified, this becomes
equivalent:

```bash
python3 -m pip install 'hermeneutic==0.1.7'
```

### Prepare retrieval, then install

```bash
hermeneutic mine "$HOME"/.claude/projects/*/ \
  --out "$HOME/.hermeneutic/triples.jsonl"
ollama pull nomic-embed-text
hermeneutic compile-index
hermeneutic compile --verbose "a representative prompt"
hermeneutic install-compile-hook
```

`compile --verbose` should confirm that the index loads and the local Ollama
probe succeeds. Its stdout can still be empty when no prior correction clears
the similarity threshold; that is a valid no-match result.

Use Claude Code's `/hooks` view to confirm the `UserPromptSubmit` entry. The hook
fails soft: no corpus, no index, no similar match, an unavailable Ollama process,
or an internal compile error produces no injected context and does not block the
prompt. This optional behavior never replaces the deterministic stage-one gate.

Uninstall only the Hermeneutic compile wrapper and its registered entry with:

```bash
hermeneutic uninstall-compile-hook
```

The installer is a wheel surface. It edits `~/.claude/settings.json` and writes
`~/.claude/hooks/hermeneutic-compile.py`; it preserves unrelated hook entries
and refuses to overwrite an unmarked file at that wrapper path. It recognizes
and removes the exact shell-form registration used by earlier Hermeneutic
installers. It does not print a settings diff for approval before writing and
currently targets `$HOME/.claude`, not `CLAUDE_CONFIG_DIR`.

No minimum Claude Code version was live-tested for v0.1.7. Use a release whose
hook reference documents `UserPromptSubmit` and
`hookSpecificOutput.additionalContext`.

## Built-in response Stop gate

Maturity: `REMOVE`.

Do not present `hermeneutic install-hook` as a supported v0.1.7 Claude Code
integration. The retained compatibility wrapper reads `transcript_path`, even
though current Claude Code documentation says a Stop-time transcript is not
guaranteed to contain the final answer and recommends `last_assistant_message`.
It also writes its advisory to stderr while exiting 0 instead of returning a
JSON `systemMessage`, the documented cross-platform user-warning channel. The
built-in wrapper additionally suppresses low-severity RISK output because those
advisories exit 0.

No live Claude Code run demonstrated the promised visible warning. The code may
remain for compatibility, but it must stay out of the ready-support matrix. If
it is already installed, remove it with:

```bash
hermeneutic uninstall-hook
```

## Standalone Claude plugin Stop gate

Maturity: `REMOVE`.

The repository/sdist plugin bundle has a valid-looking manifest and a locally
exercised gate script, but it uses the same transcript-reading and exit-0 stderr
warning path. Consequently, there is no supported install recipe for this
plugin in v0.1.7. It also requires Hermeneutic in the plugin command's `python3`
interpreter; the plugin bundle does not carry the Python package.

If an earlier recipe was used, remove the plugin and optionally its marketplace:

```text
/plugin uninstall hermeneutic-gate@hermeneutic
/plugin marketplace remove hermeneutic
```

Removing the marketplace also removes plugins installed from it. Review the
scope in Claude Code's plugin UI before removal.

Sources checked 2026-07-15:

- [Claude Code hooks reference](https://code.claude.com/docs/en/hooks)
- [Claude Code plugin installation and removal](https://code.claude.com/docs/en/discover-plugins)
