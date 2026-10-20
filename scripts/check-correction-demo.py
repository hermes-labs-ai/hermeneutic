"""Run outside the checkout with an installed hermeneutic; --ollama adds live retrieval."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--ollama", action="store_true")
args = parser.parse_args()
root = Path(tempfile.mkdtemp(prefix="hermeneutic-demo-check-"))
env = {**os.environ, "HERMENEUTIC_HOME": str(root / "memory")}
# Avoid inheriting a personal telemetry sink or a source-tree import path.
env.pop("HERMENEUTIC_TELEMETRY", None)
env.pop("PYTHONPATH", None)


def run(*arguments):
    result = subprocess.run(["hermeneutic", *arguments], cwd=root, env=env,
                            text=True, capture_output=True, check=True)
    return result.stdout


run("demo", "--out", str(root / "sessions"))
triples = root / "triples.jsonl"
run("mine", str(root / "sessions"), "--format", "openai", "--glob", "*.json", "--out", str(triples))
rows = [json.loads(line) for line in triples.read_text().splitlines()]
assert len(rows) == 3
before = triples.read_bytes(), triples.stat().st_mtime_ns
preview = run("inspect", str(triples), "--limit", "1")
assert len(preview.splitlines()) == 1
assert "Cite command output" in preview
assert before == (triples.read_bytes(), triples.stat().st_mtime_ns)
buckets = run("bucket", str(triples))
for name in ("over_completion", "scope_creep", "tone_format"):
    assert any(line.split() == [name, "1"] for line in buckets.splitlines())
# Simple native keyword baseline: the same evidence is easy to find here.
keyword_rows = [i for i, row in enumerate(rows, 1) if "verification" in row["orig_prompt"]]
assert keyword_rows == [1]
offline_recall = json.loads(run("recall", "Prepare a widget service release and summarize the verification results.",
                                "--triples", str(triples), "--limit", "1"))
assert offline_recall["matches"][0]["evidence"] == "triple-id-1"
receipt = {"synthetic": True, "triples": len(rows), "keyword_rows": keyword_rows,
           "triples_sha256": hashlib.sha256(triples.read_bytes()).hexdigest(),
           "offline_checks": "passed", "live_retrieval": "not requested"}
if args.ollama:
    run("compile-index", "--triples", str(triples))
    query = "Prepare a widget service release and summarize the verification results."
    preamble = run("compile", query, "--triples", str(triples), "--k", "1")
    assert "[evidence: triple-id-1]" in preamble, preamble
    assert "`over_completion`" in preamble, preamble
    receipt.update(live_retrieval="passed", query=query, preamble=preamble,
                   embedding_model="nomic-embed-text", endpoint="http://127.0.0.1:11434")
print(json.dumps(receipt, indent=2))
