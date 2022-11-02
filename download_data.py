from service.downloader import Downloader
from service.database import Database

from database.remiss import Remiss

AMOUNT = 3000
RESET_DB = False

if RESET_DB:
    Database.drop_tables()
    Database.create_tables()
    print(f'I-0 - Recreated database.\n')

downloader = Downloader()

saved_remisser = Remiss.query.all()
print(f'I-1 - Found {len(saved_remisser)} remisser in the database.\n')

print('Querying regeringen.se...')
remisser = downloader.get_last_remisser(AMOUNT)

nb_of_remisser = len(remisser)
print(f'I-2 - Found {nb_of_remisser} remisser online.\n')

for index, online_remiss in enumerate(remisser, start=1):
    found = False
    for saved_remiss in saved_remisser:
        if saved_remiss.url == online_remiss.url:
            print(
                  f'{index}/{nb_of_remisser} remiss(er) - '
                  f'Already saved (id {saved_remiss.id})'
                  )
            found = True

    if found:
        continue

    Database.add(online_remiss)
    Database.flush()

    documents = downloader.get_documents(online_remiss)

    for doc in documents:
        Database.add(doc)

    Database.commit()
    print(
          f'{index}/{nb_of_remisser} remiss(er) saved - '
          f'{len(documents)} documents(s)'
          )

Database.close()
