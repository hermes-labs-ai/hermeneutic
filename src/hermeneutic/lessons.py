"""Explicit, scoped interpretation of correction evidence and bounded transfer.

The host supplies the interpretation. Retrieval is a conservative lexical
selector over task examples, not an interpreter or an applicability decision.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path

MAX_MEMORY_BYTES = 1_048_576
MAX_CORPUS_BYTES = 16_777_216
MAX_RECORD_BYTES = 1_048_576
MAX_LESSONS = 100
MAX_LESSON_CHARS = 1200
MAX_WHEN_EXAMPLES = 8
MAX_WHEN_CHARS = 240
MAX_INSTRUCTION_CHARS = 4000
MAX_MATCHES = 5
_EPISODE_CAPS = {
    "session": 128, "timestamp": 64, "orig_prompt": 600,
    "prior_assistant": 600, "user_correction": 800, "next_assistant": 600,
}
_STOPWORDS = frozenset([
    "the", "and", "for", "that", "this", "with", "from", "have", "will", "your", "you", "are",
    "should", "what", "how", "when", "can", "could", "would", "our", "using", "use", "only", "into",
    "about", "not", "without", "need", "any", "before", "after", "then", "just", "than", "but", "was",
    "were", "does", "did", "its", "they", "them", "their", "there", "here", "been", "being", "also",
    "please", "help", "want", "like", "make", "take", "give", "work", "today", "again",
])
USAGE = (
    "Host-interpreted historical context; check applicability and conflicts. "
    "Current explicit instructions take precedence. Lexical matches do not establish semantic applicability. "
    "Single-term overlaps are weak cues and require particular applicability review. "
    "Use only through host-controlled explicit insertion; do not execute automatically. "
    "If lessons conflict, do not silently choose a winner; clarify or revoke and replace the old lesson."
)


class LessonMemoryError(ValueError):
    """A bounded-input, evidence, storage, or concurrency check failed."""


def _json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("ascii")


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _strict_json(raw: bytes):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise LessonMemoryError("duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(_value):
        raise LessonMemoryError("non-standard JSON constant")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise LessonMemoryError("invalid UTF-8 JSON") from error


def _text(value, name: str, cap: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > cap or (not empty and not value.strip()):
        raise LessonMemoryError(f"invalid or overlong {name}")
    try:
        value.encode("utf-8")
    except UnicodeError as error:
        raise LessonMemoryError(f"invalid Unicode in {name}") from error
    return value


def _scope(value: str) -> str:
    _text(value, "scope", 128)
    if value.strip() != value or any(ord(char) < 32 for char in value):
        raise LessonMemoryError("scope must be an explicit opaque label without control characters")
    return value


def _identity(info) -> tuple:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


@contextmanager
def _parent(path: str | Path):
    """Pin the parent directory, rejecting symlinks in every path component."""
    path = Path(path).absolute()
    if path.name in ("", ".", ".."):
        raise LessonMemoryError("expected an explicit file path")
    directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parent.parts[1:]:
            if part == "..":
                raise LessonMemoryError("parent traversal is not supported")
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        yield directory, path.name
    finally:
        os.close(directory)


def _verify_parent(path: str | Path, directory: int) -> None:
    with _parent(path) as (current, _name):
        expected = os.fstat(directory)
        actual = os.fstat(current)
        if (expected.st_dev, expected.st_ino) != (actual.st_dev, actual.st_ino):
            raise LessonMemoryError("parent directory changed during operation")


def _read_at(directory: int, name: str, maximum: int, *, missing: bool = False):
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except FileNotFoundError:
        if missing:
            return None, None
        raise
    with os.fdopen(descriptor, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise LessonMemoryError("input must be a regular file with a single link")
        if before.st_size > maximum:
            raise LessonMemoryError("input exceeds size limit")
        raw = source.read(maximum + 1)
        after = os.fstat(source.fileno())
    current = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if len(raw) > maximum:
        raise LessonMemoryError("input exceeds size limit")
    if _identity(before) != _identity(after) or _identity(after) != _identity(current):
        raise LessonMemoryError("input changed during operation")
    return raw, _identity(after)


def _read_file(path: str | Path, maximum: int) -> bytes:
    with _parent(path) as (directory, name):
        raw, _token = _read_at(directory, name, maximum)
        _verify_parent(path, directory)
        return raw


def _lesson_id(record: dict) -> str:
    content = {key: record[key] for key in ("version", "interpretation", "scope", "lesson", "when", "provenance")}
    return "lesson-" + _digest(_json_bytes(content))[:24]


def _validate_record(record) -> None:
    expected = {"id", "version", "status", "interpretation", "scope", "lesson", "when", "provenance"}
    if not isinstance(record, dict) or set(record) != expected:
        raise LessonMemoryError("invalid lesson schema")
    if type(record["version"]) is not int or record["version"] != 1:
        raise LessonMemoryError("unsupported lesson version")
    if record["status"] not in ("candidate", "active", "revoked"):
        raise LessonMemoryError("invalid lesson status")
    if record["interpretation"] not in ("host_supplied", "source_verbatim"):
        raise LessonMemoryError("invalid interpretation attribution")
    _scope(record["scope"])
    _text(record["lesson"], "lesson", MAX_LESSON_CHARS)
    examples = record["when"]
    if not isinstance(examples, list) or not 1 <= len(examples) <= MAX_WHEN_EXAMPLES:
        raise LessonMemoryError("invalid task examples")
    for example in examples:
        _text(example, "task example", MAX_WHEN_CHARS)
    if len(set(examples)) != len(examples):
        raise LessonMemoryError("duplicate task example")
    provenance = record["provenance"]
    keys = {"evidence", "corpus_sha256", "record_sha256", "episode", "truncated"}
    if not isinstance(provenance, dict) or set(provenance) != keys:
        raise LessonMemoryError("invalid provenance schema")
    if (not isinstance(provenance["evidence"], str)
            or not re.fullmatch(r"triple-id-[1-9][0-9]{0,8}", provenance["evidence"])):
        raise LessonMemoryError("invalid evidence identifier")
    for key in ("corpus_sha256", "record_sha256"):
        if not isinstance(provenance[key], str) or not re.fullmatch(r"[0-9a-f]{64}", provenance[key]):
            raise LessonMemoryError("invalid evidence fingerprint")
    episode = provenance["episode"]
    truncated = provenance["truncated"]
    if not isinstance(episode, dict) or set(episode) != set(_EPISODE_CAPS):
        raise LessonMemoryError("invalid episode snapshot")
    if not isinstance(truncated, dict) or set(truncated) != set(_EPISODE_CAPS):
        raise LessonMemoryError("invalid episode truncation flags")
    for key, cap in _EPISODE_CAPS.items():
        _text(episode[key], "episode field", cap, empty=True)
        if type(truncated[key]) is not bool:
            raise LessonMemoryError("invalid episode truncation flag")
    if (record["interpretation"] == "source_verbatim" and record["status"] == "active"
            and truncated["user_correction"]):
        raise LessonMemoryError("truncated source correction requires an explicit host interpretation")
    if record["id"] != _lesson_id(record):
        raise LessonMemoryError("lesson identity mismatch")


def _load_at(directory: int, name: str):
    raw, token = _read_at(directory, name, MAX_MEMORY_BYTES, missing=True)
    if raw is None:
        return {"schema_version": 1, "revision": 0, "lessons": []}, token
    store = _strict_json(raw)
    if not isinstance(store, dict) or set(store) != {"schema_version", "revision", "lessons"}:
        raise LessonMemoryError("invalid memory schema")
    if type(store["schema_version"]) is not int or store["schema_version"] != 1:
        raise LessonMemoryError("unsupported memory schema version")
    if type(store["revision"]) is not int or not 0 <= store["revision"] <= 1_000_000_000:
        raise LessonMemoryError("invalid memory revision")
    if not isinstance(store["lessons"], list) or len(store["lessons"]) > MAX_LESSONS:
        raise LessonMemoryError("invalid or overfull lesson list")
    ids = set()
    for record in store["lessons"]:
        _validate_record(record)
        if record["id"] in ids:
            raise LessonMemoryError("duplicate lesson identity")
        ids.add(record["id"])
    return store, token


def _load(memory: str | Path) -> dict:
    with _parent(memory) as (directory, name):
        store, _token = _load_at(directory, name)
        _verify_parent(memory, directory)
        return store


def _assert_unchanged(directory: int, name: str, token) -> None:
    try:
        current = _identity(os.stat(name, dir_fd=directory, follow_symlinks=False))
    except FileNotFoundError:
        current = None
    if current != token:
        raise LessonMemoryError("memory changed during update")


def _update(memory: str | Path, change):
    with _parent(memory) as (directory, name):
        lock_name = ".hermeneutic-" + _digest(os.fsencode(name))[:16] + ".lock"
        try:
            lock = os.open(lock_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                           0o600, dir_fd=directory)
        except FileExistsError as error:
            raise LessonMemoryError("memory update in progress; inspect a stale lock before retrying") from error
        lock_identity = _identity(os.fstat(lock))
        temporary = None
        try:
            store, token = _load_at(directory, name)
            result, changed = change(store)
            if changed:
                store["revision"] += 1
                if store["revision"] > 1_000_000_000:
                    raise LessonMemoryError("memory revision limit reached")
                raw = _json_bytes(store) + b"\n"
                if len(raw) > MAX_MEMORY_BYTES:
                    raise LessonMemoryError("memory exceeds size limit")
                temporary = ".hermeneutic-" + uuid.uuid4().hex + ".tmp"
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     0o600, dir_fd=directory)
                with os.fdopen(descriptor, "wb") as destination:
                    destination.write(raw)
                    destination.flush()
                    os.fsync(destination.fileno())
                _verify_parent(memory, directory)
                _assert_unchanged(directory, name, token)
                os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
                temporary = None
                os.fsync(directory)
            else:
                _assert_unchanged(directory, name, token)
            _verify_parent(memory, directory)
            return result
        finally:
            os.close(lock)
            if temporary is not None:
                os.unlink(temporary, dir_fd=directory)
            try:
                current_lock = _identity(os.stat(lock_name, dir_fd=directory, follow_symlinks=False))
            except FileNotFoundError:
                current_lock = None
            if current_lock == lock_identity:
                os.unlink(lock_name, dir_fd=directory)


def _provenance(triples: str | Path, evidence: str) -> dict:
    if not isinstance(evidence, str) or not re.fullmatch(r"triple-id-[1-9][0-9]{0,8}", evidence):
        raise LessonMemoryError("evidence must name an existing triple-id-N")
    target = int(evidence.removeprefix("triple-id-"))
    raw = _read_file(triples, MAX_CORPUS_BYTES)
    selected = None
    position = 0
    for line in raw.splitlines(keepends=True):
        if not line.strip():
            continue
        if len(line) > MAX_RECORD_BYTES:
            raise LessonMemoryError("corpus record exceeds size limit")
        episode = _strict_json(line)
        required = set(_EPISODE_CAPS) - {"orig_prompt"}
        if not isinstance(episode, dict) or not required <= set(episode) <= set(_EPISODE_CAPS):
            raise LessonMemoryError("invalid correction episode schema")
        episode.setdefault("orig_prompt", "")
        for value in episode.values():
            _text(value, "correction episode field", MAX_RECORD_BYTES, empty=True)
        position += 1
        if position == target:
            if not episode["user_correction"].strip():
                raise LessonMemoryError("selected episode has no explicit correction")
            selected = {
                "evidence": evidence,
                "corpus_sha256": _digest(raw),
                "record_sha256": _digest(line),
                "episode": {key: episode[key][:cap] for key, cap in _EPISODE_CAPS.items()},
                "truncated": {key: len(episode[key]) > cap for key, cap in _EPISODE_CAPS.items()},
            }
    if selected is None:
        raise LessonMemoryError("evidence identifier does not resolve in this corpus")
    return selected


def learn_lesson(*, triples: str | Path, evidence: str, scope: str, memory: str | Path,
                 lesson: str | None = None, when: list[str] | None = None) -> dict:
    """Prepare a source-verbatim candidate or store a host-supplied interpretation.

    Omitted interpretation preserves correction text as a candidate that needs
    explicit confirmation. Omitted examples use the original prompt. This does
    not synthesize meaning. Repeating a revoked lesson does not reactivate it.
    """
    scope = _scope(scope)
    provenance = _provenance(triples, evidence)
    supplied = lesson is not None
    lesson = _text(lesson if supplied else provenance["episode"]["user_correction"],
                   "lesson", MAX_LESSON_CHARS).strip()
    if when is None:
        original = provenance["episode"]["orig_prompt"][:MAX_WHEN_CHARS].strip()
        if not original:
            raise LessonMemoryError("source has no original prompt; supply a representative task example")
        when = [original]
    if not isinstance(when, list) or not 1 <= len(when) <= MAX_WHEN_EXAMPLES:
        raise LessonMemoryError("supply a bounded nonempty list of task examples")
    examples = [_text(example, "task example", MAX_WHEN_CHARS).strip() for example in when]
    record = {
        "version": 1, "status": "active" if supplied else "candidate",
        "interpretation": "host_supplied" if supplied else "source_verbatim",
        "scope": scope, "lesson": lesson, "when": examples, "provenance": provenance,
    }
    record["id"] = _lesson_id(record)
    _validate_record(record)

    def change(store):
        existing = next((item for item in store["lessons"] if item["id"] == record["id"]), None)
        if existing is not None:
            return existing, False
        if len(store["lessons"]) >= MAX_LESSONS:
            raise LessonMemoryError("lesson capacity reached")
        store["lessons"].append(record)
        return record, True

    return _update(memory, change)


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[^\W\d_]{3,}", text.casefold())) - _STOPWORDS


def _limit(value: int, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise LessonMemoryError("invalid result limit")
    return value


def recall_lessons(instruction: str, *, scope: str, memory: str | Path,
                   limit: int = 3, disabled: bool = False) -> list[dict]:
    """Select bounded same-scope active lessons by WHEN examples only.

    Require two shared terms, or the smaller nonempty term set when sparse,
    and at least half of both sets. Unseen paraphrases can still abstain.
    """
    _scope(scope)
    _text(instruction, "instruction", MAX_INSTRUCTION_CHARS, empty=True)
    _limit(limit, MAX_MATCHES)
    if type(disabled) is not bool:
        raise LessonMemoryError("disabled must be a boolean")
    if disabled:
        return []
    terms = _terms(instruction)
    if not terms:
        return []
    matches = []
    for record in _load(memory)["lessons"]:
        if record["status"] != "active" or record["scope"] != scope:
            continue
        best = None
        for example in record["when"]:
            example_terms = _terms(example)
            if not example_terms:
                continue
            shared = terms & example_terms
            if len(shared) < min(2, len(terms), len(example_terms)):
                continue
            query_coverage = len(shared) / len(terms)
            example_coverage = len(shared) / len(example_terms)
            if min(query_coverage, example_coverage) < 0.5:
                continue
            candidate = {
                **record, "matched_when": example, "shared_terms": sorted(shared),
                "weak_match": len(shared) < 2,
                "query_coverage": round(query_coverage, 6),
                "example_coverage": round(example_coverage, 6),
            }
            key = (min(query_coverage, example_coverage), len(shared))
            if best is None or key > best[0]:
                best = key, candidate
        if best is not None:
            matches.append(best)
    matches.sort(key=lambda item: (-item[0][0], -item[0][1], item[1]["id"]))
    return [item[1] for item in matches[:limit]]


def render_context(instruction: str, *, scope: str, memory: str | Path,
                   limit: int = 3, disabled: bool = False) -> dict:
    """Render selected interpretations for an explicit host insertion decision."""
    matches = recall_lessons(instruction, scope=scope, memory=memory, limit=limit, disabled=disabled)
    context = ""
    if matches:
        selected = [{"id": item["id"], "scope": item["scope"], "lesson": item["lesson"],
                     "evidence": item["provenance"]["evidence"],
                     "record_sha256": item["provenance"]["record_sha256"]} for item in matches]
        context = USAGE + "\n" + json.dumps({"lessons": selected}, ensure_ascii=True)
    return {"schema_version": 1, "enabled": not disabled, "scope": scope,
            "context": context, "matches": matches, "usage": USAGE}


def inspect_lessons(*, memory: str | Path, limit: int = 20) -> dict:
    """Inspect bounded original evidence snapshots, including tombstones."""
    _limit(limit, MAX_LESSONS)
    records = _load(memory)["lessons"]
    return {"schema_version": 1, "total": len(records), "lessons": records[:limit]}


def revoke_lesson(lesson_id: str, *, memory: str | Path) -> dict:
    """Tombstone a lesson without removing its interpretation or evidence."""
    if not isinstance(lesson_id, str) or not re.fullmatch(r"lesson-[0-9a-f]{24}", lesson_id):
        raise LessonMemoryError("invalid lesson identifier")

    def change(store):
        record = next((item for item in store["lessons"] if item["id"] == lesson_id), None)
        if record is None:
            raise LessonMemoryError("lesson identifier does not resolve in this memory")
        if record["status"] == "revoked":
            return record, False
        record["status"] = "revoked"
        return record, True

    return _update(memory, change)


def confirm_lesson(lesson_id: str, *, memory: str | Path) -> dict:
    """Activate an inspected candidate; revoked lessons cannot be reactivated."""
    if not isinstance(lesson_id, str) or not re.fullmatch(r"lesson-[0-9a-f]{24}", lesson_id):
        raise LessonMemoryError("invalid lesson identifier")

    def change(store):
        record = next((item for item in store["lessons"] if item["id"] == lesson_id), None)
        if record is None:
            raise LessonMemoryError("lesson identifier does not resolve in this memory")
        if record["status"] == "revoked":
            raise LessonMemoryError("revoked lessons cannot be confirmed; learn a new interpretation")
        if record["interpretation"] == "source_verbatim" and record["provenance"]["truncated"]["user_correction"]:
            raise LessonMemoryError("truncated source correction requires an explicit host interpretation")
        if record["status"] == "active":
            return record, False
        record["status"] = "active"
        return record, True

    return _update(memory, change)
