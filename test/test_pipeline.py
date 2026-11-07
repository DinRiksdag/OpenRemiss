from hashlib import sha256

import pytest

from build_remissinstans_list import main as extract_lists
from clean_data import main as clean_names
from models import Consultee, Document
from service.document_parser import DocumentParser
from service.downloader import Downloader
from service.storage import load, save


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
