"""Stage 2 (optional): hermes-rubric adapter.

Wraps the `hermes-rubric` CLI if it's available on PATH. If not installed,
`available()` returns False and the router skips this stage gracefully.

hermes-rubric: https://github.com/hermes-labs-ai/hermes-rubric
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RubricResult:
    aggregate: float
    max_possible: float
    per_dim: list[dict]
    raw: dict

    @property
    def normalized(self) -> float:
        if self.max_possible <= 0:
            return 0.0
        return self.aggregate / self.max_possible

    def passed(self, threshold: float = 0.7) -> bool:
        return self.normalized >= threshold


def available() -> bool:
    """Is hermes-rubric callable on this system?"""
    return shutil.which("hermes-rubric") is not None


def score(
    intent: str,
    draft: str,
    context: str = "",
    backend: str = "ollama-local",
    timeout: int = 600,
) -> RubricResult | None:
    """Run hermes-rubric on a draft. Returns None if hermes-rubric is not installed."""
    if not available():
        return None

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        target = td / "draft.md"
        ctx = td / "context.md"
        out = td / "result.json"
        target.write_text(draft, encoding="utf-8")
        ctx.write_text(context or "(no context provided)", encoding="utf-8")

        cmd = [
            "hermes-rubric",
            "--intent", intent,
            "--context", str(ctx),
            "--target", str(target),
            "--target-type", "draft",
            "--backend", backend,
            "--out", str(out),
        ]
        try:
            subprocess.run(cmd, check=True, timeout=timeout, capture_output=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None

        if not out.exists():
            return None
        try:
            data = json.loads(out.read_text())
        except json.JSONDecodeError:
            return None

    return RubricResult(
        aggregate=float(data.get("aggregate", 0)),
        max_possible=float(data.get("max_possible", 10)),
        per_dim=data.get("per_dim_scores", []),
        raw=data,
    )
