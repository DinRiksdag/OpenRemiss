from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from models import Consultee, Document, Remiss
from service.storage import TABLES, load, save


@pytest.mark.parametrize("model", [Remiss, Document, Consultee])
def test_empty_dataset_has_a_stable_schema(data_dir, model):
    assert load(model, data_dir) == []
    save(model, [], data_dir)
    assert load(model, data_dir) == []
    name, schema = TABLES[model]
    frame = pd.read_parquet(data_dir / f"{name}.parquet")
    assert frame.columns.tolist() == list(schema)
    assert all(str(frame[column].dtype) == dtype for column, dtype in schema.items())


def test_roundtrip_dates_unicode_and_nullable_fields(data_dir):
    remisser = [
        Remiss(
            url="https://example.org/remiss",
            title="Översyn av miljöfrågor",
            published_on=date(2026, 11, 6),
        ),
    ]
    documents = [
        Document(
            remiss_url=remisser[0].url,
            url="https://example.org/response.pdf",
            name="Göteborgs universitet",
            kind="answer",
            organisation="Göteborgs universitet",
        ),
        Document(
            remiss_url=remisser[0].url,
            url="https://example.org/list.pdf",
            name="Remissinstanser",
            kind="consultee_list",
            extraction_status="complete",
        ),
    ]
    consultees = [
        Consultee(
            remiss_url=remisser[0].url,
            document_url=documents[1].url,
            name="1. Göteborgs universitet",
            cleaned_name="Göteborgs universitet",
        )
    ]
    save(Remiss, remisser, data_dir)
    save(Document, documents, data_dir)
    save(Consultee, consultees, data_dir)

    assert load(Remiss, data_dir) == remisser
    assert load(Document, data_dir) == documents
    assert load(Consultee, data_dir) == consultees
    frame = pd.read_parquet(data_dir / "remisser.parquet")
    assert pd.api.types.is_datetime64_any_dtype(frame["published_on"])
    assert "__index_level_0__" not in frame.columns


def test_invalid_stored_rows_are_rejected(data_dir):
    document = Document(
        remiss_url="https://example.org/r",
        url="https://example.org/d",
        name="Example",
        kind="answer",
    )
    save(Document, [document], data_dir)
    frame = pd.read_parquet(data_dir / "documents.parquet")
    frame.loc[0, "kind"] = "not-a-document-kind"
    frame.to_parquet(data_dir / "documents.parquet", index=False)
    with pytest.raises(ValidationError):
        load(Document, data_dir)


def test_failed_write_preserves_previous_snapshot(data_dir, monkeypatch):
    document = Document(
        remiss_url="https://example.org/r",
        url="https://example.org/d",
        name="Original",
        kind="answer",
    )
    save(Document, [document], data_dir)
    document.name = "Changed"

    def broken_write(self, path, **kwargs):
        Path(path).write_bytes(b"incomplete")
        raise OSError("Disk full")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", broken_write)
    with pytest.raises(OSError, match="Disk full"):
        save(Document, [document], data_dir)
    assert load(Document, data_dir)[0].name == "Original"
    assert not list(data_dir.glob("*.tmp"))
