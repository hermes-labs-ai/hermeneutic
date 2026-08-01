from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE_COMMAND = "bash scripts/smoke-installed-cli.sh"
SDIST_CHECK = (
    "tar -tzf dist/hermeneutic-*.tar.gz | "
    "grep -Fq 'scripts/smoke-installed-cli.sh'"
)


def test_ci_and_release_run_the_installed_cli_smoke() -> None:
    for relative in (".github/workflows/ci.yml", ".github/workflows/release.yml"):
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        assert SMOKE_COMMAND in workflow


def test_package_workflows_inspect_the_built_source_distribution() -> None:
    for relative in (".github/workflows/ci.yml", ".github/workflows/release.yml"):
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        assert SDIST_CHECK in workflow
