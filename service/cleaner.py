class Cleaner(object):

    @staticmethod
    def remove_leading_numbers(text):
        return text.lstrip('0123456789abc.-_ abc ')

    @staticmethod
    def remove_line_breaks(text):
        return text.replace('\n', '').replace('\r', '')

    @staticmethod
    def replace_by_popular_contained(text):
        db = [] #Database('remisser.db')
        popular_org_names = Database.get_popular_remiss_file_organisations()

        for popular_org_name in popular_org_names:
            if popular_org_name in text and popular_org_name != text:
                # print(f'{text} -> {popular_org_name}')
                text = popular_org_name
                break
        return text

    @staticmethod
    def get_organisation_name(text):
        text = Cleaner.remove_leading_numbers(text)
        #text = Cleaner.replace_by_popular_contained(text)
        return text

    @staticmethod
    def is_consultee_list(filename):
        return 'Remissinstanser' in filename or \
               'Remissmissiv' in filename or \
               'Remisslista' in filename or \
               'Remiss av' in filename

    @staticmethod
    def is_other_document(filename):
        return not Cleaner.is_consultee_list(filename) and \
              ('Remissammanställning' in filename
               or 'Remissbrev' in filename
               or 'Promemoria' in filename
               or 'Remiss-PM' in filename
               or 'Remiss av' in filename
               or 'Inbjudan' in filename)
