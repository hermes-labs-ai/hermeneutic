"""Reject-mining harvester: turn session logs into a labeled review queue.

Why this module exists
----------------------
The mining that improves the gate was 100% manual: a human re-reads chat
logs, spots corrections, and hand-writes triples. That doesn't scale past a
few sessions, so the rule corpus goes stale while live fires pile up
unreviewed. This harvester automates the harvest half of that loop with zero
LLM calls: it *replays* the regex gate (a pure function) over every assistant
turn in a log directory, reads the user's actual next reaction, and classifies
each event into one of three review-queue kinds:

- ``confirmed_catch``          — gate fires AND the next user turn is a
                                 correction. The gate proved itself; the
                                 triple is corpus-ready.
- ``possible_false_positive``  — gate fires but the user's next turn is NOT a
                                 correction. The reviewable over-steer set:
                                 tune rules against these.
- ``missed_drift``             — the user corrected, but the gate stayed
                                 silent on the turn they corrected. The
                                 false-negative set: new rules come from here.

The output is an append-friendly JSONL queue for *batch* review — a human (or
later, a local model) flips ``status`` from "pending" to "accepted"/"rejected",
and accepted records feed the triples corpus. Reviewing a queue beats
re-reading chats: months of logs reduce to a few hundred classified rows.

When a telemetry sink (see ``telemetry.py``) is supplied, records replayed
here are cross-referenced against *live* fires by draft fingerprint
(``draft_sha256``), so you can tell "would fire today" apart from "actually
fired in production".
"""
from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path

from hermeneutic.gates.regex import highest_severity, risk_score
from hermeneutic.triples import (
    DEFAULT_PATTERNS,
    READERS,
    Triple,
    _is_subagent,
    _looks_like_correction,
)

_EXCERPT = 1200


@dataclass
class QueueRecord:
    """One reviewable harvest event."""
    kind: str                    # confirmed_catch | possible_false_positive | missed_drift
    session: str
    timestamp: str
    rule_ids: list[str]          # rules that fired on the assistant turn ([] for missed_drift)
    severity: str | None
    orig_prompt: str             # user turn that produced the assistant turn
    assistant_excerpt: str       # the (would-be) gated draft
    user_reaction: str           # the user's actual next turn
    draft_sha256: str            # fingerprint of the FULL assistant turn (joins telemetry)
    live_fire: bool = False      # True when a telemetry record matches draft_sha256
    status: str = "pending"      # pending | accepted | rejected (flipped at review time)
    matched: list[str] = field(default_factory=list)  # matched_text per hit, for review at a glance

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_sanitized_json(self) -> str:
        """Serialize with ALL text content removed — classification metadata
        only: kinds, rule ids, severity, timestamps, content fingerprints and
        text LENGTHS, never text. The session name is hashed too (it can embed
        project paths). This reduces exposure but is not anonymization; review
        the metadata against your policy before sharing it off-machine.
        """
        d = asdict(self)
        for field_name in ("orig_prompt", "assistant_excerpt", "user_reaction"):
            d[f"{field_name}_len"] = len(d.pop(field_name) or "")
        d.pop("matched", None)
        d["session"] = _sha256(self.session)[:16]
        d["sanitized"] = True
        return json.dumps(d, ensure_ascii=False)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _live_fingerprints(telemetry_path: str | Path | None) -> set[str]:
    """Collect draft fingerprints of live gate fires from a telemetry sink."""
    if not telemetry_path:
        return set()
    path = Path(telemetry_path)
    if not path.is_file():
        return set()
    prints: set[str] = set()
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("event") == "gate" and rec.get("draft_sha256"):
                    prints.add(rec["draft_sha256"])
    except OSError:
        return prints
    return prints


def harvest_file(
    path: str | Path,
    fmt: str = "claude-code",
    live: set[str] | None = None,
) -> list[QueueRecord]:
    """Replay the gate over one session file and classify every event."""
    path = Path(path)
    reader = READERS.get(fmt)
    if reader is None:
        raise ValueError(f"unknown format: {fmt}. Available: {list(READERS)}")
    correction_rx = [re.compile(p, re.IGNORECASE) for p in DEFAULT_PATTERNS]
    live = live or set()

    turns = list(reader.iter_turns(path))
    records: list[QueueRecord] = []

    for i, (role, text, ts) in enumerate(turns):
        if role != "assistant" or not text.strip() or _is_subagent(text):
            continue
        # The user's actual next turn decides the classification; an
        # assistant turn with no following user turn is unknowable — skip.
        reaction = None
        for j in range(i + 1, len(turns)):
            r_role, r_text, _ = turns[j]
            if r_role == "user" and r_text.strip() and not _is_subagent(r_text):
                reaction = r_text
                break
        if reaction is None:
            continue

        hits = risk_score(text)
        corrected = _looks_like_correction(reaction, correction_rx)
        if hits and corrected:
            kind = "confirmed_catch"
        elif hits:
            kind = "possible_false_positive"
        elif corrected:
            kind = "missed_drift"
        else:
            continue  # gate silent, user content — nothing to review

        # Nearest preceding real user turn = the prompt that produced this draft.
        orig = ""
        for j in range(i - 1, -1, -1):
            if turns[j][0] == "user" and turns[j][1].strip() and not _is_subagent(turns[j][1]):
                orig = turns[j][1][:_EXCERPT]
                break

        fingerprint = _sha256(text)
        records.append(QueueRecord(
            kind=kind,
            session=path.stem,
            timestamp=ts,
            rule_ids=[h.rule_id for h in hits],
            severity=highest_severity(hits),
            orig_prompt=orig,
            assistant_excerpt=text[:_EXCERPT],
            user_reaction=reaction[:800],
            draft_sha256=fingerprint,
            live_fire=fingerprint in live,
            matched=[h.matched_text for h in hits],
        ))
    return records


def harvest_dir(
    directory: str | Path,
    fmt: str = "claude-code",
    glob: str = "*.jsonl",
    telemetry_path: str | Path | None = None,
) -> Iterator[QueueRecord]:
    """Harvest all session files in a directory. Yields queue records lazily.

    Duplicate assistant turns (same content fingerprint + kind) are emitted
    once — re-running over overlapping log dirs won't flood the queue.
    """
    directory = Path(directory)
    live = _live_fingerprints(telemetry_path)
    seen: set[tuple[str, str]] = set()
    for fp in sorted(directory.glob(glob)):
        for rec in harvest_file(fp, fmt=fmt, live=live):
            key = (rec.kind, rec.draft_sha256)
            if key in seen:
                continue
            seen.add(key)
            yield rec


def promote(queue_path: str | Path) -> Iterator[Triple]:
    """Convert reviewed queue records into corpus triples.

    Only records with ``status: "accepted"`` and a correction-bearing kind
    (``confirmed_catch`` / ``missed_drift``) become triples — a false positive
    has no user correction to learn from. The repair turn is not captured at
    harvest time, so ``next_assistant`` is empty; the compile layer retrieves
    on ``orig_prompt``/``user_correction``, which are both present.
    """
    with open(queue_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("status") != "accepted":
                continue
            if d.get("kind") not in ("confirmed_catch", "missed_drift"):
                continue
            yield Triple(
                session=d.get("session", ""),
                timestamp=d.get("timestamp", ""),
                orig_prompt=d.get("orig_prompt", ""),
                prior_assistant=d.get("assistant_excerpt", ""),
                user_correction=d.get("user_reaction", ""),
                next_assistant="",
            )
