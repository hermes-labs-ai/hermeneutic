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

from hermeneutic.gates.regex import highest_severity, risk_score
from hermeneutic.triples import READERS, mine_dir


def _cmd_mine(args: argparse.Namespace) -> int:
    out = sys.stdout if args.out == "-" else open(args.out, "w", encoding="utf-8")
    n = 0
    try:
        for trip in mine_dir(args.directory, fmt=args.format, glob=args.glob):
            out.write(trip.to_json() + "\n")
            n += 1
    finally:
        if out is not sys.stdout:
            out.close()
    print(f"mined {n} triples", file=sys.stderr)
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
    draft = Path(args.draft).read_text(encoding="utf-8") if args.draft else sys.stdin.read()
    hits = risk_score(draft)
    sev = highest_severity(hits)
    if not hits:
        print("PASS — no risk patterns matched.")
        return 0
    print(f"RISK — highest severity: {sev}")
    for h in hits:
        print(f"  {h}")
        print(f"    why: {h.description}")
    return 1 if sev in ("high", "med") else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="hermeneutic", description="Mine corrections, gate the next response.")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_mine = sub.add_parser("mine", help="Mine triples from session logs.")
    p_mine.add_argument("directory", help="Directory containing session logs.")
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

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
