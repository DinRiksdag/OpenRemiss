from pathlib import Path
from typing import Sequence, TypeVar

import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import BaseModel

from models import Consultee, Document, Remiss

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
Record = TypeVar("Record", bound=BaseModel)
TABLES: dict[type[BaseModel], tuple[str, pa.Schema]] = {
    Remiss: (
        "remisser",
        pa.schema(
            [
                ("url", pa.string()),
                ("title", pa.string()),
                ("published_on", pa.date32()),
                ("issuer", pa.string()),
                ("diary_number", pa.string()),
            ]
        ),
    ),
    Document: (
        "documents",
        pa.schema(
            [
                ("remiss_url", pa.string()),
                ("url", pa.string()),
                ("name", pa.string()),
                ("kind", pa.string()),
                ("organisation", pa.string()),
                ("extraction_status", pa.string()),
                ("extraction_error", pa.string()),
            ]
        ),
    ),
    Consultee: (
        "consultees",
        pa.schema(
            [
                ("remiss_url", pa.string()),
                ("document_url", pa.string()),
                ("name", pa.string()),
                ("cleaned_name", pa.string()),
            ]
        ),
    ),
}


def load(model: type[Record], data_dir: Path = DATA_DIR) -> list[Record]:
    name, _ = TABLES[model]
    path = data_dir / f"{name}.parquet"
    if not path.exists():
        return []
    records = pq.read_table(path).to_pylist()
    return [model.model_validate(record) for record in records]


def save(
    model: type[Record], records: Sequence[Record], data_dir: Path = DATA_DIR
) -> None:
    """Write a typed snapshot without replacing the previous file on failure."""
    name, schema = TABLES[model]
    rows = [
        model.model_validate(record.model_dump()).model_dump() for record in records
    ]
    table = pa.Table.from_pylist(rows, schema=schema)
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{name}.parquet"
    partial = path.with_suffix(".parquet.tmp")
    try:
        pq.write_table(table, partial)
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)
