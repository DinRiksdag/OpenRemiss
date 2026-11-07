import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import logging
from time import monotonic

from tqdm import tqdm

from models import Consultee, Document
from service.downloader import Downloader, UnsupportedDocumentError
from service.document_parser import DocumentParser
from service.logging_config import configure_logging
from service.storage import DATA_DIR, load, save

logger = logging.getLogger(__name__)


def main(
    data_dir=DATA_DIR,
    cache_dir=DATA_DIR.parent / "tmp",
    reset=False,
    checkpoint_every=50,
    checkpoint_seconds=30,
):
    if checkpoint_every < 1 or checkpoint_seconds <= 0:
        raise ValueError("Checkpoint limits must be positive")
    documents = load(Document, data_dir)
    consultees = defaultdict(list)
    for row in load(Consultee, data_dir):
        consultees[(row.remiss_url, row.document_url)].append(row)
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
        desc="Extracting",
        unit="file",
        bar_format="{desc} |{bar:10}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]{postfix}",
        dynamic_ncols=True,
        disable=None,
    )
    progress.set_postfix(
        ok=counts["complete"], failed=counts["failed"], skip=counts["skipped"]
    )
    dirty = False
    unsaved = 0
    last_checkpoint = monotonic()

    def checkpoint():
        nonlocal dirty, unsaved, last_checkpoint
        # Save names before marking documents complete so interrupted writes are resumable.
        save(Consultee, [row for rows in consultees.values() for row in rows], data_dir)
        save(Document, documents, data_dir)
        dirty = False
        unsaved = 0
        last_checkpoint = monotonic()
        logger.info("Saved extraction checkpoint")

    try:
        for index, document in enumerate(progress, start=1):
            previous_status = document.extraction_status
            filepath = cache_dir / (sha256(document.url.encode()).hexdigest() + ".pdf")
            dirty = True
            try:
                logger.info(
                    "[%d/%d] %s (%s)",
                    index,
                    len(pending),
                    document.url,
                    "cached PDF" if filepath.exists() else "downloading PDF",
                )
                names = extract_document(document, filepath)
                if names is not None:
                    consultees[(document.remiss_url, document.url)] = names
                elif document.extraction_status in ("failed", "skipped"):
                    consultees.pop((document.remiss_url, document.url), None)
            finally:
                counts[previous_status] -= 1
                counts[document.extraction_status] += 1
                progress.set_postfix(
                    ok=counts["complete"],
                    failed=counts["failed"],
                    skip=counts["skipped"],
                    refresh=False,
                )
            unsaved += 1
            if (
                unsaved >= checkpoint_every
                or monotonic() - last_checkpoint >= checkpoint_seconds
            ):
                checkpoint()
    finally:
        progress.close()
        if dirty:
            checkpoint()

    summary = (
        f"Extraction finished: {counts['complete']} complete, "
        f"{counts['failed']} failed, {counts['skipped']} skipped; "
        f"{sum(len(rows) for rows in consultees.values())} organisation records"
    )
    logger.info(summary)
    print(summary)


def extract_document(document, filepath):
    try:
        if not filepath.exists():
            Downloader.get_file(document.url, filepath)
        names = DocumentParser.extract_list(str(filepath))
        rows = (
            [
                Consultee(
                    remiss_url=document.remiss_url, document_url=document.url, name=name
                )
                for name in names
            ]
            if names is not None
            else None
        )
    except UnsupportedDocumentError as error:
        document.extraction_status = "skipped"
        document.extraction_error = str(error)
        logger.warning("Skipping non-PDF invitation list: %s", document.url)
        return
    except Exception as error:
        document.extraction_status = "failed"
        document.extraction_error = str(error)
        logger.exception("Failed to extract invitation list: %s", document.url)
        return

    if names is None:
        document.extraction_status = "failed"
        document.extraction_error = "No invitation list could be extracted"
        logger.warning("No invitation list could be extracted: %s", document.url)
    else:
        document.extraction_status = "complete"
        document.extraction_error = None
        logger.info("Extracted %d organisations from %s", len(names), document.url)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reset", action="store_true", help="Re-extract completed lists"
    )
    args = parser.parse_args()
    configure_logging("extraction")
    main(reset=args.reset)
