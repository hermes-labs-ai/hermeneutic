#!/usr/bin/env python3
"""The deployment's own drift gate: don't declare this mission done — prove it.

    python3 forward-deployed/gate.py

hermeneutic's thesis applied to its own deployment: a completion claim
("installed, adapted, working") must pass a deterministic gate before it
ships. Exit 0 means the forward-deployed mission is actually complete:

1. **Boot evidence is fresh and green** — ``forward-deployed/boot-report.json``
   exists, was produced after the newest change to the working tree, and its
   verdict is ``fits-as-shipped``. (Adapted something? Re-run ``boot.py``
   until it is.)
2. **The suite passes here, now** — ``pytest -q`` green in THIS environment,
   not the author's.
3. **Invariants hold mechanically** — no network imports outside
   ``compile.py`` (the gate stays zero-LLM; localhost Ollama embeddings are
   the single sanctioned exception), and the sanitized serializer still
   strips text fields.
4. **The mission carries its receipt, always** — ``FORWARD-DEPLOYED-REPORT.md``
   exists at the repo root ("no adaptations needed" is a valid report) and
   passes ``check_report.py`` CLEAN.

Stdlib only. No network. Exit 1 lists exactly what is missing.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BOOT_REPORT = Path(__file__).resolve().parent / "boot-report.json"
REPORT = REPO / "FORWARD-DEPLOYED-REPORT.md"

MATERIAL_DIRS = (
    ".claude-plugin",
    ".github",
    "claude-plugin",
    "codex-plugin",
    "docs",
    "evals",
    "examples",
    "forward-deployed",
    "integrations",
    "src",
    "tests",
)
GENERATED_PATHS = {
    Path("FORWARD-DEPLOYED-REPORT.md"),
    Path("forward-deployed/boot-report.json"),
    Path("forward-deployed/mission-state.json"),
}
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}

NETWORK_TOKENS = re.compile(r"\b(urllib\.request|urlopen|requests\.|httpx|socket\.create_connection|http\.client)\b")


def _material_files() -> list[Path]:
    """Return release material whose modification invalidates boot evidence."""
    files = [
        path
        for path in REPO.iterdir()
        if path.is_file() and path.name != ".git" and path.relative_to(REPO) not in GENERATED_PATHS
    ]
    for top in MATERIAL_DIRS:
        root = REPO / top
        if not root.is_dir():
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file()
            and path.relative_to(REPO) not in GENERATED_PATHS
            and not (set(path.relative_to(REPO).parts) & IGNORED_PARTS)
        )
    return files


def main() -> int:
    failures: list[str] = []

    # -- 1. boot evidence: present, parseable, green, fresh -------------------
    if not BOOT_REPORT.is_file():
        failures.append("no boot evidence: run `python3 forward-deployed/boot.py` first")
        boot_mtime = 0.0
    else:
        boot_mtime = BOOT_REPORT.stat().st_mtime
        try:
            verdict = json.loads(BOOT_REPORT.read_text())["verdict"]
        except (json.JSONDecodeError, KeyError):
            verdict = "unparseable"
        if verdict != "fits-as-shipped":
            failures.append(
                f"boot verdict is {verdict!r} — adapt (or finish adapting), then re-run boot.py until fits-as-shipped"
            )
        # Freshness covers the whole shipped product surface, including plugin
        # manifests, integration docs, metadata, and non-Python harness files.
        # Generated receipts and cache/venv directories are deliberately out.
        newer = [p for p in _material_files() if p.stat().st_mtime > boot_mtime + 1]
        if newer and verdict == "fits-as-shipped":
            failures.append(
                f"boot evidence is stale: {len(newer)} source file(s) changed after the last boot run — re-run boot.py"
            )

    # -- 2. suite green here, now --------------------------------------------
    # (skipped when gate.py itself runs under pytest — prevents recursion; the
    # suite's own result already covers this case)
    import os
    if os.environ.get("PYTEST_CURRENT_TEST"):
        pass
    else:
        p = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=REPO, capture_output=True, text=True)
        if p.returncode != 0:
            tail = (p.stdout or "").strip().splitlines()[-1:] or ["no output"]
            failures.append(f"test suite not green in this environment: {tail[0]}")

    # -- 3. invariants, mechanically ------------------------------------------
    for path in sorted((REPO / "src" / "hermeneutic").rglob("*.py")):
        if path.name == "compile.py":  # sanctioned: localhost Ollama embeddings
            continue
        hits = NETWORK_TOKENS.findall(path.read_text(encoding="utf-8", errors="replace"))
        if hits:
            failures.append(f"zero-LLM invariant broken: network token {hits[0]!r} in src/hermeneutic/{path.name}")
    sanitized_src = (REPO / "src" / "hermeneutic" / "harvest.py").read_text(encoding="utf-8")
    if "to_sanitized_json" not in sanitized_src or "_len" not in sanitized_src:
        failures.append("privacy invariant broken: sanitized serializer missing or no longer strips text to lengths")

    # -- 4. the report is ALWAYS required, and must be CLEAN -------------------
    # (a fits-as-shipped run still owes its receipt; "no adaptations" is a
    # one-line report, not a skipped one)
    if not REPORT.is_file():
        failures.append(
            "FORWARD-DEPLOYED-REPORT.md is missing — the mission always ends with its "
            "receipt (copy forward-deployed/REPORT-TEMPLATE.md; 'no adaptations needed' is a valid report)"
        )
    else:
        lint = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parent / "check_report.py"), str(REPORT)],
            capture_output=True, text=True,
        )
        if lint.returncode == 2:
            failures.append("check_report.py could not read FORWARD-DEPLOYED-REPORT.md (usage error) — check the path")
        elif lint.returncode != 0:
            failures.append("FORWARD-DEPLOYED-REPORT.md is not CLEAN — resolve check_report.py flags")

    # change detection is informational for the PASS message; when git metadata
    # is unavailable (tarball deployment) assume changed — the conservative read
    if (REPO / ".git").exists():
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                               capture_output=True, text=True).stdout.strip()
        material = [ln[3:] for ln in dirty.splitlines()
                    if ln[3:] not in ("forward-deployed/boot-report.json", "FORWARD-DEPLOYED-REPORT.md")]
        latest_tag = subprocess.run(["git", "describe", "--tags", "--abbrev=0"], cwd=REPO,
                                    capture_output=True, text=True).stdout.strip()
        if latest_tag:
            ahead = subprocess.run(["git", "rev-list", "--count", f"{latest_tag}..HEAD"], cwd=REPO,
                                   capture_output=True, text=True).stdout.strip()
            changed = bool(material) or (ahead.isdigit() and int(ahead) > 0)
        else:
            changed = True
    else:
        changed = True

    if failures:
        print("GATE: NOT DONE —")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("GATE: PASS — boot green, suite green here, invariants hold, report present and CLEAN"
          + ("" if changed else " (tree matches shipped release)")
          + ". The mission claim is earned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
