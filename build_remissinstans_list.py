from hashlib import sha256
from pathlib import Path

from database.document import Document
from database.consultee import Consultee

from service.downloader import Downloader
from service.document_parser import DocumentParser
from service.database import Database

import sqlalchemy.exc

RESET_DB = False
RESET_FILES = False
RESET_OCR = False

if RESET_DB:
    Database.delete_all(Consultee)
    Database.commit()
    print("Emptied the consultee table.\n")

saved_documents = Document.query.filter(Document.type == "consultee_list")

for document in saved_documents:
    if not RESET_DB and document.consultee_list != []:
        print(f"Consultees for remiss {document.remiss_id} already saved.")
        continue
    elif RESET_DB:
        Consultee.query.filter(Consultee.consultee_list_id == document.id).delete()

    file_url = document.files[0].url
    filename = sha256(file_url.encode()).hexdigest() + ".pdf"
    filepath = Path("tmp") / str(document.remiss_id) / filename

    if RESET_FILES or not filepath.exists():
        Downloader.get_file(file_url, filepath)

    if not RESET_OCR:
        ocr_filepath = filepath.with_name(filepath.stem + "-ocr.pdf")

        if ocr_filepath.exists():
            print("Found an OCRed version, using it instead.")
            filepath = ocr_filepath

    consultee_list = DocumentParser.extract_list(str(filepath))

    if not consultee_list:
        print(f"Document for Remiss {document.remiss_id} was not extracted.")
        continue

    consultee_list = [Consultee(name=consultee) for consultee in consultee_list]

    document.consultee_list = consultee_list
    try:
        Database.commit()
    except sqlalchemy.exc.InterfaceError:
        print(consultee_list)

    print(f"Saved {len(consultee_list)} organisations for remiss {document.remiss_id}")

Database.close()
