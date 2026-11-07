"""Register all related ORM models when the database package is imported."""

from .answer import Answer
from .consultee import Consultee
from .consultee_list import ConsulteeList
from .content import Content
from .document import Document
from .file import File
from .remiss import Remiss

__all__ = [
    "Answer",
    "Consultee",
    "ConsulteeList",
    "Content",
    "Document",
    "File",
    "Remiss",
]
