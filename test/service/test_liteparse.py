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


@pytest.mark.parametrize(
    "label,expected",
    [
        ("5] . Gotlands kommun", (5, "Gotlands kommun")),
        ("92” . Söderköpings kommun", (92, "Söderköpings kommun")),
        ("9”. . Vellinge kommun", (9, "Vellinge kommun")),
        ("10 1. Region Jämtland Härjedalen", (101, "Region Jämtland Härjedalen")),
        (
            "10. 2. Kommunala samverkansorganet Region Västerbotten",
            (102, "Kommunala samverkansorganet Region Västerbotten"),
        ),
    ],
)
def test_damaged_number_label_punctuation(label, expected):
    assert DocumentParser.numbered(label) == expected


@pytest.mark.parametrize("date", ["20 januari 2020", "22 juni 2015"])
def test_calendar_dates_are_prose_not_list_numbers(date):
    row = date + ". En komplettering remitterades den 7 februari."
    assert DocumentParser.numbered(row) is None
    assert DocumentParser.is_prose(row)


def test_scan_number_column_keeps_only_the_organisation_words(monkeypatch):
    items = [TextBox(text="Remissinstanser", x=70, y=100, width=100, height=10)]
    for i, (label, name) in enumerate(
        [
            ("1", "Sveriges riksbank"),
            ("AA", "Konsumentverket"),
            ("N", "Skatteverket"),
            (">", "Försäkringskassan"),
        ]
    ):
        items.extend(
            [
                TextBox(text=label, x=70, y=150 + 22 * i, width=4, height=10),
                TextBox(text=name, x=90, y=150 + 22 * i, width=120, height=10),
            ]
        )
    document = ParsedDocument(text="", pages=[ParsedPage(height=842, items=items)])
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "Sveriges riksbank",
        "Konsumentverket",
        "Skatteverket",
        "Försäkringskassan",
    ]


def test_scan_number_column_can_be_recognised_without_readable_digits(monkeypatch):
    items = [TextBox(text="Remissinstanser", x=70, y=100, width=100, height=10)]
    names = [
        "Försvarsmakten",
        "Riksrevisionen",
        "Skatteverket",
        "Sveriges akademikers centralorganisation, SACO-S",
    ]
    for i, (label, name) in enumerate(zip(["SoS", "N", ">", "än"], names)):
        items.extend(
            [
                TextBox(text=label, x=70, y=150 + 22 * i, width=4, height=10),
                TextBox(
                    text=name, x=90, y=150 + 22 * i, width=len(name) * 5, height=10
                ),
            ]
        )
    document = ParsedDocument(text="", pages=[ParsedPage(height=842, items=items)])
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == names


def test_person_initials_are_not_inferred_to_be_list_numbers(monkeypatch):
    names = ["A. Aramachi", "B. Bengtsson", "C. Carlsson", "D. Davidsson"]
    document = document_with_rows(["Remissinstanser", *names])
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == names


def test_offset_number_box_joins_its_name_without_becoming_a_recipient():
    page = ParsedPage(
        height=842,
        items=[
            TextBox(text="10.", x=70, y=200, width=12, height=17),
            TextBox(text="Skatteverket", x=90, y=205, width=80, height=17),
            *[
                TextBox(text="Other", x=90, y=250 + 20 * i, width=30, height=9)
                for i in range(5)
            ],
        ],
    )
    assert DocumentParser.page_rows(page)[0] == "10. Skatteverket"


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


@pytest.mark.parametrize(
    "rows,expected",
    [
        (
            ["1. LSU - Sveriges barn- och", "ungdomsorganisationer", "2. FAR"],
            ["LSU - Sveriges barn- och ungdomsorganisationer", "FAR"],
        ),
        (
            [
                "1. Stockholms universitet",
                "(Juridiska institutionen)",
                "2. Umeå universitet",
            ],
            ["Stockholms universitet (Juridiska institutionen)", "Umeå universitet"],
        ),
        (
            [
                "1. Myndigheten (förslaget att",
                "Kriminalvården ska ta över uppgiften)",
                "2. FAR",
            ],
            ["Myndigheten (förslaget att Kriminalvården ska ta över uppgiften)", "FAR"],
        ),
        (["• FAR", "• Umeå universitet"], ["FAR", "Umeå universitet"]),
        (
            [
                "FAR",
                "atsec information security AB",
                "eSam",
                "4spar AB",
                "4Finance AB",
                "2030-sekretariatet",
                "1000 möjligheter",
            ],
            [
                "FAR",
                "atsec information security AB",
                "eSam",
                "4spar AB",
                "4Finance AB",
                "2030-sekretariatet",
                "1000 möjligheter",
            ],
        ),
        (
            ["1. Umeå universitet", "2. Umeå universitet"],
            ["Umeå universitet", "Umeå universitet"],
        ),
        (
            ["1. Kommunförbundet", "2. FAR", "Bilaga:", "En rapport"],
            ["Kommunförbundet", "FAR"],
        ),
        (
            ["100.Svenskt Sigill", "101.Sveriges Konsumenter"],
            ["Svenskt Sigill", "Sveriges Konsumenter"],
        ),
        (
            ["IT&Telekom\xadföretagen", "Sveriges\u00a0Kommuner", "Föreningen ﬁlm"],
            ["IT&Telekomföretagen", "Sveriges Kommuner", "Föreningen film"],
        ),
    ],
    ids=[
        "short-wrapped-name",
        "qualifier-on-new-line",
        "capitalised-continuation",
        "bullets",
        "legitimate-capitalisation-and-digits",
        "source-duplicates",
        "attachment-is-not-an-organisation",
        "three-digit-numbering-without-space",
        "invisible-characters-and-ligatures",
    ],
)
def test_reviewed_extraction_patterns(monkeypatch, rows, expected):
    document = document_with_rows(["Remissinstanser", *rows])
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == expected


def test_new_heading_takes_precedence_over_a_title_or_prose_mention(monkeypatch):
    document = document_with_rows(
        [
            "Remisslista avseende utredningen",
            "hemtjänsten (SOU 2020:70)",
            "remissinstanser.",
            "Remissinstanser",
            "FAR",
            "Umeå universitet",
        ]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == ["FAR", "Umeå universitet"]


def test_prose_mention_after_numbered_list_is_not_a_heading(monkeypatch):
    document = document_with_rows(
        [
            "Remiss",
            "1. FAR",
            "2. Umeå universitet",
            "3. Lunds universitet",
            "Remissvaren ska skickas till regeringen",
            "remissinstanser innebär remissen en inbjudan att lämna synpunkter.",
        ]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "FAR",
        "Umeå universitet",
        "Lunds universitet",
    ]


def test_truncated_ocr_numbers_do_not_end_the_list(monkeypatch):
    document = document_with_rows(
        [
            "Remissinstanser",
            "39. FAR",
            "4. Umeå universitet",
            "42. Lunds universitet",
            "43. LO",
            "1. Bifogad rapport",
            "2. En annan rapport",
        ]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "FAR",
        "Umeå universitet",
        "Lunds universitet",
        "LO",
    ]


def test_digits_in_a_wrapped_qualification_are_not_list_numbers(monkeypatch):
    document = document_with_rows(
        [
            "Remissinstanser",
            "1. FAR (förslaget för de",
            "24 nämnderna)",
            "2. Umeå universitet",
        ]
    )
    document.pages[0].items[2].x = 90
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "FAR (förslaget för de 24 nämnderna)",
        "Umeå universitet",
    ]


def test_right_aligned_one_digit_list_numbers_are_removed(monkeypatch):
    document = document_with_rows(
        [
            "Remissinstanser",
            "1 All-emballage",
            "10 Boverket",
            "11 FAR",
            "12 Umeå universitet",
            "13 LO",
        ]
    )
    document.pages[0].items[1].x = 79
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "All-emballage",
        "Boverket",
        "FAR",
        "Umeå universitet",
        "LO",
    ]


def test_native_vertical_side_label_does_not_pollute_names(monkeypatch):
    document = document_with_rows(
        [
            "Remissinstanser",
            "FAR",
            "Umeå universitet",
            "Dokumentegenskaper, Ärendenummer 2024/1",
            "känslig",
        ]
    )
    document.pages[0].items.append(
        TextBox(text="Brev", x=23, y=178, width=8, height=16, rotation=270)
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == ["FAR", "Umeå universitet"]


def test_multidigit_trafikverket_reference_is_page_furniture(monkeypatch):
    document = document_with_rows(
        ["Remissinstanser", "FAR", "TRV 2023/70321 2024-01-15", "Umeå universitet"]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == ["FAR", "Umeå universitet"]


def test_small_font_parenthetical_continuation_is_joined(monkeypatch):
    document = document_with_rows(
        [
            "Remissinstanser",
            "Svensk Sjöfart (till den del promemorian avser ytterligare uppgifter i en",
            "ansökan om godkännande för tonnagebeskattning)",
            "FAR",
        ]
    )
    for item in document.pages[0].items:
        item.height = 8
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "Svensk Sjöfart (till den del promemorian avser ytterligare uppgifter i en "
        "ansökan om godkännande för tonnagebeskattning)",
        "FAR",
    ]


def test_missing_ocr_parenthesis_does_not_merge_later_recipients(monkeypatch):
    document = document_with_rows(
        ["Remissinstanser", "FAR (avsnitt 2.5", "Umeå universitet", "Lunds universitet"]
    )
    for item in document.pages[0].items:
        item.height = 8
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "FAR (avsnitt 2.5",
        "Umeå universitet",
        "Lunds universitet",
    ]


@pytest.mark.parametrize(
    "rows,expected",
    [
        (
            ["1. 2030-sekretariatet", "2. 1000 möjligheter", "3. 1,6 miljonerklubben"],
            ["2030-sekretariatet", "1000 möjligheter", "1,6 miljonerklubben"],
        ),
        (
            ["21 Grams", "FAR", "Umeå universitet"],
            ["21 Grams", "FAR", "Umeå universitet"],
        ),
        (
            ["40. FAR", "4. Umeå universitet", "42. Lunds universitet"],
            ["FAR", "Umeå universitet", "Lunds universitet"],
        ),
        (
            [
                '"Tanums kommun',
                "& Arbetsmiljöverket",
                "- - Försvarsmakten",
                ". 2030-sekretariatet",
                ".Åklagarmyndigheten",
                ".",
                "--------",
                ".SE (Stiftelsen för internetinfrastruktur)",
            ],
            [
                "Tanums kommun",
                "Arbetsmiljöverket",
                "Försvarsmakten",
                "2030-sekretariatet",
                "Åklagarmyndigheten",
                ".SE (Stiftelsen för internetinfrastruktur)",
            ],
        ),
        (["FAR", "Näringsdepartementet har utarbetat en promemoria"], ["FAR"]),
        (["FAR", "Europeiska kommissionen har presenterat ett förslag"], ["FAR"]),
        (["FAR", "14.00. Remissmötet kommer att genomföras på skype"], ["FAR"]),
        (["FAR", "I augusti 2013 trädde 2006 års konvention i kraft"], ["FAR"]),
        (["FAR", "Bakgrund", "Förslaget beskrivs nedan"], ["FAR"]),
        (
            [
                "FAR",
                "Riksdagen har 2019 beslutat om ett nytt mål för den regionala",
                "tillväxtpolitiken (budgetpropositionen för 2020, prop. 2019/20:1)",
                "med stärkt lokal och regional konkurrenskraft i hela landet.",
            ],
            ["FAR"],
        ),
        (["FAR", "remissen ligger att regeringen vill ha synpunkter"], ["FAR"]),
        (["1 bilaga", "1. FAR", "2. Umeå universitet"], ["FAR", "Umeå universitet"]),
        (
            ["36. FAR", "3 7 Transportarbetareförbundet", "38. Lunds universitet"],
            ["FAR", "Transportarbetareförbundet", "Lunds universitet"],
        ),
        (
            ["99. FAR", "100Sveriges Kommuner och Landsting", "101LO"],
            ["FAR", "Sveriges Kommuner och Landsting", "LO"],
        ),
        (
            ["1 FAR", "2= Bodens kommun", "3=Borgholms kommun"],
            ["FAR", "Bodens kommun", "Borgholms kommun"],
        ),
    ],
)
def test_patterns_reported_in_the_dataset(monkeypatch, rows, expected):
    document = document_with_rows(["Remissinstanser", *rows])
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == expected


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


@pytest.mark.parametrize("version", [1, 2])
def test_old_text_caches_are_rebuilt(tmp_path, monkeypatch, version):
    source = tmp_path / "source.pdf"
    source.with_suffix(".liteparse.json").write_text('{"version": %d}' % version)
    calls = []

    def parse(path):
        calls.append(path)
        return SimpleNamespace(pages=[])

    monkeypatch.setattr(
        document_parser, "get_parser", lambda path: SimpleNamespace(parse=parse)
    )
    result = parse_document(source)
    assert result.version == 3
    assert calls == [source]
    assert parse_document(source) == result
    assert calls == [source]


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


@pytest.mark.parametrize("numbered", [False, True])
def test_draft_title_requires_a_recipient_sequence_before_inferencing_a_list(
    monkeypatch, numbered
):
    rows = [
        "Remiss",
        "Utkast till lagrådsremiss Upphandling av vissa kollektivtrafiktjänster",
        "Kammarrätten i Stockholm",
        "Förvaltningsrätten i Malmö",
        "Göteborgs tingsrätt",
        "4. Domstolsverket" if numbered else "Domstolsverket",
        "5. Konkurrensverket" if numbered else "Konkurrensverket",
        "6. Trafikverket" if numbered else "Trafikverket",
        "Remissvaren ska ha kommit in i mars",
    ]
    document = document_with_rows(rows)
    for item in document.pages[0].items[2:]:
        item.y += 20
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    actual = DocumentParser.extract_list("example.pdf")
    assert (
        actual
        == [
            "Kammarrätten i Stockholm",
            "Förvaltningsrätten i Malmö",
            "Göteborgs tingsrätt",
            "Domstolsverket",
            "Konkurrensverket",
            "Trafikverket",
        ]
        if numbered
        else actual is None
    )


@pytest.mark.parametrize(
    "prose",
    [
        "Promemorian skicka inledningsvis ut med e-post och skickas därefter ut till",
        "Byggkonkurrensutredningen betänkande Plats för fler som bygger mer (SOU 2015:105) remitteras härmed till ovanstående remissinstanser.",
    ],
)
def test_delivery_and_forwarding_prose_is_not_a_recipient(monkeypatch, prose):
    document = document_with_rows(
        ["Remissinstanser", "1. Skandia", "2.", "3. Wallenstam", prose]
    )
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == ["Skandia", "Wallenstam"]


def test_numeric_qualification_continuation_is_not_an_orphaned_list_number(monkeypatch):
    document = document_with_rows(
        [
            "Remissinstanser",
            "1. Svenska Petroleum & Biodrivmedel Institutet (SPBI) (Avsnitt 3, 4 och",
            "5)",
            "2. Wallenstam",
        ]
    )
    document.pages[0].items[2].x = 90
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == [
        "Svenska Petroleum & Biodrivmedel Institutet (SPBI) (Avsnitt 3, 4 och 5)",
        "Wallenstam",
    ]


@pytest.mark.parametrize(
    "lines",
    [
        [
            "Byggkonkurrensutredningen betänkande Plats för fler som bygger mer",
            "(SOU 2015:105) remitteras härmed till ovanstående remissinstanser.",
        ],
        [
            "Promemorian Anpassade krav för tillfälliga anläggningsboenden",
            "remitteras härmed till ovanstående remissinstanser.",
        ],
    ],
)
def test_wrapped_forwarding_paragraph_is_removed_in_full(monkeypatch, lines):
    document = document_with_rows(["Remissinstanser", "1. Wallenstam", *lines])
    monkeypatch.setattr(document_parser, "parse_document", lambda path: document)
    assert DocumentParser.extract_list("example.pdf") == ["Wallenstam"]
