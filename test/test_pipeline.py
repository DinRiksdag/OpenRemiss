from hashlib import sha256
from io import BytesIO
import logging

import pytest

from build_remissinstans_list import main as extract_lists
from clean_data import main as clean_names
from models import Consultee, Document
from service.document_parser import DocumentParser
from service.downloader import Downloader
from service import downloader
from service.storage import load, save
import build_remissinstans_list as pipeline


def invitation(url):
    return Document(
        remiss_url="https://example.org/remiss",
        url=url,
        name="Remissinstanser",
        kind="consultee_list",
        extraction_status="pending",
    )


def test_extraction_reuses_completed_results_and_can_reset(
    data_dir, tmp_path, monkeypatch
):
    doc = invitation("https://example.org/list.pdf")
    save(Document, [doc], data_dir)
    downloads = []
    parses = []

    def download(url, path):
        downloads.append(url)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"%PDF-test")
        return path

    def extract(path):
        parses.append(path)
        return ["1. Göteborgs universitet", "Barnombudsmannen"]

    monkeypatch.setattr(Downloader, "get_file", download)
    monkeypatch.setattr(DocumentParser, "extract_list", extract)
    cache_dir = tmp_path / "cache"
    extract_lists(data_dir, cache_dir)
    extract_lists(data_dir, cache_dir)
    assert downloads == [doc.url]
    assert len(parses) == 1
    assert len(load(Consultee, data_dir)) == 2
    assert load(Document, data_dir)[0].extraction_status == "complete"
    extract_lists(data_dir, cache_dir, reset=True)
    assert len(parses) == 2
    assert len(load(Consultee, data_dir)) == 2


def test_completed_empty_list_is_not_reprocessed(data_dir, tmp_path, monkeypatch):
    doc = invitation("https://example.org/list.pdf")
    doc.extraction_status = "complete"
    save(Document, [doc], data_dir)

    def unexpected_parse(path):
        raise AssertionError("Already complete")

    monkeypatch.setattr(DocumentParser, "extract_list", unexpected_parse)
    extract_lists(data_dir, tmp_path)
    assert load(Consultee, data_dir) == []


def test_interruption_preserves_completed_extractions(data_dir, tmp_path, monkeypatch):
    documents = [
        invitation("https://example.org/first.pdf"),
        invitation("https://example.org/second.pdf"),
    ]
    save(Document, documents, data_dir)

    def download(url, path):
        path.write_bytes(b"%PDF-test")
        return path

    def extract(path):
        if sha256(documents[1].url.encode()).hexdigest() in path:
            raise ValueError("Cannot parse second document")
        return ["Barnombudsmannen"]

    monkeypatch.setattr(Downloader, "get_file", download)
    monkeypatch.setattr(DocumentParser, "extract_list", extract)
    with pytest.raises(ValueError, match="Cannot parse second"):
        extract_lists(data_dir, tmp_path)
    stored = load(Document, data_dir)
    assert stored[0].extraction_status == "complete"
    assert stored[1].extraction_status == "failed"
    assert stored[1].extraction_error == "Cannot parse second document"
    assert [row.name for row in load(Consultee, data_dir)] == ["Barnombudsmannen"]

    monkeypatch.setattr(
        DocumentParser, "extract_list", lambda path: ["Socialstyrelsen"]
    )
    extract_lists(data_dir, tmp_path)
    assert [row.name for row in load(Consultee, data_dir)] == [
        "Barnombudsmannen",
        "Socialstyrelsen",
    ]


def test_cleaning_preserves_source_names_and_is_repeatable(data_dir):
    documents = [
        Document(
            remiss_url=f"https://example.org/r{i}",
            url=f"https://example.org/d{i}",
            name="1. Lunds universitet",
            kind="answer",
        )
        for i in range(3)
    ] + [
        Document(
            remiss_url="https://example.org/other",
            url="https://example.org/other.pdf",
            name="Lunds universitet (Juridiska fakulteten)",
            kind="answer",
        ),
    ]
    consultees = [
        Consultee(
            remiss_url="https://example.org/r0",
            document_url="https://example.org/list",
            name="12. Lunds universitet (Juridiska fakulteten)",
        )
    ]
    save(Document, documents, data_dir)
    save(Consultee, consultees, data_dir)
    clean_names(data_dir)
    first_result = load(Document, data_dir)
    clean_names(data_dir)

    assert load(Document, data_dir) == first_result
    assert all(doc.organisation == "Lunds universitet" for doc in first_result)
    assert first_result[0].name == "1. Lunds universitet"
    assert load(Consultee, data_dir)[0].cleaned_name == "Lunds universitet"
    assert load(Consultee, data_dir)[0].name == consultees[0].name


def test_non_pdf_invitations_are_logged_skipped_and_processing_continues(
    data_dir, tmp_path, monkeypatch, caplog
):
    documents = [
        invitation("https://example.org/first.docx"),
        invitation("https://example.org/second.DOCX"),
        invitation("https://example.org/mislabelled.docx"),
    ]
    save(Document, documents, data_dir)
    requests = []

    def fetch(request, timeout):
        requests.append(request.full_url)
        payload = (
            b"%PDF-test" if request.full_url == documents[2].url else b"PK\x03\x04word"
        )
        return BytesIO(payload)

    monkeypatch.setattr(downloader, "urlopen", fetch)
    monkeypatch.setattr(
        DocumentParser, "extract_list", lambda path: ["Barnombudsmannen"]
    )
    extract_lists(data_dir, tmp_path)
    stored = load(Document, data_dir)
    assert [doc.extraction_status for doc in stored] == [
        "skipped",
        "skipped",
        "complete",
    ]
    assert all(
        doc.extraction_error is not None
        and "Unsupported non-PDF" in doc.extraction_error
        for doc in stored[:2]
    )
    assert all(doc.url in caplog.text for doc in stored[:2])
    assert [row.document_url for row in load(Consultee, data_dir)] == [documents[2].url]
    assert len(list(tmp_path.glob("*.pdf"))) == 1
    extract_lists(data_dir, tmp_path)
    assert requests == [doc.url for doc in documents]


def test_html_error_response_is_not_silently_skipped(data_dir, tmp_path, monkeypatch):
    save(Document, [invitation("https://example.org/list.pdf")], data_dir)
    monkeypatch.setattr(
        downloader, "urlopen", lambda request, timeout: BytesIO(b"<html>error</html>")
    )
    with pytest.raises(ValueError, match="Expected a PDF"):
        extract_lists(data_dir, tmp_path)
    assert load(Document, data_dir)[0].extraction_status == "failed"


def test_extraction_logs_progress_and_unrecognised_lists(
    data_dir, tmp_path, monkeypatch, caplog
):
    documents = [
        invitation("https://example.org/unrecognised.pdf"),
        invitation("https://example.org/valid.pdf"),
    ]
    save(Document, documents, data_dir)
    for doc in documents:
        (tmp_path / (sha256(doc.url.encode()).hexdigest() + ".pdf")).write_bytes(
            b"%PDF-test"
        )
    results = iter([None, ["Barnombudsmannen"]])
    monkeypatch.setattr(DocumentParser, "extract_list", lambda path: next(results))
    caplog.set_level(logging.INFO, logger="build_remissinstans_list")

    extract_lists(data_dir, tmp_path)

    assert "Processing 2 invitation lists" in caplog.text
    assert f"[1/2] {documents[0].url} (cached PDF)" in caplog.text
    assert f"No invitation list could be extracted: {documents[0].url}" in caplog.text
    assert f"[2/2] {documents[1].url} (cached PDF)" in caplog.text
    assert "1 complete, 1 failed, 0 skipped; 1 organisation records" in caplog.text
    assert [doc.extraction_status for doc in load(Document, data_dir)] == [
        "failed",
        "complete",
    ]


def test_parquet_writes_are_batched(data_dir, tmp_path, monkeypatch):
    documents = [invitation(f"https://example.org/{i}.pdf") for i in range(5)]
    save(Document, documents, data_dir)
    for doc in documents:
        (tmp_path / (sha256(doc.url.encode()).hexdigest() + ".pdf")).write_bytes(
            b"%PDF-test"
        )
    monkeypatch.setattr(
        DocumentParser, "extract_list", lambda path: ["Barnombudsmannen"]
    )
    writes = []

    def record_save(model, rows, directory):
        writes.append((model, len(rows)))
        save(model, rows, directory)

    monkeypatch.setattr(pipeline, "save", record_save)
    extract_lists(data_dir, tmp_path, checkpoint_every=2)
    assert [count for model, count in writes if model is Consultee] == [2, 4, 5]
    assert sum(model is Document for model, _ in writes) == 3
    assert all(doc.extraction_status == "complete" for doc in load(Document, data_dir))


def test_keyboard_interrupt_flushes_pending_results(data_dir, tmp_path, monkeypatch):
    documents = [invitation(f"https://example.org/{i}.pdf") for i in range(2)]
    save(Document, documents, data_dir)
    for doc in documents:
        (tmp_path / (sha256(doc.url.encode()).hexdigest() + ".pdf")).write_bytes(
            b"%PDF-test"
        )
    calls = []

    def extract(path):
        calls.append(path)
        if len(calls) == 2:
            raise KeyboardInterrupt()
        return ["Barnombudsmannen"]

    monkeypatch.setattr(DocumentParser, "extract_list", extract)
    with pytest.raises(KeyboardInterrupt):
        extract_lists(data_dir, tmp_path)
    assert [row.extraction_status for row in load(Document, data_dir)] == [
        "complete",
        "pending",
    ]
    assert len(load(Consultee, data_dir)) == 1


def test_elapsed_time_triggers_a_checkpoint(data_dir, tmp_path, monkeypatch):
    documents = [invitation(f"https://example.org/{i}.pdf") for i in range(3)]
    save(Document, documents, data_dir)
    for doc in documents:
        (tmp_path / (sha256(doc.url.encode()).hexdigest() + ".pdf")).write_bytes(
            b"%PDF-test"
        )
    clock = [0]
    monkeypatch.setattr(pipeline, "monotonic", lambda: clock[0])

    def extract(path):
        clock[0] += 20
        return ["Barnombudsmannen"]

    checkpoints = []

    def record_save(model, rows, directory):
        if model is Consultee:
            checkpoints.append(len(rows))
        save(model, rows, directory)

    monkeypatch.setattr(DocumentParser, "extract_list", extract)
    monkeypatch.setattr(pipeline, "save", record_save)
    extract_lists(data_dir, tmp_path)
    assert checkpoints == [2, 3]
