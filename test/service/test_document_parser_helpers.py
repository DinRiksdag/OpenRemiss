import pytest

from service.document_parser import DocumentParser


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
