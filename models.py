from datetime import date
from typing import Literal

from pydantic import BaseModel

DocumentKind = Literal["answer", "consultee_list", "other"]


class Remiss(BaseModel):
    url: str
    title: str
    published_on: date
    issuer: str | None = None
    diary_number: str | None = None


class Document(BaseModel):
    remiss_url: str
    url: str
    name: str
    kind: DocumentKind
    organisation: str | None = None
    extraction_status: Literal["pending", "complete", "failed", "skipped"] | None = None
    extraction_error: str | None = None


class Consultee(BaseModel):
    remiss_url: str
    document_url: str
    name: str
    cleaned_name: str | None = None
