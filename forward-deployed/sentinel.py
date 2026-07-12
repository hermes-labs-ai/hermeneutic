#!/usr/bin/env python3
"""Runtime sentinel — consented enforcement inside the Codex loop itself.

    python3 forward-deployed/sentinel.py install    [--config PATH]   # one command, reversible
    python3 forward-deployed/sentinel.py uninstall  [--config PATH]
    python3 forward-deployed/sentinel.py notify '<payload-json>'      # what Codex invokes

`install` wires this script into Codex's native `notify` (turn-ended) hook
in `~/.codex/config.toml`. From then on, at the end of every agent turn:

1. **Mission enforcement** — while the forward-deployed mission is
   incomplete, an assistant turn that *sounds* finished (completion-claim
   shapes) triggers a desktop nudge to the human:
   "harness says NOT DONE — next step: X". The agent can skip steps; it can
   no longer skip them *quietly*.
2. **Live drift gate** — after the mission, every turn's last message keeps
   getting gated (zero-LLM, advisory). A RISK fires a one-line
   notification with the rule ids. This is real-time Codex gating —
   advisory, never blocking.

Consent and safety: installing is an explicit human action and reversible
(`uninstall`). If a `notify` hook already exists, install REFUSES and prints
how to compose the two by hand — it never overwrites someone else's hook.
The config is backed up first. Notifications carry rule ids and step names
only — never message text. Stdlib only; no network; a sanitized one-line
JSONL trace goes to `build/sentinel.log` inside this repo.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
STATE = HERE / "mission-state.json"
LOG = REPO / "build" / "sentinel.log"
DEFAULT_CONFIG = Path.home() / ".codex" / "config.toml"
MARKER = "forward-deployed/sentinel.py"


# ---------------------------------------------------------------- decisions
def _mission_done() -> bool:
    try:
        chain = json.loads(STATE.read_text())
        return any(e.get("step") == "GATE" for e in chain)
    except (OSError, json.JSONDecodeError):
        return False


def _next_step() -> str:
    try:
        done = {e.get("step") for e in json.loads(STATE.read_text())}
    except (OSError, json.JSONDecodeError):
        done = set()
    for s in ("ENV", "BOOT", "HARVEST", "REPORT", "GATE"):
        if s not in done:
            return s
    return "COMPLETE"


def decide(last_message: str, mission_done: bool) -> list[str]:
    """Pure decision core: returns notification strings (no text echoed)."""
    sys.path.insert(0, str(REPO / "src"))
    from hermeneutic.gates.regex import risk_score

    notes: list[str] = []
    hits = risk_score(last_message or "")
    rule_ids = sorted({h.rule_id for h in hits})
    completionish = any(r.startswith("completion") or r == "number_then_completion" for r in rule_ids)
    if not mission_done and completionish:
        notes.append("hermeneutic sentinel: turn sounds finished, but the harness says "
                     f"NOT DONE — next step: {_next_step()}")
    if hits:
        notes.append(f"hermeneutic: RISK ({', '.join(rule_ids)}) — advisory, verify before trusting")
    return notes


def _notify_human(text: str) -> None:
    if platform.system() == "Darwin":
        subprocess.run(["osascript", "-e",
                        f'display notification {json.dumps(text)} with title "hermeneutic"'],
                       capture_output=True)
    elif platform.system() == "Linux":
        subprocess.run(["notify-send", "hermeneutic", text], capture_output=True)
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "note": text}) + "\n")


def _cmd_notify(payload: str) -> int:
    try:
        d = json.loads(payload)
    except json.JSONDecodeError:
        return 0  # never break the host harness
    if "turn-complete" not in str(d.get("type", "")):
        return 0
    msg = d.get("last-assistant-message") or d.get("last_assistant_message") or ""
    for note in decide(msg, _mission_done()):
        _notify_human(note)
    return 0


# ---------------------------------------------------------------- install
def _install_line() -> str:
    return f'notify = ["{sys.executable}", "{HERE / "sentinel.py"}", "notify"]'


def _cmd_install(config: Path) -> int:
    if not config.parent.is_dir():
        print(f"ERROR: no Codex config dir at {config.parent} — is Codex CLI installed?", file=sys.stderr)
        return 1
    text = config.read_text(encoding="utf-8") if config.is_file() else ""
    if MARKER in text:
        print("Already installed — sentinel is live. Remove with: sentinel.py uninstall")
        return 0
    if re.search(r"^\s*notify\s*=", text, flags=re.M):
        print("REFUSING: a notify hook already exists in config.toml and it isn't mine.\n"
              "I never overwrite someone else's hook. To compose them, create a small\n"
              "wrapper script that calls your current hook AND:\n"
              f"    {sys.executable} {HERE / 'sentinel.py'} notify \"$@\"\n"
              "then point notify at the wrapper.", file=sys.stderr)
        return 1
    backup = config.with_suffix(".toml.bak-hermeneutic")
    if config.is_file():
        backup.write_text(text, encoding="utf-8")
    # TOML: top-level keys must precede any [table] header — insert, never append
    lines = text.splitlines()
    at = next((i for i, ln in enumerate(lines) if ln.strip().startswith("[")), len(lines))
    lines.insert(at, _install_line())
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Installed: sentinel wired into {config} (backup at {backup.name}).\n"
          "Advisory only — it notifies, never blocks. Remove anytime with: sentinel.py uninstall")
    return 0


def _cmd_uninstall(config: Path) -> int:
    if not config.is_file():
        print("Nothing to do — no config file.")
        return 0
    lines = config.read_text(encoding="utf-8").splitlines()
    kept = [ln for ln in lines if MARKER not in ln]
    if len(kept) == len(lines):
        print("Nothing to do — sentinel was not installed.")
        return 0
    config.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print("Removed: sentinel is no longer in the notify hook.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["install", "uninstall", "notify"])
    ap.add_argument("payload", nargs="?", default="{}")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    args = ap.parse_args()
    if args.command == "install":
        return _cmd_install(Path(args.config).expanduser())
    if args.command == "uninstall":
        return _cmd_uninstall(Path(args.config).expanduser())
    return _cmd_notify(args.payload)


if __name__ == "__main__":
    raise SystemExit(main())
