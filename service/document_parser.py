import re
import math
import pandas as pd

from service.tabula_parser import TabulaParser


class DocumentParser(object):

    @staticmethod
    def extract_list(filename):
        first_page = TabulaParser.extract_first_page(filename)
        next_pages = TabulaParser.extract_next_pages(filename)

        all_pages = first_page + next_pages

        all_rows = DocumentParser.pick_right_columns(all_pages)

        if not all_pages:
            print(f'Document is a scan, not supported yet.')
            return

        all_rows = all_rows.tolist()

        start = DocumentParser.detect_start(all_rows)

        if not start:
            print(f'Document is most likely not a remissinstans.')
            return

        consultee_list = all_rows[start:]

        end = DocumentParser.detect_end(consultee_list)

        if not end:
            print(f'Document is partly a scan, not supported yet.')
            return

        consultee_list = consultee_list[:end]

        consultee_list = DocumentParser.remove_leading_numbers(consultee_list)
        consultee_list = DocumentParser.remove_leading_spaces(consultee_list)
        consultee_list = DocumentParser.merge_multiline(consultee_list)
        consultee_list = DocumentParser.remove_trailing_comma(consultee_list)
        consultee_list = DocumentParser.remove_last_paragraph(consultee_list)

        return consultee_list

    @staticmethod
    def pick_right_columns(df_list):
        all_rows = pd.Series(dtype=pd.StringDtype())

        for df in df_list:
            right_column = df[df.columns[0]]

            len_right_column = right_column.astype(str).str.len().sum()

            for i in range(1, len(df.columns)):
                column = df[df.columns[1]]
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

            if any(word in s.lower() for word in words):
                return i + 1

        return None

    @staticmethod
    def detect_end(rows):
        for i, s in enumerate(rows):
            words = ['remiss', 'remitt', 'betänkande', ' har ']

            if any(word in s.lower() for word in words):
                return i

        return None

    @staticmethod
    def remove_last_paragraph(rows):
        for i, s in enumerate(rows):
            if len(s.split()) >= 17:
                if '(' not in s or ')' not in s or len(s[s.index('('):s.index(')')]) / len(s) < 0.5:
                    return rows[:i]

        return rows

    @staticmethod
    def remove_trailing_comma(rows):
        return [row.rstrip(',') for row in rows]

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

            r = row[0]

            if '(' in row and not ')' in row:
                # Unclosed parenthesis
                rows[i] += ' ' + rows[i + 1]
                del rows[i + 1]

            if (i > 0 and not r.isupper()         # If not capital letter
                      and len(rows[i - 1]) > 60): # and the previous row is long
                if rows[i - 1].endswith('-'):
                    # Merges word split with '-'
                    rows[i - 1] = rows[i - 1][:-1] + row
                else:
                    # Merges lines cut between two words
                    rows[i - 1] += ' ' + row

                del rows[i]
                i -= 1
            i += 1
        return rows
