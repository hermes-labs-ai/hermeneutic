"""Mine (prior_assistant, user_correction, next_assistant) triples from chat logs.

Supports two formats out of the box:
  - "claude-code": Anthropic Claude Code session JSONL (~/.claude/projects/*/*.jsonl)
  - "openai": ChatCompletion-style messages list (one JSON file per session)

Add a new format by subclassing LogReader.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

# Strong correction markers — start of message, case-insensitive.
# These are the *steer signals*: explicit user pushback on the prior assistant turn.
DEFAULT_PATTERNS = [
    r"^\s*no[\s,.!]",
    r"^\s*no+\b",
    r"^\s*not (that|what|quite|exactly|the)",
    r"^\s*that'?s not",
    r"^\s*i (didn'?t|did not|never) (mean|say|ask)",
    r"^\s*i meant\b",
    r"^\s*actually[,\s]",
    r"^\s*wait[,\s.]",
    r"^\s*stop\b",
    r"^\s*wrong\b",
    r"^\s*don'?t\b.*\b(do|use|run|make|write|add|build)",
    r"^\s*you (misunderstood|missed|didn'?t)",
    r"^\s*hold on",
    r"^\s*re-?read",
    r"^\s*you'?re (off|wrong|missing)",
    r"^\s*nope\b",
    r"\bi said\b",
    r"\bnot what i\b",
    r"^\s*ugh\b",
]

# Substrings that mark a "user" turn as actually subagent / system input — skip these.
SUBAGENT_MARKERS = [
    "You are QA for",
    "Answer ONLY: YES or NO",
    "<system-reminder>",
    "Caveat:",
    "[Request interrupted",
]


@dataclass
class Triple:
    """A single (drift, steer, repair) record.

    v0.1.5 added `orig_prompt` (the user turn that produced the drift) to
    enable the compile layer's prompt-similarity retrieval. Old triples
    written before v0.1.5 load fine with `orig_prompt` defaulting to "".
    """
    session: str
    timestamp: str
    prior_assistant: str
    user_correction: str
    next_assistant: str
    orig_prompt: str = ""  # NEW in v0.1.5; empty for triples mined with v0.1.x

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> Triple:
        """Backwards-compatible loader — accepts v0.1.x triples missing orig_prompt."""
        d = json.loads(line)
        d.setdefault("orig_prompt", "")
        return cls(**d)


# ---------- format readers ----------

class LogReader:
    """Subclass and override `iter_turns` to support a new chat-log format."""
    name = "base"

    def iter_turns(self, path: Path) -> Iterator[tuple[str, str, str]]:
        """Yield (role, text, timestamp) for each turn in chronological order."""
        raise NotImplementedError


class ClaudeCodeReader(LogReader):
    """Anthropic Claude Code session JSONL."""
    name = "claude-code"

    def iter_turns(self, path: Path) -> Iterator[tuple[str, str, str]]:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    role = d.get("type")
                    if role not in ("user", "assistant"):
                        continue
                    msg = d.get("content") or d.get("message") or {}
                    if not isinstance(msg, dict):
                        continue
                    text = _extract_text(msg.get("content", ""))
                    yield role, text, d.get("timestamp", "")
        except OSError:
            return


class OpenAIReader(LogReader):
    """OpenAI ChatCompletion-style messages list. One JSON file per session.

    Expected shape: {"messages": [{"role": "user|assistant", "content": "..."}, ...]}
    or just a top-level list of messages.
    """
    name = "openai"

    def iter_turns(self, path: Path) -> Iterator[tuple[str, str, str]]:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                d = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        msgs = d.get("messages") if isinstance(d, dict) else d
        if not isinstance(msgs, list):
            return
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = m.get("role")
            if role not in ("user", "assistant"):
                continue
            content = m.get("content", "")
            text = content if isinstance(content, str) else _extract_text(content)
            yield role, text, m.get("timestamp", "")


class CodexReader(LogReader):
    """OpenAI Codex CLI session rollouts (``~/.codex/sessions/**/rollout-*.jsonl``).

    Schema (verified against live Codex CLI sessions, 2026-07-08): one JSON
    object per line; conversation turns are ``{"type": "response_item",
    "payload": {"type": "message", "role": "user"|"assistant",
    "content": [{"type": "input_text"|"output_text", "text": ...}]}}``.
    Injected wrappers (``<environment_context>``, permissions preambles,
    developer role) are skipped; genuine user pushback survives.
    """
    name = "codex"

    def iter_turns(self, path: Path) -> Iterator[tuple[str, str, str]]:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if d.get("type") != "response_item":
                        continue
                    p = d.get("payload") or {}
                    if p.get("type") != "message":
                        continue
                    role = p.get("role")
                    if role not in ("user", "assistant"):
                        continue
                    text = _extract_text(p.get("content", ""))
                    if role == "user" and text.lstrip().startswith("<"):
                        # environment_context / permissions wrappers, not the human
                        continue
                    yield role, text, d.get("timestamp", "")
        except OSError:
            return


READERS: dict[str, LogReader] = {
    "claude-code": ClaudeCodeReader(),
    "codex": CodexReader(),
    "openai": OpenAIReader(),
}


def _extract_text(content) -> str:
    """Pull text out of a content field that may be str or list-of-blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                if b.get("type") in ("text", "input_text", "output_text"):
                    parts.append(b.get("text", ""))
                elif b.get("type") == "tool_use":
                    parts.append(f"[tool:{b.get('name','?')}]")
        return "\n".join(parts)
    return ""


# ---------- mining ----------

def _looks_like_correction(text: str, patterns: list[re.Pattern]) -> bool:
    if not text or len(text) > 2000:
        return False
    head = text[:300]
    return any(p.search(head) for p in patterns)


def _is_subagent(text: str) -> bool:
    if not text:
        return True
    head = text[:200]
    return any(m in head for m in SUBAGENT_MARKERS)


def mine_file(
    path: str | Path,
    fmt: str = "claude-code",
    patterns: Iterable[str] | None = None,
) -> list[Triple]:
    """Mine one session file into triples."""
    path = Path(path)
    reader = READERS.get(fmt)
    if reader is None:
        raise ValueError(f"unknown format: {fmt}. Available: {list(READERS)}")
    compiled = [re.compile(p, re.IGNORECASE) for p in (patterns or DEFAULT_PATTERNS)]

    turns = list(reader.iter_turns(path))
    triples: list[Triple] = []

    for i, (role, text, ts) in enumerate(turns):
        if role != "user":
            continue
        if _is_subagent(text):
            continue
        if not _looks_like_correction(text, compiled):
            continue
        # prior assistant turn (the drift)
        prior = None
        prior_idx = -1
        for j in range(i - 1, -1, -1):
            if turns[j][0] == "assistant" and turns[j][1].strip() and not _is_subagent(turns[j][1]):
                prior = turns[j]
                prior_idx = j
                break
        if not prior:
            continue
        # original user prompt (the input that produced the drift) — search back
        # from prior_assistant for the nearest non-subagent user turn.
        orig = ""
        for j in range(prior_idx - 1, -1, -1):
            if turns[j][0] == "user" and turns[j][1].strip() and not _is_subagent(turns[j][1]):
                orig = turns[j][1][:1500]
                break
        # next assistant turn within a small window (the repair)
        nxt = None
        for j in range(i + 1, min(i + 5, len(turns))):
            if turns[j][0] == "assistant" and turns[j][1].strip() and not _is_subagent(turns[j][1]):
                nxt = turns[j]
                break
        triples.append(Triple(
            session=path.stem,
            timestamp=ts,
            orig_prompt=orig,
            prior_assistant=prior[1][:1200],
            user_correction=text[:800],
            next_assistant=(nxt[1][:1200] if nxt else ""),
        ))
    return triples


def mine_dir(
    directory: str | Path,
    fmt: str = "claude-code",
    glob: str = "*.jsonl",
    patterns: Iterable[str] | None = None,
) -> Iterator[Triple]:
    """Mine all session files in a directory. Yields triples lazily."""
    directory = Path(directory)
    for fp in sorted(directory.glob(glob)):
        yield from mine_file(fp, fmt=fmt, patterns=patterns)
