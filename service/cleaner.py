from service.database import Database

from rapidfuzz import fuzz

class Cleaner(object):

    def smart_ratio(name1, name2):
        names = [name1, name2]

        for i, name in enumerate(names):
            if '(' in name:
                name = name[:name.index('(')]

            name = name.lower()
            name = name.replace(' i ', '')
            name = name.replace(' ', '')
            name = name.replace('.', '')
            name = name.replace(',', '')
            names[i] = name

        to_replace = {
            'aktiebolag': 'ab'
            }

        for i, name in enumerate(names):
            for word in to_replace.keys():
                names[i] = name.replace(word, to_replace[word])

        to_remove = [
            'förbund',
            'förening',
            'sverige',
            'svensk',
            'företag',
            'institut',
            'industri',
            'inspektion',
            ' kommun',
            ' stad',
            'styrelse',
            ' ab',
            'ambassad',
            'råd',
            'tingsrätt',
            'organisation',
            'universitet'
            ]

        for word in to_remove:
            if all(word in name for name in names):
                for i, name in enumerate(names):
                    names[i] = name.replace(word, '')

        ratio = fuzz.ratio(names[0], names[1])

        return ratio if len(names[0]) >= 5 and len(names[1]) >= 5 else 0

    @staticmethod
    def closest_in_list(text, list_to_compare, tolerance):

        closest = ''
        highest_ratio = 0

        for name in list_to_compare:
            ratio = Cleaner.smart_ratio(name, text)

            if ratio > highest_ratio:
                closest = name
                highest_ratio = ratio

        if highest_ratio > tolerance:
            print(f'{highest_ratio} – {text} --> {closest}')
            return closest

    @staticmethod
    def replace_by_popular(text, tolerance):
        popular_names = [name[0] for name in Database.get_popular_names(100 - tolerance)]

        return Cleaner.closest_in_list(text, popular_names, tolerance)

    @staticmethod
    def remove_leading_characters(text):
        return text.lstrip('0123456789abc.-_ abc ')

    @staticmethod
    def remove_trailing_characters(text):
        return text.rstrip('0123456789.-_ ')

    @staticmethod
    def remove_line_breaks(text):
        return text.replace('\n', '').replace('\r', '')

    @staticmethod
    def replace_by_popular_contained(text):
        q = Database.get_popular_answering_organisations(250)
        popular_org_names = [r[0] for r in q]

        for popular_org_name in popular_org_names:
            if popular_org_name in text:
                if popular_org_name != text:
                    print(f'{text} -> {popular_org_name}')
                    text = popular_org_name
                break
        return text

    @staticmethod
    def light_clean(text):
        text = Cleaner.remove_leading_characters(text)
        text = Cleaner.remove_trailing_characters(text)
        return text

    @staticmethod
    def deep_clean(text):
        text = Cleaner.replace_by_popular_contained(text)
        return text

    @staticmethod
    def is_consultee_list(filename):
        return any(s in filename for s in [ 'Remissmissiv',
                                            'Remisslista',
                                            'Remiss av'
                                            ])

    @staticmethod
    def is_other_document(filename):
        return not Cleaner.is_consultee_list(filename) and \
              ('Remissammanställning' in filename
               or 'Remissbrev' in filename
               or 'Promemoria' in filename
               or 'Remiss-PM' in filename
               or 'Remiss av' in filename
               or 'Inbjudan' in filename)

    @staticmethod
    def long_substr(data):
        substr = ''
        if len(data) > 1 and len(data[0]) > 0:
            for i in range(len(data[0])):
                for j in range(len(data[0])-i+1):
                    if (j > len(substr)
                            and all(data[0][i:i+j] in x for x in data)):
                        substr = data[0][i:i+j]
        return substr
