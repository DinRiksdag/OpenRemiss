import logging
from functools import lru_cache
from pathlib import Path
import re
from statistics import median
from typing import Literal

from liteparse import LiteParse
from pydantic import BaseModel


logger = logging.getLogger(__name__)


class TextBox(BaseModel):
    text: str
    x: float
    y: float
    width: float
    height: float


class ParsedPage(BaseModel):
    height: float
    items: list[TextBox]


class ParsedDocument(BaseModel):
    version: Literal[1] = 1
    text: str
    pages: list[ParsedPage]


@lru_cache(maxsize=2)
def get_parser(tessdata_path: Path, ocr_pages: str | None = None) -> LiteParse:
    return LiteParse(
        ocr_enabled=ocr_pages is not None,
        target_pages=ocr_pages,
        include_complexity=ocr_pages is None,
        ocr_language="swe",
        tessdata_path=str(tessdata_path),
        num_workers=2,
        emit_word_boxes=True,
        output_format="text",
        quiet=True,
    )


def parse_document(filename: Path, *, refresh: bool = False) -> ParsedDocument:
    cache = filename.with_suffix(".liteparse.json")
    if cache.exists() and not refresh:
        logger.info("Using cached text and coordinates: %s", cache)
        return ParsedDocument.model_validate_json(cache.read_text(encoding="utf-8"))

    logger.info(
        "Extracting text with LiteParse (Swedish OCR when needed): %s", filename
    )
    result = get_parser(filename.parent / "tessdata").parse(filename)
    # Use LiteParse's classifications; sparse lists and embedded logos need no OCR.
    ocr_reasons = {
        "scanned",
        "garbled",
        "vector-text",
        "invisible-text-layer",
        "annotation-text",
    }
    ocr_pages = [
        page.page_num
        for page in result.pages
        if page.complexity and ocr_reasons.intersection(page.complexity.reasons)
    ]
    if ocr_pages:
        logger.info("Running Swedish OCR on pages %s of %s", ocr_pages, filename)
        scanned = get_parser(
            filename.parent / "tessdata", ",".join(map(str, ocr_pages))
        ).parse(filename)
        replacements = {page.page_num: page for page in scanned.pages}
        result.pages = [replacements.get(page.page_num, page) for page in result.pages]
    document = ParsedDocument(
        text="\n\n".join(page.text for page in result.pages),
        pages=[
            ParsedPage(
                height=page.height,
                items=[
                    TextBox(
                        text=word.text,
                        x=word.x,
                        y=word.y,
                        width=word.width,
                        height=word.height,
                    )
                    for item in page.text_items
                    for word in (item.words or [item])
                ],
            )
            for page in result.pages
        ],
    )
    partial = cache.with_suffix(".json.tmp")
    try:
        partial.write_text(document.model_dump_json(), encoding="utf-8")
        partial.replace(cache)
    finally:
        partial.unlink(missing_ok=True)
    return document


class DocumentParser:
    @staticmethod
    def extract_list(filename, *, refresh=False):
        document = (
            parse_document(Path(filename), refresh=True)
            if refresh
            else parse_document(Path(filename))
        )
        all_rows = [
            row for page in document.pages for row in DocumentParser.page_rows(page)
        ]
        start = DocumentParser.detect_start(all_rows)
        if start is None:
            logger.info("No invitation list heading found: %s", filename)
            return

        consultee_list = all_rows[start:]
        # Long headings can wrap across several lines before a numbered list.
        first_number = next(
            (
                i
                for i, row in enumerate(consultee_list[:10])
                if re.match(r"^\d{1,3}\s*[.),]\s", row)
            ),
            None,
        )
        if len(all_rows[start - 1].split()) > 2 and first_number is not None:
            consultee_list = consultee_list[first_number:]

        end = DocumentParser.detect_end(consultee_list)
        if end is not None:
            consultee_list = consultee_list[:end]

        last_number = 0
        for index, row in enumerate(consultee_list):
            match = re.match(r"^(\d{1,3})\s*[.),]\s", row)
            if match:
                number = int(match[1])
                if number <= last_number:
                    consultee_list = consultee_list[:index]
                    break
                last_number = number

        consultee_list = [
            row for row in consultee_list if DocumentParser.detect_start([row]) is None
        ]
        consultee_list = DocumentParser.remove_page_numbers(consultee_list)
        consultee_list = DocumentParser.remove_footer_lines(consultee_list)
        consultee_list = DocumentParser.remove_leading_numbers(consultee_list)
        consultee_list = DocumentParser.remove_leading_spaces(consultee_list)
        consultee_list = DocumentParser.merge_multiline(consultee_list)
        consultee_list = DocumentParser.remove_trailing_comma(consultee_list)
        consultee_list = DocumentParser.remove_last_paragraph(consultee_list)

        return [name for name in consultee_list if name.strip()] or None

    @staticmethod
    def page_rows(page: ParsedPage) -> list[str]:
        items = [item for item in page.items if item.text.strip() and item.height > 0]
        if not items:
            return []
        tolerance = median(item.height for item in items) * 0.45
        lines: list[tuple[float, list[TextBox]]] = []
        for item in sorted(items, key=lambda item: (item.y + item.height / 2, item.x)):
            center = item.y + item.height / 2
            if lines and abs(center - lines[-1][0]) <= tolerance:
                lines[-1][1].append(item)
            else:
                lines.append((center, [item]))
        rows = []
        for center, line in lines:
            text = " ".join(
                item.text.strip() for item in sorted(line, key=lambda item: item.x)
            )
            if center > page.height * 0.65 and any(
                marker in text.casefold()
                for marker in ("postadress", "telefonväxel", "besöksadress")
            ):
                break
            if re.fullmatch(r"\d+(?:\s*\(\s*\d+\s*\))?", text):
                continue
            rows.append(text)
        return rows

    @staticmethod
    def detect_start(rows):
        for i, s in enumerate(rows):
            if re.match(
                r"^(?:remissinstanser?|remisslista|sändlista)\b", s.strip(), re.I
            ):
                return i + 1

        return None

    @staticmethod
    def detect_end(rows):
        for i, s in enumerate(rows):
            words = ["remiss", "remitt", "betänkande", " har "]

            if any(word in str(s).lower() for word in words) or s.casefold().startswith(
                "bilagor"
            ):
                return i

        return None

    @staticmethod
    def remove_page_numbers(rows):
        i = 0
        while i < len(rows):
            if re.match(r"[0-9]{1,2} \([0-9]{1,2}\)", rows[i]):
                del rows[i]
                i -= 1

            i += 1

        return rows

    @staticmethod
    def remove_footer_lines(rows):
        i = 0
        while i < len(rows):
            row = rows[i]
            words = [
                "telefonväxel",
                "postadress",
                "fax:",
                "besöksadress",
                "08-405",
                "webb:",
                "33 st",
            ]

            if any(word in str(row).lower() for word in words):
                del rows[i]
                i -= 1

            i += 1

        return rows

    @staticmethod
    def remove_leading_numbers(rows):
        for i in range(len(rows)):
            row = rows[i]
            if "." in row[:5]:
                num = row[: row.index(".")]
                num = num.replace("l", "1")
                num = num.replace("O", "0")
                num = num.replace(" ", "")

                row = num + row[row.index(".") :]

            row = re.sub(r"^\d{1,3}\s*[.),]", "", row)  # Remove list numbering.
            row = re.sub(r"^\d{1,3}\s", "", row)  # Remove '1 ', '2 ', '3 '...
            rows[i] = row

        return rows

    @staticmethod
    def remove_leading_spaces(rows):
        return [row.lstrip() for row in rows]

    @staticmethod
    def merge_multiline(rows):
        i = 0
        while i < len(rows):
            if i < len(rows):
                row = rows[i]
            else:
                continue

            if row:
                r = row[0]
            else:
                i += 1
                continue

            # if rows[i - 1][-1:] == ',' and row[-1:] != ',':
            #    # Trailing comma that doesn't seem to be the norm
            #    rows[i - 1] += ' ' + row
            #    del rows[i]

            if i > 0 and ")" in row and "(" not in row:
                # Unclosed parenthesis
                rows[i - 1] += " " + rows[i]
                del rows[i]
                continue

            if (
                i > 0
                and not r.isupper()  # If not capital letter
                and len(rows[i - 1]) > 60
            ):  # and the previous row is long
                if rows[i - 1].endswith("-"):
                    # Merges word split with '-'
                    rows[i - 1] = rows[i - 1][:-1] + row
                else:
                    # Merges lines cut between two words
                    rows[i - 1] += " " + row

                del rows[i]
                continue
            i += 1
        return rows

    @staticmethod
    def remove_trailing_comma(rows):
        return [row.rstrip(",") for row in rows]

    @staticmethod
    def remove_last_paragraph(rows):
        for i, s in enumerate(rows):
            if len(s.split()) >= 17:
                if (
                    "(" not in s
                    or ")" not in s
                    or len(s[s.index("(") : s.index(")")]) / len(s) < 0.5
                ):
                    return rows[:i]

        return rows
