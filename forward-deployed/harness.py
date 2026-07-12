#!/usr/bin/env python3
"""The forward-deployed harness — a step-machine that DRIVES the mission.

    python3 forward-deployed/harness.py            # print next instruction / verify last step
    python3 forward-deployed/harness.py verify     # audit the whole mission chain

Protocol for the agent running inside it: run the command, do exactly what
it prints, run it again. Repeat until it prints MISSION COMPLETE. Each step
is verified mechanically from artifacts on disk before the next unlocks —
work that didn't happen doesn't advance the mission, no matter how it is
described. Progress lives in ``forward-deployed/mission-state.json`` as a
hash chain: every entry commits to the previous entry and to digests of the
step's artifacts, so a skipped or hand-edited step is detectable later by
anyone with the repo (``verify`` recomputes the chain).

Steps: ENV → BOOT → HARVEST → REPORT → GATE → COMPLETE (attestation).
Stdlib only. No network. The chain is tamper-EVIDENT, not tamper-proof —
the same guarantee any local harness gives.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
STATE = HERE / "mission-state.json"
BOOT_REPORT = HERE / "boot-report.json"
HARVEST_OUT = REPO / "build" / "report.jsonl"
REPORT = REPO / "FORWARD-DEPLOYED-REPORT.md"

GENESIS = "hermeneutic-forward-deployed-v1"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.is_file() else "absent"


def _load() -> list[dict]:
    if STATE.is_file():
        try:
            return json.loads(STATE.read_text())
        except json.JSONDecodeError:
            return []
    return []


def _chain_hash(prev: str, step: str, at: str, artifacts: dict[str, str]) -> str:
    payload = prev + "|" + step + "|" + at + "|" + json.dumps(artifacts, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _advance(chain: list[dict], step: str, artifacts: dict[str, str]) -> None:
    prev = chain[-1]["hash"] if chain else GENESIS
    at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entry = {
        "step": step,
        "at": at,
        "artifacts": artifacts,
        "hash": _chain_hash(prev, step, at, artifacts),
    }
    chain.append(entry)
    STATE.write_text(json.dumps(chain, indent=2) + "\n")


def _verify_chain(chain: list[dict]) -> tuple[bool, str]:
    prev = GENESIS
    for i, e in enumerate(chain):
        if e.get("hash") != _chain_hash(prev, e.get("step", ""), e.get("at", ""), e.get("artifacts", {})):
            return False, f"chain breaks at entry {i} ({e.get('step')}) — state was edited by hand"
        prev = e["hash"]
    return True, f"chain intact: {len(chain)} step(s), head {prev[:16]}"


def _sanitized_file_ok(path: Path) -> tuple[bool, str]:
    """Mechanically confirm a harvest output is the sanitized shape."""
    if not path.is_file():
        return False, f"{path.relative_to(REPO)} does not exist"
    n = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        n += 1
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            return False, f"line {n} is not JSON"
        if not d.get("sanitized"):
            return False, f"line {n} lacks sanitized:true — re-run harvest WITH --sanitized"
        if any(k in d for k in ("orig_prompt", "assistant_excerpt", "user_reaction", "matched")):
            return False, f"line {n} carries text fields — this is NOT a sanitized report"
    return (n > 0), (f"{n} sanitized records" if n else "file is empty — point harvest at the real session dir")


def _boot_verdict() -> str:
    if not BOOT_REPORT.is_file():
        return "absent"
    try:
        return json.loads(BOOT_REPORT.read_text()).get("verdict", "unparseable")
    except json.JSONDecodeError:
        return "unparseable"


STEPS = ["ENV", "BOOT", "HARVEST", "REPORT", "GATE"]


def _instruction(step: str, note: str = "") -> int:
    banner = f"[forward-deployed harness] STEP {step}"
    body = {
        "ENV": (
            "Install this package with its dev extra into the environment you'll use:\n"
            "    pip install -e '.[dev]'\n"
            "Then run me again."
        ),
        "BOOT": (
            "Run the boot verification:\n"
            "    python3 forward-deployed/boot.py    # --sessions DIR --format X if logs live elsewhere\n"
            "If it says adaptation-needed: read FORWARD-DEPLOYED-HARNESS.md sections\n"
            "'Invariants' and 'Permitted adaptations', fix the failed steps (tests for\n"
            "every change), and re-run boot until fits-as-shipped. Then run me again."
        ),
        "HARVEST": (
            "CONFIRM WITH YOUR HUMAN FIRST — this reads their session logs (sanitized,\n"
            "nothing leaves the machine). With their ok:\n"
            "    hermeneutic harvest <session-dir> --format <fmt> --sanitized --out build/report.jsonl\n"
            "If they decline, or there are no logs yet:\n"
            "    echo '<one-line reason>' > build/HARVEST-SKIPPED\n"
            "Then run me again — I verify the output is genuinely sanitized (or record the skip)."
        ),
        "REPORT": (
            "Write the mission report: copy forward-deployed/REPORT-TEMPLATE.md to\n"
            "FORWARD-DEPLOYED-REPORT.md at the repo root and fill it in (counts,\n"
            "categories, this repo's diffs only — 'None — fits as shipped.' is valid).\n"
            "Lint it until CLEAN:\n"
            "    python3 forward-deployed/check_report.py FORWARD-DEPLOYED-REPORT.md\n"
            "Then run me again."
        ),
        "GATE": (
            "Final gate — the definition of done:\n"
            "    python3 forward-deployed/gate.py\n"
            "If NOT DONE, finish what it lists. Then run me again."
        ),
    }[step]
    print(banner + (f" — {note}" if note else ""))
    print()
    print(body)
    return 3  # exit 3 = mission in progress, instruction issued


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        ok, msg = _verify_chain(_load())
        print(("VERIFY: PASS — " if ok else "VERIFY: FAIL — ") + msg)
        return 0 if ok else 1

    chain = _load()
    ok, msg = _verify_chain(chain)
    if not ok:
        print(f"[forward-deployed harness] STATE INVALID — {msg}.")
        print("Delete forward-deployed/mission-state.json and restart the mission honestly.")
        return 1
    done = [e["step"] for e in chain]

    # ENV — pytest importable
    if "ENV" not in done:
        if importlib.util.find_spec("pytest") is None:
            return _instruction("ENV")
        _advance(chain, "ENV", {"python": sys.version.split()[0]})
    # BOOT — verdict fits-as-shipped
    if "BOOT" not in done:
        v = _boot_verdict()
        if v != "fits-as-shipped":
            return _instruction("BOOT", note=f"boot verdict: {v}")
        _advance(chain, "BOOT", {"boot-report": _digest(BOOT_REPORT)})
    # HARVEST — sanitized output, mechanically checked (or an explicit human skip)
    if "HARVEST" not in done:
        skip = REPO / "build" / "HARVEST-SKIPPED"
        if skip.is_file():
            _advance(chain, "HARVEST", {"skipped": _digest(skip)})
        else:
            ok, detail = _sanitized_file_ok(HARVEST_OUT)
            if not ok:
                return _instruction("HARVEST", note=detail)
            _advance(chain, "HARVEST", {"report.jsonl": _digest(HARVEST_OUT), "detail": detail})
    # REPORT — exists and CLEAN
    if "REPORT" not in done:
        if not REPORT.is_file():
            return _instruction("REPORT")
        lint = subprocess.run([sys.executable, str(HERE / "check_report.py"), str(REPORT)],
                              capture_output=True, text=True)
        if lint.returncode != 0:
            return _instruction("REPORT", note="report exists but is not CLEAN yet")
        _advance(chain, "REPORT", {"report.md": _digest(REPORT)})
    # GATE — exit 0
    if "GATE" not in done:
        gate = subprocess.run([sys.executable, str(HERE / "gate.py")], capture_output=True, text=True)
        if gate.returncode != 0:
            return _instruction("GATE", note=(gate.stdout.strip().splitlines() or ["gate failed"])[-1])
        _advance(chain, "GATE", {"gate": "PASS", "report.md": _digest(REPORT)})

    chain = _load()
    head = chain[-1]["hash"]
    print("MISSION COMPLETE")
    print(f"attestation: {head}")
    print()
    print("Tell your human: the deployment is verified end to end. They should")
    print("review FORWARD-DEPLOYED-REPORT.md, then send it plus build/report.jsonl")
    print("and the attestation line above to roli@hermes-labs.ai.")
    print("Anyone with this clone can audit the run: python3 forward-deployed/harness.py verify")
    print()
    print("Optional, human's call — runtime enforcement inside the agent loop itself (Codex notify hook):")
    print("    python3 forward-deployed/sentinel.py install")
    print("(advisory notify hook: nudges on unearned completion claims and live-gates")
    print(" every turn; reversible; refuses to touch an existing notify hook)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
