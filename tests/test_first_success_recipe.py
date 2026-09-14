"""Lock the published first-success recipe for the standalone gate.

`README.md` publishes a three-step recipe: a risky draft that must fire, a
neutral draft that must not, and a missing file that must stay a distinct
error. This module pins both halves of that promise:

* the behavioural half — the exact strings and exit codes a reader copies, so
  a rule edit that changes what the recipe prints fails here first;
* the published half — the README block itself, so the recipe, its release
  pin, and its link to the fail-loud invariant cannot quietly disappear while
  the behavioural tests stay green.

Scope, precisely: only `README.md` is read. The same risky draft also appears
in `llms.txt`, `FORWARD-DEPLOYED-HARNESS.md`, `demo.tape` and
`scripts/smoke-installed-cli.sh`; those surfaces are *not* pinned here, and the
neutral draft and missing-file case are published only in the README and the
smoke script.

The gate is also advertised as needing no credentials and no private files.
`test_gate_recipe_needs_no_credentials_or_private_files` asserts that by
running the recipe with the environment stripped and `HOME` pointed at a path
that does not exist.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from hermeneutic.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent

RISKY_DRAFT = "Done — shipped 14 files, all tests pass."
NEUTRAL_DRAFT = "Draft ready for review."
RISKY_RULE_IDS = ("completion_with_number", "completion_with_all_quantifier")

# The README publishes this exact command as the missing-file boundary. The
# behavioural test below drives the same filename, so the published recipe and
# the behaviour it promises cannot drift apart.
MISSING_DRAFT_NAME = "missing.txt"
PUBLISHED_MISSING_COMMAND = f"hermeneutic gate --draft {MISSING_DRAFT_NAME}"

# The README's second exit-2 path, quoted verbatim from `_cmd_gate`.
NON_UTF8_DIAGNOSTIC = (
    "ERROR: input is not valid UTF-8 text — the gate reads text drafts only."
)

# The installed console script is not on PATH inside a stripped environment,
# so drive the same entry point the script wraps.
_GATE_ENTRY = "from hermeneutic.cli import main; raise SystemExit(main(['gate']))"


def test_published_risky_draft_fires_both_rules(capsys, tmp_path):
    draft = tmp_path / "risky.txt"
    draft.write_text(RISKY_DRAFT, encoding="utf-8")

    rc = main(["gate", "--draft", str(draft)])

    out = capsys.readouterr().out
    assert rc == 1
    assert "RISK — highest severity: high" in out
    for rule_id in RISKY_RULE_IDS:
        assert rule_id in out


def test_published_neutral_draft_passes(capsys, tmp_path):
    draft = tmp_path / "neutral.txt"
    draft.write_text(NEUTRAL_DRAFT, encoding="utf-8")

    rc = main(["gate", "--draft", str(draft)])

    assert rc == 0
    assert "PASS — no risk patterns matched." in capsys.readouterr().out


def test_missing_draft_stays_a_distinct_error(capsys, tmp_path):
    rc = main(["gate", "--draft", str(tmp_path / MISSING_DRAFT_NAME)])

    assert rc == 2, "a missing draft must not collapse into the RISK exit code"
    captured = capsys.readouterr()
    assert "not found" in (captured.out + captured.err)


def test_non_utf8_draft_exits_2_with_the_published_diagnostic(capsys, tmp_path):
    """The README's other exit-2 path: input the gate cannot read as text.

    Pinned together with its diagnostic, so the published wording cannot drift
    from what the CLI actually prints, and so a non-UTF-8 draft can never be
    scored as if it were an empty one.
    """
    draft = tmp_path / "not-utf8.txt"
    # 0xFF is not a legal UTF-8 start byte, so decoding fails outright.
    draft.write_bytes(b"Done \xff shipped 14 files, all tests pass.")

    rc = main(["gate", "--draft", str(draft)])

    assert rc == 2, "unreadable input must not collapse into PASS or RISK"
    captured = capsys.readouterr()
    assert NON_UTF8_DIAGNOSTIC in captured.err
    assert "PASS" not in captured.out and "RISK" not in captured.out


def test_readme_publishes_the_non_utf8_failure_and_its_diagnostic():
    """The doc must name the real failure, not the mining-side zero-parse one."""
    # The README wraps prose, so compare against a whitespace-normalised copy.
    readme = " ".join(_readme().split())
    assert NON_UTF8_DIAGNOSTIC in readme, "the exact diagnostic must be published"
    assert "non-UTF-8 file" in readme
    assert "zero-parse" not in readme, (
        "zero-parse is the mining invariant; the gate's second exit 2 is non-UTF-8 input"
    )


def test_gate_recipe_needs_no_credentials_or_private_files(tmp_path):
    """The recipe must work with no inherited env and no readable home."""
    stripped = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path / "no-such-home"),
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }

    risky = subprocess.run(
        [sys.executable, "-c", _GATE_ENTRY],
        input=RISKY_DRAFT + "\n",
        capture_output=True,
        text=True,
        env=stripped,
        cwd=os.fspath(tmp_path),
        check=False,
    )
    assert risky.returncode == 1
    for rule_id in RISKY_RULE_IDS:
        assert rule_id in risky.stdout

    neutral = subprocess.run(
        [sys.executable, "-c", _GATE_ENTRY],
        input=NEUTRAL_DRAFT + "\n",
        capture_output=True,
        text=True,
        env=stripped,
        cwd=os.fspath(tmp_path),
        check=False,
    )
    assert neutral.returncode == 0
    assert "PASS — no risk patterns matched." in neutral.stdout


# --- the published README block -------------------------------------------

README = REPO_ROOT / "README.md"
GUIDE = "FORWARD-DEPLOYED-HARNESS.md"
GUIDE_ANCHOR = "invariants--never-break-these-whatever-you-change"


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def test_readme_publishes_the_recipe_this_module_pins():
    """The behavioural tests are only meaningful if the README still says this."""
    readme = _readme()
    assert RISKY_DRAFT in readme
    assert NEUTRAL_DRAFT in readme
    for rule_id in RISKY_RULE_IDS:
        assert rule_id in readme
    assert "PASS — no risk patterns matched." in readme


def test_readme_binds_the_missing_file_command_to_its_exit_code():
    """The published command and its exit-2 meaning must travel together.

    Asserting the bare substring "exits `2`" is not enough: the README states
    exit `2` in three places (this recipe, the fail-loud invariant sentence,
    and the exit-code list), so deleting the recipe line leaves the other two
    and a substring check still passes. Requiring the exact command adjacent
    to its exit code fails the moment the recipe itself is removed or its
    interpretation is separated from it.
    """
    import re

    readme = _readme()
    assert PUBLISHED_MISSING_COMMAND in readme, (
        f"the published missing-file recipe `{PUBLISHED_MISSING_COMMAND}` is gone"
    )

    bound = re.compile(
        re.escape(f"`{PUBLISHED_MISSING_COMMAND}`") + r"[^.\n]{0,40}exits `2`"
    )
    assert bound.search(readme), (
        "the missing-file command must be published together with its exit `2` "
        "interpretation, not merely somewhere in the same document"
    )


def _quick_start() -> str:
    """The Quick start section only — where a first-time reader installs."""
    readme = _readme()
    start = readme.index("## Quick start")
    return readme[start : readme.index("\n## ", start + len("## Quick start"))]


def test_readme_pins_the_packaged_release():
    """A floating install stops being release-matched the moment 0.1.12 ages out.

    Scoped to the Quick start block: that is the install a first-time reader
    runs, and a pin elsewhere in the README must not satisfy this on its behalf.
    """
    import re

    from hermeneutic import __version__

    quick_start = _quick_start()
    installs = re.findall(r"^.*pip install hermeneutic.*$", quick_start, re.MULTILINE)
    assert installs, "Quick start must publish an install command"
    # Every install line, not merely one of them: an unpinned line next to a
    # pinned one is still an unpinned recipe for whoever copies that line.
    for line in installs:
        assert f"hermeneutic=={__version__}" in line, f"unpinned install: {line.strip()}"
    assert f"hermeneutic {__version__}" in quick_start


def test_readme_links_the_fail_loud_guide_and_the_anchor_resolves():
    """`|| true` guidance must point at the invariant, not just assert it."""
    import re

    readme = _readme()
    assert f"]({GUIDE}#{GUIDE_ANCHOR})" in readme, "no Markdown link to the guide"

    guide = REPO_ROOT / GUIDE
    slugs = {
        re.sub(r"[^\w\s-]", "", line.lstrip("#").strip().lower()).replace(" ", "-")
        for line in guide.read_text(encoding="utf-8").splitlines()
        if line.startswith("#")
    }
    assert GUIDE_ANCHOR in slugs, f"anchor does not resolve in {GUIDE}"


# --- outbound-network deny guard ------------------------------------------

# Prepended to the CHILD script, so the denial is installed in the gate's own
# process before hermeneutic is imported rather than asserted from the parent.
# A `sitecustomize.py` would shadow the interpreter's own, which on some builds
# is what puts site-packages on the path.
_DENY_OUTBOUND = """\
import socket


class OutboundNetworkDenied(RuntimeError):
    pass


def _deny(*args, **kwargs):
    raise OutboundNetworkDenied("outbound network access attempted")


socket.socket = _deny
socket.create_connection = _deny
socket.getaddrinfo = _deny
"""


def test_default_gate_runs_with_outbound_network_denied(tmp_path):
    """The advertised offline claim, enforced inside the gate's own process.

    The prepended denial guard runs before the CLI imports anything, so any
    socket attempt raises. The published risky/neutral pair must still produce
    its exact verdicts and exit codes.
    """
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(tmp_path / "no-such-home"),
        "PYTHONPATH": str(REPO_ROOT / "src"),
    }

    def _gate(draft: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-c", _DENY_OUTBOUND + "\n" + _GATE_ENTRY],
            input=draft + "\n",
            capture_output=True,
            text=True,
            env=env,
            cwd=os.fspath(tmp_path),
            check=False,
        )

    # The guard must actually bite, or this test proves nothing.
    proof = subprocess.run(
        [sys.executable, "-c", _DENY_OUTBOUND + "\nimport socket\nsocket.socket()\n"],
        capture_output=True, text=True, env=env, cwd=os.fspath(tmp_path), check=False,
    )
    assert proof.returncode != 0
    assert "OutboundNetworkDenied" in proof.stderr

    risky = _gate(RISKY_DRAFT)
    assert risky.returncode == 1
    for rule_id in RISKY_RULE_IDS:
        assert rule_id in risky.stdout

    neutral = _gate(NEUTRAL_DRAFT)
    assert neutral.returncode == 0
    assert "PASS — no risk patterns matched." in neutral.stdout
