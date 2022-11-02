import json
import html
from bs4 import BeautifulSoup
from datetime import datetime

from database.remiss import Remiss
from database.answer import Answer
from database.consultee_list import ConsulteeList
from database.document import Document
from database.file import File

from service.cleaner import Cleaner

REGERING_URL = 'https://www.regeringen.se'


class WebParser(object):

    @staticmethod
    def get_remiss_amount(response):
        htmlData = html.unescape(response.decode('utf-8'))
        soup = BeautifulSoup(htmlData, 'html.parser')

        amount = soup.select_one('strong[class==filterHitCount]')
        return int(amount.text)

    @staticmethod
    def get_remiss_list(response):
        remisser = []

        soup = BeautifulSoup(response['Message'], 'html.parser')
        blocks = soup.select('div[class=sortcompact]')

        for block in blocks:
            link = block.select('a[href^="/remisser"]')

            if len(link) == 0:
                link = block.select('a[href^="/rapporter"]')

            if len(link) == 0:
                continue

            link = link[0]

            url = REGERING_URL + link['href']
            title = link.contents[0]
            date = datetime.strptime(
                                     block.select('time')[0]['datetime'],
                                     '%Y-%m-%d'
                                     )
            issuer = block.select('a')[-1].contents[0]

            remiss = Remiss(issuer=issuer,
                            published_on=date,
                            title=title,
                            url=url)
            remisser.append(remiss)

        remisser.reverse()
        return remisser

    @staticmethod
    def get_document_list(remiss_id, response):
        documents = []

        soup = BeautifulSoup(response, 'html.parser')
        list = soup.select('ul[class=list--Block--icons]')

        def create_document(link):
            url = REGERING_URL + link['href']
            filename = link.contents[0]
            filename = filename[:filename.find('(pdf')]

            file = File(name=filename, url=url)

            if Cleaner.is_consultee_list(filename):
                return ConsulteeList(remiss_id=remiss_id, files=[file])
            elif Cleaner.is_other_document(filename):
                return Document(remiss_id=remiss_id, files=[file])

            return Answer(remiss_id=remiss_id, files=[file])

        if len(list) == 0:
            return []
        elif len(list) == 1:
            for link in list[0].select('a'):
                document = create_document(link)
                documents.append(document)

            return documents
        else:
            for link in list[0].select('a'):
                document = create_document(link)
                documents.append(document)

            for link in list[1].select('a'):
                document = create_document(link)
                documents.append(document)

            return documents

    @staticmethod
    def get_remiss_instanser(pdf):
        instanser = []

        htmlData = html.unescape(pdf)

        soup = BeautifulSoup(htmlData, 'html.parser')

        for e in soup.findAll('br'):
            e.extract()

        remiss_instanser_div = [tag for tag in soup.findAll('div')
                                if 'Remissinstanser' in tag.text][0]
        remissvaren_span = [tag for tag in soup.findAll('span')
                            if 'Remissvaren' in tag.text][0]

        first_instans_span = remiss_instanser_div.next_sibling.contents[0]

        instans_attributes = first_instans_span.attrs

        span_list = soup.find_all(attrs=instans_attributes)

        if remissvaren_span not in span_list:
            print(f'List format is not supported (yet).')
            return

        span_list = span_list[:span_list.index(remissvaren_span)]

        for instans_span in span_list:
            organisation = Cleaner.remove_line_breaks(instans_span.contents[0])
            organisation = organisation.strip()

            instanser.append(organisation)
        return instanser
