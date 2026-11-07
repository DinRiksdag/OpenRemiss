from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

import pytest

from service.cleaner import Cleaner
from service.document_parser import DocumentParser
from service.downloader import Downloader
from service.document_reviews import SOURCE_EXCEPTIONS

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
pytestmark = pytest.mark.quality


def normalise_typography(name):
    return " ".join(name.translate(str.maketrans({"–": "-", "—": "-"})).split())


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            case,
            id=case["id"],
            marks=pytest.mark.source_exception
            if case["url"] in SOURCE_EXCEPTIONS
            else [],
        )
        for case in CASES
    ],
)
def test_document_extraction(case, record_testsuite_property, request):
    source = ROOT / "tmp" / (sha256(case["url"].encode()).hexdigest() + ".pdf")
    if not source.exists():
        Downloader.get_file(case["url"], source)
    assert sha256(source.read_bytes()).hexdigest() == case["pdf_sha256"], (
        f"Source PDF changed: {case['url']}. Review the PDF before updating its checksum."
    )
    started = perf_counter()
    actual = DocumentParser.extract_list(source, refresh=True)
    record_testsuite_property(
        f"extraction_seconds[{case['id']}]", round(perf_counter() - started, 3)
    )
    for text in case.get("expected_excludes", []):
        assert not any(text in name for name in actual or [])
    issue = case.get("known_issue")
    if issue and case.get("known_issue_affects_count"):
        # Source changes and extraction exceptions must still fail normally.
        request.applymarker(
            pytest.mark.xfail(reason=issue, strict=True, raises=AssertionError)
        )
    if "expected_count" in case:
        assert len(actual or []) == case["expected_count"]
    if issue and not case.get("known_issue_affects_count"):
        request.applymarker(
            pytest.mark.xfail(reason=issue, strict=True, raises=AssertionError)
        )
    for name in case.get("expected_contains", []):
        assert actual is not None and name in actual
    for name in case.get("expected_cleaned_contains", []):
        assert actual is not None
        assert name in [
            Cleaner.deep_clean(Cleaner.light_clean(row), []) for row in actual
        ]
    if "expected_names" in case:
        if case["expected_names"] is None:
            assert actual is None
        else:
            assert actual is not None
            # Keep name spelling and order exact, ignoring only layout typography.
            assert [normalise_typography(name) for name in actual] == [
                normalise_typography(name) for name in case["expected_names"]
            ]
