# Hermes Agent

Hermeneutic ships as an opt-in Hermes Agent pip plugin. It uses Hermes Agent's
native `transform_llm_output` hook, which runs once after the tool loop and
before the final response is delivered.

Install `hermeneutic` into the same Python environment as Hermes Agent, then
enable the discovered plugin:

```bash
pip install hermeneutic
hermes plugins enable hermeneutic
```

The plugin runs Hermeneutic's fixed English surface-pattern gate locally. Clean
responses and low-severity advisories pass through unchanged. When a medium- or
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
