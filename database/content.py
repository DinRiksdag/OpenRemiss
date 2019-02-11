from .base import Base
from sqlalchemy import Column, Integer, String, Date


class Content(Base):
    """Content model."""

    __tablename__ = 'content'

    id = Column(Integer, primary_key=True)
    issuer = Column(String)
    published_on = Column(Date)
    title = Column(String)
    url = Column(String)
    type = Column(String)

    __mapper_args__ = {
        'polymorphic_identity': 'content',
        'polymorphic_on': type
    }
