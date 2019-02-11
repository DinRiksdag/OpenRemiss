from .base import Base
from sqlalchemy import ForeignKey, Column, Integer, String
from sqlalchemy.orm import relationship


class Document(Base):
    """Document model."""

    __tablename__ = 'document'

    id = Column(Integer, primary_key=True)
    remiss_id = Column(Integer, ForeignKey('remiss.id'))
    remiss = relationship('Remiss', back_populates='other_documents')
    files = relationship('File', back_populates='document')
    type = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'document',
        'polymorphic_on': type
    }
