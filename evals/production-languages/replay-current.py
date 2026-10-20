"""Replay exposed simulations as regressions, without replacing the sealed receipt."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("frozen_language_eval", HERE / "run.py")
EVAL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVAL)


def summarize(metrics):
    """Keep severity-specific TP/FN separate from any-hit clean FP/TN."""
    result = {key: value for key, value in metrics.items() if key != "outcomes"}
    tp = metrics["high_severity_recall"]["count"]
    positive_count = metrics["high_severity_recall"]["denominator"]
    fp = metrics["false_positive"]["count"]
    negative_count = metrics["false_positive"]["denominator"]
    result["counts"] = {
        "high_severity_tp": tp, "high_severity_fn": positive_count - tp,
        "any_hit_fp": fp, "no_hit_tn": negative_count - fp,
        "uncertain": None,
    }
    return result


def evaluate():
    inputs = ("development.json", "holdout.json", "candidate.json", "results.json", "manifest.json")
    hashes = {f"evals/production-languages/{name}": EVAL.digest(HERE / name) for name in inputs}
    hashes.update(EVAL.source_hashes())
    hashes["evals/production-languages/replay-current.py"] = EVAL.digest(Path(__file__))
    return {
        "schema": 1,
        "interpretation": "Exposed simulated cases replayed on current source; not a new holdout or promotion result.",
        "uncertainty": "Uncertain count is unmeasured: simulated binary labels lack independent human/native-speaker adjudication.",
        "metric_contract": "TP/FN require high hits on high labels; FP counts any hit on clean labels. No precision claim.",
        "sha256": hashes,
        "splits": {
            split: {
                lang: {mode: summarize(metrics) for mode, metrics in modes.items()}
                for lang, modes in EVAL.evaluate(EVAL.load_cases(HERE / f"{split}.json")).items()
            }
            for split in ("development", "holdout")
        },
        "decision": "Advisory only. Fresh independent real-language evidence and owner approval required for promotion.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate current-regression.json only.")
    args = parser.parse_args()
    result = evaluate()
    receipt = HERE / "current-regression.json"
    if args.write:
        EVAL.write(receipt, result)
    elif json.loads(receipt.read_text()) != result:
        raise ValueError("Current regression receipt is stale; regenerate deliberately with --write")
    for split, languages in result["splits"].items():
        for lang, modes in languages.items():
            for mode, metrics in modes.items():
                print(split, lang, mode, metrics["counts"])


if __name__ == "__main__":
    main()
