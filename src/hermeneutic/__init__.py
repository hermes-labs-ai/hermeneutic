"""hermeneutic — mine your AI chat logs for corrections, gate the next response."""

from hermeneutic.gates.regex import RiskHit, risk_score
from hermeneutic.gates.twin import LLMJudge, PressureProbe, TwinVerdict
from hermeneutic.router import GateResult, Router
from hermeneutic.triples import Triple, mine_dir, mine_file

__version__ = "0.2.0"

__all__ = [
    "GateResult",
    "LLMJudge",
    "PressureProbe",
    "RiskHit",
    "Router",
    "Triple",
    "TwinVerdict",
    "mine_dir",
    "mine_file",
    "risk_score",
]
