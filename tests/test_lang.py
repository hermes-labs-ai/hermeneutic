"""Language router, original-span telemetry, CLI and receipt integration."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hermeneutic import Router, lang
from hermeneutic.cli import main
from hermeneutic.gates.regex import risk_score

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {
    "ko": "5개 파일을 수정했습니다.", "zh": "已完成 5 个文件。", "ja": "5件の修正が完了しました。",
    "tr": "5 dosya tamamland\u0131.", "de": "Ich habe 5 Dateien abgeschlossen.",
    "fr": "J'ai terminé 5 fichiers.", "es": "He completado 5 archivos.", "pt": "Eu concluí 5 arquivos.",
}


@pytest.mark.parametrize("code,text", SAMPLES.items())
def test_cli_explicit_and_auto_language(code, text, tmp_path, capsys):
    path = tmp_path / "draft.txt"
    path.write_text(text, encoding="utf-8")
    for choice in (code, "auto"):
        assert main(["gate", "--draft", str(path), "--lang", choice]) == 1
        assert "RISK" in capsys.readouterr().out
    assert main(["gate", "--draft", str(path)]) == 0
    assert "PASS" in capsys.readouterr().out


@pytest.mark.parametrize("text", ["", "123!? 🧪", "Done — shipped 14 files, all tests pass.",
                                  "Here are three options with tradeoffs.", "Also check the robust implementation."])
def test_english_path_is_unchanged(text):
    assert lang.detect(text) == "en"
    assert lang.normalize(text) == text
    assert lang.risk_score(text) == risk_score(text)


def test_shared_script_ambiguity_and_explicit_override():
    # Portuguese and Spanish share these two markers; auto must not guess.
    text = "definitivamente todos"
    assert lang.detect(text) == "en"
    assert lang.risk_score(text) == []
    assert lang.risk_score(text, lang="pt")
    assert lang.risk_score(text, lang="es")
    # Kana disambiguates Japanese; kanji-only input requires caller context.
    assert lang.detect("完了しました。") == "ja"
    assert lang.detect("修正") == "zh"
    assert lang.normalize("修正", lang="ja").strip() == "completed"


@pytest.mark.parametrize("code,text", SAMPLES.items())
def test_hits_reference_original_draft(code, text):
    hits = lang.risk_score(text, lang=code)
    for hit in hits:
        assert 0 <= hit.start < hit.end <= len(text)
        assert hit.matched_text == text[hit.start:hit.end]
    assert hits


def test_router_gates_normalized_text_but_passes_original_to_probe():
    seen = []

    class Probe:
        def review(self, request, draft):
            from hermeneutic.gates.twin import TwinVerdict
            seen.append(draft)
            return TwinVerdict(verdict="ship", reason="fixture", flip_condition="new evidence")

    text = SAMPLES["ko"]
    result = Router(probe=Probe(), use_rubric=False, lang="auto").gate("request", text)
    assert result.risk_hits and seen == [text]
    assert result.final_output == text and result.original_draft == text
    assert Router(use_rubric=False).gate("request", text).risk_hits == []


def test_telemetry_hashes_original_matched_span(tmp_path, monkeypatch, capsys):
    import hashlib
    sink = tmp_path / "telemetry.jsonl"
    monkeypatch.setenv("HERMENEUTIC_TELEMETRY", str(sink))
    monkeypatch.setenv("HERMENEUTIC_TELEMETRY_CONTEXT", "hash")
    text = SAMPLES["ko"]
    path = tmp_path / "draft.txt"
    path.write_text(text, encoding="utf-8")
    assert main(["gate", "--draft", str(path), "--lang", "auto"]) == 1
    capsys.readouterr()
    record = json.loads(sink.read_text())
    hit = lang.risk_score(text)[0]
    assert record["audit"][0]["matched_sha256"] == hashlib.sha256(text[hit.start:hit.end].encode()).hexdigest()


def test_validation_receipt_matches_current_source_and_fixtures():
    spec = importlib.util.spec_from_file_location("language_eval", ROOT / "evals/languages/run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    receipt = json.loads((ROOT / "evals/languages/results.json").read_text(encoding="utf-8"))
    assert receipt == module.evaluate(), "Regenerate with python evals/languages/run.py --write"


@pytest.mark.parametrize("code,text", SAMPLES.items())
def test_python_response_hooks_gate_original_language(code, text, tmp_path, monkeypatch):
    from hermeneutic.hermes_agent_plugin import check_outgoing_claims

    assert check_outgoing_claims(text).startswith(text)
    monkeypatch.setenv("HERMENEUTIC_QWEN_STATE_DIR", str(tmp_path / "qwen-state"))
    for relative, payload, decision in (
        ("integrations/gemini-cli/hermeneutic_after_agent.py", {"prompt_response": text}, "deny"),
        ("integrations/qwen-code/hermeneutic_stop.py", {"last_assistant_message": text, "session_id": code}, "block"),
    ):
        spec = importlib.util.spec_from_file_location(f"{code}_hook", ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.evaluate(payload)["decision"] == decision
        if "gemini" in relative:
            retry = module.evaluate({**payload, "stop_hook_active": True})
        else:
            retry = module.evaluate(payload)
        assert retry.get("decision", "allow") == "allow"
        assert "bounded retry" in retry["systemMessage"]


@pytest.mark.parametrize("code,text", SAMPLES.items())
def test_cli_response_hooks_enable_auto_mapping(code, text, tmp_path, monkeypatch):
    from hermeneutic.install_hook import WRAPPER_MARKER, WRAPPER_TEMPLATE

    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(json.dumps({"type": "assistant", "message": {"content": text}}) + "\n")
    generated = tmp_path / "installed-hook.py"
    generated.write_text(WRAPPER_TEMPLATE.format(marker=WRAPPER_MARKER))
    for script in (ROOT / "claude-plugin/scripts/hermeneutic-gate.py", generated):
        process = subprocess.run([sys.executable, str(script)],
                                 input=json.dumps({"transcript_path": str(transcript)}),
                                 capture_output=True, text=True, check=True)
        assert "RISK" in process.stderr
    codex = subprocess.run([sys.executable, str(ROOT / "codex-plugin/scripts/codex-gate.py")],
                           input=json.dumps({"last_assistant_message": text}),
                           capture_output=True, text=True, check=True)
    output = json.loads(codex.stdout)
    assert "RISK" in output["systemMessage"] and "decision" not in output


@pytest.mark.parametrize("code,text", SAMPLES.items())
def test_scanning_and_normalization_use_identical_tables(code, text):
    assert [h.rule_id for h in lang.risk_score(text, lang=code)] == [
        h.rule_id for h in risk_score(lang.normalize(text, lang=code))
    ]


@pytest.mark.parametrize("code,text", [
    ("ko", "테스트92개가 통과했습니다."),
    ("zh", "测试92个已完成。"),
    ("ja", "テストが92件通過した。"),
])
def test_cjk_number_prefix_does_not_hide_completion(code, text):
    assert any(h.rule_id == "number_then_completion" for h in lang.risk_score(text, lang=code))
    assert "92" in lang.normalize(text, lang=code)
