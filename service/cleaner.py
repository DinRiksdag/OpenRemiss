from service.database import Database


class Cleaner(object):

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
        q = Database.get_popular_organisation_names(250)
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
