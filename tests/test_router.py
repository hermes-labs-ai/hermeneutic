"""End-to-end router tests with stub judge — no LLM calls."""
from __future__ import annotations

from hermeneutic.gates.twin import PressureProbe, stub_judge
from hermeneutic.router import Router


def test_clean_draft_ships_at_regex():
    router = Router(probe=None, use_rubric=False)
    res = router.gate(request="explain X", draft="Here is X. It works like this.")
    assert res.shipped_at_stage == "regex"
    assert res.final_output == "Here is X. It works like this."
    assert not res.repaired


def test_risky_draft_with_no_probe_returns_twin_skipped():
    router = Router(probe=None, use_rubric=False)
    res = router.gate(request="ship it", draft="Done — 14 files shipped, all tests pass.")
    assert res.shipped_at_stage == "twin-skipped"
    assert res.risk_hits  # caught by regex


def test_probe_ship_verdict_passes_through():
    probe = PressureProbe(judge=stub_judge("ship", "looks fine", "n/a"))
    router = Router(probe=probe, use_rubric=False)
    res = router.gate(request="ship it", draft="Done — 14 files shipped, all tests pass.")
    assert res.shipped_at_stage == "twin"
    assert res.twin_verdict.verdict == "ship"


def test_probe_revise_with_repairer_repairs():
    probe = PressureProbe(judge=stub_judge("revise", "needs evidence", "show test output"))

    def repairer(_req, draft, reason):
        return f"{draft}\n\n[REVISED — addressing: {reason}]"

    router = Router(probe=probe, repairer=repairer, use_rubric=False)
    res = router.gate(request="ship it", draft="Done — 14 files shipped.")
    assert res.shipped_at_stage == "repair"
    assert res.repaired
    assert "REVISED" in res.final_output


def test_probe_hold_without_repairer_signals_hold():
    probe = PressureProbe(judge=stub_judge("hold", "fabricated number", "show provenance"))
    router = Router(probe=probe, use_rubric=False)
    res = router.gate(request="ship it", draft="Done — 14 files shipped, all tests pass.")
    assert res.shipped_at_stage == "hold"
    assert not res.repaired


def test_severity_threshold_can_let_low_through():
    probe = PressureProbe(judge=stub_judge("hold", "n/a", "n/a"))
    # threshold "high" means only "high" severity triggers downstream stages
    router = Router(probe=probe, use_rubric=False, regex_severity_threshold="high")
    # "comprehensive" is a "low" hit only — should ship at regex
    res = router.gate(request="ship", draft="Built a comprehensive solution.")
    assert res.shipped_at_stage == "regex"


def test_gate_result_summary_is_human_readable():
    probe = PressureProbe(judge=stub_judge("ship", "ok", "n/a"))
    router = Router(probe=probe, use_rubric=False)
    res = router.gate(request="x", draft="Done with 5 things, all passing.")
    s = res.summary()
    assert "shipped@" in s
    assert "twin=ship" in s
