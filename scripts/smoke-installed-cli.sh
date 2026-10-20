#!/usr/bin/env bash
set -euo pipefail

hermeneutic --help >/dev/null

risk_status=0
risk_output="$(
  printf '%s\n' 'Done — shipped 14 files, all tests pass.' | hermeneutic gate
)" || risk_status=$?
test "$risk_status" -eq 1
printf '%s\n' "$risk_output"
grep -Fq 'completion_with_number' <<<"$risk_output"
grep -Fq 'completion_with_all_quantifier' <<<"$risk_output"

pass_output="$(
  printf '%s\n' 'The report is ready for review.' | hermeneutic gate
)"
printf '%s\n' "$pass_output"
grep -Fq 'PASS — no risk patterns matched.' <<<"$pass_output"

# Published first-success pair: the neutral counterpart to the risky draft.
neutral_output="$(
  printf '%s\n' 'Draft ready for review.' | hermeneutic gate
)"
printf '%s\n' "$neutral_output"
grep -Fq 'PASS — no risk patterns matched.' <<<"$neutral_output"

# A missing draft must stay a distinct error, not collapse into the RISK exit.
missing_status=0
hermeneutic gate --draft "$(mktemp -u)/absent.txt" >/dev/null 2>&1 || missing_status=$?
test "$missing_status" -eq 2

# Exercise the installed CLI, without importing a source checkout.
python3 - <<'PYTHON'
import subprocess

samples = {
    "ko": ("5개 파일을 수정했습니다.", "확실하지 않습니다."),
    "zh": ("已完成 5 个文件。", "完成所有任务"),
    "ja": ("5件の修正が完了しました。", "5件を修正してください"),
    "tr": ("5 dosya tamamlandı.", "Kesinlikle emin değilim."),
    "de": ("Ich habe 5 Dateien abgeschlossen.", "5 Tests haben nicht bestanden."),
    "fr": ("J'ai terminé 5 fichiers.", "Ce n'est pas garanti."),
    "es": ("He completado 5 archivos.", "El resultado no está garantizado."),
    "pt": ("Eu concluí 5 arquivos.", "5 arquivos não estão concluídos."),
}
for code, (positive, negative) in samples.items():
    for choice in (code, "auto"):
        result = subprocess.run(["hermeneutic", "gate", "--lang", choice],
                                input=positive, text=True, capture_output=True)
        assert result.returncode == 0, (code, choice, result.stdout, result.stderr)
        assert "completion" in result.stdout
        assert "ADVISORY" in result.stdout and f"({code})" in result.stdout
    result = subprocess.run(["hermeneutic", "gate", "--lang", code],
                            input=negative, text=True, capture_output=True)
    assert result.returncode == 0, (code, result.stdout, result.stderr)
    assert "PASS" in result.stdout
print("Installed language CLI: eight positive pairs and eight negative controls passed.")
PYTHON
