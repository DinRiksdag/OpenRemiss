from database import base

from database import answer, consultee_list, consultee, content, document, file, remiss


class Database(object):

    @staticmethod
    def name():
        return base.db_name

    @staticmethod
    def create_tables():
        base.Base.metadata.create_all(base.engine)

    @staticmethod
    def drop_tables():
        base.Base.metadata.drop_all(base.engine)

    @staticmethod
    def query(object):
        base.db_session.query(object)

    @staticmethod
    def add(object):
        base.db_session.add(object)

    @staticmethod
    def delete_all(table):
        table.query.delete()

    @staticmethod
    def flush():
        base.db_session.flush()

    @staticmethod
    def commit():
        base.db_session.commit()

    @staticmethod
    def remove():
        base.db_session.remove()

    @staticmethod
    def close():
        base.db_session.close()
