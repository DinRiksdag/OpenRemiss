from database.document import Document
from sqlalchemy import ForeignKey, Column, Integer
from sqlalchemy.orm import relationship


class ConsulteeList(Document):
    """ConsulteeList model."""

    __tablename__ = 'consultee_list'

    id = Column(Integer, ForeignKey('document.id'), primary_key=True)
    remiss = relationship('Remiss', back_populates='consultees')
    consultee_list = relationship('Consultee', back_populates='consultee_list')

    __mapper_args__ = {
        'polymorphic_identity': 'consultee_list',
    }
