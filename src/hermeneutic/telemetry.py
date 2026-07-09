"""Structured fire telemetry for the gate and compile paths.

Why this module exists
----------------------
Before this, a fire left no domain-level trace. The Stop-hook wrapper writes
its RISK verdict to *stderr* and always exits 0 (advisory), and the
chain-of-custody receipt layer records only that the hook ran plus a hash of
*stdout* — so it cannot distinguish RISK from PASS, and cannot see which
pattern matched. The compile path is only marginally better: a receipt can
tell that *some* preamble was injected (non-empty stdout) but not which
buckets, at what similarity, or whether the target session was a human or an
autonomous agent. Net result: over-steering / false-positive rate is
**unmeasurable**. This sink closes that gap — it is the prerequisite for every
downstream self-improvement (auto-tuning severity thresholds, human-vs-agent
firing modes, false-positive review).

Design invariants
-----------------
- **Opt-in, off by default.** Emits *only* when ``HERMENEUTIC_TELEMETRY`` names
  a writable path. Unset → every function here is a no-op. This keeps public
  behavior byte-identical unless a user explicitly turns it on.
- **Never raises, never blocks.** Telemetry is best-effort. Any failure
  (permission, disk, serialization) is swallowed; the gate/compile result is
  never affected.
- **Append-only JSONL.** One record per line; trivially greppable and
  replay-friendly for later analysis.
- **Context-aware.** Each record captures whether the fire happened in a
  human-interactive session or an agent/subagent/headless one, so
  false-positive analysis can be segmented (the dominant firing context is
  non-interactive agent sessions).
- **Local-only.** The sink is a file on the user's machine. Nothing is ever
  transmitted anywhere.

Audit log (before/after context)
--------------------------------
Verdict + rule_ids alone make a false positive unreviewable — you know *that*
``unhedged_certainty`` fired, not *on what text*. When
``HERMENEUTIC_TELEMETRY_CONTEXT`` is set, gate records additionally carry an
``audit`` list: per hit, the matched text plus a window of surrounding draft
text (``before`` / ``after``), so any verdict can be reviewed after the fact.

Modes (privacy is a spectrum; pick where the log will live):
- unset / ``none`` — no draft content in the log (v0.1.6 behavior).
- ``hash``         — SHA-256 of each window + lengths. Proves *what* fired on
                     *which* content without storing any text.
- ``raw``          — the text windows themselves. Full local review/demo mode.

Whenever the draft is available at record time, records also carry
``draft_sha256`` + ``draft_len`` (content fingerprint for dedup/correlation;
non-reversible) in every mode.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ENV_SINK = "HERMENEUTIC_TELEMETRY"
ENV_CONTEXT = "HERMENEUTIC_TELEMETRY_CONTEXT"

# Characters of draft text captured on each side of a matched span.
AUDIT_WINDOW = 120

# Env markers Claude Code exposes to hook subprocesses (verified present in a
# live hook environment 2026-07-05). Used to segment human vs agent fires.
#   CLAUDE_CODE_CHILD_SESSION — set for spawned child / subagent sessions
#   AI_AGENT                  — set in autonomous/agent execution contexts
#   CLAUDE_CODE_ENTRYPOINT    — how the session was launched (cli / print / ...)
#   CLAUDECODE                — set whenever running under Claude Code at all
_AGENT_MARKERS = ("CLAUDE_CODE_CHILD_SESSION", "AI_AGENT")


def sink_path() -> Path | None:
    """Return the configured telemetry path, or None when disabled."""
    raw = os.environ.get(ENV_SINK)
    if not raw or not raw.strip():
        return None
    return Path(raw).expanduser()


def enabled() -> bool:
    return sink_path() is not None


def context_mode() -> str:
    """Return the audit-context mode: "none" (default), "hash", or "raw".

    Unrecognized values degrade to "none" — misconfiguration must never
    accidentally log draft text.
    """
    raw = os.environ.get(ENV_CONTEXT, "").strip().lower()
    return raw if raw in ("hash", "raw") else "none"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _audit_entries(draft: str, hits) -> list[dict]:
    """Build per-hit audit entries with before/matched/after windows.

    ``hits`` is a list of ``RiskHit``. Hits from older callers that lack span
    fields (start/end < 0) fall back to locating ``matched_text`` in the
    draft; unlocatable hits still get an entry, just without windows.
    """
    mode = context_mode()
    entries: list[dict] = []
    for h in hits:
        entry: dict = {"rule_id": h.rule_id, "severity": h.severity}
        start = getattr(h, "start", -1)
        end = getattr(h, "end", -1)
        if start < 0 or end < 0 or end > len(draft):
            probe = h.matched_text.removesuffix("...")
            start = draft.find(probe)
            end = start + len(probe) if start >= 0 else -1
        if start >= 0 and end >= start:
            before = draft[max(0, start - AUDIT_WINDOW):start]
            matched = draft[start:end]
            after = draft[end:end + AUDIT_WINDOW]
            if mode == "raw":
                entry.update({"before": before, "matched": matched, "after": after})
            else:  # hash
                entry.update({
                    "before_sha256": _sha256(before), "before_len": len(before),
                    "matched_sha256": _sha256(matched), "matched_len": len(matched),
                    "after_sha256": _sha256(after), "after_len": len(after),
                })
        entries.append(entry)
    return entries


def detect_context() -> dict:
    """Best-effort human-vs-agent context from the process environment.

    Returns a dict with a derived ``context`` label plus the *raw* markers it
    was derived from, so downstream analysis never has to trust the label
    blindly — it can re-segment on the raw fields.
    """
    entrypoint = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")
    child = os.environ.get("CLAUDE_CODE_CHILD_SESSION", "")
    ai_agent = os.environ.get("AI_AGENT", "")
    under_claude = bool(os.environ.get("CLAUDECODE"))

    if any(os.environ.get(m) for m in _AGENT_MARKERS):
        context = "agent"
    elif under_claude:
        context = "human"
    else:
        context = "unknown"

    return {
        "context": context,
        "entrypoint": entrypoint,
        "child_session": bool(child),
        "ai_agent": bool(ai_agent),
    }


def _write(record: dict) -> None:
    path = sink_path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"ts": datetime.now(timezone.utc).isoformat(), **record}
        record.setdefault("session_id", os.environ.get("CLAUDE_CODE_SESSION_ID", ""))
        record.update(detect_context())
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Best-effort: telemetry must never break the gate/compile path.
        return


def record_gate(
    *,
    verdict: str,
    severity: str | None,
    rule_ids: list[str],
    draft: str | None = None,
    hits: list | None = None,
) -> None:
    """Record one gate fire. No-op unless telemetry is enabled.

    ``draft`` + ``hits`` are optional (older callers keep working). When the
    draft is provided, the record carries its fingerprint; when hits are also
    provided and ``HERMENEUTIC_TELEMETRY_CONTEXT`` is on, each hit gets a
    reviewable before/matched/after audit entry.
    """
    if not enabled():
        return
    record: dict = {
        "event": "gate",
        "verdict": verdict,           # "PASS" | "RISK"
        "severity": severity,         # "high" | "med" | "low" | None
        "rule_ids": rule_ids,
        "n_hits": len(rule_ids),
    }
    if draft is not None:
        record["draft_sha256"] = _sha256(draft)
        record["draft_len"] = len(draft)
        if hits and context_mode() != "none":
            record["audit_mode"] = context_mode()
            record["audit"] = _audit_entries(draft, hits)
    _write(record)


def record_compile(
    *,
    injected: bool,
    buckets: list[str],
    n_matches: int,
    prompt: str | None = None,
) -> None:
    """Record one compile fire. No-op unless telemetry is enabled."""
    if not enabled():
        return
    record: dict = {
        "event": "compile",
        "injected": injected,
        "buckets": buckets,
        "n_matches": n_matches,
    }
    if prompt is not None:
        record["prompt_sha256"] = _sha256(prompt)
        record["prompt_len"] = len(prompt)
        if context_mode() == "raw":
            record["audit_mode"] = "raw"
            record["prompt_excerpt"] = prompt[:2 * AUDIT_WINDOW]
    _write(record)
