from .base import Base
from sqlalchemy import ForeignKey, Column, Integer, String
from sqlalchemy.orm import relationship


class File(Base):
    """File model."""

    __tablename__ = 'file'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('document.id'))
    document = relationship('Document', back_populates='files')
    name = Column(String)
    url = Column(String)
