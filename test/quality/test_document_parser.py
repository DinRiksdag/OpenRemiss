from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

import pytest

from service.document_parser import DocumentParser
from service.downloader import Downloader

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads(Path(__file__).with_name("cases.json").read_text(encoding="utf-8"))
pytestmark = pytest.mark.quality


def normalise_typography(name):
    return " ".join(name.translate(str.maketrans({"–": "-", "—": "-"})).split())


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_document_extraction(case, record_testsuite_property):
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
    if "expected_count" in case:
        assert len(actual or []) == case["expected_count"]
    if "expected_names" in case:
        if case["expected_names"] is None:
            assert actual is None
        else:
            assert actual is not None
            # Keep name spelling and order exact, ignoring only layout typography.
            assert [normalise_typography(name) for name in actual] == [
                normalise_typography(name) for name in case["expected_names"]
            ]
