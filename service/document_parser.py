import re

import pandas as pd
from pikepdf import Pdf

from service.ocr import OCR
from service.tabula_parser import TabulaParser


class DocumentParser(object):

    @staticmethod
    def extract_list(filename):
        first_page = TabulaParser.extract_first_page(filename)
        next_pages = TabulaParser.extract_next_pages(filename)

        if first_page is None and next_pages is None:
            return

        all_pages = first_page + next_pages

        if (DocumentParser.has_scanned_pages(filename, all_pages)
        and '-ocr.pdf' not in filename):
            print('Document is at least partly a scan, attempting ocr...')
            filename = OCR.ocr(filename)

            return DocumentParser.extract_list(filename)

        all_rows = DocumentParser.pick_right_columns(all_pages)
        all_rows = all_rows.tolist()

        start = DocumentParser.detect_start(all_rows)

        if not start:
            print('Document is most likely not a remissinstans.')

            if '-ocr.pdf' not in filename:
                print('Attempting a scan in case it fixes an issue...')
                filename = OCR.ocr(filename)

                return DocumentParser.extract_list(filename)

            return

        consultee_list = all_rows[start:]

        end = DocumentParser.detect_end(consultee_list)

        if end:
            consultee_list = consultee_list[:end]

        consultee_list = DocumentParser.remove_page_numbers(consultee_list)
        consultee_list = DocumentParser.remove_footer_lines(consultee_list)
        consultee_list = DocumentParser.remove_leading_numbers(consultee_list)
        consultee_list = DocumentParser.remove_leading_spaces(consultee_list)
        consultee_list = DocumentParser.merge_multiline(consultee_list)
        consultee_list = DocumentParser.remove_trailing_comma(consultee_list)
        consultee_list = DocumentParser.remove_last_paragraph(consultee_list)

        return consultee_list

    @staticmethod
    def has_scanned_pages(filename, all_pages):
        return all_pages and len(all_pages) < len(Pdf.open(filename).pages)

    @staticmethod
    def pick_right_columns(df_list):
        all_rows = pd.Series(dtype=pd.StringDtype())

        for df in df_list:
            right_column = df[df.columns[0]]

            len_right_column = right_column.astype(str).str.len().sum()

            for i in range(1, len(df.columns)):
                column = df[df.columns[i]]
                len_column = column.astype(str).str.len().sum()

                if len_column > len_right_column:
                    len_right_column = len_column
                    right_column = column

            all_rows= pd.concat([all_rows, right_column])

        return all_rows.dropna()

    @staticmethod
    def detect_start(rows):
        for i, s in enumerate(rows):
            words = ['remissinstans', 'sändlista']

            if (any(word in str(s).lower() for word in words)
            and len(s.split()) <= 2):
                return i + 1

        return None

    @staticmethod
    def detect_end(rows):
        for i, s in enumerate(rows):
            words = ['remiss', 'remitt', 'betänkande', ' har ']

            if any(word in str(s).lower() for word in words):
                return i

        return None

    @staticmethod
    def remove_page_numbers(rows):
        i = 0
        while i < len(rows):
            if re.match('[0-9]{1,2} \([0-9]{1,2}\)', rows[i]):
                del rows[i]
                i -= 1

            i += 1

        return rows

    @staticmethod
    def remove_footer_lines(rows):
        i = 0
        while i < len(rows):
            row = rows[i]
            words = [
                'telefonväxel',
                'postadress',
                'fax:',
                'besöksadress',
                '08-405',
                'webb:',
                '33 st'
                ]

            if any(word in str(row).lower() for word in words):
                del rows[i]
                i -= 1

            i += 1

        return rows

    @staticmethod
    def remove_leading_numbers(rows):
        for i in range(len(rows)):
            row = rows[i]
            if '.' in row[:5]:
                num = row[:row.index('.')]
                num = num.replace('l', '1')
                num = num.replace('O', '0')
                num = num.replace(' ', '')

                row = num + row[row.index('.'):]


            row = re.sub(r'^\d{1,3}\.', '', row) # Remove '1. ', '2. ', '3. '...
            row = re.sub(r'^\d{1,3}\s', '', row) # Remove '1 ', '2 ', '3 '...
            rows[i] = row

        return rows

    @staticmethod
    def remove_leading_spaces(rows):
        return [row.lstrip() for row in rows]

    @staticmethod
    def merge_multiline(rows):
        i = 0
        while i < len(rows):
            if i < len(rows):
                row = rows[i]
            else:
                continue

            if row:
                r = row[0]
            else:
                i += 1
                continue

            #if rows[i - 1][-1:] == ',' and row[-1:] != ',':
            #    # Trailing comma that doesn't seem to be the norm
            #    rows[i - 1] += ' ' + row
            #    del rows[i]

            if (')' in row
            and '(' not in row):
                # Unclosed parenthesis
                rows[i - 1] += ' ' + rows[i]
                del rows[i]
                continue

            if (i > 0
            and not r.isupper()         # If not capital letter
            and len(rows[i - 1]) > 60): # and the previous row is long
                if rows[i - 1].endswith('-'):
                    # Merges word split with '-'
                    rows[i - 1] = rows[i - 1][:-1] + row
                else:
                    # Merges lines cut between two words
                    rows[i - 1] += ' ' + row

                del rows[i]
                continue
            i += 1
        return rows

    @staticmethod
    def remove_trailing_comma(rows):
        return [row.rstrip(',') for row in rows]

    @staticmethod
    def remove_last_paragraph(rows):
        for i, s in enumerate(rows):
            if len(s.split()) >= 17:
                if ('(' not in s or ')' not in s
                    or len(s[s.index('('):s.index(')')]) / len(s) < 0.5):
                    return rows[:i]

        return rows
