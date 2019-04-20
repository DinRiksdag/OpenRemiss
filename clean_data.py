from service.database import Database
from service.cleaner import Cleaner
from database.remiss import Remiss
from database.answer import Answer
from database.document import Document
from database.consultee import Consultee

saved_remisser = Remiss.query.all()
saved_answers = Answer.query.all()

RESET_DB = False

print('II-1 Cleaning file names...')
for remiss_index, remiss in enumerate(saved_remisser, start=1):
    answers_for_remiss = Answer.query.filter_by(remiss_id=remiss.id).all()

    nb_of_remisser = len(saved_remisser)

    for answer in answers_for_remiss:
        if RESET_DB or answer.organisation is None:
            org_name = answer.files[0].name

            if len(answers_for_remiss) > 3:
                filenames = [a.files[0].name for a in answers_for_remiss]

                common = Cleaner.long_substr(filenames)

                if len(common) > 3:
                    org_name = org_name.replace(common, '')

            org_name = Cleaner.get_organisation_name(org_name)

            answer.organisation = org_name
            Database.commit()
    print(f'{remiss_index}/{nb_of_remisser} - Cleaned')

saved_lists = Document.query.filter(Document.type == 'consultee_list').all()

print('II-2 Cleaning organisation names from consultee lists...')
for document_index, consultee_list in enumerate(saved_lists, start=1):
    consultees_for_list = Consultee.query.filter_by(
                                consultee_list_id=consultee_list.id
                                                    ).all()

    nb_of_consultee_lists = len(saved_lists)

    for consultee in consultees_for_list:
        if RESET_DB or consultee.cleaned_name is None:
            org_name = consultee.name

            org_name = Cleaner.get_organisation_name(org_name)

            consultee.cleaned_name = org_name
            Database.commit()
    print(f'{document_index}/{nb_of_consultee_lists} - Cleaned')
