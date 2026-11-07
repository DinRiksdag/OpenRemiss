import pytest
import pandas as pd

from service.document_parser import DocumentParser
from service.tabula_parser import TabulaParser


def test_extracts_names_from_tabula_dataframes(monkeypatch):
    first_page = pd.DataFrame(
        {
            "numbers": [None, 1, None],
            "names": ["Remissinstanser", "Göteborgs universitet", None],
        }
    )
    next_page = pd.DataFrame({"names": ["2. Barnombudsmannen"], "empty": [None]})
    monkeypatch.setattr(TabulaParser, "extract_first_page", lambda path: [first_page])
    monkeypatch.setattr(TabulaParser, "extract_next_pages", lambda path: [next_page])
    monkeypatch.setattr(DocumentParser, "has_scanned_pages", lambda path, pages: False)

    assert DocumentParser.extract_list("example.pdf") == [
        "Göteborgs universitet",
        "Barnombudsmannen",
    ]


@pytest.mark.parametrize("heading", ["Remissinstanser", "Sändlista"])
def test_detect_list_boundaries(heading):
    rows = ["Department", heading, "Stockholms universitet", "Remissvar skickas till"]
    start = DocumentParser.detect_start(rows)
    assert start == 2
    assert DocumentParser.detect_end(rows[start:]) == 1


def test_remove_page_furniture():
    rows = ["1 (2)", "Stockholms universitet", "Telefonväxel: 08-405 10 00"]
    rows = DocumentParser.remove_page_numbers(rows)
    assert DocumentParser.remove_footer_lines(rows) == ["Stockholms universitet"]


@pytest.mark.parametrize("prefix", ["1. ", "12 ", "l. "])
def test_remove_organisation_numbering(prefix):
    rows = DocumentParser.remove_leading_numbers([f"{prefix}Stockholms universitet"])
    assert DocumentParser.remove_leading_spaces(rows) == ["Stockholms universitet"]


def test_merge_wrapped_organisation_name():
    rows = ["Universitetet (Juridiska", "fakulteten)", "Barnombudsmannen"]
    assert DocumentParser.merge_multiline(rows) == [
        "Universitetet (Juridiska fakulteten)",
        "Barnombudsmannen",
    ]
