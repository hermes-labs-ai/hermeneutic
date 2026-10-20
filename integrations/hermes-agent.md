# Hermes Agent

## Incoming lesson context

Install `hermeneutic==0.1.16a2` where Hermes Agent's shell tools can invoke it.
Derive, inspect, and confirm a source-correction candidate with the
[dishes walkthrough](../docs/correction-memory-demo.md), without retyping the
correction into a second rule. Then give a fresh Hermes Agent session the
generic instruction from the
[shared recipe](lesson-context.md). The agent explicitly runs:

```sh
hermeneutic context '<current instruction>' --scope my-project \
  --memory /private/path/lessons.json
```

It must inspect the attributed correction, check applicability, and act under
the current instruction. Do not repeat the lesson in the session instruction.
This path requires a working Hermes Agent installation/provider, shell tools,
and access to the intended memory file. It installs no automatic incoming hook;
the existing outgoing plugin below does not call `context` or learn lessons.
A fresh-host action receipt is separate from local command or plugin tests.

The [public source-default trial](../evals/product-baseline/hermes-path.json)
supplied installed CLI context in fresh native Hermes Agent prompts. Without
context, the plan included an unrelated desk mug; with the confirmed source
correction, it selected only the sink bowl and table plate. This is a preview
scope-selection observation in a synthetic task, not recovery from sink-only
undercompletion, real-world work, or verification of automatic incoming hooks.
The outgoing plugin was not the mechanism delivering this context.

## Optional outgoing advisory plugin

Hermeneutic ships as an opt-in Hermes Agent pip plugin. It uses Hermes Agent's
native `transform_llm_output` hook, which runs once after the tool loop and
before the final response is delivered.

Install `hermeneutic` into the same Python environment as Hermes Agent, then
enable the discovered plugin:

```bash
python3 -m pip install hermeneutic==0.1.16a2
hermes plugins enable hermeneutic
```

The plugin runs Hermeneutic's fixed surface-pattern gate with automatic
experimental vocabulary mapping locally. Clean responses and low-severity findings pass through unchanged. When a medium- or
high-severity pattern creates an evidence obligation, the plugin appends a
short advisory naming the matched rule before delivery. It does not call a
model, read personal correction logs, block the response, or claim that a pass
proves correctness.

Disable it with:

```bash
hermes plugins disable hermeneutic
```

This integration follows Hermes Agent's `hermes_agent.plugins` entry-point and
`transform_llm_output` contracts. It remains `MECHANICALLY_TESTED_INTEGRATION`
until exercised in a released Hermes Agent installation.
