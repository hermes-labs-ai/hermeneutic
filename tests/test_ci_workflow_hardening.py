import re
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"


def _checkout_steps(workflow: str) -> list[str]:
    lines = workflow.splitlines()
    steps: list[str] = []
    for index, line in enumerate(lines):
        match = re.match(r"^(?P<indent>\s*)-\s+uses:\s*actions/checkout@", line)
        if match is None:
            continue

        indent = re.escape(match.group("indent"))
        body: list[str] = []
        for following in lines[index + 1 :]:
            if re.match(rf"^{indent}-\s", following):
                break
            body.append(following)
        steps.append("\n".join(body))
    return steps


def test_ci_workflow_uses_immutable_actions_and_restricted_checkout() -> None:
    if not WORKFLOW.exists():
        pytest.skip("repository workflow contract is not part of the source distribution")

    workflow = WORKFLOW.read_text(encoding="utf-8")

    action_refs = re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", workflow, re.MULTILINE)
    assert action_refs, "CI workflow must retain its action steps"
    assert all(
        re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", ref) for ref in action_refs
    ), "every CI action must use an immutable 40-character commit SHA"

    assert re.search(r"^permissions:\n  contents: read\s*$", workflow, re.MULTILINE)

    checkout_blocks = _checkout_steps(workflow)
    assert checkout_blocks, "CI workflow must retain a checkout step"
    assert all(
        re.search(r"^\s+persist-credentials:\s*false\s*$", block, re.MULTILINE)
        for block in checkout_blocks
    ), "checkout must not persist repository credentials"


def test_each_checkout_step_is_checked_independently() -> None:
    workflow = """steps:
  - uses: actions/checkout@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    with:
      persist-credentials: true
  - uses: actions/checkout@bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    with:
      persist-credentials: false
"""

    checkout_blocks = _checkout_steps(workflow)

    assert len(checkout_blocks) == 2
    assert not all(
        re.search(r"^\s+persist-credentials:\s*false\s*$", block, re.MULTILINE)
        for block in checkout_blocks
    )
