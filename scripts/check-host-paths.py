"""Explicit opt-in live trials of the public dishes example in installed hosts.

Synthetic object-selection plans only. No hooks or host settings are installed.
Uses source-derived confirmed context from the installed Hermeneutic package.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", required=True, help="Fresh wheel interpreter")
    parser.add_argument("--host", choices=("claude", "hermes"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("lesson_trial", root / "scripts/check-lesson-demo.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.CLI_PYTHON = args.python
    design = json.loads((root / "evals/lesson-transfer/design-demo.json").read_text())
    result = {
        "schema_version": 1, "synthetic": True, "host": args.host,
        "classification": "Public design trial, not held-out validation or user research.",
        "delivery": "Explicit installed CLI context supplied in a fresh host prompt; no automatic hook.",
        "interpretation": "Confirmed verbatim source correction, no reauthored rule or WHEN cues.",
        "later_instruction": "Wash the dishes after supper.",
        "runs": {},
    }
    with tempfile.TemporaryDirectory(prefix="hermeneutic-host-") as directory:
        workspace = Path(directory).resolve()
        def command(*arguments):
            return subprocess.run(
                [args.python, "-I", "-m", "hermeneutic.cli", *arguments],
                cwd=workspace, env=runner.clean_environment(workspace / "memory-home"),
                text=True, capture_output=True, check=True, timeout=20,
            ).stdout
        command("demo", "--scenario", "dishes", "--out", str(workspace / "sessions"))
        corpus = workspace / "triples.jsonl"
        command("mine", str(workspace / "sessions"), "--format", "openai", "--glob", "*.json",
                "--out", str(corpus))
        memory = workspace / "lessons.json"
        learned = json.loads(command("learn", "--triples", str(corpus), "--evidence", "triple-id-1",
                                     "--scope", design["teaching"]["scope"], "--memory", str(memory)))["lesson"]
        command("confirm", learned["id"], "--memory", str(memory))
        context = json.loads(command("context", result["later_instruction"], "--scope",
                                     design["teaching"]["scope"], "--memory", str(memory)))
        result["context"] = context
        assert len(context["matches"]) == 1
        result["source_sha256"] = hashlib.sha256(corpus.read_bytes()).hexdigest()
        for mode in ("without_memory", "with_memory"):
            prompt = runner.action_prompt(result["later_instruction"], "wash dishes", design["world"],
                                          design["teaching"]["scope"], context if mode == "with_memory" else None)
            prompt += "\nReturn only JSON matching this schema:\n" + json.dumps(runner.ACTION_SCHEMA)
            with tempfile.TemporaryDirectory(prefix="hermeneutic-isolated-host-") as host_directory:
                if args.host == "claude":
                    invocation = ["claude", "--print", "--safe-mode", "--tools", "",
                                  "--no-session-persistence", "--output-format", "json",
                                  "--json-schema", json.dumps(runner.ACTION_SCHEMA), "--max-budget-usd", "0.5"]
                else:
                    invocation = ["hermes", "chat", "--safe-mode", "--toolsets", "",
                                  "--query-file", "-", "--oneshot", "--quiet", "--max-turns", "1",
                                  "--run-budget", "60"]
                print(f"Public host trial: {args.host} / {mode}", flush=True)
                try:
                    run = subprocess.run(invocation, input=prompt, cwd=host_directory, text=True,
                                         capture_output=True, timeout=90, check=False)
                    if run.returncode:
                        result["runs"][mode] = {"error": "host_nonzero_exit", "exit_code": run.returncode}
                    else:
                        raw = run.stdout.strip()
                        if args.host == "claude":
                            envelope = json.loads(raw)
                            output = envelope.get("structured_output")
                            if not output:
                                output = json.loads(envelope.get("result", ""))
                        else:
                            start = raw.find("{")
                            output, _ = json.JSONDecoder().raw_decode(raw[start:])
                        result["runs"][mode] = {"output": output, "score": runner.score_action(design, output)}
                except subprocess.TimeoutExpired:
                    result["runs"][mode] = {"error": "host_timeout"}
                except (ValueError, KeyError, TypeError):
                    result["runs"][mode] = {"error": "host_did_not_return_action_schema"}
                args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"host": args.host, "runs": result["runs"]}, indent=2))


if __name__ == "__main__":
    main()
