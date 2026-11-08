"""Export the current datasets and native pivot-table leaderboards to XLSX.

The template owns formatting. Streaming OOXML data and pivot caches keeps this
export portable: only the project's existing PyArrow dependency is needed.
"""

import argparse
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import re
from typing import Any
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = Path(__file__).with_name("templates") / "openremiss.xlsx"
MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"
ET.register_namespace("x", MAIN)
ET.register_namespace("r", REL)
INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def element(tag, parent=None, **attributes):
    attrs = {key: str(value) for key, value in attributes.items()}
    if parent is None:
        return ET.Element(f"{{{MAIN}}}{tag}", attrs)
    return ET.SubElement(parent, f"{{{MAIN}}}{tag}", attrs)


def xml_bytes(root):
    namespace = root.tag.partition("}")[0].lstrip("{")
    if namespace in (PKG, CONTENT):
        # OPC package manifests use their namespace as the default namespace.
        ET.register_namespace("", namespace)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def column(index):
    result = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def cell_xml(address, value, style="0"):
    start = f'<x:c r="{address}" s="{style}"'
    if value is None:
        return start + "/>"
    if isinstance(value, date):
        value = (value - date(1899, 12, 30)).days
    if isinstance(value, (int, float)):
        return f"{start}><x:v>{value}</x:v></x:c>"
    text = str(value)
    if INVALID_XML.search(text) or len(text) > 32767:
        raise ValueError(f"Text cannot be represented in Excel at {address}")
    # Inline strings remain literal even when a source name begins with '='.
    return (
        f'{start} t="inlineStr"><x:is><x:t xml:space="preserve">'
        f"{escape(text)}</x:t></x:is></x:c>"
    )


def row_xml(index, values, styles, widths):
    lines = max(
        (
            max((len(part) + width - 1) // width for part in str(value).split("\n"))
            for value, width in zip(values, widths)
            if value is not None
        ),
        default=1,
    )
    height = min(409, max(22, 14 * lines + 6))
    cells = "".join(
        cell_xml(f"{column(i)}{index}", value, style)
        for i, (value, style) in enumerate(zip(values, styles), 1)
    )
    return f'<x:row r="{index}" ht="{height}" customHeight="1">{cells}</x:row>'


def names_by_frequency(names):
    """Unify casing only; retain different spellings, aliases and qualifications."""
    result = {}
    for name, _ in Counter(name for name in names if name).most_common():
        result.setdefault(name.casefold(), name)
    return result


def participation_rows(records, *, respondents):
    labels = [
        (
            row.get("organisation")
            if respondents
            else row.get("cleaned_name") or row["name"]
        )
        for row in records
        if not respondents or row["kind"] == "answer"
    ]
    canonical = names_by_frequency(labels)
    seen = set()
    for row in records:
        raw_name = (
            row.get("organisation")
            if respondents
            else row.get("cleaned_name") or row["name"]
        )
        eligible = bool(raw_name) and (not respondents or row["kind"] == "answer")
        name = canonical[raw_name.casefold()] if eligible else None
        key = (name, row["remiss_url"])
        first = int(eligible and key not in seen)
        if eligible:
            seen.add(key)
        if respondents:
            yield [
                row["name"],
                row.get("organisation"),
                row["kind"],
                row["remiss_url"],
                row["url"],
                row.get("extraction_status"),
                row.get("extraction_error"),
                name,
                first,
                int(eligible),
            ]
        else:
            yield [
                row.get("cleaned_name"),
                row["name"],
                row["remiss_url"],
                row["document_url"],
                name,
                first,
            ]


def ranking(records, *, respondents):
    totals = defaultdict(lambda: [0, 0])
    for row in records:
        name, first = row[-3:-1] if respondents else row[-2:]
        if name:
            totals[name][0] += first
            totals[name][1] += row[-1] if respondents else 1
    return [
        [name, *counts]
        for name, counts in sorted(
            totals.items(),
            key=lambda pair: (-pair[1][0], -pair[1][1], pair[0].casefold()),
        )
    ]


def write_sheet(archive, path, original, rows, *, leaderboard=False):
    root = ET.fromstring(original)
    data = root.find(f"{{{MAIN}}}sheetData")
    assert data is not None
    template_rows = list(data)
    style_row = next(
        row for row in template_rows if row.get("r") == ("7" if leaderboard else "2")
    )
    styles = [cell.get("s", "0") for cell in style_row]
    if leaderboard:
        styles = styles[:3]
    widths = [
        max(1, int(float(col.get("width", "20"))))
        for col in root.findall(f"{{{MAIN}}}cols/{{{MAIN}}}col")
    ][: len(styles)]
    header_count = 6 if leaderboard else 1
    headers = [row for row in template_rows if int(row.get("r", "0")) <= header_count]
    data.clear()
    # Preserve the template's namespaces, panes, column widths and table links.
    wrapper = ET.tostring(root, encoding="unicode")
    before, after = wrapper.split("<x:sheetData />", 1)
    with archive.open(path, "w") as target:
        target.write(
            (
                '<?xml version="1.0" encoding="utf-8"?>' + before + "<x:sheetData>"
            ).encode()
        )
        for header in headers:
            target.write(ET.tostring(header, encoding="utf-8"))
        for index, values in enumerate(rows, header_count + 1):
            target.write(row_xml(index, values, styles, widths).encode())
        if leaderboard:
            total = [
                "Total participations",
                sum(row[1] for row in rows),
                sum(row[2] for row in rows),
            ]
            target.write(row_xml(len(rows) + 7, total, styles, widths).encode())
        target.write(("</x:sheetData>" + after).encode())


def pivot_parts(number, rows, leaders, *, respondents):
    sheet = "Documents" if respondents else "Consultees"
    source = f"H1:J{len(rows) + 1}" if respondents else f"E1:F{len(rows) + 1}"
    fields = ["leaderboard_name", "consultation_count"]
    if respondents:
        fields.append("response_documents")
    names = [row[0] for row in leaders]
    has_blank = respondents and any(row[-3] is None for row in rows)
    indexes = {name: i for i, name in enumerate(names)}
    definition = element(
        "pivotCacheDefinition",
        recordCount=len(rows),
        saveData=1,
        refreshOnLoad=0,
        enableRefresh=1,
        createdVersion=6,
        refreshedVersion=6,
        minRefreshableVersion=3,
    )
    definition.set(f"{{{REL}}}id", "rIdRecords")
    cache_source = element("cacheSource", definition, type="worksheet")
    element("worksheetSource", cache_source, ref=source, sheet=sheet)
    cache_fields = element("cacheFields", definition, count=len(fields))
    for i, name in enumerate(fields):
        field = element("cacheField", cache_fields, name=name, numFmtId=0)
        if i == 0:
            shared = element(
                "sharedItems",
                field,
                count=len(names) + int(has_blank),
                containsBlank=int(has_blank),
                containsString=1,
            )
            for label in names:
                element("s", shared, v=label)
            if has_blank:
                element("m", shared)
        else:
            shared = element(
                "sharedItems",
                field,
                count=2,
                containsSemiMixedTypes=0,
                containsNumber=1,
                containsInteger=1,
                containsString=0,
                minValue=0,
                maxValue=1,
            )
            element("n", shared, v=0)
            element("n", shared, v=1)
    pivot = element(
        "pivotTableDefinition",
        name=f"OpenRemissLeaderboard{number}",
        cacheId=number,
        dataCaption="Values",
        grandTotalCaption="Total participations",
        rowGrandTotals=0,
        colGrandTotals=1,
        compact=0,
        compactData=0,
        outline=0,
        outlineData=0,
    )
    element(
        "location",
        pivot,
        ref=f"A6:C{len(leaders) + 7}",
        firstHeaderRow=0,
        firstDataRow=1,
        firstDataCol=1,
    )
    pivot_fields = element("pivotFields", pivot, count=len(fields))
    for i in range(len(fields)):
        field = element("pivotField", pivot_fields, showAll=0, defaultSubtotal=0)
        if i == 0:
            field.set("axis", "axisRow")
            field.set("sortType", "descending")
            if not respondents:
                field.set("dataField", "1")
            items = element("items", field, count=len(names) + int(has_blank))
            for j in range(len(names)):
                element("item", items, x=j)
            if has_blank:
                element("item", items, x=len(names), h=1)
            scope = element("autoSortScope", field)
            area = element("pivotArea", scope)
            refs = element("references", area, count=1)
            reference = element("reference", refs, field=4294967294)
            element("x", reference, v=0)
        else:
            field.set("dataField", "1")
    row_fields = element("rowFields", pivot, count=1)
    element("field", row_fields, x=0)
    row_items = element("rowItems", pivot, count=len(names) + 1)
    for i in range(len(names)):
        item = element("i", row_items)
        element("x", item, v=i)
    element("x", element("i", row_items, t="grand"))
    col_fields = element("colFields", pivot, count=1)
    element("field", col_fields, x=-2)
    col_items = element("colItems", pivot, count=2)
    for i in range(2):
        item = element("i", col_items, i=i)
        element("x", item, v=i)
    values = element("dataFields", pivot, count=2)
    element(
        "dataField", values, name="Consultations", fld=1, subtotal="sum", numFmtId=3
    )
    element(
        "dataField",
        values,
        name="Response documents" if respondents else "List entries",
        fld=2 if respondents else 0,
        subtotal="sum" if respondents else "count",
        numFmtId=3,
    )
    element(
        "pivotTableStyleInfo",
        pivot,
        name="PivotStyleMedium9",
        showRowHeaders=1,
        showColHeaders=1,
        showRowStripes=0,
        showColStripes=0,
        showLastColumn=1,
    )
    return definition, pivot, indexes


def relationship(kind, target, identifier):
    return ET.Element(
        f"{{{PKG}}}Relationship",
        {"Id": identifier, "Type": f"{REL}/{kind}", "Target": target},
    )


def add_pivots(archive, files, datasets, leaderboards):
    workbook = ET.fromstring(files["xl/workbook.xml"])
    caches = element("pivotCaches", workbook)
    workbook_rels = ET.fromstring(files["xl/_rels/workbook.xml.rels"])
    types = ET.fromstring(files["[Content_Types].xml"])
    for number, (rows, leaders) in enumerate(zip(datasets, leaderboards), 1):
        respondents = number == 1
        definition, pivot, indexes = pivot_parts(
            number, rows, leaders, respondents=respondents
        )
        cache = element("pivotCache", caches, cacheId=number)
        cache.set(f"{{{REL}}}id", f"rIdPivotCache{number}")
        workbook_rels.append(
            relationship(
                "pivotCacheDefinition",
                f"pivotCache/pivotCacheDefinition{number}.xml",
                f"rIdPivotCache{number}",
            )
        )
        sheet_rels = ET.Element(f"{{{PKG}}}Relationships")
        sheet_rels.append(
            relationship(
                "pivotTable",
                f"../pivotTables/pivotTable{number}.xml",
                f"rIdPivot{number}",
            )
        )
        archive.writestr(
            f"xl/worksheets/_rels/sheet{number + 1}.xml.rels", xml_bytes(sheet_rels)
        )
        rels = ET.Element(f"{{{PKG}}}Relationships")
        rels.append(
            relationship(
                "pivotCacheRecords", f"pivotCacheRecords{number}.xml", "rIdRecords"
            )
        )
        archive.writestr(
            f"xl/pivotCache/_rels/pivotCacheDefinition{number}.xml.rels",
            xml_bytes(rels),
        )
        table_rels = ET.Element(f"{{{PKG}}}Relationships")
        table_rels.append(
            relationship(
                "pivotCacheDefinition",
                f"../pivotCache/pivotCacheDefinition{number}.xml",
                "rIdCache",
            )
        )
        archive.writestr(
            f"xl/pivotTables/_rels/pivotTable{number}.xml.rels", xml_bytes(table_rels)
        )
        archive.writestr(
            f"xl/pivotCache/pivotCacheDefinition{number}.xml", xml_bytes(definition)
        )
        archive.writestr(f"xl/pivotTables/pivotTable{number}.xml", xml_bytes(pivot))
        with archive.open(
            f"xl/pivotCache/pivotCacheRecords{number}.xml", "w"
        ) as target:
            target.write(
                f'<x:pivotCacheRecords xmlns:x="{MAIN}" count="{len(rows)}">'.encode()
            )
            for row in rows:
                name, flag = row[-3:-1] if respondents else row[-2:]
                values = [indexes.get(name, len(indexes)), flag]
                if respondents:
                    values.append(row[-1])
                target.write(
                    (
                        "<x:r>" + "".join(f'<x:x v="{v}"/>' for v in values) + "</x:r>"
                    ).encode()
                )
            target.write(b"</x:pivotCacheRecords>")
        for part, content_type in [
            (f"pivotTables/pivotTable{number}.xml", "pivotTable"),
            (f"pivotCache/pivotCacheDefinition{number}.xml", "pivotCacheDefinition"),
            (f"pivotCache/pivotCacheRecords{number}.xml", "pivotCacheRecords"),
        ]:
            ET.SubElement(
                types,
                f"{{{CONTENT}}}Override",
                {
                    "PartName": f"/xl/{part}",
                    "ContentType": f"application/vnd.openxmlformats-officedocument.spreadsheetml.{content_type}+xml",
                },
            )
    for path, root in [
        ("xl/workbook.xml", workbook),
        ("xl/_rels/workbook.xml.rels", workbook_rels),
        ("[Content_Types].xml", types),
    ]:
        archive.writestr(path, xml_bytes(root))


def export_spreadsheet(data_dir: Path, output: Path, *, updated: date | None = None):
    remisser = pq.read_table(data_dir / "remisser.parquet").to_pylist()
    documents = pq.read_table(data_dir / "documents.parquet").to_pylist()
    consultees = pq.read_table(data_dir / "consultees.parquet").to_pylist()
    document_rows = list(participation_rows(documents, respondents=True))
    consultee_rows = list(participation_rows(consultees, respondents=False))
    response_ranking = ranking(document_rows, respondents=True)
    consultee_ranking = ranking(consultee_rows, respondents=False)
    remiss_rows = [
        [row[key] for key in ["title", "published_on", "issuer", "diary_number", "url"]]
        for row in remisser
    ]
    with ZipFile(TEMPLATE) as template:
        files = {name: template.read(name) for name in template.namelist()}
    overview = ET.fromstring(files["xl/worksheets/sheet1.xml"])
    dates = [row["published_on"] for row in remisser]
    statuses = Counter(
        row.get("extraction_status")
        for row in documents
        if row["kind"] == "consultee_list"
    )
    values: dict[str, Any] = {
        "B5": updated or date.today(),
        "B6": f"{min(dates)} – {max(dates)}" if dates else "No consultations",
        "B8": len(remisser),
        "B9": len(documents),
        "B10": sum(row["kind"] == "answer" for row in documents),
        "B11": len(consultees),
        "A19": f"Consultee extraction: {statuses['complete']:,} PDFs complete; {statuses['failed']} failed; {statuses['skipped']} skipped; {statuses['pending']} pending.",
    }
    for row in overview.findall(f"{{{MAIN}}}sheetData/{{{MAIN}}}row"):
        for cell in list(row):
            address = cell.get("r")
            if address in values:
                position = list(row).index(cell)
                row.remove(cell)
                replacement = ET.fromstring(
                    f'<root xmlns:x="{MAIN}">{cell_xml(address, values[address], cell.get("s", "0"))}</root>'
                )[0]
                row.insert(position, replacement)
    files["xl/worksheets/sheet1.xml"] = xml_bytes(overview)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".xlsx.tmp")
    datasets = [
        response_ranking,
        consultee_ranking,
        remiss_rows,
        document_rows,
        consultee_rows,
    ]
    replaced = {"xl/workbook.xml", "xl/_rels/workbook.xml.rels", "[Content_Types].xml"}
    replaced.update(f"xl/worksheets/sheet{i}.xml" for i in range(2, 7))
    replaced.update(f"xl/tables/table{i}.xml" for i in range(1, 4))
    try:
        with ZipFile(
            temporary, "w", compression=ZIP_DEFLATED, compresslevel=6
        ) as archive:
            for path, content in files.items():
                if path not in replaced:
                    archive.writestr(path, content)
            for i, rows in enumerate(datasets, 2):
                write_sheet(
                    archive,
                    f"xl/worksheets/sheet{i}.xml",
                    files[f"xl/worksheets/sheet{i}.xml"],
                    rows,
                    leaderboard=i < 4,
                )
            for i, rows in enumerate(datasets[2:], 1):
                path = f"xl/tables/table{i}.xml"
                table = ET.fromstring(files[path])
                ref = f"A1:{column(len(rows[0]) if rows else [5, 10, 6][i - 1])}{max(2, len(rows) + 1)}"
                table.set("ref", ref)
                auto_filter = table.find(f"{{{MAIN}}}autoFilter")
                if auto_filter is not None:
                    auto_filter.set("ref", ref)
                archive.writestr(path, xml_bytes(table))
            add_pivots(
                archive,
                files,
                [document_rows, consultee_rows],
                [response_ranking, consultee_ranking],
            )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "consultations": len(remisser),
        "documents": len(documents),
        "consultees": len(consultees),
        "respondent_organisations": len(response_ranking),
        "consultee_organisations": len(consultee_ranking),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs" / "OpenRemiss.xlsx"
    )
    args = parser.parse_args()
    summary = export_spreadsheet(args.data_dir, args.output)
    print(f"Saved {args.output}")
    print(
        ", ".join(
            f"{count:,} {label.replace('_', ' ')}" for label, count in summary.items()
        )
    )


if __name__ == "__main__":
    main()
