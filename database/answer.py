from database.document import Document
from sqlalchemy import ForeignKey, Column, Integer, String
from sqlalchemy.orm import relationship


class Answer(Document):
    """Answer model."""

    __tablename__ = 'answer'

    id = Column(Integer, ForeignKey('document.id'), primary_key=True)
    remiss = relationship('Remiss', back_populates='answers')
    organisation = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'answer',
    }
