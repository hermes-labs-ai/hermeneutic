import re
from pathlib import Path

WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_uses_immutable_actions_and_restricted_checkout() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    action_refs = re.findall(r"^\s*-?\s*uses:\s*([^\s#]+)", workflow, re.MULTILINE)
    assert action_refs, "CI workflow must retain its action steps"
    assert all(
        re.fullmatch(r"[^@\s]+@[0-9a-f]{40}", ref) for ref in action_refs
    ), "every CI action must use an immutable 40-character commit SHA"

    assert re.search(r"^permissions:\n  contents: read\s*$", workflow, re.MULTILINE)

    checkout_blocks = re.findall(
        r"(?ms)^\s*- uses:\s*actions/checkout@[^\n]+\n(?P<block>(?:\s+.*\n)*)",
        workflow,
    )
    assert checkout_blocks, "CI workflow must retain a checkout step"
    assert all(
        re.search(r"^\s+persist-credentials:\s*false\s*$", block, re.MULTILINE)
        for block in checkout_blocks
    ), "checkout must not persist repository credentials"
