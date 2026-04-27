"""Stage 3: PressureProbe — a generic LLM critic with bring-your-own calibration.

The architecture is decoupled from any specific reviewer's priors. PressureProbe
forces a structured verdict (ship | revise | hold), an evidence pointer, and a
flip-condition. The *calibration* — what voice, what severity, what red flags —
is supplied by the caller via `calibration` text.

This means a user with poor epistemic hygiene who deploys PressureProbe still
benefits structurally: they can't game "what would falsify this?" by being lazy.
The architecture does some of the work even when the calibration is generic.

Default calibration is "rigorous-skeptic" — see DEFAULT_CALIBRATION below.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

Verdict = Literal["ship", "revise", "hold"]


@dataclass
class TwinVerdict:
    verdict: Verdict
    reason: str
    flip_condition: str
    raw: str = ""

    def should_repair(self) -> bool:
        return self.verdict in ("revise", "hold")


class LLMJudge(Protocol):
    """Anything callable that takes a prompt and returns a string completion.

    Plug in OpenAI, Anthropic, Ollama, your own twin — anything that maps
    prompt -> text completion. Keep it small; PressureProbe handles structure.
    """

    def __call__(self, prompt: str) -> str: ...


DEFAULT_CALIBRATION = """\
You are a rigorous skeptic reviewing an outgoing assistant draft.
Your job is to apply pressure, not polish.

Bias toward HOLD when you see:
- Numeric claims without a tool-call provenance in the same turn.
- Completion verbs ("done", "shipped", "all green") without a verifiable artifact.
- Subagent or tool output passed through without verification.
- Universal quantifiers ("every", "all", "always") with no enumeration.
- Fluent prose with no concrete referent.

Bias toward SHIP when:
- Every claim has a visible source (file path, command output, citation).
- Scope matches the user's actual request — no volunteered extras.
- Hedges appear where evidence is incomplete.
"""


_PROMPT_TEMPLATE = """\
{calibration}

USER REQUEST:
{request}

DRAFT RESPONSE TO REVIEW:
{draft}

Return EXACTLY this format, nothing else:

VERDICT: <ship|revise|hold>
REASON: <one sentence, concrete>
FLIP: <one sentence — what evidence would change your verdict>
"""


class PressureProbe:
    """Generic LLM critic. Plug in any LLMJudge, supply optional calibration."""

    def __init__(
        self,
        judge: LLMJudge,
        calibration: str = DEFAULT_CALIBRATION,
    ):
        self.judge = judge
        self.calibration = calibration

    def review(self, request: str, draft: str) -> TwinVerdict:
        prompt = _PROMPT_TEMPLATE.format(
            calibration=self.calibration,
            request=request,
            draft=draft,
        )
        raw = self.judge(prompt)
        return _parse_verdict(raw)


def _parse_verdict(raw: str) -> TwinVerdict:
    verdict: Verdict = "hold"  # safe default — fail closed
    reason = ""
    flip = ""
    for line in raw.splitlines():
        s = line.strip()
        upper = s.upper()
        if upper.startswith("VERDICT:"):
            v = s.split(":", 1)[1].strip().lower()
            if v.startswith("ship"):
                verdict = "ship"
            elif v.startswith("revise"):
                verdict = "revise"
            else:
                verdict = "hold"
        elif upper.startswith("REASON:"):
            reason = s.split(":", 1)[1].strip()
        elif upper.startswith("FLIP:"):
            flip = s.split(":", 1)[1].strip()
    return TwinVerdict(verdict=verdict, reason=reason, flip_condition=flip, raw=raw)


# ---------- convenience: a stub judge for testing ----------

def stub_judge(verdict: Verdict = "ship", reason: str = "stub", flip: str = "n/a") -> LLMJudge:
    """Return a deterministic LLMJudge for tests / dry-runs."""
    text = f"VERDICT: {verdict}\nREASON: {reason}\nFLIP: {flip}\n"
    def _j(_prompt: str) -> str:
        return text
    return _j
