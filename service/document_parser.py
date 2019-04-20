from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage, PDFTextExtractionNotAllowed
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams, LTTextBoxHorizontal
from pdfminer.converter import PDFPageAggregator, HTMLConverter
from io import BytesIO

from service.web_parser import WebParser
from service.cleaner import Cleaner

from database.consultee import Consultee


class DocumentParser(object):

    @staticmethod
    def get_text(file):
        elements = DocumentParser.get_elements(file)

        extracted_text = ''

        for element in elements:
            if isinstance(element, LTTextBoxHorizontal):
                extracted_text += 'new element: '
                extracted_text += element.get_text()

        return extracted_text

    @staticmethod
    def get_elements(file):
        elements = []

        for page in DocumentParser.get_pages(file):
            for element in DocumentParser.get_elements_for_page(page):
                elements.append(element)

        return elements

    @staticmethod
    def get_pages(file):
        parser = PDFParser(file)
        document = PDFDocument(parser)

        if not document.is_extractable:
            document = PDFDocument(parser, '')

        if not document.is_extractable:
            raise PDFTextExtractionNotAllowed

        return PDFPage.create_pages(document)

    @staticmethod
    def get_elements_for_page(page):
        elements = []

        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        interpreter.process_page(page)
        layout = device.get_result()
        for element in layout:
            if isinstance(element, LTTextBoxHorizontal):
                elements.append(element)

        return elements

    @staticmethod
    def get_html(file):
        rsrcmgr = PDFResourceManager()
        retstr = BytesIO()
        laparams = LAParams()
        codec = 'utf-8'
        device = HTMLConverter(rsrcmgr, retstr, codec=codec, laparams=laparams)

        interpreter = PDFPageInterpreter(rsrcmgr, device)

        for page in PDFPage.get_pages(file,
                                      set(),
                                      maxpages=0,
                                      caching=True,
                                      check_extractable=True):
            interpreter.process_page(page)

        text = retstr.getvalue().decode()
        device.close()
        retstr.close()
        return text

    @staticmethod
    def extract_list(file):
        text = DocumentParser.get_text(file)

        if len(text) == 0:
            print(f'Document is a scan, not supported yet.')
            return

        if DocumentParser.is_numbered_list(text):
            return DocumentParser.extract_numbered_list(file)
        elif DocumentParser.is_remiss_instans(text):
            return DocumentParser.extract_non_numbered_list(file)

    @staticmethod
    def extract_numbered_list(file):
        elements = DocumentParser.get_elements(file)
        text = DocumentParser.get_text(file)

        separator = ' '

        if DocumentParser.is_bullet_numbered_list(text):
            separator = '. '

        index = 1
        total = 1

        for i in range(1, 1000):
            if str(total + 1) + separator in text:
                total += 1

        consultee_list = []

        for element in elements:
            element_text = element.get_text()

            for i in range(index, total + 1):
                index_string = str(i) + separator
                if index_string not in element_text:
                    break

                index = i + 1
                organisation = element_text[element_text.find(index_string):]
                organisation = organisation[:organisation.find(' \n')]
                organisation = Cleaner.remove_leading_numbers(organisation)

                organisation = Consultee(name=organisation)

                consultee_list.append(organisation)

        return consultee_list

    @staticmethod
    def extract_non_numbered_list(file):
        pdf_html = DocumentParser.get_html(file)

        organisations = WebParser.get_remiss_instanser(pdf_html)

        if not organisations:
            return

        consultee_list = []

        for index, organisation in enumerate(organisations, start=1):
            consultee = Consultee(name=organisation)
            consultee_list.append(consultee)

        return consultee_list

    @staticmethod
    def is_remiss_instans(text):
        return 'Remissinstanser' in text

    @staticmethod
    def is_numbered_list(text):
        return DocumentParser.is_bullet_numbered_list(text) or \
               DocumentParser.is_non_bullet_numbered_list(text)

    @staticmethod
    def is_non_bullet_numbered_list(text):
        return '1 ' in text and \
               '2 ' in text and \
               '3 ' in text

    @staticmethod
    def is_bullet_numbered_list(text):
        return '1.' in text and \
               '2.' in text and \
               '3.' in text
