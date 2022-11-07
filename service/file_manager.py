import os
import rapidfuzz.fuzz as fuzz

class FileManager(object):

    @staticmethod
    def filepath_exists(filepath):
        return os.path.exists(filepath)

    @staticmethod
    def get_filepath(filepath):
        return open(filepath, 'rb')

    @staticmethod
    def move(old_filepath, new_filepath):
        dirpath = os.path.dirname(new_filepath)
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)

        if os.path.exists(old_filepath):
            os.rename(old_filepath, new_filepath)
        elif os.path.exists(old_filepath + '.pdf'):
            os.rename(old_filepath + '.pdf', new_filepath)
        else:
            for file in os.listdir('tmp/'):
                path = os.path.join('tmp/', file)
                if os.path.isfile(path) and fuzz.ratio(path, new_filepath):
                    os.rename(path, new_filepath)
