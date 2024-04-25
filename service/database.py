from sqlalchemy import func
from sqlalchemy.sql.functions import coalesce

from database.answer import Answer
from database.consultee import Consultee

from database import base

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

    def empty_column(table, column):
        table.query.update({column: None})

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

    @staticmethod
    def get_popular_answering_organisations(amount):
        return base.db_session.query(
                            Answer.organisation,
                            func.count(Answer.organisation)
                        ).group_by(
                            Answer.organisation
                        ).order_by(
                            func.count(Answer.organisation).desc()
                        ).limit(
                            amount
                        ).all()

    def __best_names(best_name):
        return base.db_session.query(
                            best_name,
                            func.count(best_name)
                        ).group_by(
                            best_name
                        )

    @staticmethod
    def get_popular_names(percent):
        best_name = coalesce(Consultee.cleaned_name, Consultee.cleaned_name)
        best_names = Database.__best_names()

        return best_names.order_by(
                            func.count(best_name).asc()
                        ).limit(
                            int(best_names.count() * percent / 100)
                        ).all()
