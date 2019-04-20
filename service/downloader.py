import urllib.request

from service.web_parser import WebParser


class Downloader(object):

    @staticmethod
    def get_last_remisser(amount):
        REGERING_URL = 'https://www.regeringen.se'
        REGERING_QUERY_URL = REGERING_URL + '/Filter/GetFilteredItems?'

        parameters = {
                        'filterType': 'Taxonomy',
                        'preFilteredCategories': 2099,
                        'displayLimited': 'true',
                        'pageSize': amount,
                        'page': 1,
                     }

        query_string = urllib.parse.urlencode(parameters)
        url = REGERING_QUERY_URL + query_string

        contents = Downloader.get(url)

        return WebParser.get_remiss_list(contents)

    @staticmethod
    def get_documents(remiss):
        contents = Downloader.get(remiss.url)

        return WebParser.get_document_list(remiss.id, contents)

    @staticmethod
    def get(url):
        try:
            return urllib.request.urlopen(url).read()
        except urllib.error.HTTPError as err:
            print(f'ERROR {err.code}: Could not download {url}.')
