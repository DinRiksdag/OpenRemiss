import urllib

from database.document import Document
from database.consultee import Consultee

from service.downloader import Downloader
from service.document_parser import DocumentParser
from service.database import Database
from service.file_manager import FileManager

RESET_DB = False
RESET_FILES = False

if RESET_DB:
    Database.delete_all(Consultee)
    Database.commit()
    print(f'Emptied the consultee table.\n')

saved_documents = Document.query.filter(Document.type == 'consultee_list')

for document in saved_documents:
    if not RESET_DB and document.consultee_list != []:
        print(f'Consultees for remiss {document.remiss_id} already saved.')
        continue
    elif RESET_DB:
        Consultee.query.filter(
                Consultee.consultee_list_id == document.id
                              ).delete()

    filepath = f'tmp/{document.remiss_id}/{document.id}.pdf'

    if RESET_FILES or not FileManager.filepath_exists(filepath):
        try:
            tmp_filepath = Downloader().get_file(document.files[0].url)
        except urllib.error.HTTPError:
            print(f'404: File for Remiss {document.remiss_id} not found.')

        if tmp_filepath is not None:
            FileManager.move(tmp_filepath, filepath)

    if FileManager.filepath_exists(filepath):
        f = FileManager.get_filepath(filepath)
    else:
        print('File could not be found.')
        continue

    consultee_list = DocumentParser.extract_list(filepath)

    if not consultee_list:
        print(f'Document for Remiss {document.remiss_id} was not extracted.')
        continue

    consultee_list = [Consultee(name=consultee) for consultee in consultee_list]

    document.consultee_list = consultee_list

    Database.commit()

    print(f'Saved {len(consultee_list)} organisations for remiss {document.remiss_id}')

Database.close()
