"""Replay public development contracts against the installed API and CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from hermeneutic import __version__, check_draft


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cases_path = root / "evals/product-baseline/cases.json"
    cases = json.loads(cases_path.read_text())["cases"]
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("HERMENEUTIC_TELEMETRY") and key != "PYTHONPATH"}
    results = []
    for case in cases:
        report = check_draft(case["draft"], lang=case["lang"]).to_dict()
        run = subprocess.run(
            [sys.executable, "-I", "-m", "hermeneutic.cli", "gate", "--json", "--lang", case["lang"]],
            input=case["draft"], text=True, capture_output=True, env=env, check=False,
        )
        assert report["verdict"] == case["verdict"], case["id"]
        assert report["should_block"] is case["should_block"], case["id"]
        assert sorted({hit["origin"] for hit in report["findings"]}) == case["origins"], case["id"]
        assert run.returncode == int(case["should_block"]), (case["id"], run.returncode)
        assert json.loads(run.stdout) == report, case["id"]
        assert "PRIVATE_SENTINEL_4fe7" not in run.stdout
        assert all("matched_text" not in hit for hit in report["findings"])
        results.append({"id": case["id"], "status": "pass", "verdict": report["verdict"],
                        "should_block": report["should_block"]})
    receipt = {
        "schema_version": 1, "package_version": __version__,
        "scope": "Installed API/CLI mechanics on exposed development controls; not an independent accuracy benchmark.",
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "results": results,
    }
    rendered = json.dumps(receipt, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
