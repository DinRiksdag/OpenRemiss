import json
import html
from bs4 import BeautifulSoup

from model.remiss import Remiss
from model.remiss_file import RemissFile

from service.cleaner import Cleaner

REGERING_URL = 'https://www.regeringen.se'


class Parser(object):

    def get_remiss_list(self, response):
        remisser = []

        jsonData = json.loads(response)
        htmlData = jsonData['Message']
        htmlData = html.unescape(htmlData)

        soup = BeautifulSoup(htmlData, 'html.parser')
        blocks = soup.select('div[class=sortcompact]')

        for block in blocks:
            link = block.select('a[href^=/remisser]')

            if len(link) == 0:
                break

            link = link[0]

            url = REGERING_URL + link['href']
            title = link.contents[0]
            date = block.select('time')[0]['datetime']
            sender = block.select('a')[-1].contents[0]

            remiss = Remiss(None, title, url, date, sender)
            remisser.append(remiss)
        return remisser

    def get_file_list(self, remiss_id, response):
        files = []

        htmlData = html.unescape(response)
        soup = BeautifulSoup(htmlData, 'html.parser')
        list = soup.select('ul[class=list--Block--icons]')

        def create_file(link, type):
            url = REGERING_URL + link['href']
            filename = link.contents[0]
            filename = filename[:filename.find('(pdf')]

            return RemissFile(None, remiss_id, filename, None, url, type)

        if len(list) == 0:
            return []
        elif len(list) == 1:
            for link in list[0].select('a'):
                file = create_file(link, 'answer')

                if Cleaner.is_instance(file.filename):
                    file.type = 'instance'

                files.append(file)

            return files
        else:
            for link in list[0].select('a'):
                files.append(create_file(link, 'instance'))

            for link in list[1].select('a'):
                file = create_file(link, 'answer')

                if Cleaner.is_instance(file.filename):
                    file.type = 'instance'

                files.append(file)

            return files
