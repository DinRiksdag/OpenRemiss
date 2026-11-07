from types import SimpleNamespace

import pytest
from liteparse import LiteParse

from service import document_parser
from service.document_parser import (
    DocumentParser,
    ParsedDocument,
    ParsedPage,
    TextBox,
    parse_document,
)


def document_with_rows(rows):
    return ParsedDocument(
        text="\n".join(rows),
        pages=[
            ParsedPage(
                height=842,
                items=[
                    TextBox(text=row, x=70, y=160 + 18 * i, width=200, height=12)
                    for i, row in enumerate(rows)
                ],
            )
        ],
    )


def test_long_heading_and_wrapped_names(monkeypatch):
    document = document_with_rows(
        [
            "Remisslista E-delegationens delbetänkande Så enkelt som möjligt",
            "för så många som möjligt (SOU 2014:75)",
            "1. Stockholms universitet (Juridiska",
            "fakulteten)",
            "2. Barnombudsmannen",
            "Remissvar skickas till regeringen",
        ]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "Stockholms universitet (Juridiska fakulteten)",
        "Barnombudsmannen",
    ]


def test_word_boxes_with_separated_numbering_preserve_first_entries(monkeypatch):
    document = document_with_rows(
        [
            "Remissinstanser",
            "1 . Arvika kommun",
            "2 . Barnombudsmannen",
            "3. Göteborgs universitet",
        ]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "Arvika kommun",
        "Barnombudsmannen",
        "Göteborgs universitet",
    ]


def test_later_numbering_does_not_drop_unnumbered_first_entries(monkeypatch):
    document = document_with_rows(
        [
            "Remissinstanser",
            "Arvika kommun",
            "Barnombudsmannen",
            "3. Göteborgs universitet",
        ]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "Arvika kommun",
        "Barnombudsmannen",
        "Göteborgs universitet",
    ]


def test_numbering_restart_ends_invitation_list(monkeypatch):
    document = document_with_rows(
        [
            "Remissinstanser",
            "1. Arvika kommun",
            "2. Barnombudsmannen",
            "1. Rapport som bifogas",
        ]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "Arvika kommun",
        "Barnombudsmannen",
    ]


def test_cover_letter_without_heading_is_not_an_invitation_list(monkeypatch):
    document = document_with_rows(
        ["Betänkande SOU 2014:75", "Remissvar skickas till regeringen"]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") is None


def test_footer_addresses_are_not_merged_into_names(monkeypatch):
    document = document_with_rows(["Remissinstanser", "Barnombudsmannen"])
    document.pages[0].items.extend(
        [
            TextBox(text="Postadress Telefonväxel", x=70, y=750, width=200, height=12),
            TextBox(
                text="103 33 Stockholm 08-405 10 00", x=70, y=770, width=200, height=12
            ),
        ]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == ["Barnombudsmannen"]


def test_parsed_text_and_coordinates_are_cached_without_ocr_pdf(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-test")
    calls = []
    word = SimpleNamespace(text="Göteborg", x=70, y=200, width=45, height=12)
    result = SimpleNamespace(
        text="Göteborg",
        pages=[
            SimpleNamespace(
                height=842,
                text="Göteborg",
                complexity=None,
                text_items=[SimpleNamespace(words=[word])],
            )
        ],
    )

    def parse(path):
        calls.append(path)
        return result

    monkeypatch.setattr(
        document_parser, "get_parser", lambda path: SimpleNamespace(parse=parse)
    )
    first = parse_document(source)
    assert parse_document(source) == first
    assert calls == [source]
    assert first.pages[0].items[0].text == "Göteborg"
    assert first.pages[0].items[0].x == 70
    assert parse_document(source, refresh=True) == first
    assert calls == [source, source]
    assert source.with_suffix(".liteparse.json").exists()
    assert list(tmp_path.glob("*.pdf")) == [source]
    assert not list(tmp_path.glob("*.tmp"))


def test_failed_parse_does_not_cache_an_incomplete_result(tmp_path, monkeypatch):
    source = tmp_path / "source.pdf"

    def fail(path):
        raise RuntimeError("OCR failed")

    monkeypatch.setattr(
        document_parser, "get_parser", lambda path: SimpleNamespace(parse=fail)
    )
    with pytest.raises(RuntimeError, match="OCR failed"):
        parse_document(source)
    assert not source.with_suffix(".liteparse.json").exists()


def test_ocr_targets_liteparse_classified_scans_and_preserves_native_pages(
    tmp_path, monkeypatch
):
    def page(number, text, reasons):
        item = SimpleNamespace(text=text, x=70, y=160, width=100, height=12, words=[])
        return SimpleNamespace(
            page_num=number,
            height=842,
            text=text,
            text_items=[item],
            complexity=SimpleNamespace(reasons=reasons),
        )

    native = SimpleNamespace(
        pages=[
            page(1, "Native invitation list", ["sparse-text", "embedded-images"]),
            page(2, "", ["scanned"]),
            page(3, "", ["no-text"]),
        ]
    )
    scanned = SimpleNamespace(pages=[page(2, "Göteborgs universitet", [])])
    calls = []

    def parser(tessdata_path, ocr_pages=None):
        calls.append(ocr_pages)
        return SimpleNamespace(
            parse=lambda path: native if ocr_pages is None else scanned
        )

    monkeypatch.setattr(document_parser, "get_parser", parser)
    result = parse_document(tmp_path / "mixed.pdf")
    assert calls == [None, "2"]
    assert [p.items[0].text for p in result.pages] == [
        "Native invitation list",
        "Göteborgs universitet",
        "",
    ]


def test_native_pdf_extraction_with_real_liteparse(tmp_path, monkeypatch):
    parser = LiteParse(ocr_enabled=False, emit_word_boxes=True, quiet=True)
    monkeypatch.setattr(document_parser, "get_parser", lambda path: parser)
    lines = [
        "Remisslista",
        "1. Göteborgs universitet",
        "2. Barnombudsmannen",
        "Remissvar skickas till regeringen",
    ]
    stream = (
        b"BT /F1 12 Tf 70 650 Td 18 TL\n"
        + b"\n".join(b"(" + line.encode("cp1252") + b") Tj T*" for line in lines)
        + b"\nET"
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    source = tmp_path / "invitation.pdf"
    source.write_bytes(pdf)
    assert DocumentParser.extract_list(source) == [
        "Göteborgs universitet",
        "Barnombudsmannen",
    ]
    assert not list((tmp_path / "tessdata").glob("*.traineddata"))
