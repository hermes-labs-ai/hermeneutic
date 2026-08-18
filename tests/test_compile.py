"""Tests for the compile layer (Layer 2)."""
from __future__ import annotations

import io
import json
import re
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from hermeneutic import compile as hcompile
from hermeneutic.triples import Triple


def _seeded_embedder(salt: int = 0):
    """Return a deterministic fake embedder.

    Maps each input to a 16-dim vector based on character bigrams. Same input
    → same vector. Similar inputs → similar vectors. No Ollama needed.
    """
    def emb(text: str) -> list[float]:
        v = [0.0] * 16
        for i in range(len(text) - 1):
            bigram = text[i:i+2]
            slot = (hash(bigram) + salt) % 16
            v[slot] += 1.0
        return v if any(v) else [1.0] + [0.0] * 15
    return emb


def _write_triples(path: Path, triples: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(t) for t in triples) + "\n")


@pytest.fixture
def fixture_corpus(tmp_path):
    """Five triples spanning multiple buckets, all with orig_prompt."""
    triples_path = tmp_path / "triples.jsonl"
    _write_triples(triples_path, [
        {"session": "s1", "timestamp": "t1", "orig_prompt": "build me a thing",
         "prior_assistant": "Done — shipped 5 files",
         "user_correction": "wait, are you sure? show evidence",
         "next_assistant": "let me verify"},
        {"session": "s2", "timestamp": "t2", "orig_prompt": "build me a thing",
         "prior_assistant": "Built it",
         "user_correction": "just go, stop asking",
         "next_assistant": "executing"},
        {"session": "s3", "timestamp": "t3", "orig_prompt": "fix the bug",
         "prior_assistant": "I'll refactor the whole module",
         "user_correction": "no scope creep, just the bug",
         "next_assistant": "narrow fix only"},
        {"session": "s4", "timestamp": "t4", "orig_prompt": "build me a thing",
         "prior_assistant": "I made up some numbers",
         "user_correction": "stop, you fabricated that",
         "next_assistant": "removed"},
        {"session": "s5", "timestamp": "t5", "orig_prompt": "send the email",
         "prior_assistant": "I'll also clean up the inbox",
         "user_correction": "I said just send the email",
         "next_assistant": "sent"},
    ])
    return triples_path


def test_triple_from_json_backcompat():
    """v0.1 triples without orig_prompt load with empty default."""
    line = json.dumps({
        "session": "old", "timestamp": "old",
        "prior_assistant": "x", "user_correction": "no", "next_assistant": "y",
    })
    t = Triple.from_json(line)
    assert t.orig_prompt == ""
    assert t.prior_assistant == "x"


def test_compile_index_builds_and_caches(fixture_corpus, tmp_path):
    home = tmp_path / "home"
    res = hcompile.compile_index(fixture_corpus, home=home, embedder=_seeded_embedder())
    assert res.state == "built"
    assert res.n_eligible == 5
    assert res.n_v01_legacy == 0
    assert (home / "embeddings.json").is_file()

    # Re-running with same triples → up-to-date
    res2 = hcompile.compile_index(fixture_corpus, home=home, embedder=_seeded_embedder())
    assert res2.state == "up-to-date"


def test_compile_index_handles_v01_legacy_triples(tmp_path):
    """Triples without orig_prompt count as legacy and are skipped, not crash."""
    triples_path = tmp_path / "triples.jsonl"
    _write_triples(triples_path, [
        {"session": "s1", "timestamp": "t1",  # no orig_prompt
         "prior_assistant": "x", "user_correction": "no", "next_assistant": "y"},
        {"session": "s2", "timestamp": "t2", "orig_prompt": "real prompt",
         "prior_assistant": "x", "user_correction": "wait, are you sure", "next_assistant": "y"},
    ])
    res = hcompile.compile_index(triples_path, home=tmp_path / "home", embedder=_seeded_embedder())
    assert res.n_v01_legacy == 1
    assert res.n_eligible == 1
    assert res.state == "built"


def test_compile_returns_empty_when_no_index(fixture_corpus, tmp_path):
    out = hcompile.compile_prompt("build me a thing", fixture_corpus,
                                  home=tmp_path / "no-index-here", embedder=_seeded_embedder())
    assert out == ""


def test_compile_returns_preamble_for_matching_prompt(fixture_corpus, tmp_path):
    home = tmp_path / "home"
    hcompile.compile_index(fixture_corpus, home=home, embedder=_seeded_embedder())
    out = hcompile.compile_prompt("build me a thing", fixture_corpus,
                                  home=home, k=5, threshold=0.0,
                                  embedder=_seeded_embedder())
    assert "compile-preamble" in out
    assert "[end preamble]" in out
    # Should contain at least one bucket reference from our fixture
    assert "bucket" in out


def test_compile_deterministic(fixture_corpus, tmp_path):
    home = tmp_path / "home"
    hcompile.compile_index(fixture_corpus, home=home, embedder=_seeded_embedder())
    a = hcompile.compile_prompt("build me a thing", fixture_corpus,
                                home=home, threshold=0.0, embedder=_seeded_embedder())
    b = hcompile.compile_prompt("build me a thing", fixture_corpus,
                                home=home, threshold=0.0, embedder=_seeded_embedder())
    assert a == b


def test_compile_empty_prompt_returns_empty(fixture_corpus, tmp_path):
    home = tmp_path / "home"
    hcompile.compile_index(fixture_corpus, home=home, embedder=_seeded_embedder())
    assert hcompile.compile_prompt("", fixture_corpus, home=home, embedder=_seeded_embedder()) == ""
    assert hcompile.compile_prompt("   ", fixture_corpus, home=home, embedder=_seeded_embedder()) == ""


def test_compile_threshold_filters(fixture_corpus, tmp_path):
    home = tmp_path / "home"
    hcompile.compile_index(fixture_corpus, home=home, embedder=_seeded_embedder())
    # Threshold above 1.0 → nothing matches
    out = hcompile.compile_prompt("build me a thing", fixture_corpus,
                                  home=home, threshold=2.0, embedder=_seeded_embedder())
    assert out == ""


def test_bucket_for_routes_correction_text():
    assert hcompile.bucket_for("wait, are you sure?")[0] == "over_completion"
    assert hcompile.bucket_for("just go")[0] == "over_confirmation"
    assert hcompile.bucket_for("no scope creep")[0] == "scope_creep"
    assert hcompile.bucket_for("you fabricated that")[0] == "fabrication"
    assert hcompile.bucket_for("I said X already")[0] == "missed_constraint"
    assert hcompile.bucket_for("perfectly fine") is None


def test_e2e_mine_index_compile_on_fixture(tmp_path):
    """End-to-end: mine a fixture session log → build index → compile."""
    log = tmp_path / "session.jsonl"
    # Build a tiny session: user says "build me a thing", assistant drifts,
    # user steers with a correction.
    entries = [
        {"type": "user", "timestamp": "2026-04-26T00:00:00Z",
         "content": {"role": "user", "content": "build me a thing"}},
        {"type": "assistant", "timestamp": "2026-04-26T00:00:01Z",
         "content": {"role": "assistant", "content": "Done — shipped 5 files, all good"}},
        {"type": "user", "timestamp": "2026-04-26T00:00:02Z",
         "content": {"role": "user", "content": "wait, are you sure?"}},
        {"type": "assistant", "timestamp": "2026-04-26T00:00:03Z",
         "content": {"role": "assistant", "content": "let me verify"}},
    ]
    log.write_text("\n".join(json.dumps(e) for e in entries))

    # Mine
    from hermeneutic.triples import mine_file
    triples = mine_file(log, fmt="claude-code")
    assert len(triples) == 1
    assert triples[0].orig_prompt == "build me a thing"

    # Save mined triples
    triples_path = tmp_path / "triples.jsonl"
    triples_path.write_text("\n".join(t.to_json() for t in triples))

    # Index
    home = tmp_path / "home"
    res = hcompile.compile_index(triples_path, home=home, embedder=_seeded_embedder())
    assert res.state == "built"

    # Compile a similar prompt
    out = hcompile.compile_prompt("build me a thing", triples_path, home=home,
                                  threshold=0.0, embedder=_seeded_embedder())
    assert "compile-preamble" in out
    assert "over_completion" in out  # the fixture correction is "wait, are you sure?"


MARKER_RX = re.compile(r"\[evidence: triple-id-(\d+)\]")
BULLET_RX = re.compile(r"^- (\d+) prior steer\(s\) in bucket `([^`]+)`: (.+)$")


def test_e2e_evidence_markers_resolve_to_exact_corpus_rows(fixture_corpus, tmp_path):
    """E2E: write corpus → index → compile → every marker resolves to its row.

    Every advice bullet must carry `[evidence: triple-id-N]` markers, and each
    N must be the one-based nonblank JSONL row number of a corpus Triple whose
    user_correction routes to that bullet's bucket.
    """
    home = tmp_path / "home"
    hcompile.compile_index(fixture_corpus, home=home, embedder=_seeded_embedder())
    out = hcompile.compile_prompt("build me a thing", fixture_corpus,
                                  home=home, k=5, threshold=0.0,
                                  embedder=_seeded_embedder())
    corpus_rows = [Triple.from_json(line) for line in fixture_corpus.read_text().splitlines() if line.strip()]
    bullets = [BULLET_RX.match(line) for line in out.splitlines() if line.startswith("- ")]
    assert bullets and all(bullets)

    seen_ids: list[int] = []
    for bullet in bullets:
        bucket, tail = bullet.group(2), bullet.group(3)
        ids = [int(n) for n in MARKER_RX.findall(tail)]
        assert ids, f"bullet lacks evidence markers: {bullet.group(0)}"
        assert ids == sorted(set(ids)), f"markers not ascending/deduplicated: {ids}"
        for n in ids:
            assert 1 <= n <= len(corpus_rows), f"triple-id-{n} does not resolve to a loaded corpus row"
            supporting = corpus_rows[n - 1]
            resolved = hcompile.bucket_for(supporting.user_correction)
            assert resolved is not None
            assert resolved[0] == bucket, (
                f"triple-id-{n} routes to bucket {resolved[0]!r}, "
                f"but is cited under {bucket!r}"
            )
        seen_ids += ids

    # No markers outside advice bullets (header/footer stay marker-free).
    assert sorted(seen_ids) == sorted(int(n) for n in MARKER_RX.findall(out))
    # The fixture retrieves every row (threshold 0, distinct buckets), so the
    # emitted bucket→ids mapping must be exactly the corpus's own routing.
    expected: dict[str, list[int]] = {}
    for row_number, triple in enumerate(corpus_rows, start=1):
        expected.setdefault(hcompile.bucket_for(triple.user_correction)[0], []).append(row_number)
    got = {b.group(2): [int(n) for n in MARKER_RX.findall(b.group(3))] for b in bullets}
    assert got == expected


def test_markers_ascend_by_row_number_for_multiple_same_bucket_matches(tmp_path):
    """Two same-bucket matches cite both rows in ascending numeric order,
    even when the higher row number is the higher-similarity match."""
    triples_path = tmp_path / "triples.jsonl"
    _write_triples(triples_path, [
        {"session": "s1", "timestamp": "t1", "orig_prompt": "build me a thingy",
         "prior_assistant": "Done", "user_correction": "are you sure about that?",
         "next_assistant": "checking"},
        {"session": "s2", "timestamp": "t2", "orig_prompt": "refactor everything please",
         "prior_assistant": "Sure", "user_correction": "too much, don't add extra refactors",
         "next_assistant": "narrowed"},
        {"session": "s3", "timestamp": "t3", "orig_prompt": "build me a thing",
         "prior_assistant": "Done", "user_correction": "wait, are you really done? prove it",
         "next_assistant": "verifying"},
    ])
    home = tmp_path / "home"
    hcompile.compile_index(triples_path, home=home, embedder=_seeded_embedder())
    out = hcompile.compile_prompt("build me a thing", triples_path,
                                  home=home, k=5, threshold=0.0,
                                  embedder=_seeded_embedder())
    over_completion = [line for line in out.splitlines() if "`over_completion`" in line]
    assert len(over_completion) == 1
    assert over_completion[0].endswith("[evidence: triple-id-1] [evidence: triple-id-3]")
    assert MARKER_RX.findall(over_completion[0]) == ["1", "3"]


def test_duplicate_index_entries_do_not_duplicate_markers(tmp_path):
    """A corrupt index citing the same corpus row twice emits one marker."""
    triples_path = tmp_path / "triples.jsonl"
    _write_triples(triples_path, [
        {"session": "s1", "timestamp": "t1", "orig_prompt": "build me a thing",
         "prior_assistant": "Done", "user_correction": "wait, are you sure?",
         "next_assistant": "checking"},
    ])
    emb = _seeded_embedder()
    vec = hcompile._normalize(emb("build me a thing"))
    hcompile.save_index(hcompile.EmbedIndex(
        triples_sha256=hcompile._sha256_file(triples_path),
        model=hcompile.DEFAULT_EMBED_MODEL,
        dim=len(vec), vectors=[vec, vec], triple_indices=[0, 0],
    ), home=tmp_path / "home")
    out = hcompile.compile_prompt("build me a thing", triples_path,
                                  home=tmp_path / "home", threshold=0.0, embedder=emb)
    assert "over_completion" in out
    assert MARKER_RX.findall(out) == ["1"]


def test_stale_out_of_range_index_entries_cannot_generate_markers(fixture_corpus, tmp_path):
    """Out-of-range index entries must never be cited, even when the hash matches.

    Simulates a corrupt index whose triples_sha256 agrees with the corpus but
    whose triple_indices point past it: truncate the corpus, then rewrite the
    stored hash to match, so only the bounds check stands between a stale
    entry and a fabricated citation.
    """
    home = tmp_path / "home"
    hcompile.compile_index(fixture_corpus, home=home, embedder=_seeded_embedder())
    surviving = [line for line in fixture_corpus.read_text().splitlines() if line.strip()][:2]
    fixture_corpus.write_text("\n".join(surviving) + "\n")
    idx = hcompile.load_index(home)
    idx.triples_sha256 = hcompile._sha256_file(fixture_corpus)
    hcompile.save_index(idx, home=home)
    out = hcompile.compile_prompt("build me a thing", fixture_corpus,
                                  home=home, k=5, threshold=0.0,
                                  embedder=_seeded_embedder())
    ids = [int(n) for n in MARKER_RX.findall(out)]
    assert ids, "surviving rows must still be cited"
    assert all(1 <= n <= 2 for n in ids)
    # Buckets only reachable via the removed rows must not appear at all.
    assert "scope_creep" not in out
    assert "fabrication" not in out
    assert "missed_constraint" not in out


def test_compile_returns_empty_when_corpus_reordered_at_same_length(tmp_path):
    """Reordering corpus rows without changing file length must not misattribute.

    Same-length rows defeat the index-bounds check: every stale triple_index
    still resolves, but to the wrong current Triple. The compile must detect
    the content change (triples_sha256 mismatch) and emit nothing rather than
    cite advice and evidence rows under the wrong correction.
    """
    row_a = {"session": "s1", "timestamp": "t1", "orig_prompt": "build me a widget",
             "prior_assistant": "Done", "user_correction": "wait, are you sure?",
             "next_assistant": "checking"}
    row_b = {"session": "s2", "timestamp": "t2", "orig_prompt": "fix the login bug",
             "prior_assistant": "Sure", "user_correction": "too much, simplify!",
             "next_assistant": "narrowed"}
    assert len(json.dumps(row_a)) == len(json.dumps(row_b))
    triples_path = tmp_path / "triples.jsonl"
    _write_triples(triples_path, [row_a, row_b])
    home = tmp_path / "home"
    hcompile.compile_index(triples_path, home=home, embedder=_seeded_embedder())
    original_size = triples_path.stat().st_size

    _write_triples(triples_path, [row_b, row_a])
    assert triples_path.stat().st_size == original_size
    out = hcompile.compile_prompt("build me a widget", triples_path,
                                  home=home, threshold=0.0, embedder=_seeded_embedder())
    assert out == ""


def test_negative_index_entry_generates_no_bullet_or_marker(tmp_path):
    """A corrupt negative index entry must not wrap around into a real row."""
    triples_path = tmp_path / "triples.jsonl"
    _write_triples(triples_path, [
        {"session": "s1", "timestamp": "t1", "orig_prompt": "build me a thing",
         "prior_assistant": "Done", "user_correction": "wait, are you sure?",
         "next_assistant": "checking"},
    ])
    emb = _seeded_embedder()
    vec = hcompile._normalize(emb("build me a thing"))
    hcompile.save_index(hcompile.EmbedIndex(
        triples_sha256=hcompile._sha256_file(triples_path),
        model=hcompile.DEFAULT_EMBED_MODEL,
        dim=len(vec), vectors=[vec], triple_indices=[-1],
    ), home=tmp_path / "home")
    out = hcompile.compile_prompt("build me a thing", triples_path,
                                  home=tmp_path / "home", threshold=0.0, embedder=emb)
    assert out == ""


def test_marker_ids_count_nonblank_rows_only(tmp_path):
    """triple-id-N numbers nonblank JSONL rows; blank lines don't shift IDs."""
    triples_path = tmp_path / "triples.jsonl"
    row1 = json.dumps({"session": "s1", "timestamp": "t1", "orig_prompt": "build me a thing",
                       "prior_assistant": "Done", "user_correction": "wait, are you sure?",
                       "next_assistant": "checking"})
    row2 = json.dumps({"session": "s2", "timestamp": "t2", "orig_prompt": "build me a thing",
                       "prior_assistant": "Sure", "user_correction": "no scope creep please",
                       "next_assistant": "narrowed"})
    triples_path.write_text(row1 + "\n\n\n" + row2 + "\n")
    home = tmp_path / "home"
    hcompile.compile_index(triples_path, home=home, embedder=_seeded_embedder())
    out = hcompile.compile_prompt("build me a thing", triples_path,
                                  home=home, threshold=0.0, embedder=_seeded_embedder())
    scope_line = [line for line in out.splitlines() if "`scope_creep`" in line]
    assert len(scope_line) == 1
    assert MARKER_RX.findall(scope_line[0]) == ["2"]
    assert sorted(MARKER_RX.findall(out)) == ["1", "2"]


def test_compile_index_skips_when_no_triples_file(tmp_path):
    """Missing triples file raises FileNotFoundError, not silent."""
    with pytest.raises(FileNotFoundError):
        hcompile.compile_index(tmp_path / "nope.jsonl", home=tmp_path / "home",
                               embedder=_seeded_embedder())


def test_install_compile_hook_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    from hermeneutic import install_hook
    install_hook.install_compile()
    res = install_hook.install_compile()
    cfg = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    wrapper = str((tmp_path / ".claude" / "hooks" / "hermeneutic-compile.py").resolve())
    matches = [
        h for entry in cfg["hooks"]["UserPromptSubmit"]
        for h in entry.get("hooks", [])
        if h.get("args") == [wrapper]
    ]
    assert len(matches) == 1
    assert matches[0]["command"] == sys.executable
    assert res["settings_state"] == "already-present"


def test_compile_hook_emits_exact_userpromptsubmit_additional_context(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    from hermeneutic import install_hook

    result = install_hook.install_compile()
    wrapper = Path(result["wrapper_path"])
    preamble = "[hermeneutic compile-preamble — derived from 1 past correction]\n- verify first\n[end preamble]"
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout=preamble + "\n", stderr=""),
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(json.dumps({
            "hook_event_name": "UserPromptSubmit",
            "prompt": "ship the release",
        })),
    )

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(wrapper), run_name="__main__")

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": preamble,
        }
    }
    assert "systemMessage" not in captured.out


@pytest.mark.parametrize(
    ("returncode", "stdout", "stderr"),
    [
        (0, "", ""),  # missing corpus or empty compiler result
        (0, "", "[hermeneutic] ollama probe: FAIL"),  # optional Ollama unavailable
        (1, "must not inject", "malformed index state"),
        (2, "must not inject", "compiler error"),
    ],
)
def test_compile_hook_fails_soft_without_invalid_context(
    tmp_path, monkeypatch, capsys, returncode, stdout, stderr,
):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    from hermeneutic import install_hook

    wrapper = Path(install_hook.install_compile()["wrapper_path"])
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], returncode, stdout=stdout, stderr=stderr,
        ),
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"prompt": "ship it"})))

    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(wrapper), run_name="__main__")

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize(
    "payload",
    ["not json", "[]", "{}", '{"prompt": 7}', '{"prompt": "   "}'],
)
def test_compile_hook_ignores_malformed_or_empty_input(tmp_path, monkeypatch, capsys, payload):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    from hermeneutic import install_hook

    wrapper = Path(install_hook.install_compile()["wrapper_path"])

    def unexpected_run(*args, **kwargs):
        raise AssertionError("compiler must not run for malformed or empty input")

    monkeypatch.setattr(subprocess, "run", unexpected_run)
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(wrapper), run_name="__main__")

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize("error", [subprocess.TimeoutExpired("compile", 4), OSError("boom")])
def test_compile_hook_ignores_subprocess_errors(tmp_path, monkeypatch, capsys, error):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    from hermeneutic import install_hook

    wrapper = Path(install_hook.install_compile()["wrapper_path"])

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(subprocess, "run", fail)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"prompt": "ship it"})))
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(wrapper), run_name="__main__")

    assert exc.value.code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_install_compile_hook_preserves_other_userpromptsubmit(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    settings = tmp_path / ".claude" / "settings.json"
    settings.write_text(json.dumps({
        "hooks": {"UserPromptSubmit": [
            {"hooks": [{"type": "command", "command": "bash /other.sh"}]}
        ]}
    }))
    from hermeneutic import install_hook
    install_hook.install_compile()
    install_hook.uninstall_compile()
    cfg = json.loads(settings.read_text())
    cmds = [h["command"] for entry in cfg["hooks"]["UserPromptSubmit"] for h in entry["hooks"]]
    assert "bash /other.sh" in cmds
    assert not any("hermeneutic-compile.py" in c for c in cmds)


def test_uninstall_compile_when_nothing_installed(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    from hermeneutic import install_hook
    res = install_hook.uninstall_compile()
    assert res["wrapper_state"] == "absent"
    assert res["settings_state"] == "absent"


def test_install_compile_hook_refuses_foreign_wrapper(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    wrapper = hooks / "hermeneutic-compile.py"
    wrapper.write_text("# user-owned hook\n")
    from hermeneutic import install_hook

    with pytest.raises(install_hook.InstallError, match="Refusing to overwrite"):
        install_hook.install_compile()


def test_install_compile_hook_rejects_malformed_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text("{not json")
    from hermeneutic import install_hook

    with pytest.raises(install_hook.InstallError, match="malformed JSON"):
        install_hook.install_compile()
    assert not (claude / "hooks" / "hermeneutic-compile.py").exists()


@pytest.mark.parametrize("settings", [[], {"hooks": []}, {"hooks": {"UserPromptSubmit": {}}}])
def test_install_compile_hook_rejects_invalid_settings_shape(tmp_path, monkeypatch, settings):
    monkeypatch.setenv("HOME", str(tmp_path))
    claude = tmp_path / ".claude"
    claude.mkdir()
    (claude / "settings.json").write_text(json.dumps(settings))
    from hermeneutic import install_hook

    with pytest.raises(install_hook.InstallError, match="invalid hook structure"):
        install_hook.install_compile()
    assert not (claude / "hooks" / "hermeneutic-compile.py").exists()


def test_uninstall_compile_preserves_foreign_wrapper(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    wrapper = hooks / "hermeneutic-compile.py"
    wrapper.write_text("# user-owned hook\n")
    from hermeneutic import install_hook

    result = install_hook.uninstall_compile()
    assert result["wrapper_state"] == "preserved-foreign"
    assert wrapper.read_text() == "# user-owned hook\n"


def test_compile_hook_exec_form_handles_home_path_with_spaces(tmp_path, monkeypatch):
    home = tmp_path / "home with spaces"
    monkeypatch.setenv("HOME", str(home))
    (home / ".claude").mkdir(parents=True)
    from hermeneutic import install_hook

    result = install_hook.install_compile()
    settings = json.loads((home / ".claude" / "settings.json").read_text())
    handler = settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert handler == {
        "type": "command",
        "command": sys.executable,
        "args": [str(Path(result["wrapper_path"]).resolve())],
        "timeout": 5,
    }


def test_install_compile_hook_migrates_exact_legacy_shell_registration(tmp_path, monkeypatch):
    home = tmp_path / "home with spaces"
    monkeypatch.setenv("HOME", str(home))
    (home / ".claude").mkdir(parents=True)
    from hermeneutic import install_hook

    first = install_hook.install_compile()
    settings_path = home / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    handler = settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    handler["command"] = f"python3 {Path(first['wrapper_path']).resolve()}"
    handler.pop("args")
    settings_path.write_text(json.dumps(settings))

    migrated = install_hook.install_compile()
    settings = json.loads(settings_path.read_text())
    handlers = settings["hooks"]["UserPromptSubmit"][0]["hooks"]
    assert migrated["settings_state"] == "migrated"
    assert handlers == [{
        "type": "command",
        "command": sys.executable,
        "args": [str(Path(first["wrapper_path"]).resolve())],
        "timeout": 5,
    }]


def test_uninstall_compile_cleans_exact_legacy_shell_registration(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    from hermeneutic import install_hook

    result = install_hook.install_compile()
    settings_path = tmp_path / ".claude" / "settings.json"
    settings = json.loads(settings_path.read_text())
    handler = settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    handler["command"] = f"python3 {Path(result['wrapper_path']).resolve()}"
    handler.pop("args")
    settings_path.write_text(json.dumps(settings))

    removed = install_hook.uninstall_compile()
    assert removed == {"wrapper_state": "removed", "settings_state": "removed"}


def test_uninstall_compile_preserves_unrelated_similar_command(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    claude = tmp_path / ".claude"
    claude.mkdir()
    settings_path = claude / "settings.json"
    settings_path.write_text(json.dumps({
        "hooks": {"UserPromptSubmit": [{
            "hooks": [{"type": "command", "command": "bash /other/hermeneutic-compile.py"}]
        }]}
    }))
    from hermeneutic import install_hook

    install_hook.install_compile()
    install_hook.uninstall_compile()
    settings = json.loads(settings_path.read_text())
    assert settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"] == (
        "bash /other/hermeneutic-compile.py"
    )


def test_uninstall_compile_preserves_install_when_settings_becomes_malformed(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    from hermeneutic import install_hook

    result = install_hook.install_compile()
    (tmp_path / ".claude" / "settings.json").write_text("{not json")
    removed = install_hook.uninstall_compile()
    assert removed == {"wrapper_state": "preserved", "settings_state": "malformed"}
    assert Path(result["wrapper_path"]).is_file()


def test_uninstall_compile_preserves_install_when_settings_shape_is_invalid(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    from hermeneutic import install_hook

    result = install_hook.install_compile()
    (tmp_path / ".claude" / "settings.json").write_text("[]")
    removed = install_hook.uninstall_compile()
    assert removed == {"wrapper_state": "preserved", "settings_state": "malformed"}
    assert Path(result["wrapper_path"]).is_file()


def test_gate_and_compile_installers_uninstall_independently(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / ".claude").mkdir()
    from hermeneutic import install_hook

    gate = install_hook.install()
    compile_result = install_hook.install_compile()
    install_hook.uninstall_compile()
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert settings["hooks"]["Stop"]
    assert Path(gate["wrapper_path"]).is_file()
    assert not Path(compile_result["wrapper_path"]).exists()

    compile_result = install_hook.install_compile()
    install_hook.uninstall()
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert settings["hooks"]["UserPromptSubmit"]
    assert Path(compile_result["wrapper_path"]).is_file()
