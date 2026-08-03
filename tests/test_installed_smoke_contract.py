from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SMOKE_COMMAND = "bash scripts/smoke-installed-cli.sh"
SDIST_CHECK = (
    "tar -tzf dist/hermeneutic-*.tar.gz | "
    "grep -Fq 'scripts/smoke-installed-cli.sh'"
)


def workflow_text(relative: str) -> str:
    path = ROOT / relative
    if not path.exists():
        pytest.skip("repository workflow contract is not part of the source distribution")
    return path.read_text(encoding="utf-8")


def test_ci_and_release_run_the_installed_cli_smoke() -> None:
    for relative in (".github/workflows/ci.yml", ".github/workflows/release.yml"):
        workflow = workflow_text(relative)
        assert SMOKE_COMMAND in workflow


def test_package_workflows_inspect_the_built_source_distribution() -> None:
    for relative in (".github/workflows/ci.yml", ".github/workflows/release.yml"):
        workflow = workflow_text(relative)
        assert SDIST_CHECK in workflow
