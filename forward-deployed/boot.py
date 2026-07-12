#!/usr/bin/env python3
"""Forward-deployed boot: verify hermeneutic fits this harness, in one command.

    python3 forward-deployed/boot.py [--sessions DIR] [--format codex]

Runs the BOOT sequence from FORWARD-DEPLOYED-HARNESS.md and writes
``forward-deployed/boot-report.json`` — sanitized by construction: counts,
categories, and pass/fail only; any path outside this repository is stripped
from captured output before it is stored.

Exit 0: every step passed — the package fits this harness as shipped.
Exit 1: one or more steps failed — the failures are the adaptation queue.

Stdlib only. Never makes a network call. Never reads log *content* itself —
the probe step invokes ``hermeneutic harvest --sanitized`` and reports only
the event count.
"""
from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REPORT = Path(__file__).resolve().parent / "boot-report.json"


def _sanitize(text: str) -> str:
    """Strip anything that could identify this environment from output."""
    home = str(Path.home())
    text = text.replace(str(REPO), "<repo>").replace(home, "<home>")
    # remaining absolute paths → placeholder (rooted at a real directory name,
    # so fractions like "111/180" survive)
    text = re.sub(
        r"(?:/(?:Users|home|private|var|tmp|opt|etc|usr|mnt|srv)/[^\s'\"]+|[A-Za-z]:\\[^\s'\"]+)",
        "<path>", text,
    )
    return text[:2000]


def _run(cmd: list[str], timeout: int = 600) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd, cwd=REPO, capture_output=True, text=True, timeout=timeout,
        )
        return p.returncode, _sanitize((p.stdout or "") + (p.stderr or ""))
    except FileNotFoundError as e:
        return 127, _sanitize(str(e))
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sessions", default=None,
                    help="Log dir for the harvest probe (default: ~/.claude/projects if present).")
    ap.add_argument("--format", default="claude-code", choices=["claude-code", "codex", "openai"],
                    help="Log format for the harvest probe (default: claude-code).")
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict] = []

    def record(name: str, ok: bool, detail: str) -> None:
        steps.append({"step": name, "status": "pass" if ok else "FAIL", "detail": detail})
        print(f"  [{'pass' if ok else 'FAIL'}] {name}: {detail}", file=sys.stderr)

    # 1. import + version
    try:
        sys.path.insert(0, str(REPO / "src"))
        import hermeneutic
        record("import", True, f"version {hermeneutic.__version__}")
    except Exception as e:
        record("import", False, _sanitize(f"{type(e).__name__}: {e}"))

    # 2. test suite (pytest ships in the dev extra, not the runtime deps)
    import importlib.util
    if importlib.util.find_spec("pytest") is None:
        record("pytest", False,
               "pytest not installed — run: pip install -e '.[dev]', then re-run boot (env setup, not a defect)")
    else:
        rc, out = _run([py, "-m", "pytest", "-q"])
        m = re.search(r"(\d+) passed(?:, (\d+) skipped)?", out)
        record("pytest", rc == 0 and bool(m),
               m.group(0) if m else f"exit {rc}: {out[-300:]}")

    # 3. gate self-test
    rc, out = _run(["bash", str(REPO / "evals" / "self_test.sh")])
    record("self_test", rc == 0 and "PASS" in out, out.strip().splitlines()[-1] if out.strip() else f"exit {rc}")

    # 4. gate smoke trio (documented expectations: RISK / PASS(contrast guard) / PASS)
    smoke = [
        ("overclaim_fires", "Done — shipped 14 files, all tests pass.", True),
        ("partial_progress_passes", "Fixed 3 of the 14 failing tests; 11 still fail.", False),
        ("plan_passes", "I will ship the remaining files tomorrow.", False),
    ]
    for name, draft, should_fire in smoke:
        p = subprocess.run([py, "-m", "hermeneutic.cli", "gate"],
                           cwd=REPO, input=draft, capture_output=True, text=True)
        fired = p.returncode == 1
        got = "RISK" if fired else ("PASS" if p.returncode == 0 else f"exit {p.returncode}")
        record(f"smoke:{name}", fired == should_fire,
               f"expected {'RISK' if should_fire else 'PASS'}, got {got}")

    # 5. harvest probe on real logs (sanitized; count only; temp file removed)
    sess = Path(args.sessions).expanduser() if args.sessions else Path.home() / ".claude" / "projects"
    if sess.is_dir():
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=True) as tf:
            rc, out = _run([py, "-m", "hermeneutic.cli", "harvest", str(sess),
                            "--format", args.format, "--sanitized", "--out", tf.name])
            m = re.search(r"harvested (\d+) review candidates", out)
            n = int(m.group(1)) if m else 0
            record("harvest_probe", rc == 0 and n > 0,
                   f"{n} events from {args.format} logs" if m else f"exit {rc}: {out[-300:]}")
    else:
        record("harvest_probe", False,
               f"no session dir found (looked for a {args.format} dir; pass --sessions)")

    report = {
        "harness": "forward-deployed boot v1",
        "environment": {
            "os_family": platform.system(),
            "python": platform.python_version(),
            "package": getattr(sys.modules.get("hermeneutic"), "__version__", "unimportable"),
        },
        "steps": steps,
        "verdict": "fits-as-shipped" if all(s["status"] == "pass" for s in steps) else "adaptation-needed",
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"\nverdict: {report['verdict']}  (full result: {REPORT.name})", file=sys.stderr)
    return 0 if report["verdict"] == "fits-as-shipped" else 1


if __name__ == "__main__":
    raise SystemExit(main())
