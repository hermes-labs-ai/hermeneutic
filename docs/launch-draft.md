# Owner preview launch draft — Hermeneutic 0.1.16a2

Draft for owner review. This file is not a publication or evidence of delivery.

---

You ask an agent to wash the dishes. It washes only the sink dishes. You
correct it: the dirty plates on the table count too. When a fresh agent later
gets “wash the dishes after supper,” you should not have to teach that scope
correction again.

Hermeneutic derives a lesson candidate from the original correction and
instruction. Inspect and confirm it for the project scope without rewriting
the correction into a second rule. Before a later task, the host retrieves
attributed context. The fresh agent checks applicability and uses the correction
to change the relevant action under the current instruction.

This is a preview, with stable 0.1.15 still available. Install the exact
prerelease pin to try the loop with a packaged fictional episode:

```sh
python3 -m pip install hermeneutic==0.1.16a2
demo_dir="$(mktemp -d)"
demo_dir="$(cd "$demo_dir" && pwd -P)"
hermeneutic demo --scenario dishes --out "$demo_dir/sessions"
```

The [walkthrough](correction-memory-demo.md) shows how to preserve the episode,
derive and confirm its source candidate, request context in a fresh invocation,
and inspect the resulting action. It includes disabled-memory and false-transfer
checks. No model, account, or server is required for the local memory commands.

The default candidate retains the correction verbatim; it is not model
synthesis. A host may explicitly add interpretation when the source needs it.
Matching is a conservative lexical baseline over instruction cues. It can miss
unseen paraphrases or retrieve a lesson that does not apply; the host must judge
meaning against its source and the current request. Successful retrieval is
not proof of changed agent behavior.

The initial [frozen Codex comparison](../evals/lesson-transfer/fresh-agent-results.json)
showed no uplift: its positive tasks were correct with and without memory. A
separate [public Hermes trial](../evals/product-baseline/hermes-path.json)
changed an overbroad object selection by excluding an office-desk mug. That is
a bounded scope-selection observation, not recovery from sink-only washing or
proof of general effectiveness. The
[evaluation guide](../evals/lesson-transfer/README.md) separates these trials
from further counterfactual evidence.

A separate [frozen counterfactual](../evals/lesson-transfer/counterfactual-agent-results.json)
recorded a positive action-plan change after the confirmed correction supplied
a nonobvious ready-marker; its narrower and unrelated controls stayed correct.
That bounded synthetic result has its own denominator and does not change the
initial no-uplift result or establish general effectiveness.

The release keeps a separate outgoing check: `hermeneutic gate --json` and
`check_draft(...).to_dict()` expose surface-pattern findings, origins, positions,
and blocking decisions. Matched text is omitted by default. That gate checks
wording; it cannot prove the action occurred. Experimental language mapping
remains advisory after an independent simulated evaluation missed its targets.

Start with the [lesson walkthrough](correction-memory-demo.md) and
[host capability matrix](../integrations/README.md). Inspect evidence of
applicability and action transfer before relying on the workflow. This release
does not introduce a new raw-episode retrieval algorithm or claim general
improvement in agent accuracy.
