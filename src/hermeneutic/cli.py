"""hermeneutic CLI.

Subcommands:
  mine    Walk a directory of session logs and emit triples.jsonl
  bucket  Bucket a triples.jsonl into surface-pattern categories
  gate    Run the regex-only gate on a draft (read from stdin or --draft)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from hermeneutic import __version__
from hermeneutic.gates.regex import highest_severity, risk_score
from hermeneutic.triples import READERS, mine_dir


def _open_out(path: str, mode: str = "w"):
    """Open an --out target, creating missing parent directories."""
    if path == "-":
        return sys.stdout
    parent = Path(path).parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    return open(path, mode, encoding="utf-8")


def _cmd_mine(args: argparse.Namespace) -> int:
    # Fail loud before mining: a typo'd directory must not be silently
    # skipped just because another directory yielded triples.
    missing = [d for d in args.directory if not Path(d).is_dir()]
    if missing:
        print(
            "ERROR: not a directory: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2
    out = _open_out(args.out)
    n = 0
    mined_by_directory: list[tuple[str, int]] = []
    try:
        for directory in args.directory:
            directory_n = 0
            for trip in mine_dir(directory, fmt=args.format, glob=args.glob):
                out.write(trip.to_json() + "\n")
                n += 1
                directory_n += 1
            mined_by_directory.append((directory, directory_n))
    finally:
        if out is not sys.stdout:
            out.close()
    print(f"mined {n} triples", file=sys.stderr)
    # Diagnose every zero-result argument independently. A valid directory
    # must not hide a second directory whose files matched but could not parse.
    for directory, directory_n in mined_by_directory:
        if directory_n == 0:
            rc = _report_zero_parse(directory, args.glob, args.format)
            if rc != 0:
                return rc
    return 0


def _report_zero_parse(directory: str, glob: str, fmt: str) -> int:
    """Loud failure for the worst silent mode: 0 events parsed.

    A user pointing the miner at an unsupported log format gets zero output
    that is indistinguishable from "no corrections found" — they conclude
    the tool is broken and never file a bug. Distinguish the cases loudly:
    exit 2 when nothing could be parsed (path/format problem), exit 0 when
    logs parsed fine and there was genuinely nothing to find.
    """
    files = sorted(Path(directory).glob(glob))
    print("", file=sys.stderr)
    if not files:
        print(
            f"ZERO EVENTS: no files matched {glob!r} in {directory}.\n"
            f"Check the path, or pass --glob (e.g. --glob '*.json').",
            file=sys.stderr,
        )
        return 2
    # Distinguish "unsupported format" from "parsed fine, nothing found":
    # probe up to 5 files and count turns the reader actually yields.
    reader = READERS[fmt]
    turns = sum(1 for fp in files[:5] for _ in reader.iter_turns(fp))
    if turns == 0:
        print(
            f"ZERO EVENTS from {len(files)} file(s) — the {fmt!r} reader "
            f"could not parse any turns.\nYour logs are probably a different "
            f"format. Supported: {list(READERS)}.\nPlease open an issue with "
            f"ONE sample session file (redact freely) and we'll add a reader:\n"
            f"  https://github.com/hermes-labs-ai/hermeneutic/issues",
            file=sys.stderr,
        )
        return 2
    print(
        f"Parsed OK ({turns} turns in the first {min(5, len(files))} "
        f"file(s)) — genuinely no correction events matched. Normal for "
        f"small or clean logs; try a larger directory.",
        file=sys.stderr,
    )
    return 0


def _cmd_bucket(args: argparse.Namespace) -> int:
    import re
    from collections import Counter

    BUCKETS = [
        ("scope_creep",        r"\b(too much|over[- ]?engineer|scope|just (do|the)|simpler|simplify|less|smaller|stop adding|don'?t (add|build|refactor))"),
        ("wrong_target",       r"\b(not (that|this|the right)|wrong (file|repo|project|one)|i meant|different)"),
        ("missed_constraint",  r"\b(i (said|told you)|already|forgot|missed|you didn'?t|re-?read|memory|claude\.md|handbook)"),
        ("tone_format",        r"\b(too long|too verbose|tl;?dr|shorter|terse|stop (explaining|summari)|preamble|just (give|tell|show))"),
        ("over_confirmation",  r"\b(just do|stop asking|execute|go|ship|run it|why are you asking)"),
        ("over_completion",    r"\b(wait,? (are you|really)|are you sure|did you actually|prove it|where'?s the (evidence|proof))"),
        ("misread_intent",     r"\b(misunderstood|missed (the|my)|that'?s not what|missing the point|you'?re off|wrong direction)"),
        ("fabrication",        r"\b(made up|fabricat|hallucinat|where did you get|that'?s not real|doesn'?t exist|made that up)"),
        ("tool_choice",        r"\b(use (the|a)|wrong tool|why (didn'?t|aren'?t) you|should have used)"),
    ]
    rxs = [(name, re.compile(rx, re.I)) for name, rx in BUCKETS]
    counts = Counter()
    unbucketed = 0
    n = 0
    with open(args.triples) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            n += 1
            d = json.loads(line)
            text = d.get("user_correction", "")
            placed = False
            for name, rx in rxs:
                if rx.search(text):
                    counts[name] += 1
                    placed = True
                    break
            if not placed:
                unbucketed += 1

    print(f"total: {n}")
    for name, _ in BUCKETS:
        print(f"  {name:20s} {counts[name]:5d}")
    print(f"  {'(unbucketed)':20s} {unbucketed:5d}")
    return 0


def _cmd_gate(args: argparse.Namespace) -> int:
    from hermeneutic import telemetry
    try:
        draft = Path(args.draft).read_text(encoding="utf-8") if args.draft else sys.stdin.read()
    except FileNotFoundError:
        print(f"ERROR: draft file not found: {args.draft}", file=sys.stderr)
        return 2
    except UnicodeDecodeError:
        print(
            "ERROR: input is not valid UTF-8 text — the gate reads text drafts only.",
            file=sys.stderr,
        )
        return 2
    hits = risk_score(draft)
    sev = highest_severity(hits)
    telemetry.record_gate(
        verdict="RISK" if hits else "PASS",
        severity=sev,
        rule_ids=[h.rule_id for h in hits],
        draft=draft,
        hits=hits,
    )
    if not hits:
        print("PASS — no risk patterns matched.")
        return 0
    print(f"RISK — highest severity: {sev}")
    for h in hits:
        print(f"  {h}")
        print(f"    why: {h.description}")
    return 1 if sev in ("high", "med") else 0


def _cmd_compile_index(args: argparse.Namespace) -> int:
    from hermeneutic import compile as hcompile
    triples_path = Path(args.triples) if args.triples else (hcompile.home_dir() / "triples.jsonl")
    if not triples_path.is_file():
        print(f"ERROR: triples file not found at {triples_path}", file=sys.stderr)
        print("Run `hermeneutic mine <log-dir> --out ~/.hermeneutic/triples.jsonl` first.", file=sys.stderr)
        return 1
    try:
        res = hcompile.compile_index(triples_path, home=hcompile.home_dir())
    except hcompile.MalformedTriplesError as e:
        print(f"ERROR: malformed triples file {triples_path}: {e}", file=sys.stderr)
        print("Fix the reported JSONL row or re-run `hermeneutic mine` to rebuild the corpus.", file=sys.stderr)
        return 2
    except hcompile.OllamaUnavailable as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("Start Ollama and ensure `nomic-embed-text` is pulled, then re-run.", file=sys.stderr)
        return 1
    print(f"state: {res.state}")
    print(f"triples: {res.n_triples} ({res.n_eligible} eligible, {res.n_v01_legacy} v0.1 legacy)")
    if res.n_v01_legacy > 0:
        print(f"NOTE: {res.n_v01_legacy} v0.1 triples lack `orig_prompt` — re-mine to enable them.")
    if res.state == "built":
        print(f"index: dim={res.dim} model={res.model}")
    return 0


def _cmd_compile(args: argparse.Namespace) -> int:
    import re
    import time

    from hermeneutic import compile as hcompile
    prompt = sys.stdin.read() if not args.prompt else args.prompt
    triples_path = Path(args.triples) if args.triples else (hcompile.home_dir() / "triples.jsonl")
    verbose = getattr(args, "verbose", False)
    if not triples_path.is_file():
        if verbose:
            print(f"[hermeneutic] no triples corpus at {triples_path}", file=sys.stderr)
        return 0  # silent — no corpus, no preamble
    if verbose:
        idx = hcompile.load_index(hcompile.home_dir())
        if idx is None:
            print("[hermeneutic] no embedding index — run `hermeneutic compile-index` first", file=sys.stderr)
            return 0
        print(
            f"[hermeneutic] index: dim={idx.dim} model={idx.model} "
            f"vectors={len(idx.vectors)}", file=sys.stderr,
        )
        # Probe ollama — surfaces the most common silent-failure mode.
        try:
            t0 = time.time()
            hcompile.ollama_embed("probe", model=idx.model, timeout=3.0)
            print(
                f"[hermeneutic] ollama probe: ok ({time.time() - t0:.2f}s)",
                file=sys.stderr,
            )
        except hcompile.OllamaUnavailable as e:
            print(f"[hermeneutic] ollama probe: FAIL — {e}", file=sys.stderr)
            return 0
        t0 = time.time()
    out = hcompile.compile_prompt(
        prompt, triples_path, home=hcompile.home_dir(),
        k=args.k, threshold=args.threshold,
    )
    if verbose:
        print(
            f"[hermeneutic] compile took {time.time() - t0:.2f}s, "
            f"preamble bytes={len(out)}",
            file=sys.stderr,
        )
    from hermeneutic import telemetry
    if telemetry.enabled():
        buckets = re.findall(r"in bucket `([^`]+)`", out) if out else []
        m = re.match(r"\[hermeneutic compile-preamble — derived from (\d+)", out or "")
        telemetry.record_compile(
            injected=bool(out),
            buckets=buckets,
            n_matches=int(m.group(1)) if m else 0,
            prompt=prompt,
        )
    if out:
        print(out)
    return 0


def _cmd_harvest(args: argparse.Namespace) -> int:
    from collections import Counter

    from hermeneutic import harvest, telemetry

    telemetry_path = args.telemetry or telemetry.sink_path()
    counts: Counter = Counter()
    live_fires = 0
    out = _open_out(args.out)
    try:
        sanitized = getattr(args, "sanitized", False)
        for rec in harvest.harvest_dir(
            args.directory, fmt=args.format, glob=args.glob,
            telemetry_path=telemetry_path,
        ):
            out.write((rec.to_sanitized_json() if sanitized else rec.to_json()) + "\n")
            counts[rec.kind] += 1
            live_fires += rec.live_fire
    finally:
        if out is not sys.stdout:
            out.close()

    total = sum(counts.values())
    print(f"harvested {total} review candidates", file=sys.stderr)
    for kind in ("confirmed_catch", "possible_false_positive", "missed_drift"):
        print(f"  {kind:26s} {counts[kind]:6d}", file=sys.stderr)
    if telemetry_path:
        print(f"  cross-referenced live fires {live_fires:6d}", file=sys.stderr)
    if total == 0:
        return _report_zero_parse(args.directory, args.glob, args.format)
    if total:
        print(
            "\nReview: flip \"status\" to accepted/rejected in the queue, then\n"
            "run `hermeneutic promote <queue>` to feed accepted records into\n"
            "your triples corpus.",
            file=sys.stderr,
        )
    return 0


def _cmd_promote(args: argparse.Namespace) -> int:
    from hermeneutic import harvest

    out = _open_out(args.out, "a")
    n = 0
    try:
        for trip in harvest.promote(args.queue):
            out.write(trip.to_json() + "\n")
            n += 1
    finally:
        if out is not sys.stdout:
            out.close()
    dest = "stdout" if args.out == "-" else args.out
    print(f"promoted {n} accepted records to {dest}", file=sys.stderr)
    if n and args.out != "-":
        print("Re-run `hermeneutic compile-index` to pick them up.", file=sys.stderr)
    return 0


def _cmd_stats(args: argparse.Namespace) -> int:
    import os
    from collections import Counter

    from hermeneutic import telemetry

    sink = Path(args.sink) if args.sink else telemetry.sink_path()
    if sink is None:
        print(
            f"ERROR: no telemetry sink — pass --sink or set {telemetry.ENV_SINK}.",
            file=sys.stderr,
        )
        return 1
    if not sink.is_file():
        print(f"ERROR: telemetry file not found at {sink}", file=sys.stderr)
        return 1

    gate_verdicts: Counter = Counter()
    gate_severity: Counter = Counter()
    gate_rules: Counter = Counter()
    gate_context: Counter = Counter()
    compile_total = 0
    compile_injected = 0
    compile_buckets: Counter = Counter()
    audited = 0
    malformed = 0
    first_ts = last_ts = None

    with open(sink, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            ts = rec.get("ts")
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
            event = rec.get("event")
            if event == "gate":
                gate_verdicts[rec.get("verdict", "?")] += 1
                if rec.get("severity"):
                    gate_severity[rec["severity"]] += 1
                for rid in rec.get("rule_ids", []):
                    gate_rules[rid] += 1
                gate_context[rec.get("context", "unknown")] += 1
                if rec.get("audit"):
                    audited += 1
            elif event == "compile":
                compile_total += 1
                if rec.get("injected"):
                    compile_injected += 1
                for b in rec.get("buckets", []):
                    compile_buckets[b] += 1

    n_gate = sum(gate_verdicts.values())
    stats = {
        "sink": str(sink),
        "first_ts": first_ts,
        "last_ts": last_ts,
        "malformed_lines": malformed,
        "gate": {
            "total": n_gate,
            "verdicts": dict(gate_verdicts),
            "risk_rate": round(gate_verdicts["RISK"] / n_gate, 4) if n_gate else None,
            "severity": dict(gate_severity),
            "rules": dict(gate_rules.most_common()),
            "context": dict(gate_context),
            "with_audit_context": audited,
        },
        "compile": {
            "total": compile_total,
            "injected": compile_injected,
            "injection_rate": round(compile_injected / compile_total, 4) if compile_total else None,
            "buckets": dict(compile_buckets.most_common()),
        },
    }

    if args.json:
        print(json.dumps(stats, indent=2))
        return 0

    print(f"telemetry: {sink}")
    if first_ts:
        print(f"span:      {first_ts} → {last_ts}")
    if malformed:
        print(f"malformed: {malformed} lines skipped")
    print()
    print(f"gate fires: {n_gate}")
    if n_gate:
        for v, c in gate_verdicts.most_common():
            print(f"  {v:8s} {c:6d}  ({c / n_gate:.1%})")
        if gate_severity:
            print("  severity (RISK fires):")
            for s in ("high", "med", "low"):
                if gate_severity[s]:
                    print(f"    {s:6s} {gate_severity[s]:6d}")
        if gate_rules:
            print("  rules:")
            for rid, c in gate_rules.most_common():
                print(f"    {rid:32s} {c:6d}")
        print("  context:")
        for ctx, c in gate_context.most_common():
            print(f"    {ctx:8s} {c:6d}")
        print(f"  with audit context: {audited}")
    print()
    print(f"compile fires: {compile_total}")
    if compile_total:
        print(f"  injected {compile_injected}  ({compile_injected / compile_total:.1%})")
        for b, c in compile_buckets.most_common():
            print(f"    {b:24s} {c:6d}")
    if n_gate == 0 and compile_total == 0:
        mode = os.environ.get(telemetry.ENV_CONTEXT, "none")
        print(f"\nNo events yet. Sink is wired (context mode: {mode}); fires will appear here.")
    return 0


def _cmd_install_compile_hook(args: argparse.Namespace) -> int:
    from hermeneutic import install_hook
    try:
        result = install_hook.install_compile()
    except install_hook.InstallError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"wrapper: {result['wrapper_state']} at {result['wrapper_path']}")
    print(f"settings.json: {result['settings_state']}")
    if result["settings_state"] in {"added", "migrated"}:
        print("\nDone. Restart Claude Code for the compile hook to take effect.")
    elif result["settings_state"] == "already-present":
        print("\nAlready installed — wrapper refreshed, settings.json untouched.")
    return 0


def _cmd_uninstall_compile_hook(args: argparse.Namespace) -> int:
    from hermeneutic import install_hook
    result = install_hook.uninstall_compile()
    print(f"wrapper: {result['wrapper_state']}")
    print(f"settings.json: {result['settings_state']}")
    return 0


def _cmd_install_hook(args: argparse.Namespace) -> int:
    from hermeneutic import install_hook
    try:
        result = install_hook.install()
    except install_hook.InstallError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"wrapper: {result['wrapper_state']} at {result['wrapper_path']}")
    print(f"settings.json: {result['settings_state']}")
    if result["settings_state"] == "added":
        print("\nDone. Restart Claude Code for the hook to take effect.")
    elif result["settings_state"] == "already-present":
        print("\nAlready installed — wrapper refreshed, settings.json untouched.")
    return 0


def _cmd_uninstall_hook(args: argparse.Namespace) -> int:
    from hermeneutic import install_hook
    result = install_hook.uninstall()
    print(f"wrapper: {result['wrapper_state']}")
    print(f"settings.json: {result['settings_state']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hermeneutic", description="Mine corrections, gate the next response.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_mine = sub.add_parser("mine", help="Mine triples from session logs.")
    p_mine.add_argument(
        "directory",
        nargs="+",
        help="One or more directories containing session logs (globs expand fine).",
    )
    p_mine.add_argument("--format", choices=list(READERS), default="claude-code")
    p_mine.add_argument("--glob", default="*.jsonl")
    p_mine.add_argument("--out", default="-", help="Output path (default stdout).")
    p_mine.set_defaults(func=_cmd_mine)

    p_bucket = sub.add_parser("bucket", help="Bucket a triples.jsonl by surface pattern.")
    p_bucket.add_argument("triples", help="Path to triples.jsonl.")
    p_bucket.set_defaults(func=_cmd_bucket)

    p_gate = sub.add_parser("gate", help="Run the regex-only risk gate on a draft.")
    p_gate.add_argument("--draft", help="Path to draft file (default: read stdin).")
    p_gate.set_defaults(func=_cmd_gate)

    p_harvest = sub.add_parser(
        "harvest",
        help="Replay the gate over session logs into a labeled review queue (reject-mining).",
    )
    p_harvest.add_argument("directory", help="Directory containing session logs.")
    p_harvest.add_argument("--format", choices=list(READERS), default="claude-code")
    p_harvest.add_argument("--glob", default="*.jsonl")
    p_harvest.add_argument("--out", default="-", help="Queue output path (default stdout).")
    p_harvest.add_argument(
        "--telemetry",
        help="Telemetry sink to cross-reference live fires (default: $HERMENEUTIC_TELEMETRY).",
    )
    p_harvest.add_argument(
        "--sanitized", action="store_true",
        help="Strip ALL text from the queue: kinds, rule ids, severities, "
             "timestamps, fingerprints and lengths only. This is data "
             "minimization, not anonymization; review before sharing. "
             "review/promote need the un-sanitized queue.",
    )
    p_harvest.set_defaults(func=_cmd_harvest)

    p_promote = sub.add_parser(
        "promote",
        help="Append accepted review-queue records to a triples corpus.",
    )
    p_promote.add_argument("queue", help="Path to a reviewed queue.jsonl.")
    p_promote.add_argument("--out", default="-", help="Triples corpus to append to (default stdout).")
    p_promote.set_defaults(func=_cmd_promote)

    p_stats = sub.add_parser("stats", help="Summarize the telemetry sink (fires, rules, contexts).")
    p_stats.add_argument("--sink", help="Path to telemetry JSONL (default: $HERMENEUTIC_TELEMETRY).")
    p_stats.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    p_stats.set_defaults(func=_cmd_stats)

    p_install = sub.add_parser(
        "install-hook",
        help="Install a Claude Code Stop hook that gates assistant outputs (advisory mode).",
    )
    p_install.set_defaults(func=_cmd_install_hook)

    p_uninstall = sub.add_parser(
        "uninstall-hook",
        help="Remove the Claude Code Stop hook installed by `install-hook`.",
    )
    p_uninstall.set_defaults(func=_cmd_uninstall_hook)

    p_idx = sub.add_parser("compile-index", help="Build/refresh the embedding index from a triples.jsonl.")
    p_idx.add_argument("--triples", help="Path to triples.jsonl (default: ~/.hermeneutic/triples.jsonl).")
    p_idx.set_defaults(func=_cmd_compile_index)

    p_compile = sub.add_parser(
        "compile",
        help="Compile a user prompt into a past-corrections preamble (Layer 2).",
    )
    p_compile.add_argument("prompt", nargs="?", help="The prompt to compile (default: read stdin).")
    p_compile.add_argument("--triples", help="Path to triples.jsonl (default: ~/.hermeneutic/triples.jsonl).")
    p_compile.add_argument("--k", type=int, default=5, help="Top-K matches to consider.")
    p_compile.add_argument("--threshold", type=float, default=0.4, help="Cosine similarity floor.")
    p_compile.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print pipeline diagnostics to stderr (index, ollama probe, latency).",
    )
    p_compile.set_defaults(func=_cmd_compile)

    p_ich = sub.add_parser(
        "install-compile-hook",
        help="Install a Claude Code UserPromptSubmit hook that injects compile preambles.",
    )
    p_ich.set_defaults(func=_cmd_install_compile_hook)

    p_uch = sub.add_parser(
        "uninstall-compile-hook",
        help="Remove the Claude Code UserPromptSubmit hook installed by `install-compile-hook`.",
    )
    p_uch.set_defaults(func=_cmd_uninstall_compile_hook)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
