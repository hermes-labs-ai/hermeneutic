# HANDOFF — hermeneutic v0.1.0

**Built:** 2026-04-25 (session origin: hermeneutic-gap mining of 1,423 Claude Code sessions → 326 triples).

## Status

| Item | State |
|---|---|
| Repo scaffolded | ✅ `~/Documents/projects/hermeneutic/` |
| Core: triples miner | ✅ `src/hermeneutic/triples.py` (Claude Code + OpenAI formats) |
| Gates: regex / twin / rubric adapter | ✅ `src/hermeneutic/gates/` (6 evidence-derived patterns) |
| Router + CLI | ✅ `src/hermeneutic/{router,cli}.py` |
| Tests | ✅ 26/26 passing, ruff clean |
| Distribution kit | ✅ README, AGENTS.md, llms.txt, CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, CITATION.cff, docs/THEORY.md, examples/before_after.md, .github/workflows/ci.yml |
| Tool-vault manifest | ✅ `~/ai-infra/manifests/hermeneutic.yaml` |
| Hermes-rubric audit | ✅ 5.6/10 — README empirical-claim grounding patched (was 4/10) |
| Hermes-seal manifest + categories | ✅ all 4 categories pass (continuity / reliability / compliance / mom_ready). Manifest at `.hermes-seal.yaml`, SBOM at `sbom.cdx.json` |
| Hermes-seal **grant** (signing) | ⏸ requires root key — `sudo hermes-seal grant ~/Documents/projects/hermeneutic` (Roli only — MAXIM 15) |
| GitHub push | ⏸ awaiting Roli approval (public-repo-gate hook) |
| PyPI publish | ⏸ awaiting Roli approval |

## Self-test (gate caught its own drift)

Ran `hermeneutic gate` on a deliberately drift-shaped draft:

```
$ echo "Done — built 4 modules and shipped 26 tests, all green. The agents converged on a comprehensive solution." | hermeneutic gate
RISK — highest severity: high
  [high] completion_with_number: 'Done — built 4'
  [high] completion_with_number: 'shipped 26'
  [high] completion_with_all_quantifier: 'Done — built 4 modules and shipped 26 tests, all'
  [high] subagent_passthrough: 'agents converged'
  [low]  fluent_summary_no_evidence: 'comprehensive'
```

5 hits in ~0ms. The gate works on its own announcement language — meta-validation.

## Decisions made this session

- **Twin architecture split:** ship `PressureProbe` (the role) publicly, keep rolitwin's specific calibration private. Default calibration is "rigorous-skeptic." Users supply their own calibration text.
- **Publish scope:** architecture + miner + gates + 6 patterns are public. The 326 triples themselves, rolitwin priors, and any cogito-derived data stay private.
- **Org:** `hermes-labs-ai`.
- **Name:** `hermeneutic`.

## Next steps (need Roli)

1. **Hermes-seal grant** — `sudo hermes-seal grant ~/Documents/projects/hermeneutic` (root-only by design).
2. **GitHub push** — create repo at `hermes-labs-ai/hermeneutic`, push v0.1.0 tag.
3. **PyPI publish** — `python -m build && twine upload dist/*`.
4. **Cross-link** — add hermeneutic to scaffold-lint / hermes-rubric / agent-convergence-scorer READMEs as audit-stack sibling.
5. **Optional** — open follow-up issues for: embedding-clustered patterns (the 112 unbucketed corrections), repair-pass re-gating, calibration-drift study.

## Memory pointer

Add memory file: `~/.claude/projects/-Users-rbr-lpci/memory/project_hermeneutic.md` once shipped.

## Honest caveats (per audit findings)

- Risk patterns derived from one user's session corpus (Roli's 1,423 sessions). May not generalize cleanly to other users without re-mining.
- Gate is correct only on drift modes already seen corrected — by definition, novel drifts pass through silently.
- Stage 2 (hermes-rubric) requires hermes-rubric on PATH; gracefully skipped otherwise.
- One-shot repair pass: a repair that itself triggers the gate is shipped anyway. Open question: should the router re-gate after repair?
