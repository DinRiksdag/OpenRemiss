from service.database import Database


class Cleaner(object):

    def remove_leading_numbers(text):
        return text.lstrip('0123456789abc.-_ abc ')

    def replace_by_popular_contained(text):
        db = Database('remisser.db')
        popular_org_names = db.get_popular_remiss_file_organisations()

        for popular_org_name in popular_org_names:
            if popular_org_name in text and popular_org_name != text:
                # print(f'{text} -> {popular_org_name}')
                text = popular_org_name
                break
        return text

    def get_organisation_name(text):
        text = Cleaner.remove_leading_numbers(text)
        text = Cleaner.replace_by_popular_contained(text)
        return text

    def is_instance(filename):
        return 'Remissinstanser' in filename or \
               'Remissmissiv' in filename or \
               'Promemoria' in filename or \
               'Remisslista' in filename or \
               'Remiss-PM' in filename or \
               'Remiss av' in filename or  \
               'Inbjudan' in filename
