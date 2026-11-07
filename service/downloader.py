import json
from pathlib import Path
from shutil import copyfileobj
from urllib.request import Request, urlopen

G0V_URL = "https://g0v.se"


class UnsupportedDocumentError(ValueError):
    """The downloaded document is not a PDF."""


class Downloader:
    @staticmethod
    def get_remisser():
        with urlopen(f"{G0V_URL}/remisser.json", timeout=60) as response:
            return json.load(response)

    @staticmethod
    def get_codes():
        with urlopen(f"{G0V_URL}/api/codes.json", timeout=30) as response:
            return json.load(response)

    @staticmethod
    def get_file(url, destination):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(".pdf.part")
        request = Request(
            url,
            headers={
                "User-Agent": "OpenRemiss/0.3 (+https://github.com/DinRiksdag/OpenRemiss)"
            },
        )
        try:
            with urlopen(request, timeout=60) as response, partial.open("wb") as output:
                header = response.read(5)
                if header != b"%PDF-":
                    if (
                        header.startswith(b"PK\x03\x04")
                        or header == b"\xd0\xcf\x11\xe0\xa1"
                    ):
                        raise UnsupportedDocumentError(
                            f"Unsupported non-PDF document from {url}"
                        )
                    raise ValueError(f"Expected a PDF from {url}")
                output.write(header)
                copyfileobj(response, output)
            partial.replace(destination)
        finally:
            partial.unlink(missing_ok=True)
        return destination
