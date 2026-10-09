"""Replay frozen synthetic fixtures; no model, network, or runtime dependencies.

    python evals/languages/run.py
    python evals/languages/run.py --write

The receipt hashes each input and implementation so future edits cannot
silently inherit old validation numbers. A caught draft has any gate hit,
including a low-severity advisory; this is not a truth or efficacy metric.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from hermeneutic import lang  # noqa: E402
from hermeneutic.gates.regex import risk_score as english_score  # noqa: E402

HERE = Path(__file__).resolve().parent


def measure(cases: list[dict], code: str) -> dict:
    drift = [c for c in cases if c["label"] == "drift"]
    clean = [c for c in cases if c["label"] == "clean"]
    missed = [c["id"] for c in drift if not lang.risk_score(c["text"], lang=code)]
    fired = [c["id"] for c in clean if lang.risk_score(c["text"], lang=code)]
    return {
        "drift_caught": len(drift) - len(missed), "drift_total": len(drift),
        "drift_catch_pct": round(100 * (len(drift) - len(missed)) / len(drift), 1),
        "clean_fired": len(fired), "clean_total": len(clean),
        "false_fire_pct": round(100 * len(fired) / len(clean), 1),
        "missed_ids": missed, "false_fire_ids": fired,
    }


def evaluate() -> dict:
    inputs = [HERE / f"{code}.json" for code in lang.LANGS if code != "en"]
    review_path = HERE / "review-cases.json"
    implementation = sorted((ROOT / "src/hermeneutic/lang").glob("*.py"))
    implementation += [ROOT / "src/hermeneutic/gates/regex.py", Path(__file__).resolve()]
    hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in inputs + [review_path] + implementation
    }
    results = {}
    for path in inputs:
        code = path.stem
        corpus = json.loads(path.read_text(encoding="utf-8"))
        cases = corpus["cases"]
        results[code] = {
            "provenance": corpus["provenance"],
            "explicit": measure(cases, code), "auto": measure(cases, "auto"),
            "english_only_drift_caught": sum(
                bool(english_score(c["text"])) for c in cases if c["label"] == "drift"
            ),
            "batches": {
                batch: measure([c for c in cases if c.get("batch") == batch], code)
                for batch in sorted({c["batch"] for c in cases if "batch" in c})
            },
        }
    review = json.loads(review_path.read_text(encoding="utf-8"))
    return {"method": "Any canonical-gate hit on synthetic drafts; development-set results, not held out.",
            "sha256": hashes, "languages": results,
            "review_regressions": {
                "provenance": review["provenance"],
                "languages": {
                    code: {"explicit": measure([c for c in review["cases"] if c["lang"] == code], code),
                           "auto": measure([c for c in review["cases"] if c["lang"] == code], "auto")}
                    for code in results
                },
            }}


def write_receipt(path: Path, results: dict) -> None:
    """Publish complete JSON atomically; a failed write preserves the old receipt."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(results, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate results.json from current source and fixtures.")
    args = parser.parse_args()
    results = evaluate()
    if args.write:
        write_receipt(HERE / "results.json", results)
    for code, metrics in results["languages"].items():
        explicit, auto = metrics["explicit"], metrics["auto"]
        print(
            f"{code}: explicit catch {explicit['drift_caught']}/{explicit['drift_total']} "
            f"({explicit['drift_catch_pct']}%), false-fire {explicit['clean_fired']}/{explicit['clean_total']} "
            f"({explicit['false_fire_pct']}%); auto catch {auto['drift_caught']}/{auto['drift_total']}, "
            f"false-fire {auto['clean_fired']}/{auto['clean_total']}"
        )


if __name__ == "__main__":
    main()
