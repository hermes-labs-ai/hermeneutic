# Hermeneutic × OpenHands

Maturity: `DESIGN_SKETCH`.

OpenHands currently documents a `UserPromptSubmit` hook that can inject
`additionalContext`, so preventive correction context is a plausible direction.
Hermeneutic v0.1.7 does not ship an installable implementation:

- the former configuration referenced an absent
  `.openhands/hooks/hermeneutic_preamble.sh` helper;
- no code implements the claimed static overclaim-rule fallback;
- `hermeneutic compile` returns no preamble when the local corpus, index, Ollama
  process, or sufficiently similar correction is unavailable;
- no OpenHands host run exercised the input field, output, helper permissions,
  or uninstall path.

No executable hook configuration is provided for v0.1.7. A future recipe must
ship its helper, parse the documented `message` input, return valid
`additionalContext`, distinguish required corpus/index/Ollama setup from the
zero-dependency core gate, test fail-soft behavior, include file-permission and
uninstall steps, and carry a live-host receipt.

This would be preventive context injection, not an outgoing-response gate:
current OpenHands documentation does not establish a final-response-text field
for the relevant completion event. No minimum OpenHands version was tested.

If the obsolete sketch was copied into a project, remove only its
`user_prompt_submit` entry from `.openhands/hooks.json` and delete any locally
created Hermeneutic helper. Review unrelated hooks before deleting the whole
file.

Source checked 2026-07-15:
[OpenHands hooks](https://docs.openhands.dev/openhands/usage/customization/hooks).
