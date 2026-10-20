#!/usr/bin/env python3
"""Evaluate a local installation switch helper against synthetic staged files only.

The external helper is not shipped with this evaluator. Supply its path and
the scoped command it expects to replace; neither value is included in results.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manager", type=Path, required=True)
    parser.add_argument("--existing-command", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    old = args.existing_command.encode("utf-8")
    cases = []
    with tempfile.TemporaryDirectory(prefix="hermeneutic-install-eval-") as directory:
        root = Path(directory)
        target = root / "AGENTS.md"
        state = root / "state"
        before = (
            b"# Synthetic instructions\nPreserve this unrelated preference.\nUse `"
            + old
            + b" recall REQUEST` when needed.\nTail stays unchanged.\n"
        )
        target.write_bytes(before)
        target.chmod(0o640)

        def run(action, *, chosen_target=target, chosen_state=state):
            process = subprocess.run(
                [args.python, str(args.manager), action, "--target", str(chosen_target), "--state", str(chosen_state)],
                capture_output=True,
                timeout=2,
                check=False,
            )
            try:
                payload = json.loads(process.stdout)
            except ValueError:
                payload = None
            return process.returncode, payload

        code, _payload = run("install")
        after = target.read_bytes()
        cases.append(
            {
                "case": "install_scoped_replacement",
                "pass": code == 0
                and after != before
                and after.startswith(b"# Synthetic instructions\nPreserve this unrelated preference.\n")
                and after.endswith(b" recall REQUEST` when needed.\nTail stays unchanged.\n")
                and old not in after,
            }
        )
        cases.append(
            {
                "case": "private_backups_and_mode",
                "pass": (state / "before").read_bytes() == before
                and (state / "after").read_bytes() == after
                and state.stat().st_mode & 0o777 == 0o700
                and all(path.stat().st_mode & 0o777 == 0o600 for path in state.iterdir())
                and target.stat().st_mode & 0o777 == 0o640,
            }
        )
        sentinel = state / "unrelated-sentinel"
        sentinel.write_bytes(b"preserve unrelated state\n")
        for action in (
            "install",
            "enable",
            "enable",
            "status",
            "disable",
            "disable",
            "status",
            "enable",
            "uninstall",
            "uninstall",
            "status",
            "install",
        ):
            code, _payload = run(action)
            expected = (
                after
                if action in ("install", "enable")
                else before
                if action in ("disable", "uninstall")
                else target.read_bytes()
            )
            cases.append(
                {
                    "case": f"{action}_{len(cases)}",
                    "pass": code == 0
                    and target.read_bytes() == expected
                    and sentinel.read_bytes() == b"preserve unrelated state\n"
                    and target.stat().st_mode & 0o777 == 0o640,
                }
            )
        concurrent = target.read_bytes() + b"Concurrent unrelated edit.\n"
        target.write_bytes(concurrent)
        code, _ = run("uninstall")
        cases.append({"case": "concurrent_edit_refused", "pass": code != 0 and target.read_bytes() == concurrent})
        other = root / "other-AGENTS.md"
        other.write_bytes(before)
        code, _ = run("install", chosen_target=other)
        cases.append({"case": "state_target_mismatch_refused", "pass": code != 0 and other.read_bytes() == before})
        for count in (0, 2):
            invalid = root / f"invalid-{count}.md"
            content = b"Unrelated file\n" + (old + b"\n") * count
            invalid.write_bytes(content)
            invalid_state = root / f"invalid-state-{count}"
            code, _ = run("install", chosen_target=invalid, chosen_state=invalid_state)
            cases.append(
                {
                    "case": f"replacement_count_{count}_refused",
                    "pass": code != 0 and invalid.read_bytes() == content and not invalid_state.exists(),
                }
            )
        for backup in ("before", "after"):
            damaged_target = root / f"damaged-{backup}.md"
            damaged_target.write_bytes(before)
            damaged_state = root / f"damaged-{backup}-state"
            run("install", chosen_target=damaged_target, chosen_state=damaged_state)
            current = damaged_target.read_bytes()
            (damaged_state / backup).write_bytes(b"Damaged backup must not become configuration.\n")
            for action in ("uninstall", "status"):
                code, _ = run(action, chosen_target=damaged_target, chosen_state=damaged_state)
                cases.append(
                    {
                        "case": f"damaged_{backup}_{action}_refused",
                        "pass": code != 0 and damaged_target.read_bytes() == current,
                    }
                )
    result = {
        "manager_sha256": hashlib.sha256(args.manager.read_bytes()).hexdigest(),
        "scope": "Synthetic staged files only; real project AGENTS configuration was not read or changed.",
        "cases": cases,
        "pass": all(row["pass"] for row in cases),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
