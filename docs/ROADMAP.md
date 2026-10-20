# Preview maturation roadmap

The product target is a changed action: after a human corrects intended scope,
a fresh agent handling an analogous instruction retrieves the attributed
correction, checks applicability, and acts differently without being taught
that lesson again. Incoming lesson context and outgoing claim checks serve
different parts of that loop. This is an evidence order, not a release schedule.

The lesson workflow ships as **0.1.16a2**, an explicit preview. The initial
[frozen comparison](../evals/lesson-transfer/fresh-agent-results.json) showed no
uplift. A separate [counterfactual](../evals/lesson-transfer/counterfactual-agent-results.json)
recorded a positive action-plan change; it and the public host trials establish
only bounded synthetic behavior.
Stable 0.1.15 remains the stable release. Maturation requires the following
work; release packaging is not evidence that these gates were met.

| Next increment | Evidence required before expanding it |
| --- | --- |
| Repeat correction transfer | Compare enabled and disabled fresh agents across further independently labeled tasks, keeping no-uplift and failure results. Inspect changed artifacts or actions, source attribution, and applicability; retain misleading controls. A narrow positive action-plan example does not establish general effectiveness. |
| Improve interpretation and abstention | Keep source-verbatim candidates, confirmed use, and optional host interpretation distinct. Freeze analogous and unrelated instructions before changing cue matching; compare action transfer, missed matches, and false transfer with the lexical baseline. Do not promote historical text into authority. |
| Make failures inspectable | Exercise missing prompts, truncated evidence, duplicate corrections, conflicting lessons, revocation, exact scope isolation, and disabled memory. Preserve source fingerprints and bounded diagnostics without exposing private logs. |
| Establish host operational acceptance | Extend the explicit-prompt trials to host-run retrieval and instrumented action artifacts in Codex, Claude Code, and Hermes Agent. Record versions, dependencies, permissions, and failures. Verify project-instruction loading before claiming it is automatic; incoming adapters are a later step. |
| Assess real-language behavior | Obtain independent labels and adjudicate uncertain cases before expanding lesson matching or draft-gate enforcement. Preserve exposed regression fixtures separately from new evidence. Experimental draft mappings remain advisory. |
| Add lateral packaging only when needed | Consider automatic host hooks, CI draft checks, and additional distribution surfaces after the correction-transfer loop has operational evidence. Each adapter needs its own install, delivery, failure, and removal checks. No GitHub Action is included in this release. |

The PR #63 retrieval experiment remains separate from this release because it
did not pass operational acceptance. The scoped-lesson baseline does not claim
an improved raw-episode retrieval algorithm. Historical raw-search comparisons
remain in the [correction-memory receipts](../evals/correction-memory/RESULTS.md).

The outgoing [structured gate report](gate-json.md) is available as a separate
check on an agent's report. It cannot establish that the reported action
occurred. See the [lesson contract](lesson-memory.md),
[walkthrough](correction-memory-demo.md), and
[host capability matrix](../integrations/README.md) for the current boundary.
