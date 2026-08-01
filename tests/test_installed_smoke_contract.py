from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE_COMMAND = "bash scripts/smoke-installed-cli.sh"


def test_ci_and_release_run_the_installed_cli_smoke() -> None:
    for relative in (".github/workflows/ci.yml", ".github/workflows/release.yml"):
        workflow = (ROOT / relative).read_text(encoding="utf-8")
        assert SMOKE_COMMAND in workflow


def test_source_distribution_includes_the_smoke_script() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"scripts/"' in pyproject
