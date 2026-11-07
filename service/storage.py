from pathlib import Path
from typing import Sequence, TypeVar

import pandas as pd
from pydantic import BaseModel

from models import Consultee, Document, Remiss

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
Record = TypeVar("Record", bound=BaseModel)
TABLES: dict[type[BaseModel], tuple[str, dict[str, str]]] = {
    Remiss: (
        "remisser",
        {
            "url": "string",
            "title": "string",
            "published_on": "datetime64[ns]",
            "issuer": "string",
            "diary_number": "string",
        },
    ),
    Document: (
        "documents",
        {
            "remiss_url": "string",
            "url": "string",
            "name": "string",
            "kind": "string",
            "organisation": "string",
            "extraction_status": "string",
            "extraction_error": "string",
        },
    ),
    Consultee: (
        "consultees",
        {
            "remiss_url": "string",
            "document_url": "string",
            "name": "string",
            "cleaned_name": "string",
        },
    ),
}


def load(model: type[Record], data_dir: Path = DATA_DIR) -> list[Record]:
    name, _ = TABLES[model]
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        return []
    frame = pd.read_parquet(path, engine="pyarrow")
    records = frame.astype(object).where(pd.notna(frame), None).to_dict("records")
    return [model.model_validate(record) for record in records]


def save(
    model: type[Record], records: Sequence[Record], data_dir: Path = DATA_DIR
) -> None:
    """Write a typed snapshot without replacing the previous file on failure."""
    name, schema = TABLES[model]
    rows = [
        model.model_validate(record.model_dump()).model_dump() for record in records
    ]
    frame = pd.DataFrame(
        {
            field: pd.Series([row[field] for row in rows], dtype=dtype)
            for field, dtype in schema.items()
        }
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{name}.parquet"
    partial = path.with_suffix(".parquet.tmp")
    try:
        frame.to_parquet(partial, engine="pyarrow", index=False)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)
