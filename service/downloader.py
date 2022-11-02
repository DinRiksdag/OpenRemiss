import urllib

from service.selenium_driver import Selenium_Driver
from service.web_parser import WebParser

REGERING_URL = 'https://www.regeringen.se'
REGERING_QUERY_URL = REGERING_URL + '/Filter/GetFilteredItems?'

def parameters(page_size, page_number):
    params = {
            'filterType': 'Taxonomy',
            'preFilteredCategories': 2099,
            'displayLimited': 'true',
            'pageSize': page_size,
            'page': page_number,
            }
    return urllib.parse.urlencode(params)

class Downloader(object):

    def __init__(self):
        self.d = Selenium_Driver()

    def get_remiss_amount(self):
        response = self.d.get_json(REGERING_QUERY_URL + parameters(1, 1))

        return response['TotalCount']

    def get_last_remisser(self, amount):

        if amount > 1000:
            page_size = 1000
        else:
            page_size = amount

        page_amount = amount // 1000 + 1

        last_remisser = []

        for page_number in range(1, page_amount + 1):
            last_remisser.extend(self.get_remisser_for_page(page_size, page_number))

        return last_remisser

    def get_remisser_for_page(self, page_size, page_number):
        contents = self.d.get_json(REGERING_QUERY_URL + parameters(page_size, page_number))

        return WebParser.get_remiss_list(contents)

    def get_documents(self, remiss):
        contents = self.d.get(remiss.url)
        return WebParser.get_document_list(remiss.id, contents)
