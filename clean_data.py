from service.database import Database
from service.cleaner import Cleaner
from service.file_manager import FileManager
import service.wikidata as wikidata
from database.remiss import Remiss
from database.answer import Answer
from database.document import Document
from database.consultee import Consultee
from database.file import File
from database.consultee_list import ConsulteeList

import pandas as pd

saved_remisser = Remiss.query.all()
saved_answers = Answer.query.all()

RESET_DB = True
RESET_WIKIDATA = False
# GOV_LIST = 'tmp/government_organisations.csv'
# if RESET_WIKIDATA or FileManager.filepath_exists(GOV_LIST):
#     gov_orgs = wikidata.get_government_organisations()
#     pd.DataFrame(gov_orgs, columns=['organisation']).to_csv(GOV_LIST)

# gov_list = pd.read_csv(GOV_LIST)['organisation'].to_list()

# print(gov_list)

print('II-1 Light cleaning file names...')
for remiss_index, remiss in enumerate(saved_remisser, start=1):
    answers_for_remiss = Answer.query.filter_by(remiss_id=remiss.id).all()

    nb_of_remisser = len(saved_remisser)

    for answer in answers_for_remiss:
        org_name = answer.files[0].name

        if len(answers_for_remiss) > 3:
            filenames = [a.files[0].name for a in answers_for_remiss]

            common = Cleaner.long_substr(filenames)

            if len(common) > 3:
                org_name = org_name.replace(common, '')

        org_name = Cleaner.light_clean(org_name)

        answer.organisation = org_name
        Database.commit()
    print(f'{remiss_index}/{nb_of_remisser} - Cleaned')

print('II-1 Deep cleaning file names...')
for remiss_index, remiss in enumerate(saved_remisser, start=1):
    answers_for_remiss = Answer.query.filter_by(remiss_id=remiss.id).all()

    nb_of_remisser = len(saved_remisser)

    for answer in answers_for_remiss:
        org_name = answer.organisation

        org_name = Cleaner.deep_clean(org_name)

        answer.organisation = org_name
        Database.commit()
    print(f'{remiss_index}/{nb_of_remisser} - Cleaned')

saved_lists = Document.query.filter(Document.type == 'consultee_list').all()

print('II-2 Light cleaning organisation names from consultee lists...')
for document_index, consultee_list in enumerate(saved_lists, start=1):
    consultees_for_list = Consultee.query.filter_by(
                                consultee_list_id=consultee_list.id
                                                    ).all()

    nb_of_consultee_lists = len(saved_lists)

    for consultee in consultees_for_list:
        org_name = consultee.name

        org_name = Cleaner.light_clean(org_name)

        consultee.cleaned_name = org_name
        Database.commit()
    print(f'{document_index}/{nb_of_consultee_lists} - Cleaned')

print('II-2 Deep cleaning organisation names from consultee lists...')
for document_index, consultee_list in enumerate(saved_lists, start=1):
    consultees_for_list = Consultee.query.filter_by(
                                consultee_list_id=consultee_list.id
                                                    ).all()

    nb_of_consultee_lists = len(saved_lists)

    for consultee in consultees_for_list:
        org_name = consultee.cleaned_name

        org_name = Cleaner.deep_clean(org_name)

        consultee.cleaned_name = org_name
        Database.commit()
    print(f'{document_index}/{nb_of_consultee_lists} - Cleaned')
