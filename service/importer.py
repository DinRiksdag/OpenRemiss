import logging
import re
from urllib.parse import urljoin

from tqdm import tqdm

from models import Consultee, Document, DocumentKind, Remiss
from service.cleaner import Cleaner
from service.document_reviews import DOCUMENT_REVIEWS
from service.storage import DATA_DIR, load, save

ORIGINAL_URL = "https://www.regeringen.se"
logger = logging.getLogger(__name__)


def document_type(name: str) -> DocumentKind:
    if re.match(r"^remissvar\b", name, re.I) or re.search(r"_svar_nr_\d+_", name, re.I):
        return "answer"
    if re.search(r"\b(?:utom|utanför)\s+remisslistan\b", name.replace("_", " "), re.I):
        return "answer"
    # Notes on response labels can mention the original invitation list.
    label = re.sub(r"\([^)]*\)", "", name).casefold()
    if re.search(
        r"\bbilaga till remissmissiv\b|\bremissinstanser som avstå(?:tt|r)\b", label
    ):
        return "other"
    if Cleaner.is_other_document(label):
        return "other"
    if Cleaner.is_consultee_list(label):
        return "consultee_list"
    return "answer"


def sync_remisser(items, codes, data_dir=DATA_DIR, *, include_source_exceptions=False):
    remisser = {remiss.url: remiss for remiss in load(Remiss, data_dir)}
    old_documents = {(doc.remiss_url, doc.url): doc for doc in load(Document, data_dir)}
    refreshed_urls = {urljoin(ORIGINAL_URL, item["url"]) for item in items}
    documents = {
        key: doc
        for key, doc in old_documents.items()
        if doc.remiss_url not in refreshed_urls
    }
    for item in tqdm(
        items, desc="Importing consultations", unit="consultation", disable=None
    ):
        url = urljoin(ORIGINAL_URL, item["url"])
        identifier = item.get("id")
        remisser[url] = Remiss(
            url=url,
            title=item["title"],
            published_on=item["published"],
            issuer=codes[item["senders"][0]] if item["senders"] else None,
            diary_number=identifier.removeprefix("Diarienummer:").strip()
            if identifier
            else None,
        )
        for attachment in item["attachments"]:
            file_url = urljoin(ORIGINAL_URL, attachment["url"])
            key = (url, file_url)
            if key in documents:
                continue
            review = DOCUMENT_REVIEWS.get(file_url)
            if (
                review
                and review.get("exclude_by_default", False)
                and not include_source_exceptions
            ):
                logger.warning(
                    "Skipping source naming exception: %s: %s",
                    file_url,
                    review["reason"],
                )
                continue
            name = re.sub(
                r"\s*\(pdf\b[^)]*\)\s*$", "", attachment["name"], flags=re.I
            ).strip()
            name = re.sub(r"\.pdf$", "", name, flags=re.I).strip()
            kind = review["kind"] if review else document_type(name)
            document = Document(
                remiss_url=url,
                url=file_url,
                name=name,
                kind=kind,
                organisation=review.get("organisation") if review else None,
                extraction_status="pending" if kind == "consultee_list" else None,
            )
            old = old_documents.get(key)
            if old and old.kind == kind:
                if old.name == name:
                    document.organisation = document.organisation or old.organisation
                document.extraction_status = old.extraction_status
                document.extraction_error = old.extraction_error
            documents[key] = document

    invitation_keys = {
        key for key, doc in documents.items() if doc.kind == "consultee_list"
    }
    consultees = [
        row
        for row in load(Consultee, data_dir)
        if (row.remiss_url, row.document_url) in invitation_keys
    ]
    save(Consultee, consultees, data_dir)
    save(Document, list(documents.values()), data_dir)
    save(Remiss, list(remisser.values()), data_dir)
    return len(items)
