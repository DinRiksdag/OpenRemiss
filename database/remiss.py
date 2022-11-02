from database.content import Content
from sqlalchemy import ForeignKey, Column, Integer, String, Date
from sqlalchemy.orm import relationship


class Remiss(Content):
    """Remiss model."""

    __tablename__ = 'remiss'

    id = Column(Integer, ForeignKey('content.id'), primary_key=True)
    diary_number = Column(String)
    deadline = Column(Date)
    consultees = relationship(
                              'ConsulteeList',
                              back_populates='remiss',
                              uselist=False,
                              viewonly=True
                              )
    answers = relationship(
                           'Answer',
                           back_populates='remiss',
                           viewonly=True
                           )
    other_documents = relationship('Document', back_populates='remiss',
    viewonly=True)

    __mapper_args__ = {
        'polymorphic_identity': 'remiss',
    }
