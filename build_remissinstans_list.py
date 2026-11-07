from hashlib import sha256

from models import Consultee, Document
from service.downloader import Downloader
from service.document_parser import DocumentParser
from service.storage import DATA_DIR, load, save


def main(data_dir=DATA_DIR, cache_dir=DATA_DIR.parent / "tmp", reset=False):
    documents = load(Document, data_dir)
    consultees = load(Consultee, data_dir)
    for document in documents:
        if document.kind != "consultee_list":
            continue
        if document.extraction_status == "complete" and not reset:
            continue

        filepath = cache_dir / (sha256(document.url.encode()).hexdigest() + ".pdf")
        ocr_filepath = filepath.with_name(filepath.stem + "-ocr.pdf")
        try:
            if not filepath.exists():
                Downloader.get_file(document.url, filepath)
            source = ocr_filepath if ocr_filepath.exists() else filepath
            names = DocumentParser.extract_list(str(source))
        except Exception as error:
            document.extraction_status = "failed"
            document.extraction_error = str(error)
            save(Document, documents, data_dir)
            raise

        if names is None:
            document.extraction_status = "failed"
            document.extraction_error = "No invitation list could be extracted"
        else:
            consultees = [
                row
                for row in consultees
                if (row.remiss_url, row.document_url)
                != (document.remiss_url, document.url)
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
            print(f"Saved {len(names)} organisations from {document.url}")
        save(Document, documents, data_dir)


if __name__ == "__main__":
    main()
