from .base import Base
from sqlalchemy import ForeignKey, Column, Integer, String
from sqlalchemy.orm import relationship


class Consultee(Base):
    """Consultee model."""

    __tablename__ = 'consultee'

    id = Column(Integer, primary_key=True)
    consultee_list_id = Column(Integer, ForeignKey('consultee_list.id'))
    consultee_list = relationship('ConsulteeList',
                                  back_populates='consultee_list')
    name = Column(String)
    cleaned_name = Column(String)
