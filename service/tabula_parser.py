import subprocess
import tabula

class TabulaParser(object):

    @staticmethod
    def extract(filename, pages, area):
        try:
            return tabula.read_pdf(
                input_path = filename,
                pages = pages,
                pandas_options = {'header': None},
                area = area
            )
        except subprocess.CalledProcessError as e:
            print(f'Document {filename} was most probably not a PDF')
            return []

    @staticmethod
    def extract_header(filename):
        return TabulaParser.extract(
            filename,
            1,
            [
                [10, 300, 100, 580], # Header with document number
                [100, 20, 200, 300]  # Department and sender name
            ]
            )

    @staticmethod
    def extract_first_page(filename):
        return TabulaParser.extract(
            filename,
            1,
            [230, 70, 760, 500] # List
            )

    @staticmethod
    def extract_next_pages(filename):
        df = TabulaParser.extract(
            filename,
            'all',
            [70, 70, 760, 500] # List
            )
        return df[1:] if df else []
