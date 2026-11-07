import logging
import json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
import re
from statistics import median
from typing import Literal
import unicodedata

from liteparse import LiteParse
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)
DATE_PREFIX = re.compile(
    r"^\d{1,2}\s+(?:januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+\d{4}\b",
    re.I,
)
NUMBER_MARK = r"""[.)\]=:"'”’»]"""
NUMBER_TOKEN = re.compile(r"\d{1,3}(?:" + NUMBER_MARK + r"|,)*")
NUMBER_PREFIX = re.compile(
    r"^(\d{1,3})\s*(?:" + NUMBER_MARK + r"(?:\s*" + NUMBER_MARK + r")*\s*|,\s+)(.+)$"
)


class TextBox(BaseModel):
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float | None = None
    rotation: float = 0
    number_in_gutter: bool = Field(default=False, exclude=True)


class ParsedPage(BaseModel):
    height: float
    width: float = 595
    items: list[TextBox]


class ParsedDocument(BaseModel):
    version: Literal[3] = 3
    number_gaps_checked: bool = False
    text: str
    pages: list[ParsedPage]


@lru_cache(maxsize=4)
def get_parser(
    tessdata_path: Path,
    ocr_pages: str | None = None,
    rotations: tuple[tuple[int, int], ...] = (),
    high_resolution: bool = False,
) -> LiteParse:
    return LiteParse(
        ocr_enabled=ocr_pages is not None,
        target_pages=ocr_pages,
        include_complexity=ocr_pages is None,
        ocr_language="swe",
        tessdata_path=str(tessdata_path),
        num_workers=2,
        dpi=300 if rotations or high_resolution else 150,
        page_orientation_corrections=list(rotations),
        emit_word_boxes=True,
        extract_text_metadata=True,
        output_format="text",
        quiet=True,
    )


def parse_document(filename: Path, *, refresh: bool = False) -> ParsedDocument:
    cache = filename.with_suffix(".liteparse.json")
    if cache.exists() and not refresh:
        cached = json.loads(cache.read_text(encoding="utf-8"))
        if cached.get("version") == 3:
            document = ParsedDocument.model_validate(cached)
            gaps = not document.number_gaps_checked and any(
                any(i.confidence is not None for i in page.items)
                and missing_numbers(DocumentParser.page_rows(page))
                for page in document.pages
            )
            if not gaps:
                logger.info("Using cached text and coordinates: %s", cache)
                return document

    logger.info(
        "Extracting text with LiteParse (Swedish OCR when needed): %s", filename
    )
    result = get_parser(filename.parent / "tessdata").parse(filename)
    # Use LiteParse's classifications; sparse lists and embedded logos need no OCR.
    ocr_reasons = {
        "scanned",
        "garbled",
        "vector-text",
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
        sideways = []
        for page in scanned.pages:
            words = [
                word
                for item in page.text_items
                for word in (item.words or [item])
                if len(word.text) >= 4 and word.width > 0
            ]
            if words and median(word.height / word.width for word in words) > 1.5:
                sideways.append(page.page_num)
        if sideways:
            logger.info("Correcting sideways scanned pages: %s", sideways)
            candidates = []
            for angle in (90, 270):
                corrected = get_parser(
                    filename.parent / "tessdata",
                    ",".join(map(str, sideways)),
                    tuple((number, angle) for number in sideways),
                ).parse(filename)
                candidates.extend(corrected.pages)

            def confidence(page):
                words = [
                    item for item in page.text_items if item.confidence is not None
                ]
                return sum(item.confidence * len(item.text) for item in words) / max(
                    sum(len(item.text) for item in words), 1
                )

            for number in sideways:
                best = max(
                    (page for page in candidates if page.page_num == number),
                    key=confidence,
                )
                scanned.pages = [
                    best if page.page_num == number else page for page in scanned.pages
                ]
        replacements = {page.page_num: page for page in scanned.pages}
        # Retry only a scan with a short, completely missing run of numbered rows.
        # A missing label with a readable name does not trigger another OCR pass.
        for number, page in list(replacements.items()):
            gaps = missing_numbers(page.text.splitlines())
            if gaps and number not in sideways:
                logger.info(
                    "Checking missing list numbers %s at 300 DPI on page %d",
                    sorted(gaps),
                    number,
                )
                higher = (
                    get_parser(
                        filename.parent / "tessdata", str(number), high_resolution=True
                    )
                    .parse(filename)
                    .pages[0]
                )
                if len(missing_numbers(higher.text.splitlines())) < len(gaps):
                    replacements[number] = higher
        result.pages = [replacements.get(page.page_num, page) for page in result.pages]
    document = ParsedDocument(
        number_gaps_checked=True,
        text="\n\n".join(page.text for page in result.pages),
        pages=[
            ParsedPage(
                height=page.height,
                width=getattr(page, "width", 595),
                items=[
                    TextBox(
                        text=word.text,
                        x=word.x,
                        y=word.y,
                        width=word.width,
                        height=word.height,
                        confidence=getattr(item, "confidence", None),
                        rotation=getattr(item, "rotation", 0),
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


def missing_numbers(rows: list[str]) -> set[int]:
    rows = [row.strip() for row in rows if row.strip() and not row.strip().isdecimal()]
    missing = set()
    for before, after in zip(rows, rows[1:]):
        left, right = DocumentParser.numbered(before), DocumentParser.numbered(after)
        if left and right and 1 < right[0] - left[0] <= 4:
            missing.update(range(left[0] + 1, right[0]))
    return missing


class DocumentParser:
    @staticmethod
    def extract_list(filename, *, refresh=False):
        document = (
            parse_document(Path(filename), refresh=True)
            if refresh
            else parse_document(Path(filename))
        )
        pages = [DocumentParser.page_lines(page) for page in document.pages]
        numbered_lines = [
            line
            for rows in pages
            for line in rows
            if DocumentParser.numbered(line.text)
        ]
        if len(numbered_lines) >= 4:
            cluster = Counter(
                round(line.x / 5) * 5 for line in numbered_lines
            ).most_common(1)[0][0]
            gutter = cluster + median(line.height for line in numbered_lines) * 1.6
            pages = [
                DocumentParser.page_lines(
                    page,
                    gutter
                    if any(item.confidence is not None for item in page.items)
                    else None,
                )
                for page in document.pages
            ]
        lines = [(page, line) for page, rows in enumerate(pages) for line in rows]
        all_rows = [line.text for _, line in lines]
        start = DocumentParser.detect_start(all_rows)
        if start is None:
            # Some consultation letters put names directly below a wrapped title.
            for index, (page, line) in enumerate(lines):
                draft_title = re.match(r"^Utkast till lagrådsremiss\b", line.text, re.I)
                following_numbers = [
                    number[0]
                    for row in all_rows[index + 1 : index + 22]
                    if (number := DocumentParser.numbered(row))
                ]
                numbered_draft = draft_title and any(
                    b == a + 1 and c == b + 1
                    for a, b, c in zip(
                        following_numbers, following_numbers[1:], following_numbers[2:]
                    )
                )
                if (
                    re.match(r"^(?:Remiss av|Remittering av)\b", line.text, re.I)
                    or numbered_draft
                ):
                    for i in range(index + 1, min(index + 8, len(lines))):
                        previous_page, previous = lines[i - 1]
                        next_page, following = lines[i]
                        if next_page != page or previous_page != page:
                            break
                        if following.y - previous.y > previous.height * 1.8:
                            candidate = all_rows[i : i + 3]
                            if len(candidate) == 3 and all(
                                not DocumentParser.is_prose(row)
                                and not re.search(
                                    r"\b(?:betänkandet|remissen|synpunkter)\b",
                                    row,
                                    re.I,
                                )
                                for row in candidate
                            ):
                                start = i
                            break
                    if start is not None:
                        break
        if start is None:
            logger.info("No invitation list heading found: %s", filename)
            return

        selected = lines[start:]
        if selected and re.fullmatch(r"\d{4}\s*[-–]\s*\d{4}", selected[0][1].text):
            selected = selected[1:]
        first = next(
            (
                i
                for i, (_, line) in enumerate(selected[:10])
                if DocumentParser.numbered(line.text)
            ),
            None,
        )
        if (
            first is not None
            and DocumentParser.numbered(selected[first][1].text)[0] == 1
        ):
            selected = selected[first:]
        names = []
        positions = defaultdict(list)
        for page, line in selected:
            if DocumentParser.numbered(line.text):
                positions[page].append(line.x)
        number_margins = {}
        for page, xs in positions.items():
            cluster = Counter(round(x / 5) * 5 for x in xs).most_common(1)[0][0]
            number_margins[page] = median(x for x in xs if abs(x - cluster) <= 5)

        numbering_active = True

        def line_number(page, line):
            # Numbers inside an indented qualification are part of the name.
            # Right-aligned one-digit labels start farther right than three-digit
            # labels; allow that width without accepting indented qualifications.
            if not numbering_active or (
                not line.number_in_gutter
                and line.x > number_margins.get(page, line.x) + 15
            ):
                return None
            return DocumentParser.numbered(line.text)

        # A scan can lose a run of list numbers while retaining the names.
        # Infer those boundaries only when the surrounding sequence accounts
        # for every intervening row (not when a name merely wraps).
        markers = [
            (i, number[0])
            for i, (page, line) in enumerate(selected)
            if (number := line_number(page, line))
        ]
        numbering_active = (
            any(
                line.number_in_gutter and DocumentParser.numbered(line.text)
                for _, line in selected
            )
            or any(
                after == before + 1
                for (_, before), (_, after) in zip(markers, markers[1:])
            )
            or sum(bool(NUMBER_PREFIX.match(selected[i][1].text)) for i, _ in markers)
            >= 2
            or (
                len(markers) == 1
                and bool(NUMBER_PREFIX.match(selected[markers[0][0]][1].text))
            )
        )
        if not numbering_active:
            markers = []
        inferred = {}
        for (_, before), (index, current), (_, after) in zip(
            markers, markers[1:], markers[2:]
        ):
            if after == before + 2 and current != before + 1:
                inferred[index] = before + 1
        for (left, first_number), (right, next_number) in zip(markers, markers[1:]):
            between = selected[left + 1 : right]
            if (
                len(between) == next_number - first_number - 1
                and between
                and all(
                    line.text[0].isupper() and not DocumentParser.is_prose(line.text)
                    for _, line in between
                )
            ):
                inferred.update(
                    {
                        left + offset: first_number + offset
                        for offset in range(1, right - left)
                    }
                )
        last_number = 0
        previous = None
        previous_page = None
        in_introduction = False
        for index, (page, line) in enumerate(selected):
            row = DocumentParser.strip_markers(line.text)
            if not row or (
                NUMBER_TOKEN.fullmatch(row)
                and not (names and names[-1].count("(") > names[-1].count(")"))
            ):
                continue
            if re.match(r"^\d{1,2}[.:]\d{2}\b", row) and DocumentParser.is_prose(row):
                break
            if DocumentParser.is_furniture(row):
                continue
            if re.match(r"^Följande (?:myndigheter|bereds)\b", row):
                # Introductions between sections of a numbered recipient list.
                previous = None
                in_introduction = True
                continue
            numbered = line_number(page, line)
            if index in inferred:
                value = numbered[1] if numbered else row
                split_digit = re.match(r"^(\d)\s+(.+)$", value)
                if (
                    numbered
                    and split_digit
                    and int(str(numbered[0]) + split_digit[1]) == inferred[index]
                ):
                    value = split_digit[2]
                numbered = inferred[index], value
            if numbered:
                in_introduction = False
                number, row = numbered
                following_numbers = [n for marker, n in markers if marker > index][:3]
                if (
                    not last_number
                    and names
                    and following_numbers
                    and number > following_numbers[0]
                    and number > len(names) + 3
                ):
                    number = len(names) + 1
                if (
                    last_number
                    and number > last_number + 3
                    and any(
                        last_number < n <= last_number + 3 for n in following_numbers
                    )
                ):
                    number = last_number + 1
                if number <= last_number:
                    following = next(iter(following_numbers), None)
                    if following is not None and following > last_number:
                        # OCR can truncate several successive two-digit labels.
                        number = last_number + 1
                    else:
                        break
                last_number = number
                row = DocumentParser.strip_markers(row)
            elif in_introduction:
                continue
            elif DocumentParser.detect_end([row]) is not None:
                break
            elif DocumentParser.is_prose(row) and not (
                names and names[-1].count("(") > names[-1].count(")")
            ):
                break
            bullet = re.match(r"^[•●▪◦]\s*", row)
            if bullet:
                row = row[bullet.end() :]
            if not row:
                continue
            continuation = False
            if names and not numbered and not bullet:
                close = (
                    previous is not None
                    and previous_page == page
                    and line.y - previous.y < max(line.height, previous.height) * 1.7
                )
                continuation = (
                    row.startswith("(")
                    or (
                        names[-1].count("(") > names[-1].count(")")
                        and (
                            previous_page != page
                            or (
                                previous is not None
                                and line.y - previous.y
                                < max(line.height, previous.height) * 2.5
                                and (
                                    row[0].islower()
                                    or row.count(")") > row.count("(")
                                    or line.x > previous.x + 5
                                )
                            )
                        )
                    )
                    or (
                        close
                        and (
                            names[-1].count("(") > names[-1].count(")")
                            or (previous is not None and line.x > previous.x + 5)
                            or (
                                row[0].islower()
                                and (
                                    bool(last_number)
                                    or len(names[-1]) > 50
                                    or re.search(
                                        r"(?:\b(?:och|för|av|i|med)|-)\s*$", names[-1]
                                    )
                                )
                            )
                        )
                    )
                )
            if continuation:
                combined = DocumentParser.join_name(names[-1], row)
                if combined.count("(") <= combined.count(
                    ")"
                ) and DocumentParser.is_prose(combined):
                    names.pop()
                    break
                names[-1] = combined
            else:
                names.append(row)
            previous, previous_page = line, page
        return [name.rstrip(",").strip() for name in names if name.strip()] or None

    @staticmethod
    def numbered(row):
        if DATE_PREFIX.match(row):
            return None
        split = re.match(r"^(\d{1,2})\s*[.:]\s*(\d)[.)]\s+(.+)$", row)
        if split:
            return int(split[1] + split[2]), split[3]
        split = re.match(r"^((?:\d\s*){2,3})[.)]\s*(.+)$", row)
        if split:
            return int(split[1].replace(" ", "")), split[2]
        match = NUMBER_PREFIX.match(row) or re.match(
            r"^(\d{1,3})(?:\s+|(?=[A-ZÅÄÖ]))(.+)$", row
        )
        if match:
            return int(match[1]), match[2]
        return None

    @staticmethod
    def strip_markers(row):
        # Preserve real names such as .SE and 1,6 miljonerklubben.
        row = re.sub(
            r"^(?:[•●▪◦*+&=<>–—-]+\s*|\.+\s+|\.(?=[A-ZÅÄÖ][a-zåäö])|[\"'“”‘’]+\s*|\([=<>]\s*)+",
            "",
            row,
        ).strip()
        return row if any(char.isalnum() for char in row) else ""

    @staticmethod
    def join_name(previous, following):
        if (
            previous.endswith("-")
            and following[0].islower()
            and not re.match(r"^(?:och|eller)\b", following)
        ):
            return previous[:-1] + following
        return previous + " " + following

    @staticmethod
    def is_prose(row):
        return (
            bool(DATE_PREFIX.match(row))
            or bool(
                re.match(
                    r"^(?:EU-kommissionen|Europeiska kommissionen)\s+har\b", row, re.I
                )
            )
            or bool(
                re.match(
                    r"^(?:Promemorian|Rapporten|Förslaget|Betänkandet)\b.*\b(?:remitterades|skickas?|översänds)\b",
                    row,
                    re.I,
                )
            )
            or bool(
                row[:1].isupper()
                and re.search(r"\bremitteras härmed till\b", row, re.I)
            )
            or bool(
                re.search(
                    r"\b(?:ska ha kommit|skickas till|presenterade den|lämna synpunkter|kan laddas|Detta utskick|hemställan och förteckning|Bifogat finner ni|har (?:utarbetat|presenterat|antagit|överlämnat)|önskar ta del|överlämnade den|antog.*förslag|remissmöte[nt]?|Mer information om förslaget|I propositionen)\b|^\d{4}\s+antog\b|^Den\s+\d+\s+\w+\s+\d{4}\b|^I\s+(?:januari|februari|mars|april|maj|juni|juli|augusti|september|oktober|november|december)\s+\d{4}\b",
                    row,
                    re.I,
                )
            )
            or len(re.sub(r"\([^()]*\)", "", row).split()) >= 17
        )

    @staticmethod
    def is_furniture(row):
        return bool(
            re.fullmatch(
                r"\d+(?:\s*\(\s*\d+\s*\))?|\d+\s+bilag(?:a|or)|\d{4}\s*\.?|Remiss|Regeringskansliet",
                row,
                re.I,
            )
        ) or bool(
            re.match(
                r"^(?:Ärendenummer|Motpartens ärendenummer|Dokumentdatum|Konfidentialitetsnivå|TMALL|TRV\s+\d+|LI\d{4}/|Trafikverket Texttelefon|\d{4}-\d\d-\d\d|\d{3}\s*\d\d\s+Stockholm)\b",
                row,
            )
        )

    @staticmethod
    def page_rows(page: ParsedPage) -> list[str]:
        return [line.text for line in DocumentParser.page_lines(page)]

    @staticmethod
    def page_lines(
        page: ParsedPage, default_gutter: float | None = None
    ) -> list[TextBox]:
        items = [
            item
            for item in page.items
            if item.text.strip()
            and item.height > 0
            and min(item.rotation % 360, 360 - item.rotation % 360) < 10
        ]
        if not items:
            return []
        typical_height = median(item.height for item in items)
        # OCR sometimes reads a vertical stack of list numbers as one tall word.
        items = [
            item
            for item in items
            if not (item.height > typical_height * 2.5 and item.width < item.height / 2)
        ]
        tolerance = median(item.height for item in items) * 0.45

        def group_items(items):
            lines: list[tuple[float, list[TextBox]]] = []
            for item in sorted(
                items, key=lambda item: (item.y + item.height / 2, item.x)
            ):
                center = item.y + item.height / 2
                if lines and abs(center - lines[-1][0]) <= tolerance:
                    lines[-1][1].append(item)
                elif (
                    lines
                    and len(lines[-1][1]) == 1
                    and NUMBER_TOKEN.fullmatch(lines[-1][1][0].text)
                    and item.x > lines[-1][1][0].x + lines[-1][1][0].width
                    and min(
                        item.y + item.height, lines[-1][1][0].y + lines[-1][1][0].height
                    )
                    - max(item.y, lines[-1][1][0].y)
                    > min(item.height, lines[-1][1][0].height) * 0.5
                ):
                    # OCR can give a number a taller, slightly higher box than its name.
                    lines[-1] = (center, [*lines[-1][1], item])
                else:
                    lines.append((center, [item]))
            return lines

        lines = group_items(items)
        footer_terms = (
            "postadress",
            "telefonväxel",
            "besöksadress",
            "texttelefon:",
            "e-post:",
            "e-post,",
            "dokumentegenskaper",
        )
        footer_y = next(
            (
                center
                for center, line in lines
                if center > page.height * 0.65
                and (
                    any(
                        term in " ".join(item.text for item in line).casefold()
                        for term in footer_terms
                    )
                    or re.search(
                        r"\bE[- ]?post\b", " ".join(item.text for item in line), re.I
                    )
                )
            ),
            page.height,
        )
        # Find footers before cropping the number column: its labels may be to
        # the left of the list and would otherwise disappear from the check.
        items = [item for item in items if item.y + item.height / 2 < footer_y]
        lines = [(center, line) for center, line in lines if center < footer_y]
        rows = []
        number_positions = []
        for _, line in lines:
            ordered = sorted(line, key=lambda item: item.x)
            if len(ordered) > 1 and NUMBER_TOKEN.fullmatch(ordered[0].text):
                number_positions.append((ordered[0].x, ordered[1].x))
        gutter = default_gutter
        if number_positions:
            # A damaged number column can contain letters instead of digits.
            # Anchor it to a readable number and repeated name-column alignment.
            for number_x, name_x in number_positions:
                aligned_prefixes = sum(
                    len(ordered) > 1
                    and len(ordered[0].text) <= 3
                    and abs(ordered[0].x - number_x) < 20
                    and ordered[0].x < name_x - 5
                    and any(abs(item.x - name_x) < 5 for item in ordered[1:])
                    for _, line in lines
                    if (ordered := sorted(line, key=lambda item: item.x))
                )
                if aligned_prefixes >= 4:
                    gutter = name_x - 2
                    break
        if len(number_positions) >= 4:
            number_x = median(x for x, _ in number_positions)
            aligned = [
                (x, following)
                for x, following in number_positions
                if abs(x - number_x) < 5
            ]
            if len(aligned) >= 4:
                gutter = median(following for _, following in aligned) - 2
        if gutter is None and any(
            re.fullmatch(r"Remissinstanser\s*:?", " ".join(i.text for i in line), re.I)
            for _, line in lines
        ):
            # Some scans lose every digit. Require several distinct, very narrow
            # labels aligned before the same name column, including a nonword mark.
            prefixes = []
            for _, line in lines:
                words = sorted(line, key=lambda item: item.x)
                if (
                    len(words) > 1
                    and len(words[0].text) <= 3
                    and words[1].x - (words[0].x + words[0].width) > 5
                    and words[0].width
                    < words[1].width / max(len(words[1].text), 1) * 1.8
                ):
                    prefixes.append((words[0], words[1]))
            for _, anchor in prefixes:
                aligned = [(a, b) for a, b in prefixes if abs(b.x - anchor.x) < 5]
                if (
                    len(aligned) >= 4
                    and len({a.text for a, _ in aligned}) >= 3
                    and any(re.fullmatch(r"[><=–—-]+", a.text) for a, _ in aligned)
                ):
                    gutter = median(b.x for _, b in aligned) - 2
                    break
        if gutter is not None:
            # Number-column noise must not determine the name rows' baselines.
            lines = group_items(
                [
                    item
                    for item in items
                    if item.x + item.width >= gutter
                    or NUMBER_TOKEN.fullmatch(item.text)
                ]
            )
        for center, line in lines:
            ordered = sorted(line, key=lambda item: item.x)
            if not ordered:
                continue
            text = ordered[0].text.strip()
            for previous, item in zip(ordered, ordered[1:]):
                gap = item.x - (previous.x + previous.width)
                character_width = min(
                    previous.width / max(len(previous.text), 1),
                    item.width / max(len(item.text), 1),
                )
                # Hidden OCR layers can insert spaces inside a visually solid word.
                joined = (
                    previous.confidence is None
                    and item.confidence is None
                    and previous.text[-1:].isalpha()
                    and item.text[:1].islower()
                    and gap < character_width * 0.15
                )
                text += ("" if joined else " ") + item.text.strip()
            if re.fullmatch(r"\d+(?:\s*\(\s*\d+\s*\))?", text):
                continue
            rows.append(
                TextBox(
                    text=" ".join(
                        unicodedata.normalize("NFKC", text)
                        .replace("\xad", "")
                        .replace("\u200b", "")
                        .split()
                    ),
                    x=min(i.x for i in ordered),
                    y=min(i.y for i in ordered),
                    width=max(i.x + i.width for i in ordered)
                    - min(i.x for i in ordered),
                    height=median(i.height for i in ordered),
                    number_in_gutter=(
                        gutter is not None
                        and len(ordered) > 1
                        and bool(NUMBER_TOKEN.fullmatch(ordered[0].text))
                        and ordered[0].x + ordered[0].width < gutter
                    ),
                )
            )
        return rows

    @staticmethod
    def detect_start(rows):
        heading = r"(?:rem\s*iss\s*instans(?:er)?|remisslista|sändlista)"
        for i, s in enumerate(rows):
            if re.fullmatch(heading + r"(?:\s*\([^)]*\))?\s*:? *", s.strip(), re.I):
                return i + 1
        for i, s in enumerate(rows):
            if re.fullmatch(
                r"Instanser som inbjuds att yttra sig\s*:?", s.strip(), re.I
            ):
                return i + 1
            if (
                re.match(r"^" + heading + r"\s+\w", s.strip(), re.I)
                and "enligt sändlista" not in s.casefold()
                and not re.search(r"\b(?:innebär|ombeds|ska)\b", s, re.I)
            ):
                return i + 1
            if re.match(
                r"^(?:Bilaga\s*\d*\s+)?Organisationer som fått frågorna", s, re.I
            ):
                return i + 1

        # A numbered invitation can follow the consultation title without a heading.
        for i, row in enumerate(rows):
            number = DocumentParser.numbered(row)
            if (
                number
                and number[0] == 1
                and any(
                    re.match(
                        r"^(?:Remiss(?:missiv)?|Remittering|Berörda för remiss)\b", s
                    )
                    for s in rows[:i]
                )
            ):
                numbers = [
                    n[0] for s in rows[i : i + 12] if (n := DocumentParser.numbered(s))
                ]
                if numbers[:3] == [1, 2, 3]:
                    return i

        return None

    @staticmethod
    def detect_end(rows):
        for i, s in enumerate(rows):
            if re.match(
                r"^(?:Remissvar(?:en|et)?\b|Remissinstanserna\b|(?:I )?remissen (?:ligger|avser|innehåller)\b|Regeringskansliets webbplats\b|Regeringskansliet önskar\b|Bakgrund\b|Sammanfattning\b|Bilag(?:a|or)\b|Kopia till\b|Svaren\b|Svaret\b|Råd om\b|(?:För )?andra remissinstanser\b|Betänkandet kan\b|Dokumentegenskaper\b|https?://|www\.)",
                s,
                re.I,
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
