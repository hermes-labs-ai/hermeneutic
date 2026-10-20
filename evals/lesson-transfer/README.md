# Interpreted-lesson transfer evaluation

This lane separates public design examples, independent frozen validation, and
fresh-agent action plans. Its episodes are fictional. No personal correction
corpus is used.

`design-demo.json` is the public sink-only dishwashing mistake and explicit
correction about dirty dining-table plates. It is excluded from validation
scores. `frozen-cases.json` contains deployment-handoff and experiment-archive
analogies, a further handoff paraphrase, unrelated and scope controls, and a
misleading same-scope request that explicitly narrows the action. `protocol.json`
records the fixture hashes and the pre-execution amendment requested by the
owner. The earlier digest is retained in its freeze history. Fixture text and
labels were withheld from the core author before source freeze.

The default public demonstration captures the attributed correction text as a
source-verbatim candidate and supplies no context until that candidate is
confirmed. It derives the retrieval cue from the original instruction. The
frozen validation separately tests explicit host-supplied interpretations, exact
scopes, and representative WHEN examples. These paths are reported separately;
the default does not infer a new interpretation through a model. The downstream
agent must check whether context applies, including the current instruction's
narrower constraints.

Run deterministic mechanics without model calls:

```bash
python scripts/check-lesson-demo.py --python /path/to/wheel-venv/bin/python \
  --receipt evals/lesson-transfer/deterministic-results.json
```

The default runs the installed package under isolated Python. Use `--python`
for a fresh wheel environment; `--source` explicitly selects the checkout.
Export the same public dishes task for another host:

```bash
python scripts/check-lesson-demo.py --emit-demo-prompt without_memory
python scripts/check-lesson-demo.py --emit-demo-prompt with_memory
```

The output schema is `ACTION_SCHEMA` in the script. Its `selected_ids` is the
agent's synthetic action plan. `memory_checks` records attributed applicability
reasoning; `explanation` explains the selected action. Choosing a lesson ID
without selecting the required objects does not count as task completion.

The opt-in fresh Codex comparison uses a new ephemeral CLI invocation for each
condition, with the same task and world in a pair. Only the supplied correction
context changes. Each condition uses a separate empty temporary directory, so
teaching files and another invocation's artifacts are unavailable in its working
directory. The CLI default model is used without an explicit model override;
the receipt records the CLI version. Each invocation has a bounded timeout; failed executions and
baseline successes remain in the result. There are no result-driven retries or
fixture, lesson, WHEN, or implementation changes.

```bash
python scripts/check-lesson-demo.py --python /path/to/wheel-venv/bin/python \
  --receipt evals/lesson-transfer/deterministic-results.json \
  --live-agents --live-public-demo \
  --live-receipt evals/lesson-transfer/fresh-agent-results.json
```

The additional public dishes pair writes `public-dishes-agent-results.json`
and is excluded from the frozen denominators. Public prompt export defaults to
`--demo-memory host_interpreted`; select `--demo-memory source_default` to inspect
the confirmed source-derived candidate's actual recalled context, including an
empty context if the later wording does not match. These paths are distinct.

The denominator for positive transfer is the frozen positive cases. Negative
controls have their own denominator. Unrelated and other-scope false recalls
are counted separately from a candidate retrieved for the intentionally
misleading narrower task. Behavioral overgeneralization is measured from extra
selected objects, independent of candidate retrieval. Exact completion also
rejects missing objects and duplicate selections. Source attribution and written
applicability explanations are recorded separately from this completion score.

These are synthetic object-selection tasks, not operations in a real home or
repository. They can establish bounded host mechanics and observed action-plan
behavior for the recorded invocations. They do not establish real-user impact,
automatic intent learning, language coverage, or general effectiveness.

## Recorded outcome

The installed-wheel run is recorded in `deterministic-results.json`; its package
identity matches the frozen core hashes. The independent fixture digest remained
unchanged throughout execution. Required lifecycle, attribution, scope, and
retrieval checks passed. The public source-derived candidate did not retrieve
for the later supper wording; the explicit host-supplied interpretation did.
That miss is preserved as a design diagnostic, not hidden by the frozen scores.

`fresh-agent-results.json` records the frozen Codex comparison:

| Measure | Without memory | With memory |
| --- | --- | --- |
| Positive exact task completion | 3/3 | 3/3 |
| Negative-control exact completion | 3/3 | 3/3 |
| Improved positive pairs | — | 0/3 |
| Regressed positive pairs | — | 0/3 |

Unrelated and other-scope queries produced no false recall (0/2). The deliberately
narrower same-scope request retrieved a candidate (1/1), but the fresh agent
explicitly rejected its broader action because the current request said to
package only the patch. It selected only that patch. No negative control had
extra selected objects with memory (0/3). These denominators distinguish a noisy
candidate from behavioral overgeneralization.

`public-dishes-agent-results.json` separately records the public Codex pair.
Both conditions selected the dirty sink bowl and dirty dining-table plate,
leaving the clean plate and office mug alone. The memory condition wrote an
attributed applicability explanation. This pair is excluded from the frozen
scores and also showed no completion improvement. No evaluated invocation used
a tool. Final action outputs are retained under `runs/`; raw runtime event JSONL
is kept outside Git in the evaluation temporary directory. Event hashes and
tool-use counts appear in the receipts.

These results demonstrate the recorded mechanics and compatibility with correct
agent behavior. The baselines already completed the tasks, so this run does not
demonstrate that memory improved downstream task completion. These original frozen cases must not be tuned or rerun selectively to obtain
an efficacy claim. The final separately frozen iteration below was authorized
after this non-discriminating result.


## Final prospective iteration

The owner authorized one final evaluation iteration after the original tasks
proved non-discriminating. `counterfactual-cases.json` and
`counterfactual-protocol.json` were hashed before execution. Original cases and
results remained unchanged; the product implementation remained frozen.

The fictional household uses an orange wooden counter from the entryway as a
reading-nook ready-marker. This is a personal chore convention rather than an
ordinary completeness requirement. Its initial correction supplies that
nonobvious inclusion. The later reset task does not restate the lesson. A
same-scope blanket-only request and an unrelated entryway-key request test
whether the host overgeneralizes. This iteration uses the default source-verbatim
candidate followed by confirmation, with no rewritten lesson or WHEN examples.

```bash
python scripts/check-lesson-demo.py --python /path/to/wheel-venv/bin/python \
  --counterfactual \
  --receipt evals/lesson-transfer/counterfactual-mechanics-results.json \
  --live-agents \
  --live-receipt evals/lesson-transfer/counterfactual-agent-results.json \
  --event-dir /path/outside/repository/agent-events
```

The result has separate denominators from the original validation. No retries,
source changes, fixture changes, lesson changes, or WHEN changes were permitted
after observing it. The protocol forbids another evaluation repair loop.

The final results are in `counterfactual-mechanics-results.json` and
`counterfactual-agent-results.json`:

| Measure | Without memory | With memory |
| --- | --- | --- |
| Personalized reset exact completion | 0/1 | 1/1 |
| Negative-control exact completion | 2/2 | 2/2 |

The baseline returned the book and folded the throw, treating the entryway
objects as outside the nook task. With the confirmed correction, the fresh
agent added the orange counter and explained the attributed household meaning.
The current task had not repeated that convention. The narrower task retrieved
the candidate but rejected its broader action, selecting only the blanket. The
unrelated task retrieved no candidate and selected only the keys. No negative
control added objects beyond its expected action (0/2); the unrelated recall
false-match count was 0/1. No evaluated call used tools or failed to execute.

This is an observed synthetic action-plan delta under the stated convention and
recorded host protocol. It does not establish a general success rate, real-user
impact, automatic semantic interpretation, or broad paraphrase coverage. The
source-default public supper wording still has its documented recall miss.
The original no-improvement results remain valid and separately reported.
