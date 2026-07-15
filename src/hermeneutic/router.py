"""3-stage gate router with optional repair pass.

  draft → [stage 1: regex risk]  ──pass──→ ship
                │ fire
                ▼
          [stage 2: rubric]  ──pass──→ ship   (skipped if hermes-rubric missing)
                │ fail
                ▼
          [stage 3: PressureProbe]  ──ship──→ ship
                │ revise / hold
                ▼
          repair pass (1 attempt) → ship

Every run returns a `GateResult` with an audit trail. Persisting reviewed
results can inform later explicit rule engineering; it does not make the fixed
gate learn or rewrite itself.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from hermeneutic.gates import rubric as _rubric
from hermeneutic.gates.regex import RiskHit, highest_severity, risk_score
from hermeneutic.gates.twin import PressureProbe, TwinVerdict

# A repairer takes (request, draft, reason) and returns a revised draft.
Repairer = Callable[[str, str, str], str]


@dataclass
class GateResult:
    final_output: str
    shipped_at_stage: str  # "regex" | "rubric" | "twin" | "repair"
    risk_hits: list[RiskHit] = field(default_factory=list)
    rubric_score: float | None = None
    twin_verdict: TwinVerdict | None = None
    repaired: bool = False
    original_draft: str = ""

    def summary(self) -> str:
        bits = [f"shipped@{self.shipped_at_stage}"]
        if self.risk_hits:
            sevs = sorted({h.severity for h in self.risk_hits})
            bits.append(f"risk={','.join(sevs)}({len(self.risk_hits)})")
        if self.rubric_score is not None:
            bits.append(f"rubric={self.rubric_score:.2f}")
        if self.twin_verdict:
            bits.append(f"twin={self.twin_verdict.verdict}")
        if self.repaired:
            bits.append("REPAIRED")
        return " ".join(bits)


class Router:
    """Wire stages together. Any stage can be disabled by passing None."""

    def __init__(
        self,
        probe: PressureProbe | None = None,
        repairer: Repairer | None = None,
        rubric_intent: str = "Verify the draft's claims are evidence-grounded and scope-disciplined.",
        rubric_threshold: float = 0.7,
        use_rubric: bool = True,
        regex_severity_threshold: str = "med",
    ):
        """
        probe: optional PressureProbe for stage 3. If None, stage 3 is skipped.
        repairer: optional callable to produce a revised draft when probe says revise/hold.
        rubric_intent: the intent string passed to hermes-rubric.
        rubric_threshold: normalized score [0,1] required to pass stage 2.
        use_rubric: skip stage 2 entirely if False or hermes-rubric is unavailable.
        regex_severity_threshold: minimum severity to trigger downstream stages.
            "low" gates everything, "high" gates only the loudest patterns.
        """
        self.probe = probe
        self.repairer = repairer
        self.rubric_intent = rubric_intent
        self.rubric_threshold = rubric_threshold
        self.use_rubric = use_rubric and _rubric.available()
        self.regex_severity_threshold = regex_severity_threshold

    def gate(self, request: str, draft: str, context: str = "") -> GateResult:
        result = GateResult(final_output=draft, shipped_at_stage="regex", original_draft=draft)

        # Stage 1: regex
        hits = risk_score(draft)
        result.risk_hits = hits
        if not self._severity_triggers(highest_severity(hits)):
            return result  # ship — no risk

        # Stage 2: rubric (if available)
        if self.use_rubric:
            rubric_res = _rubric.score(self.rubric_intent, draft, context=context)
            if rubric_res is not None:
                result.rubric_score = rubric_res.normalized
                if rubric_res.passed(self.rubric_threshold):
                    result.shipped_at_stage = "rubric"
                    return result

        # Stage 3: PressureProbe
        if self.probe is None:
            result.shipped_at_stage = "twin-skipped"
            return result

        verdict = self.probe.review(request, draft)
        result.twin_verdict = verdict

        if verdict.verdict == "ship":
            result.shipped_at_stage = "twin"
            return result

        # Repair pass (one shot)
        if self.repairer is not None:
            revised = self.repairer(request, draft, verdict.reason)
            result.final_output = revised
            result.repaired = True
            result.shipped_at_stage = "repair"
        else:
            # No repairer available — return the draft annotated with the verdict.
            # Caller decides what to do (block, warn user, etc).
            result.shipped_at_stage = "hold"

        return result

    def _severity_triggers(self, sev: str | None) -> bool:
        if sev is None:
            return False
        order = {"low": 1, "med": 2, "high": 3}
        return order.get(sev, 0) >= order.get(self.regex_severity_threshold, 2)
