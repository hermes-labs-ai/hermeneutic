# Public correction-retrieval check

This entirely synthetic set was authored after the 0.1.14 implementation, with
labels frozen before its first execution. It contains direct tasks, paraphrases
and unrelated questions, including questions that share a domain word with a
correction. It is a public regression/evaluation surface, not an independently
sampled or held-out estimate of real-world quality. No private conversation text
was copied into it. The implementation was not tuned against its results.

The expected IDs identify task-specific corrective evidence. A question defining
CSV, UTC, or a database schema does not require a correction about a prior export
or migration. These harder negatives make lexical false positives visible.

Run offline from a source checkout or unpacked source distribution:

```sh
python evals/correction-memory/runner.py \
  --triples evals/correction-memory/public/triples.jsonl \
  --cases evals/correction-memory/public/cases.json \
  --home /tmp/hermeneutic-public-check --methods keyword \
  --out /tmp/hermeneutic-public-results.json
```

The home path is unused in keyword mode. An optional embedding comparison needs
a local Ollama model and an index in a separate home directory; the parent
methodology documents that dependency. No inference is needed for the default
public check.
