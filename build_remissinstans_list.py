from collections import Counter
from hashlib import sha256
import logging

from tqdm import tqdm

from models import Consultee, Document
from service.downloader import Downloader, UnsupportedDocumentError
from service.document_parser import DocumentParser
from service.logging_config import configure_logging
from service.storage import DATA_DIR, load, save

logger = logging.getLogger(__name__)


def main(data_dir=DATA_DIR, cache_dir=DATA_DIR.parent / "tmp", reset=False):
    documents = load(Document, data_dir)
    consultees = load(Consultee, data_dir)
    invitations = [doc for doc in documents if doc.kind == "consultee_list"]
    pending = [
        doc
        for doc in invitations
        if reset or doc.extraction_status not in ("complete", "skipped")
    ]
    logger.info(
        "Processing %d invitation lists; reusing %d completed or skipped records",
        len(pending),
        len(invitations) - len(pending),
    )

    counts = Counter(doc.extraction_status for doc in invitations)
    progress = tqdm(
        pending,
        total=len(invitations),
        initial=len(invitations) - len(pending),
        desc="Invitation lists",
        unit="file",
        dynamic_ncols=True,
        disable=None,
    )
    progress.set_postfix(
        complete=counts["complete"], failed=counts["failed"], skipped=counts["skipped"]
    )
    try:
        for index, document in enumerate(progress, start=1):
            previous_status = document.extraction_status
            try:
                extract_document(
                    document,
                    documents,
                    consultees,
                    cache_dir,
                    data_dir,
                    index,
                    len(pending),
                )
            finally:
                counts[previous_status] -= 1
                counts[document.extraction_status] += 1
                progress.set_postfix(
                    complete=counts["complete"],
                    failed=counts["failed"],
                    skipped=counts["skipped"],
                    refresh=False,
                )
    finally:
        progress.close()

    summary = (
        f"Extraction finished: {counts['complete']} complete, "
        f"{counts['failed']} failed, {counts['skipped']} skipped; "
        f"{len(consultees)} organisation records"
    )
    logger.info(summary)
    print(summary)


def extract_document(
    document, documents, consultees, cache_dir, data_dir, index, total
):
    filepath = cache_dir / (sha256(document.url.encode()).hexdigest() + ".pdf")
    logger.info(
        "[%d/%d] %s (%s)",
        index,
        total,
        document.url,
        "cached PDF" if filepath.exists() else "downloading PDF",
    )
    try:
        if not filepath.exists():
            Downloader.get_file(document.url, filepath)
        names = DocumentParser.extract_list(str(filepath))
    except UnsupportedDocumentError as error:
        document.extraction_status = "skipped"
        document.extraction_error = str(error)
        logger.warning("Skipping non-PDF invitation list: %s", document.url)
        save(Document, documents, data_dir)
        return
    except Exception as error:
        document.extraction_status = "failed"
        document.extraction_error = str(error)
        save(Document, documents, data_dir)
        logger.exception("Failed to extract invitation list: %s", document.url)
        raise

    if names is None:
        document.extraction_status = "failed"
        document.extraction_error = "No invitation list could be extracted"
        logger.warning("No invitation list could be extracted: %s", document.url)
    else:
        consultees[:] = [
            row
            for row in consultees
            if (row.remiss_url, row.document_url) != (document.remiss_url, document.url)
        ]
        consultees.extend(
            Consultee(
                remiss_url=document.remiss_url, document_url=document.url, name=name
            )
            for name in names
        )
        save(Consultee, consultees, data_dir)
        document.extraction_status = "complete"
        document.extraction_error = None
        logger.info("Saved %d organisations from %s", len(names), document.url)
    save(Document, documents, data_dir)


if __name__ == "__main__":
    configure_logging("extraction")
    main()
