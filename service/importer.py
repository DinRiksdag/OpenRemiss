import re
from urllib.parse import urljoin

from models import Consultee, Document, DocumentKind, Remiss
from service.cleaner import Cleaner
from service.storage import DATA_DIR, load, save

ORIGINAL_URL = "https://www.regeringen.se"


def document_type(name: str) -> DocumentKind:
    if Cleaner.is_consultee_list(name):
        return "consultee_list"
    if Cleaner.is_other_document(name):
        return "other"
    return "answer"


def sync_remisser(items, codes, data_dir=DATA_DIR):
    remisser = {remiss.url: remiss for remiss in load(Remiss, data_dir)}
    old_documents = {(doc.remiss_url, doc.url): doc for doc in load(Document, data_dir)}
    refreshed_urls = {urljoin(ORIGINAL_URL, item["url"]) for item in items}
    documents = {
        key: doc
        for key, doc in old_documents.items()
        if doc.remiss_url not in refreshed_urls
    }
    for item in items:
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
            name = re.sub(
                r"\s*\(pdf\b[^)]*\)\s*$", "", attachment["name"], flags=re.I
            ).strip()
            name = re.sub(r"\.pdf$", "", name, flags=re.I).strip()
            kind = document_type(name)
            document = Document(
                remiss_url=url,
                url=file_url,
                name=name,
                kind=kind,
                extraction_status="pending" if kind == "consultee_list" else None,
            )
            old = old_documents.get(key)
            if old and old.kind == kind:
                if old.name == name:
                    document.organisation = old.organisation
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
