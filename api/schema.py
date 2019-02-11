import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType

from database.answer import Answer as AnswerModel
from database.consultee_list import ConsulteeList as ConsulteeListModel
from database.consultee import Consultee as ConsulteeModel
from database.document import Document as DocumentModel
from database.file import File as FileModel
from database.remiss import Remiss as RemissModel

from service.database import Database

class FileAttribute:
    name = graphene.String(description="Name of the file.")
    url = graphene.String(description="URL of the file.")


class File(SQLAlchemyObjectType):
    class Meta:
        model = FileModel


class DocumentAttribute:
    remiss_id = graphene.Int(description="Id of the answer's remiss.")
    type = graphene.String(description="Type of the document.")
    files = graphene.List(File, description="Files of the document.")


class Document(SQLAlchemyObjectType):
    class Meta:
        model = DocumentModel


class AnswerAttribute:
    organisation = graphene.String(
        description="Organisation or individual which authored the answer.")
    remiss_id = DocumentAttribute.remiss_id
    type = DocumentAttribute.type
    files = DocumentAttribute.files


class Answer(SQLAlchemyObjectType):
    class Meta:
        model = AnswerModel


class ConsulteeAttribute:
    name = graphene.String(description="Name of the consultee.")


class Consultee(SQLAlchemyObjectType):
    class Meta:
        model = ConsulteeModel


class ConsulteeListAttribute:
    consultee_list = graphene.List(
        Consultee,
        description="List of all the consultees in the document."
                                  )
    remiss_id = DocumentAttribute.remiss_id
    type = DocumentAttribute.type
    files = DocumentAttribute.files


class ConsulteeList(SQLAlchemyObjectType):
    class Meta:
        model = ConsulteeListModel


class Remiss(SQLAlchemyObjectType):
    class Meta:
        model = RemissModel


class Query(graphene.ObjectType):
    # Allows sorting over multiple columns, by default over the primary key
    answer = graphene.Field(Answer)
    answers = graphene.List(Answer)

    def resolve_answer(self, *args, **kwargs):
        return Database.query(AnswerModel).first()

    def resolve_answers(self, *args, **kwargs):
        return Database.query(AnswerModel).all()

    consultee_list = graphene.Field(ConsulteeList)
    consultee_lists = graphene.List(ConsulteeList)

    consultee = graphene.Field(Consultee)
    consultees = graphene.List(Consultee)

    document = graphene.Field(Document)
    documents = graphene.List(Document)

    file = graphene.Field(File)
    files = graphene.List(File)

    remiss = graphene.Field(Remiss)
    remisser = graphene.List(Remiss)

    def resolve_remiss(self, *args, **kwargs):
        return RemissModel.query.first()

    def resolve_remisser(self, *args, **kwargs):
        return RemissModel.query.all()


schema = graphene.Schema(query=Query)
