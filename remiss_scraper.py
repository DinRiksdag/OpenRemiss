
#
#   RemissScraper, scrapes Regeringen.se for remisser
#   Copyright (C) 2018 DinRiksdag
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published
#   by the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program. If not, see <http://www.gnu.org/licenses/>.
#


# Notice, only runs on Python 3.6 or newer

import urllib.request

from service.cleaner import Cleaner
from service.database import Database
from service.parser import Parser


AMOUNT = 1000
REGERING_URL = 'https://www.regeringen.se'
REGERING_QUERY_URL = REGERING_URL + '/Filter/GetFilteredItems?'

parameters = {
                'filterType': 'Taxonomy',
                'preFilteredCategories': 2099,
                'displayLimited': 'true',
                'pageSize': AMOUNT,
                'page': 1,
             }

query_string = urllib.parse.urlencode(parameters)
url = REGERING_QUERY_URL + query_string

db = Database('remisser.db')

# db.drop_tables()
# db.create_tables()

saved_remisser = db.get_all_remisser()
nb_of_saved_remisser = len(saved_remisser)
print(f'Found {nb_of_saved_remisser} remisser in the database.')

print('Querying regeringen.se...')
contents = urllib.request.urlopen(url).read()

parser = Parser()

remisser = parser.get_remiss_list(contents)
nb_of_remisser = len(remisser)
print(f'Found {nb_of_remisser} remisser online.\n')

for index, remiss in enumerate(remisser, start=1):
    found = False
    for saved_remiss in saved_remisser:
        if saved_remiss.url == remiss.url:
            print(f'{index}/{nb_of_remisser} remiss(er) - Already saved')
            found = True

    if found:
        continue

    remiss_id = db.save_remiss(remiss)

    contents = urllib.request.urlopen(remiss.url)
    contents = contents.read().decode('utf-8')

    files = parser.get_file_list(remiss_id, contents)

    for file in files:
        db.save_remiss_file(file)
        db.commit()
    print(
        f'{index}/{nb_of_remisser} remiss(er) - {len(files)} file(s) saved'
        )

saved_files = db.get_all_remiss_answers()

print('Cleaning filenames to get organisation name...')
for index, file in enumerate(saved_files, start=1):
    if index % (len(saved_files) // 100) == 0:
        print(
            f'{(index + 1) * 100 // len(saved_files)} % cleaned'
            )
    organisation_name = Cleaner.get_organisation_name(file.filename)
    if organisation_name != file.organisation:
        file.organisation = organisation_name
        db.update_remiss_file(file, file.id)
        db.commit()

db.close()
