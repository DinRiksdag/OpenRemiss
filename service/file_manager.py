import os

class FileManager(object):

    @staticmethod
    def filepath_exists(filepath):
        return os.path.exists(filepath)

    @staticmethod
    def get_filepath(filepath):
        return open(filepath, 'rb')

    @staticmethod
    def write_to_filepath(filepath, file):
        dirpath = os.path.dirname(filepath)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        f = open(filepath, 'wb')
        f.write(file)
        f.close()
