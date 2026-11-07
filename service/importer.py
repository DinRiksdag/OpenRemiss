import re
from datetime import date
from urllib.parse import urljoin

from sqlalchemy.orm import selectinload

from database import Answer, ConsulteeList, Document, File, Remiss
from service.cleaner import Cleaner

ORIGINAL_URL = "https://www.regeringen.se"


def document_type(name):
    if Cleaner.is_consultee_list(name):
        return ConsulteeList
    if Cleaner.is_other_document(name):
        return Document
    return Answer


def sync_remisser(items, codes, session):
    """Refresh the feed's consultations and attachments, retaining derived data.

    The caller owns the transaction. Consultation URLs and attachment URLs are
    their identities; unchanged documents keep their IDs and extracted names.
    """
    saved = {remiss.url: remiss for remiss in session.query(Remiss).all()}
    for item in items:
        url = urljoin(ORIGINAL_URL, item["url"])
        identifier = item.get("id")
        values = {
            "title": item["title"],
            "published_on": date.fromisoformat(item["published"]),
            "issuer": codes[item["senders"][0]] if item["senders"] else None,
            "diary_number": (
                identifier.removeprefix("Diarienummer:").strip() if identifier else None
            ),
        }
        remiss = saved.get(url)
        if remiss is None:
            remiss = Remiss(url=url, **values)
            session.add(remiss)
            saved[url] = remiss
        else:
            for field, value in values.items():
                setattr(remiss, field, value)
        session.flush()

        documents = (
            session.query(Document)
            .options(selectinload(Document.files))
            .filter_by(remiss_id=remiss.id)
            .all()
        )
        by_url = {file.url: doc for doc in documents for file in doc.files}
        kept = set()
        seen_urls = set()
        for attachment in item["attachments"]:
            file_url = urljoin(ORIGINAL_URL, attachment["url"])
            if file_url in seen_urls:
                continue
            seen_urls.add(file_url)
            name = re.sub(
                r"\s*\(pdf\b[^)]*\)\s*$", "", attachment["name"], flags=re.I
            ).strip()
            kind = document_type(name)
            document = by_url.get(file_url)
            if document is None or type(document) is not kind:
                document = kind(
                    remiss_id=remiss.id, files=[File(name=name, url=file_url)]
                )
                session.add(document)
            else:
                file = next(file for file in document.files if file.url == file_url)
                if file.name != name:
                    file.name = name
                    if isinstance(document, Answer):
                        document.organisation = None
            kept.add(document)
        for document in documents:
            if document not in kept:
                session.delete(document)
    return len(items)
