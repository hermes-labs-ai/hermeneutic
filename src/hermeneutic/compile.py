"""Layer 2 — input compiler.

Given a new user prompt, retrieve historical (drift, steer) pairs from past
sessions where similar prompts were misinterpreted, and synthesize a
"watch out for X" preamble. Deterministic template-based synthesis; no
LLM at compile time. Embedding via local Ollama (`nomic-embed-text`).

Storage: ~/.hermeneutic/{triples.jsonl, embeddings.json}.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from hermeneutic.triples import Triple

# ---- defaults ----

DEFAULT_HOME = Path.home() / ".hermeneutic"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_TOP_K = 10                     # max total matches surfaced (cap)
DEFAULT_N_PER_BUCKET = 2               # max matches surfaced PER bucket (bucket-aware retrieval)
DEFAULT_SIM_THRESHOLD = 0.5            # library cosine floor; CLI/hook explicitly use 0.4

# Bucket-aware retrieval prevents a common category from occupying every slot.
# The current evaluator in evals/leave-one-out/ calls compile_prompt directly,
# records both shipped default profiles, and keeps earlier measurements clearly
# labeled as historical experiments.

# Same buckets the CLI uses (kept here to avoid import cycle with cli.py).
BUCKET_PATTERNS: list[tuple[str, str, str]] = [
    ("over_completion", r"\b(wait,? (are you|really)|are you sure|did you actually|prove it|where'?s the (evidence|proof))",
     "default to citing evidence (file:line, command output) when claiming completion"),
    ("missed_constraint", r"\b(i (said|told you)|already|forgot|missed|you didn'?t|re-?read|memory|claude\.md|handbook)",
     "re-read prior turns + memory before assuming; the user often has standing instructions"),
    ("over_confirmation", r"\b(just do|stop asking|execute|go|ship|run it|why are you asking)",
     "execute when the user's intent is unambiguous; don't ask clarifying questions on imperative requests"),
    ("wrong_target", r"\b(not (that|this|the right)|wrong (file|repo|project|one)|i meant|different)",
     "if the user quoted a literal spec, use it verbatim; don't expand or substitute"),
    ("scope_creep", r"\b(too much|over[- ]?engineer|scope|just (do|the)|simpler|simplify|less|smaller|stop adding|don'?t (add|build|refactor))",
     "do only what was asked; no volunteered orchestration or extra refactors"),
    ("tone_format", r"\b(too long|too verbose|tl;?dr|shorter|terse|stop (explaining|summari)|preamble|just (give|tell|show))",
     "be concise; verdict-first, no preamble"),
    ("fabrication", r"\b(made up|fabricat|hallucinat|where did you get|that'?s not real|doesn'?t exist|made that up)",
     "every number/name/path must trace to a tool call in the same turn — never inherit from memory or docs"),
    ("tool_choice", r"\b(use (the|a)|wrong tool|why (didn'?t|aren'?t) you|should have used)",
     "check the registered tool vault before reaching for ad-hoc bash"),
]
_BUCKET_COMPILED = [(name, re.compile(pat, re.I), advice) for name, pat, advice in BUCKET_PATTERNS]


def bucket_for(correction_text: str) -> tuple[str, str] | None:
    """Return (bucket_name, advice) for a correction text, or None."""
    for name, rx, advice in _BUCKET_COMPILED:
        if rx.search(correction_text):
            return (name, advice)
    return None


# ---- embedding ----

# Embedder protocol: callable that takes a string, returns a list[float].
# Default uses Ollama; tests inject a deterministic seeded embedder.
Embedder = Callable[[str], list[float]]


class OllamaUnavailable(RuntimeError):
    pass


class MalformedTriplesError(ValueError):
    """A triples JSONL row could not be decoded into the corpus schema."""

    def __init__(self, line_number: int, detail: str):
        self.line_number = line_number
        self.detail = detail
        super().__init__(f"line {line_number}: {detail}")


def ollama_embed(text: str, *, url: str = DEFAULT_OLLAMA_URL,
                 model: str = DEFAULT_EMBED_MODEL, timeout: float = 10.0,
                 keep_alive: str = "30m") -> list[float]:
    """One-shot embedding via local Ollama. Raises OllamaUnavailable on failure.

    `keep_alive` keeps the embedding model resident in Ollama between calls.
    Without this, hook-fire cold-starts (load model + embed) exceed the
    5s Claude UserPromptSubmit timeout and the preamble is silently dropped.
    """
    payload = json.dumps({
        "model": model, "prompt": text, "keep_alive": keep_alive,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ConnectionError) as e:
        raise OllamaUnavailable(f"Ollama unreachable at {url}: {e}") from e
    vec = data.get("embedding")
    if not isinstance(vec, list) or not vec:
        raise OllamaUnavailable(f"Ollama returned no embedding (model={model}, response keys={list(data.keys())})")
    return vec


def _normalize(vec: list[float]) -> list[float]:
    s = sum(x * x for x in vec) ** 0.5
    return [x / s for x in vec] if s > 0 else vec


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=False))


# ---- index storage ----

@dataclass
class EmbedIndex:
    """In-memory index loaded from ~/.hermeneutic/embeddings.json."""
    triples_sha256: str
    model: str
    dim: int
    vectors: list[list[float]]   # already normalized
    triple_indices: list[int]    # which triple each vector came from


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def index_path(home: Path = DEFAULT_HOME) -> Path:
    return home / "embeddings.json"


def load_index(home: Path = DEFAULT_HOME) -> EmbedIndex | None:
    path = index_path(home)
    if not path.is_file():
        return None
    raw = json.loads(path.read_text())
    return EmbedIndex(
        triples_sha256=raw["triples_sha256"],
        model=raw["model"],
        dim=raw["dim"],
        vectors=raw["vectors"],
        triple_indices=raw["triple_indices"],
    )


def save_index(idx: EmbedIndex, home: Path = DEFAULT_HOME) -> None:
    home.mkdir(parents=True, exist_ok=True)
    index_path(home).write_text(json.dumps({
        "triples_sha256": idx.triples_sha256,
        "model": idx.model,
        "dim": idx.dim,
        "vectors": idx.vectors,
        "triple_indices": idx.triple_indices,
    }))


# ---- public API ----

@dataclass
class CompileIndexResult:
    state: str        # "built" | "up-to-date" | "no-eligible-triples"
    n_triples: int
    n_eligible: int
    n_v01_legacy: int  # triples without orig_prompt — surfaces migration warning
    dim: int
    model: str


def _load_triples(triples_path: Path) -> list[Triple]:
    required_fields = (
        "session", "timestamp", "prior_assistant", "user_correction", "next_assistant",
    )
    allowed_fields = {*required_fields, "orig_prompt"}
    triples: list[Triple] = []
    for line_number, line in enumerate(triples_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MalformedTriplesError(
                line_number,
                f"invalid JSON at column {exc.colno}: {exc.msg}",
            ) from None
        if not isinstance(raw, dict):
            raise MalformedTriplesError(line_number, "expected a JSON object")
        missing = [field for field in required_fields if field not in raw]
        if missing:
            label = "field" if len(missing) == 1 else "fields"
            names = ", ".join(repr(field) for field in missing)
            raise MalformedTriplesError(line_number, f"missing required {label} {names}")
        unexpected = sorted(set(raw) - allowed_fields)
        if unexpected:
            label = "field" if len(unexpected) == 1 else "fields"
            names = ", ".join(repr(field) for field in unexpected)
            raise MalformedTriplesError(line_number, f"unexpected {label} {names}")
        # Timestamp is provenance metadata and is not consumed by compilation;
        # legacy producers may emit numbers or nulls. Keep requiring the field,
        # but validate only text that the index reads.
        for field in allowed_fields - {"timestamp"}:
            if field in raw and not isinstance(raw[field], str):
                raise MalformedTriplesError(
                    line_number,
                    f"field {field!r} must be a string, got {type(raw[field]).__name__}",
                )
        raw.setdefault("orig_prompt", "")
        triples.append(Triple(**raw))
    return triples


def compile_index(triples_path: Path, *, home: Path = DEFAULT_HOME,
                  embedder: Embedder | None = None,
                  model: str = DEFAULT_EMBED_MODEL) -> CompileIndexResult:
    """Build (or refresh) the embedding index from a triples.jsonl file."""
    triples_path = Path(triples_path)
    if not triples_path.is_file():
        raise FileNotFoundError(f"triples file not found: {triples_path}")

    sha = _sha256_file(triples_path)
    existing = load_index(home)
    triples = _load_triples(triples_path)
    eligible = [(i, t) for i, t in enumerate(triples) if t.orig_prompt.strip()]
    n_legacy = len(triples) - len(eligible)

    if existing and existing.triples_sha256 == sha and existing.model == model:
        return CompileIndexResult(
            state="up-to-date", n_triples=len(triples), n_eligible=len(eligible),
            n_v01_legacy=n_legacy, dim=existing.dim, model=existing.model,
        )

    if not eligible:
        return CompileIndexResult(
            state="no-eligible-triples", n_triples=len(triples), n_eligible=0,
            n_v01_legacy=n_legacy, dim=0, model=model,
        )

    embed = embedder or (lambda t: ollama_embed(t, model=model))
    vectors: list[list[float]] = []
    triple_indices: list[int] = []
    for i, t in eligible:
        v = _normalize(embed(t.orig_prompt[:1500]))
        vectors.append(v)
        triple_indices.append(i)

    idx = EmbedIndex(
        triples_sha256=sha, model=model, dim=len(vectors[0]),
        vectors=vectors, triple_indices=triple_indices,
    )
    save_index(idx, home)
    return CompileIndexResult(
        state="built", n_triples=len(triples), n_eligible=len(eligible),
        n_v01_legacy=n_legacy, dim=idx.dim, model=model,
    )


@dataclass
class CompileMatch:
    triple: Triple
    similarity: float
    bucket: str
    advice: str


def compile_prompt(prompt: str, triples_path: Path, *, home: Path = DEFAULT_HOME,
                   k: int = DEFAULT_TOP_K, threshold: float = DEFAULT_SIM_THRESHOLD,
                   n_per_bucket: int = DEFAULT_N_PER_BUCKET,
                   embedder: Embedder | None = None,
                   model: str = DEFAULT_EMBED_MODEL) -> str:
    """Embed a prompt, retrieve bucket-aware top-N per bucket, return preamble.

    Bucket-aware retrieval semantics:
      - Score the query against every indexed vector.
      - Filter to candidates above `threshold` cosine similarity.
      - Group candidates by their bucket (via `bucket_for(user_correction)`).
      - Take top-`n_per_bucket` highest-similarity candidates within each bucket.
      - Cap total surfaced matches at `k` (sorted by within-bucket similarity).

    Returns empty string if no matches clear the threshold or index doesn't exist.

    Why bucket-aware: a global top-K can let a common correction category crowd
    out rarer categories. Current and historical aggregate measurements, with
    their different default profiles and evidence boundaries, are documented in
    evals/leave-one-out/RESULTS.md.
    """
    if not prompt.strip():
        return ""
    idx = load_index(home)
    if idx is None:
        return ""
    if idx.model != model:
        # Model mismatch — re-index needed; silent rather than break.
        return ""

    triples_path = Path(triples_path)
    triples = [Triple.from_json(line) for line in triples_path.read_text().splitlines() if line.strip()]

    embed = embedder or (lambda t: ollama_embed(t, model=model))
    try:
        q = _normalize(embed(prompt[:1500]))
    except OllamaUnavailable:
        return ""
    if len(q) != idx.dim:
        return ""  # dim mismatch — silent skip

    # Score and bin by bucket
    by_bucket: dict[str, list[CompileMatch]] = {}
    for vec, ti in zip(idx.vectors, idx.triple_indices, strict=False):
        sim = _cosine(q, vec)
        if sim < threshold:
            continue
        if ti >= len(triples):
            continue  # triples file changed between index + this call
        bucket = bucket_for(triples[ti].user_correction)
        if bucket is None:
            continue
        by_bucket.setdefault(bucket[0], []).append(CompileMatch(
            triple=triples[ti], similarity=sim,
            bucket=bucket[0], advice=bucket[1],
        ))

    # Bucket-aware: take top-n_per_bucket within each bucket, then global cap k
    scored: list[CompileMatch] = []
    for _bucket, matches in by_bucket.items():
        matches.sort(key=lambda m: -m.similarity)
        scored.extend(matches[:n_per_bucket])
    scored.sort(key=lambda m: -m.similarity)
    top = scored[:k]
    if not top:
        return ""

    return _synthesize_preamble(top)


def _synthesize_preamble(matches: list[CompileMatch]) -> str:
    """Group matches by bucket, emit a deterministic template preamble."""
    bucket_counts = Counter(m.bucket for m in matches)
    bucket_advice = {m.bucket: m.advice for m in matches}
    lines = [
        f"[hermeneutic compile-preamble — derived from {len(matches)} past corrections on similar prompts]"
    ]
    for bucket, count in sorted(bucket_counts.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {count} prior steer(s) in bucket `{bucket}`: {bucket_advice[bucket]}")
    lines.append("[end preamble]")
    return "\n".join(lines)


# ---- env-aware home dir ----

def home_dir() -> Path:
    """Honors $HERMENEUTIC_HOME for tests; defaults to ~/.hermeneutic/."""
    override = os.environ.get("HERMENEUTIC_HOME")
    return Path(override).expanduser() if override else DEFAULT_HOME
