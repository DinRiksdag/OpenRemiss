import urllib.request
import os

from pdfminer.pdfpage import PDFTextExtractionNotAllowed
from pdfminer.pdfparser import PDFSyntaxError

from database.file import File
from database.document import Document
from database.consultee_list import ConsulteeList
from database.consultee import Consultee
from database.answer import Answer
from database.remiss import Remiss

from service.downloader import Downloader
from service.document_parser import DocumentParser
from service.database import Database
from service.file_manager import FileManager
from io import BytesIO

RESET_DB = False
RESET_FILES = False

if RESET_DB:
    Database.delete_all(Consultee)
    Database.commit()
    print(f'Emptied the consultee table.\n')

saved_consultee_lists = ConsulteeList.query.all()
saved_consultees = Consultee.query.all()
saved_remisser = Remiss.query.all()
saved_documents = Document.query.filter(Document.type == 'consultee_list')

nb_of_consultees = len(saved_consultees)
print(f'Found {nb_of_consultees} consultees in the database.')

for document in saved_documents:

    if not RESET_DB and document.consultee_list != []:
        print(f'Consultees for remiss {document.remiss_id} already in database.')
        continue
    elif RESET_DB:
        Consultee.query.filter(Consultee.consultee_list_id == document.id).delete()

    filepath = f'tmp/{document.remiss_id}/{document.id}.pdf'

    if RESET_FILES or not FileManager.filepath_exists(filepath):
        try:
            f = Downloader.get(document.files[0].url)
        except urllib.error.HTTPError:
            print(f'404: Remissinstans {document.remiss_id} not found.')

        if f is not None:
            fp = BytesIO(f)
            FileManager.write_to_filepath(filepath, f)

    if FileManager.filepath_exists(filepath):
        fp = FileManager.get_filepath(filepath)
    else:
        continue

    try:
        list = DocumentParser.extract_list(fp)
    except (PDFTextExtractionNotAllowed, PDFSyntaxError):
        print(f'Document {document.remiss_id} could not be extracted.')
        continue

    if not list:
        print(f'Document {document.remiss_id} could not be extracted.')
        continue

    document.consultee_list = list

    Database.commit()

    print(f'Saved {len(list)} organisations for remiss {document.remiss_id}')

    fp.close()

Database.close()
