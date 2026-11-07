from io import BytesIO
from email.message import Message
import json
from urllib.error import HTTPError

import pytest

from service import downloader
from service.downloader import Downloader, UnsupportedDocumentError


@pytest.mark.parametrize(
    "method,route,payload",
    [
        ("get_remisser", "/remisser.json", [{"url": "/remisser/example/"}]),
        ("get_codes", "/api/codes.json", {"1287": "Justitiedepartementet"}),
    ],
)
def test_metadata_comes_from_g0v_only(monkeypatch, method, route, payload):
    calls = []

    def fetch(url, timeout):
        calls.append(url)
        return BytesIO(json.dumps(payload).encode())

    monkeypatch.setattr(downloader, "urlopen", fetch)
    assert getattr(Downloader, method)() == payload
    assert calls == ["https://g0v.se" + route]


def test_download_pdf_to_exact_destination(monkeypatch, tmp_path):
    payload = b"%PDF-1.7\nexample"
    calls = []

    def fetch(request, timeout):
        calls.append(request.full_url)
        assert request.get_header("User-agent").startswith("OpenRemiss/")
        return BytesIO(payload)

    monkeypatch.setattr(downloader, "urlopen", fetch)
    target = tmp_path / "consultation" / "list.pdf"
    url = "https://www.regeringen.se/contentassets/example/remissinstanser/"
    assert Downloader.get_file(url, target) == target
    assert target.read_bytes() == payload
    assert calls == [url]
    assert list(target.parent.iterdir()) == [target]


def test_http_error_is_reported_without_fallback(monkeypatch, tmp_path):
    calls = []

    def fetch(request, timeout):
        calls.append(request.full_url)
        raise HTTPError(request.full_url, 503, "Unavailable", Message(), None)

    monkeypatch.setattr(downloader, "urlopen", fetch)
    with pytest.raises(HTTPError):
        Downloader.get_file(
            "https://www.regeringen.se/missing.pdf", tmp_path / "list.pdf"
        )
    assert len(calls) == 1
    assert list(tmp_path.iterdir()) == []


def test_invalid_response_does_not_replace_cached_pdf(monkeypatch, tmp_path):
    monkeypatch.setattr(
        downloader, "urlopen", lambda url, timeout: BytesIO(b"<html>error</html>")
    )
    target = tmp_path / "list.pdf"
    target.write_bytes(b"%PDF-original")

    with pytest.raises(ValueError, match="Expected a PDF"):
        Downloader.get_file("https://www.regeringen.se/list.pdf", target)
    assert target.read_bytes() == b"%PDF-original"
    assert list(tmp_path.iterdir()) == [target]


def test_interrupted_download_does_not_leave_partial_file(monkeypatch, tmp_path):
    class InterruptedResponse(BytesIO):
        def read(self, size=-1):
            if self.tell() >= 5:
                raise OSError("Connection interrupted")
            return super().read(size)

    monkeypatch.setattr(
        downloader, "urlopen", lambda url, timeout: InterruptedResponse(b"%PDF-test")
    )
    with pytest.raises(OSError, match="Connection interrupted"):
        Downloader.get_file("https://www.regeringen.se/list.pdf", tmp_path / "list.pdf")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "payload", [b"PK\x03\x04office document", b"\xd0\xcf\x11\xe0\xa1legacy document"]
)
def test_office_documents_are_reported_as_unsupported(monkeypatch, tmp_path, payload):
    monkeypatch.setattr(
        downloader, "urlopen", lambda request, timeout: BytesIO(payload)
    )
    with pytest.raises(UnsupportedDocumentError, match="Unsupported non-PDF"):
        Downloader.get_file("https://example.org/list.DOCX", tmp_path / "list.pdf")
    assert list(tmp_path.iterdir()) == []
