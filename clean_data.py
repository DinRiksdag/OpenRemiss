from service.database import Database
from service.cleaner import Cleaner
from database.answer import Answer

saved_answers = Answer.query.all()

RESET_DB = False

print('II-2 Cleaning filenames to get organisation name...')
for index, answer in enumerate(saved_answers, start=1):
    if index % (len(saved_answers) // 100) == 0:
        print(
            f'{(index + 1) * 100 // len(saved_answers)} % cleaned'
            )

    if RESET_DB or answer.organisation == None:
        organisation_name = Cleaner.get_organisation_name(answer.files[0].name)
        if organisation_name != answer.organisation:
            answer.organisation = organisation_name
            Database.commit()
