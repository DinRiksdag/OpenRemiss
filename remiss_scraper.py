
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

contents = urllib.request.urlopen(url).read()

db = Database('remisser.db')
db.drop_tables()

parser = Parser()
remisser = parser.get_remiss_list(contents)

nb_of_remisser = len(remisser)
print(f'{nb_of_remisser} remisser found.')

for remiss in remisser:
    remiss_id = db.save_remiss(remiss)

    contents = urllib.request.urlopen(remiss.url)
    contents = contents.read().decode('utf-8')

    files = parser.get_file_list(remiss_id, contents)

    for file in files:
        db.save_remiss_file(file)
        db.commit()
    print(
        f'{remiss_id}/{nb_of_remisser} remiss(er) - {len(files)} file(s) saved'
        )

db.close()
