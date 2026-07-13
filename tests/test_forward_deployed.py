"""The forward-deployed kit: boot verifier + report leak-linter."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHECK = REPO / "forward-deployed" / "check_report.py"
BOOT = REPO / "forward-deployed" / "boot.py"


def test_check_report_flags_environment_leaks(tmp_path):
    report = tmp_path / "report.md"
    report.write_text(
        "## Boot\n"
        "failed at /Users/someone/projects/secret-client/app.py\n"
        "user said: 배포가 완료되었습니다 그리고 서버가 다운되었고 고객이 화가 났습니다 진짜로 큰일났어요\n"
        "contact me at someone@client-corp.com\n",
        encoding="utf-8",
    )
    p = subprocess.run([sys.executable, str(CHECK), str(report)], capture_output=True, text=True)
    assert p.returncode == 1
    assert "out-of-repo absolute path" in p.stdout
    assert "long Hangul run" in p.stdout
    assert "email address" in p.stdout


def test_check_report_template_is_clean():
    p = subprocess.run(
        [sys.executable, str(CHECK), str(REPO / "forward-deployed" / "REPORT-TEMPLATE.md")],
        capture_output=True, text=True,
    )
    assert p.returncode == 0, p.stdout
    assert "CLEAN" in p.stdout


def test_boot_help_runs():
    p = subprocess.run([sys.executable, str(BOOT), "--help"], capture_output=True, text=True)
    assert p.returncode == 0
    assert "boot-report.json" in p.stdout


def test_gate_reaches_a_verdict():
    p = subprocess.run([sys.executable, str(REPO / "forward-deployed" / "gate.py")],
                       capture_output=True, text=True)
    assert p.returncode in (0, 1)
    assert ("GATE: PASS" in p.stdout) or ("GATE: NOT DONE" in p.stdout)


def test_check_report_allows_dates_and_documented_defaults(tmp_path):
    report = tmp_path / "report.md"
    report.write_text(
        "# FORWARD-DEPLOYED REPORT\n"
        "- boot run: 2026-07-09T04:30:00Z\n"
        "- harvested ~/.codex/sessions (624 events), corpus at ~/.hermeneutic/triples.jsonl\n"
        "- contact: roli@hermes-labs.ai\n",
        encoding="utf-8",
    )
    p = subprocess.run([sys.executable, str(CHECK), str(report)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout
    assert "CLEAN" in p.stdout


def _load_harness():
    import importlib.util
    spec = importlib.util.spec_from_file_location("fdh_harness", REPO / "forward-deployed" / "harness.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_harness_chain_detects_tampering():
    h = _load_harness()
    chain = []
    prev = h.GENESIS
    for step in ("ENV", "BOOT"):
        entry = {"step": step, "at": "2026-07-09T00:00:00Z", "artifacts": {"x": step},
                 "hash": h._chain_hash(prev, step, "2026-07-09T00:00:00Z", {"x": step})}
        chain.append(entry)
        prev = entry["hash"]
    ok, _ = h._verify_chain(chain)
    assert ok
    chain[0]["step"] = "GATE"  # rewrite history
    ok, msg = h._verify_chain(chain)
    assert not ok and "entry 0" in msg


def test_harness_sanitized_check_rejects_text_fields(tmp_path):
    h = _load_harness()
    good = tmp_path / "good.jsonl"
    good.write_text('{"sanitized": true, "rule_ids": ["x"], "draft_sha256": "ab", "orig_prompt_len": 5}\n')
    ok, detail = h._sanitized_file_ok(good)
    assert ok and "1 sanitized records" in detail
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"sanitized": true, "orig_prompt": "the actual user text"}\n')
    ok, detail = h._sanitized_file_ok(bad)
    assert not ok and "text fields" in detail
    unsan = tmp_path / "unsan.jsonl"
    unsan.write_text('{"kind": "confirmed_catch"}\n')
    ok, detail = h._sanitized_file_ok(unsan)
    assert not ok and "--sanitized" in detail


SENTINEL = REPO / "forward-deployed" / "sentinel.py"


def test_sentinel_decide_nudges_on_unearned_completion(monkeypatch):
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("fdh_sentinel", SENTINEL)
    s = ilu.module_from_spec(spec)
    spec.loader.exec_module(s)
    notes = s.decide("Done — shipped 5 files, all tests pass.", mission_done=False)
    assert any("NOT DONE" in n for n in notes)
    assert any("RISK" in n for n in notes)
    assert s.decide("Here are three options, each with a tradeoff.", mission_done=False) == []
    done_notes = s.decide("Done — shipped 14 files, all tests pass.", mission_done=True)
    assert any("RISK" in n for n in done_notes)
    assert not any("NOT DONE" in n for n in done_notes)


def test_sentinel_install_refuses_foreign_hook_and_is_reversible(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('model = "x"\nnotify = ["/some/other/hook", "turn-ended"]\n')
    p = subprocess.run([sys.executable, str(SENTINEL), "install", "--config", str(cfg)],
                       capture_output=True, text=True)
    assert p.returncode == 1 and "REFUSING" in p.stderr
    assert "/some/other/hook" in cfg.read_text()

    cfg2 = tmp_path / "config2.toml"
    cfg2.write_text('model = "x"\n')
    p = subprocess.run([sys.executable, str(SENTINEL), "install", "--config", str(cfg2)],
                       capture_output=True, text=True)
    assert p.returncode == 0 and "sentinel.py" in cfg2.read_text()
    p = subprocess.run([sys.executable, str(SENTINEL), "install", "--config", str(cfg2)],
                       capture_output=True, text=True)
    assert p.returncode == 0 and "Already installed" in p.stdout
    p = subprocess.run([sys.executable, str(SENTINEL), "uninstall", "--config", str(cfg2)],
                       capture_output=True, text=True)
    assert p.returncode == 0 and "sentinel.py" not in cfg2.read_text()


def test_sentinel_install_lands_at_toml_top_level(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text('model = "x"\n\n[projects."/somewhere"]\ntrust_level = "trusted"\n')
    p = subprocess.run([sys.executable, str(SENTINEL), "install", "--config", str(cfg)],
                       capture_output=True, text=True)
    assert p.returncode == 0
    text = cfg.read_text()
    assert text.index("notify = ") < text.index("[projects."), "notify must precede the first table header"


def _run_verify(cwd: Path):
    return subprocess.run(
        [sys.executable, str(cwd / "forward-deployed" / "harness.py"), "verify"],
        capture_output=True, text=True, cwd=cwd,
    )


def _harness_copy(tmp_path: Path) -> Path:
    fd = tmp_path / "forward-deployed"
    fd.mkdir()
    fd.joinpath("harness.py").write_bytes(
        (REPO / "forward-deployed" / "harness.py").read_bytes()
    )
    return tmp_path


def test_harness_verify_fails_without_mission_state(tmp_path):
    root = _harness_copy(tmp_path)
    p = _run_verify(root)
    assert p.returncode == 1
    assert "no mission state" in p.stdout


def test_harness_verify_fails_on_empty_chain(tmp_path):
    root = _harness_copy(tmp_path)
    (root / "forward-deployed" / "mission-state.json").write_text("[]")
    p = _run_verify(root)
    assert p.returncode == 1
    assert "empty" in p.stdout


def test_harness_verify_fails_on_corrupt_state(tmp_path):
    root = _harness_copy(tmp_path)
    (root / "forward-deployed" / "mission-state.json").write_text("{not json")
    p = _run_verify(root)
    assert p.returncode == 1
    assert "not valid JSON" in p.stdout
