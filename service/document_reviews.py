import json
from pathlib import Path


DOCUMENT_REVIEWS = {
    entry["url"]: entry
    for entry in json.loads(
        Path(__file__).with_suffix(".json").read_text(encoding="utf-8")
    )
}

SOURCE_EXCEPTIONS = {
    url: entry
    for url, entry in DOCUMENT_REVIEWS.items()
    if entry.get("category") == "source_naming_error"
}
