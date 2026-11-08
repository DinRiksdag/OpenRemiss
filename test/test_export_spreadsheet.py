from datetime import date
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from models import Consultee, Document, Remiss
from scripts.export_spreadsheet import MAIN, REL, export_spreadsheet
from service.storage import save


def sheet_rows(archive, number):
    root = ET.fromstring(archive.read(f"xl/worksheets/sheet{number}.xml"))
    result = {}
    for row in root.findall(f"{{{MAIN}}}sheetData/{{{MAIN}}}row"):
        cells = {}
        for cell in row:
            if cell.get("t") == "inlineStr":
                text = cell.find(f"{{{MAIN}}}is")
                assert text is not None
                value = "".join(text.itertext())
            else:
                value = cell.findtext(f"{{{MAIN}}}v")
                if value is not None and cell.get("t") != "str":
                    value = float(value)
            if value is not None:
                cells[cell.get("r")] = value
        result[int(row.attrib["r"])] = cells
    return result


def populate(data_dir):
    remisser = [
        Remiss(
            url=f"https://example.org/r{i}",
            title=f"Consultation {i}",
            published_on=date(2025, 1, i),
        )
        for i in [1, 2]
    ]
    documents = [
        Document.model_validate(
            dict(
                remiss_url=remisser[remiss].url,
                url=f"https://example.org/d{i}",
                name=name,
                organisation=organisation,
                kind=kind,
            )
        )
        for i, (remiss, name, organisation, kind) in enumerate(
            [
                (0, "Alpha", "Alpha", "answer"),
                (0, "=literal attachment name", "ALPHA", "answer"),
                (1, "Alpha", "Alpha", "answer"),
                (0, "Joint response", "Alpha and Beta", "answer"),
                (0, "Report", None, "other"),
            ]
        )
    ]
    consultees = [
        Consultee(
            remiss_url=remisser[remiss].url,
            document_url="https://example.org/list",
            name=name,
            cleaned_name=name,
        )
        for remiss, name in [
            (0, "Alpha"),
            (0, "Alpha"),
            (0, "ALPHA"),
            (1, "Alpha"),
            (0, "Beta"),
        ]
    ]
    save(Remiss, remisser, data_dir)
    save(Document, documents, data_dir)
    save(Consultee, consultees, data_dir)


def test_export_preserves_records_and_counts_distinct_consultations(data_dir, tmp_path):
    populate(data_dir)
    output = tmp_path / "OpenRemiss.xlsx"
    summary = export_spreadsheet(data_dir, output, updated=date(2026, 11, 8))
    assert summary == dict(
        consultations=2,
        documents=5,
        consultees=5,
        respondent_organisations=2,
        consultee_organisations=2,
    )
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        respondents = sheet_rows(archive, 2)
        invited = sheet_rows(archive, 3)
        assert respondents[7] == {"A7": "Alpha", "B7": 2, "C7": 3}
        assert respondents[8] == {"A8": "Alpha and Beta", "B8": 1, "C8": 1}
        assert respondents[9] == {"A9": "Total participations", "B9": 3, "C9": 4}
        assert invited[7] == {"A7": "Alpha", "B7": 2, "C7": 4}
        assert invited[8] == {"A8": "Beta", "B8": 1, "C8": 1}
        assert len(sheet_rows(archive, 4)) == 3
        assert len(sheet_rows(archive, 5)) == 6
        assert len(sheet_rows(archive, 6)) == 6
        assert sheet_rows(archive, 5)[3]["A3"] == "=literal attachment name"
        assert sheet_rows(archive, 5)[3]["B3"] == "ALPHA"
        assert b"<x:f>" not in archive.read("xl/worksheets/sheet5.xml")
        assert (
            sheet_rows(archive, 4)[2]["B2"]
            == (date(2025, 1, 1) - date(1899, 12, 30)).days
        )


def test_export_contains_native_pivots_and_complete_refreshable_caches(
    data_dir, tmp_path
):
    populate(data_dir)
    output = tmp_path / "OpenRemiss.xlsx"
    export_spreadsheet(data_dir, output)
    with ZipFile(output) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        caches = workbook.find(f"{{{MAIN}}}pivotCaches")
        assert caches is not None
        assert len(caches) == 2
        for number, source_range in [(1, "H1:J6"), (2, "E1:F6")]:
            definition = ET.fromstring(
                archive.read(f"xl/pivotCache/pivotCacheDefinition{number}.xml")
            )
            assert definition.get("recordCount") == "5"
            assert definition.get(f"{{{REL}}}id") == "rIdRecords"
            source = definition.find(f"{{{MAIN}}}cacheSource/{{{MAIN}}}worksheetSource")
            assert source is not None and source.get("ref") == source_range
            records = ET.fromstring(
                archive.read(f"xl/pivotCache/pivotCacheRecords{number}.xml")
            )
            assert len(records) == int(records.attrib["count"]) == 5
            table = ET.fromstring(
                archive.read(f"xl/pivotTables/pivotTable{number}.xml")
            )
            assert table.get("cacheId") == str(number)
            fields = table.find(f"{{{MAIN}}}dataFields")
            assert fields is not None
            assert fields[0].get("subtotal") == "sum"
            assert fields[1].get("subtotal") == ("sum" if number == 1 else "count")
            assert (
                "pivotTable"
                in archive.read(
                    f"xl/worksheets/_rels/sheet{number + 1}.xml.rels"
                ).decode()
            )
            assert (
                "pivotCacheDefinition"
                in archive.read(
                    f"xl/pivotTables/_rels/pivotTable{number}.xml.rels"
                ).decode()
            )


def test_failed_export_does_not_replace_previous_file(data_dir, tmp_path):
    populate(data_dir)
    from service.storage import load

    documents = load(Document, data_dir)
    documents[0].name = "invalid\x00XML"
    save(Document, documents, data_dir)
    output = tmp_path / "OpenRemiss.xlsx"
    output.write_bytes(b"previous workbook")
    with pytest.raises(ValueError, match="cannot be represented"):
        export_spreadsheet(data_dir, output)
    assert output.read_bytes() == b"previous workbook"
    assert not output.with_suffix(".xlsx.tmp").exists()


def test_pivot_cache_type_flags_match_the_shared_values(data_dir, tmp_path):
    populate(data_dir)
    output = tmp_path / "OpenRemiss.xlsx"
    export_spreadsheet(data_dir, output)
    with ZipFile(output) as archive:
        for number in (1, 2):
            cache = ET.fromstring(
                archive.read(f"xl/pivotCache/pivotCacheDefinition{number}.xml")
            )
            for shared in cache.findall(
                f"{{{MAIN}}}cacheFields/{{{MAIN}}}cacheField/{{{MAIN}}}sharedItems"
            ):
                kinds = {item.tag.rsplit("}", 1)[-1] for item in shared}
                # The OOXML default is true: numeric caches must override it.
                has_text_or_blank = bool(kinds & {"s", "m", "b", "e"})
                assert (
                    shared.get("containsSemiMixedTypes", "1") == "1"
                ) == has_text_or_blank
                if kinds == {"n"}:
                    numbers = [float(item.attrib["v"]) for item in shared]
                    assert float(shared.attrib["minValue"]) == min(numbers)
                    assert float(shared.attrib["maxValue"]) == max(numbers)
