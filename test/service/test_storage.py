from datetime import date, datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
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
    assert pq.read_schema(data_dir / f"{name}.parquet") == schema


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
    table = pq.read_table(data_dir / "remisser.parquet")
    assert table.column("published_on").to_pylist() == [date(2026, 11, 6)]
    assert pa.types.is_date32(table.schema.field("published_on").type)
    assert "__index_level_0__" not in table.column_names


def test_invalid_stored_rows_are_rejected(data_dir):
    document = Document(
        remiss_url="https://example.org/r",
        url="https://example.org/d",
        name="Example",
        kind="answer",
    )
    save(Document, [document], data_dir)
    table = pq.read_table(data_dir / "documents.parquet")
    rows = table.to_pylist()
    rows[0]["kind"] = "not-a-document-kind"
    pq.write_table(
        pa.Table.from_pylist(rows, schema=table.schema), data_dir / "documents.parquet"
    )
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

    def broken_write(table, path, **kwargs):
        Path(path).write_bytes(b"incomplete")
        raise OSError("Disk full")

    monkeypatch.setattr(pq, "write_table", broken_write)
    with pytest.raises(OSError, match="Disk full"):
        save(Document, [document], data_dir)
    assert load(Document, data_dir)[0].name == "Original"
    assert not list(data_dir.glob("*.tmp"))


def test_reads_publication_timestamps_from_existing_parquet_files(data_dir):
    remiss = Remiss(
        url="https://example.org/remiss",
        title="Översyn",
        published_on=date(2026, 11, 6),
    )
    row = remiss.model_dump()
    row["published_on"] = datetime(2026, 11, 6)
    legacy_schema = pa.schema(
        [
            ("url", pa.large_string()),
            ("title", pa.large_string()),
            ("published_on", pa.timestamp("ns")),
            ("issuer", pa.large_string()),
            ("diary_number", pa.large_string()),
        ]
    )
    data_dir.mkdir()
    pq.write_table(
        pa.Table.from_pylist([row], schema=legacy_schema), data_dir / "remisser.parquet"
    )
    assert load(Remiss, data_dir) == [remiss]
    save(Remiss, [remiss], data_dir)
    assert load(Remiss, data_dir) == [remiss]


def test_invalid_record_does_not_replace_previous_snapshot(data_dir):
    document = Document(
        remiss_url="https://example.org/r",
        url="https://example.org/d",
        name="Example",
        kind="answer",
    )
    save(Document, [document], data_dir)
    invalid = document.model_copy(update={"kind": "invalid"})
    with pytest.raises(ValidationError):
        save(Document, [invalid], data_dir)
    assert load(Document, data_dir) == [document]
