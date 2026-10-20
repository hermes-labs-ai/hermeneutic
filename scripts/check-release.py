"""Check release metadata consistency without network or optional packages."""

from __future__ import annotations

import json
import re
from pathlib import Path


def verify(root: Path) -> str:
    metadata = json.loads((root / "release.json").read_text())
    version = metadata["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:a[1-9]\d*)?", version), "Supported release version required"
    assert metadata["channel"] == ("alpha" if "a" in version else "stable")
    package = (root / "pyproject.toml").read_text()
    assert re.search(rf'^version = "{re.escape(version)}"$', package, re.M)
    assert f'__version__ = "{version}"' in (root / "src/hermeneutic/__init__.py").read_text()
    assert f'version: "{version}"' in (root / "CITATION.cff").read_text()
    for name in (".zenodo.json", "gemini-extension.json", "qwen-extension.json"):
        assert json.loads((root / name).read_text())["version"] == version, name
    sbom = json.loads((root / "sbom.cdx.json").read_text())
    assert sbom["metadata"]["component"]["version"] == version
    assert f"## [{version}]" in (root / "CHANGELOG.md").read_text()
    assert f"hermeneutic=={version}" in (root / "README.md").read_text()
    assert metadata["runtime_dependencies"] == []
    assert re.search(r"^dependencies = \[\]$", package, re.M)
    assert metadata["gate"]["json_schema_version"] == 1
    assert metadata["gate"]["matched_text_default"] is False
    assert metadata["language_mapping"]["status"] == "experimental_advisory"
    assert metadata["language_mapping"]["real_language_coverage"] == "unvalidated"
    for path in (metadata["release_contract"], metadata["roadmap"],
                 metadata["language_mapping"]["evidence"], metadata["correction_memory"]["evidence"]):
        assert (root / path).is_file(), path
    return version


if __name__ == "__main__":
    print(f"Release metadata consistent: {verify(Path(__file__).resolve().parents[1])}")
