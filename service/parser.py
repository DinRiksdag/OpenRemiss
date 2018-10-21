import json
import html
from bs4 import BeautifulSoup

from model.remiss import Remiss
from model.remiss_file import RemissFile

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

            remiss = Remiss(url, title, date, sender)
            remisser.append(remiss)
        return remisser

    def get_file_list(self, remiss_id, response):
        files = []

        htmlData = html.unescape(response)
        soup = BeautifulSoup(htmlData, 'html.parser')
        list = soup.select('ul[class=list--Block--icons]')

        if len(list) == 0:
            return []

        list = list[0].select('a')

        for link in list:
            url = REGERING_URL + link['href']
            filename = link.contents[0]
            filename = filename[:filename.find('(pdf')]

            file = RemissFile(remiss_id, filename, url)
            files.append(file)
        return files
