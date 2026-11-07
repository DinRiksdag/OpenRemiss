import pytest

from service import document_parser
from service.document_parser import DocumentParser, ParsedDocument, ParsedPage, TextBox


def test_extracts_names_from_liteparse_coordinates(monkeypatch):
    document = ParsedDocument(
        text="",
        pages=[
            ParsedPage(
                height=842,
                items=[
                    TextBox(text="Remissinstanser", x=70, y=160, width=100, height=12),
                    TextBox(text="1.", x=70, y=180, width=10, height=12),
                    TextBox(
                        text="Göteborgs universitet", x=90, y=180, width=150, height=12
                    ),
                ],
            ),
            ParsedPage(
                height=842,
                items=[
                    TextBox(
                        text="2. Barnombudsmannen", x=70, y=70, width=150, height=12
                    ),
                ],
            ),
        ],
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)

    assert DocumentParser.extract_list("example.pdf") == [
        "Göteborgs universitet",
        "Barnombudsmannen",
    ]


@pytest.mark.parametrize(
    "heading",
    ["Remissinstanser", "Sändlista", "Remisslista E-delegationens delbetänkande"],
)
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
