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
