# Hermeneutic × Cline

Maturity: `REMOVE`.

Hermeneutic v0.1.7 does not ship a supported Cline integration or executable
recipe. The former inline `PreToolUse` script does not match the current Cline
contract:

- current payloads nest the tool and parameters under `preToolUse.tool` and
  `preToolUse.parameters`, not top-level `tool_name` and `tool_input`;
- current global hooks live under `~/Documents/Cline/Hooks/`, not
  `~/Documents/Cline/Rules/Hooks/`;
- `errorMessage` is shown to the user when `cancel` is true, so
  `{ "cancel": false, "errorMessage": "..." }` is not a documented visible
  advisory channel.

Cline's documented task-completion hook does not supply final assistant response
text. A future integration must first identify a supported response-bearing
event or a genuinely visible advisory mechanism, ship and test the handler,
cover the current payload shape on each supported platform, and record a live
Cline run. The former `Cline >= v3.36` claim is removed because no minimum host
version was live-tested for v0.1.7.

If the obsolete recipe was installed, disable it in Cline's Hooks UI and remove
the Hermeneutic hook file from `.clinerules/hooks/` or
`~/Documents/Cline/Hooks/`, according to where it was placed. On macOS/Linux,
review other extensionless hook files before deleting a directory; Windows hook
execution was not exercised.

Source checked 2026-07-15:
[Cline hooks](https://docs.cline.bot/customization/hooks).
