from collections import Counter
import re
import unicodedata

from tqdm import tqdm

from models import Consultee, Document
from service.document_reviews import DOCUMENT_REVIEWS


class Cleaner:
    @staticmethod
    def light_clean(text):
        text = " ".join(
            unicodedata.normalize("NFKC", text)
            .replace("\xad", "")
            .replace("\u200b", "")
            .split()
        )
        text = re.sub(r"^\d{1,3}(?:\s*[.)]\s+|_+\s*|-\s+)", "", text)
        return text.strip(" \"'“”‘’_").rstrip(" ._")

    @staticmethod
    def response_name(text, known_names=()):
        text = Cleaner.light_clean(text)
        text = re.sub(r"\.(?:pdf|docx?|odt)$", "", text, flags=re.I)
        known_names = name_index(known_names)
        former_label = re.fullmatch(r"(.+?)\s+\([^)]*\bi remisslistan\)", text, re.I)
        if former_label and (canonical := canonical_name(former_label[1], known_names)):
            return canonical
        envelope = re.fullmatch(
            r"(?:[A-Z]{1,3}[-_]?)?\d{4}[-_\s]\d+[-_][A-Z0-9]+_svar_nr_\d+_(.+)",
            text,
            re.I,
        )
        if envelope:
            text = Cleaner.light_clean(envelope[1].strip(" _-"))
        indexed = re.fullmatch(r"(\d{1,3})((?:\.\d+|\s*\(\d+\))+)([\s_]+)(.+)", text)
        if indexed and (
            int(indexed[1]) >= 10
            or "_" in indexed[3]
            or canonical_name(indexed[4], known_names)
        ):
            text = indexed[4]
            if "_" in indexed[3]:
                text = re.sub(r"^SACO_", "", text, flags=re.I)
        padded = re.fullmatch(r"(0\d{1,2})(?:[a-z](?=\s))?([\s_.-]*)(.+)", text)
        if (
            padded
            and padded[3][0].isalpha()
            and (
                len(padded[1]) == 3
                or padded[2]
                or canonical_name(padded[3], known_names)
            )
        ):
            text = padded[3]
        text = re.sub(
            r"\s+\((?:utom|utanför)\s+(?:remiss)?listan\)$", "", text, flags=re.I
        )
        text = re.sub(r"\s+(?:utanf|utanför)\s+remissl\.?$", "", text, flags=re.I)
        text = re.sub(r"^utom remisslistan[_\s]+", "", text, flags=re.I)
        text = re.sub(r"^bilaga:\s*remissvaret\s+från\s+", "", text, flags=re.I)
        text = re.sub(
            r"[\s,_–—-]+(?:(?:inklusive|inkl\.?)\s*)?"
            r"(?:bilag(?:a|or)|underbilaga|remissbilaga)"
            r"(?:\s*(?:\d+(?:\.\d+)*|[a-z]))?(?:\s+till\s+remissvar)?$",
            "",
            text,
            flags=re.I,
        )
        marker = r"remiss(?:s?var|yttrande|utlåtande)?"
        suffix = re.fullmatch(
            rf"(.+?)[\s_–—-]+(?:(?:beslut\s+om|kompletterande|yttrande\s+över|svar|beslut|missiv)\s+)?{marker}(.*)",
            text,
            re.I,
        )
        if suffix:
            base = suffix[1]
            # Swedish genitives lose the final s only when the complete base
            # matches an independently observed organisation name.
            candidates = [base[:-1], base] if base.casefold().endswith("s") else [base]
            for name in candidates:
                if canonical := canonical_name(name, known_names):
                    return canonical
            if not suffix[2]:
                return base
        prefix = re.fullmatch(
            rf"(?:kompletterande\s+)?{marker}(?:\s+från)?[\s:_–—-]+(.+)", text, re.I
        )
        if prefix:
            if canonical := canonical_name(
                Cleaner.deep_clean(prefix[1], known_names), known_names
            ):
                return canonical
            # Topic and diary metadata may follow a complete organisation label.
            base = re.split(
                r"\s+(?:angående|av|över|SOU|Ds)\b|[_\s-]+(?:[A-Z]{1,3}\s?\d{4}[./_ -]|[-–—]\s)",
                prefix[1],
                maxsplit=1,
                flags=re.I,
            )[0].strip(" _-–—")
            if canonical := canonical_name(base, known_names):
                return canonical
        return text

    @staticmethod
    def deep_clean(text, popular_names):
        names = name_index(popular_names)
        # A faculty/section qualification can be removed only after a whole-name match.
        if " (" in text and text.endswith(")"):
            base, qualification = text.split(" (", 1)
            if text.count("(") == text.count(")") and re.match(
                r"förslag(?:et|en)\b", qualification, re.I
            ):
                return canonical_name(base, names) or base
            if not re.match(r"(?:tillsammans|gemensamt|och)\b", qualification, re.I):
                if canonical := canonical_name(base, names):
                    return canonical
        return canonical_name(text, names) or text

    @staticmethod
    def is_consultee_list(filename):
        return bool(
            re.search(
                r"^(?:\d+\s+)?remissbrev\b|^remiss(?:\s|[:,\-])|^inbjudan.*(?:remissmöte|att inkomma|om yttrande)",
                filename,
                re.I,
            )
        ) or any(
            marker in filename.casefold()
            for marker in [
                "remissmissiv",
                "remisslista",
                "remissinstans",
                "remissinstaner",
                "remissmissinstans",
                "remisslinstans",
                "remissminstans",
                "remissinsatnas",
                "remissintstans",
                "remissinsatser",
                "remissmisiv",
                "remissmisslista",
                "remiss av",
                "remittering av",
                "remissinbjudan",
            ]
        )

    @staticmethod
    def is_other_document(filename):
        if re.match(
            r"^(?:betänkande(?:t)?\b|SOU\s+\d{4}[:_./-]\d+\b|utkast till lagrådsremiss\b|remissdokument\b|remiss\s+förlängd remisstid\b)",
            filename.strip(),
            re.I,
        ):
            return True
        return not Cleaner.is_consultee_list(filename) and any(
            marker in filename.casefold()
            for marker in [
                "remissammanställning",
                "remissbrev",
                "promemoria",
                "remiss-pm",
                "remiss av",
                "inbjudan",
            ]
        )


def name_key(name: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", name).casefold().split())


class NameIndex:
    """Whole-name lookups built once for each cleaning pass."""

    def __init__(self, names):
        self.exact = {}
        for name in names:
            self.exact.setdefault(name_key(name), name)
        groups = {}
        for key, name in self.exact.items():
            groups.setdefault(key.replace(" ", ""), {})[key] = name
        self.compact = {
            key: next(iter(group.values()))
            for key, group in groups.items()
            if len(group) == 1
        }


def name_index(names):
    return names if isinstance(names, NameIndex) else NameIndex(names)


def canonical_name(text: str, names) -> str | None:
    index = name_index(names)
    key = name_key(text)
    return index.exact.get(key) or index.compact.get(key.replace(" ", ""))


def clean_records(documents: list[Document], consultees: list[Consultee]) -> None:
    answers = [doc for doc in documents if doc.kind == "answer"]
    for answer in tqdm(
        answers,
        desc="Cleaning response names",
        unit="name",
        disable=None,
    ):
        reviewed_name = DOCUMENT_REVIEWS.get(answer.url, {}).get("organisation")
        answer.organisation = Cleaner.light_clean(reviewed_name or answer.name)

    frequencies = Counter(doc.organisation for doc in answers)
    popular = NameIndex(name for name, _ in frequencies.most_common(250) if name)
    known = NameIndex(
        [
            name
            for name, _ in frequencies.most_common()
            if name and not re.search(r"remiss|bilag|_svar_nr_", name, re.I)
        ]
    )
    for answer in tqdm(
        answers, desc="Matching response names", unit="name", disable=None
    ):
        answer.organisation = Cleaner.deep_clean(
            Cleaner.response_name(answer.organisation, known), popular
        )
    popular = NameIndex(
        [
            name
            for name, _ in Counter(doc.organisation for doc in answers).most_common(250)
            if name
        ]
    )
    for consultee in tqdm(
        consultees, desc="Cleaning invited names", unit="name", disable=None
    ):
        consultee.cleaned_name = Cleaner.deep_clean(
            Cleaner.light_clean(consultee.name), popular
        )
