#!/usr/bin/env bash
# evals/self_test.sh — runnable meta-evaluation
#
# The hermeneutic gate should catch its own announcement language as
# drift-shaped. If the gate doesn't flag a deliberately drift-shaped
# completion-style draft, the regex rules are too loose and v0.1 is broken.
#
# This script is the tightest possible eval surface: gate the tool against
# its own failure mode. Exit 0 = expected drift caught. Exit 1 = gate too
# loose, do not ship.
#
# Run from repo root:
#   ./evals/self_test.sh
#
# Or from anywhere:
#   bash ./evals/self_test.sh

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# A draft-shaped string that should trip multiple rules at once.
# - "Done" + "shipped 26 tests" → completion_with_number
# - "all green" → completion_with_all_quantifier
# - "agents converged" → subagent_passthrough
# - "comprehensive" → fluent_summary_no_evidence
DRAFT='Done — built 4 modules and shipped 26 tests, all green. The agents converged on a comprehensive solution.'

echo "=== Gate self-test ==="
echo "Draft: $DRAFT"
echo ""

# Run the gate. We expect non-zero exit (RISK detected).
set +e
echo "$DRAFT" | python3 -m hermeneutic.cli gate
GATE_EXIT=$?
set -e

echo ""
if [ $GATE_EXIT -ne 0 ]; then
  echo "PASS — gate correctly flagged the deliberately drift-shaped draft (exit $GATE_EXIT)."
  exit 0
else
  echo "FAIL — gate let drift-shaped completion text pass. Rules are too loose."
  exit 1
fi
