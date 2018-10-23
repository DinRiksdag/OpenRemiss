class Cleaner(object):

    def remove_leading_numbers(text):
        return text.lstrip('0123456789abc.-_ abc ')

    def get_organisation_name(text):
        text = Cleaner.remove_leading_numbers(text)
        return text

    def is_instance(filename):
        return 'Remissinstanser' in filename or \
               'Remissmissiv' in filename or \
               'Promemoria' in filename or \
               'Remisslista' in filename or \
               'Remiss-PM' in filename or \
               'Remiss av' in filename or  \
               'Inbjudan' in filename
