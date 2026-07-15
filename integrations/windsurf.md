# Hermeneutic × Windsurf / Cascade

Maturity: `REMOVE`.

Hermeneutic v0.1.7 does not ship a supported Windsurf integration or executable
recipe. The former recipe had three release-blocking gaps:

- it referenced an absent `.windsurf/hooks/hermeneutic_gate.py` helper;
- it treated the transcript payload key as unknown, while current Windsurf docs
  specify `tool_info.transcript_path` for
  `post_cascade_response_with_transcript`;
- it relied on `show_output: true` to display an advisory, while current docs
  state that `show_output` does not apply to that hook.

The current transcript is JSONL under `~/.windsurf/transcripts/` and can contain
source files, command output, tool arguments, search results, rules, and full
conversation history. Windsurf also warns that its per-step schema may change.
Any future adapter must therefore ship a robust parser, use a real user-visible
notification or explicit local-log contract, disclose the transcript's data
sensitivity and retention behavior, provide install/uninstall tests, and carry
a live-host receipt.

No Windsurf version was tested. Do not infer support from the presence of
Cascade hooks.

If the obsolete configuration was copied into a project, remove only its
`post_cascade_response_with_transcript` entry from `.windsurf/hooks.json` and
delete any locally created Hermeneutic helper. Review other hook entries before
deleting the whole file.

Source checked 2026-07-15:
[Windsurf Cascade hooks](https://docs.windsurf.com/windsurf/cascade/hooks).
