"""Review-derived policy contracts, deliberately exposed development cases."""

import json
from pathlib import Path

import pytest

from hermeneutic import check_draft

CASES = json.loads(
    (Path(__file__).parents[1] / "evals/product-baseline/cases.json").read_text()
)["cases"]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_review_derived_policy(case):
    report = check_draft(case["draft"], lang=case["lang"]).to_dict()
    assert case["provenance"]
    assert report["verdict"] == case["verdict"]
    assert report["should_block"] is case["should_block"]
    assert sorted({hit["origin"] for hit in report["findings"]}) == case["origins"]
    for hit in report["findings"]:
        assert "matched_text" not in hit
        assert hit["blocking"] == (hit["origin"] == "raw_english" and hit["severity"] in ("med", "high"))
        assert 0 <= hit["start"] < hit["end"] <= len(case["draft"])
    assert "PRIVATE_SENTINEL_4fe7" not in json.dumps(report)
