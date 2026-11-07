from datetime import date

import pytest

from models import Consultee, Document, Remiss
from service.importer import sync_remisser
from service.storage import load, save

CODES = {
    "1287": "Justitiedepartementet",
    "1291": "Klimat- och näringslivsdepartementet",
}


@pytest.fixture
def item():
    return {
        "title": "Remiss av betänkandet Lyssna på barnet! (SOU 2026:66)",
        "url": "/remisser/2026/11/remiss-av-sou-202666-lyssna-pa-barnet/",
        "published": "2026-11-06",
        "updated": None,
        "senders": ["1287", "1291"],
        "id": "Diarienummer: Ju2026/02439",
        "attachments": [
            {
                "name": "Remissinstanser Lyssna på barnet! (pdf 86 kB)",
                "url": "/contentassets/example/remissmissiv.pdf",
            },
            {
                "name": "Barnombudsmannen (pdf 1 MB)",
                "url": "/contentassets/example/barnombudsmannen/",
            },
            {
                "name": "Promemoria (pdf 20 kB)",
                "url": "https://www.regeringen.se/contentassets/example/pm.pdf",
            },
        ],
    }


def test_import_maps_g0v_metadata_and_attachment_types(data_dir, item):
    assert sync_remisser([item], CODES, data_dir) == 1
    remiss = load(Remiss, data_dir)[0]
    documents = load(Document, data_dir)
    assert remiss.title == item["title"]
    assert remiss.published_on == date(2026, 11, 6)
    assert remiss.issuer == "Justitiedepartementet"
    assert remiss.diary_number == "Ju2026/02439"
    assert remiss.url == "https://www.regeringen.se" + item["url"]
    assert [doc.kind for doc in documents] == ["consultee_list", "answer", "other"]
    assert documents[1].name == "Barnombudsmannen"
    assert documents[1].url.endswith("/barnombudsmannen/")
    assert documents[0].extraction_status == "pending"
    assert documents[1].extraction_status is None


def test_refresh_adds_responses_without_an_updated_date_and_preserves_derived_data(
    data_dir, item
):
    sync_remisser([item], CODES, data_dir)
    documents = load(Document, data_dir)
    invitation, answer, _ = documents
    answer.organisation = "Cleaned organisation"
    invitation.extraction_status = "complete"
    save(Document, documents, data_dir)
    save(
        Consultee,
        [
            Consultee(
                remiss_url=invitation.remiss_url,
                document_url=invitation.url,
                name="Original name",
                cleaned_name="Cleaned name",
            )
        ],
        data_dir,
    )

    item["title"] = "Updated title"
    item["attachments"].append(
        {"name": "Socialstyrelsen (pdf 10 kB)", "url": "/new.pdf"}
    )
    sync_remisser([item], CODES, data_dir)
    sync_remisser([item], CODES, data_dir)

    documents = load(Document, data_dir)
    assert len(load(Remiss, data_dir)) == 1
    assert load(Remiss, data_dir)[0].title == "Updated title"
    assert len(documents) == 4
    assert documents[1].organisation == "Cleaned organisation"
    assert documents[0].extraction_status == "complete"
    assert load(Consultee, data_dir)[0].cleaned_name == "Cleaned name"


def test_source_removals_delete_attachments_and_their_derived_data(data_dir, item):
    sync_remisser([item], CODES, data_dir)
    invitation = load(Document, data_dir)[0]
    save(
        Consultee,
        [
            Consultee(
                remiss_url=invitation.remiss_url,
                document_url=invitation.url,
                name="Barnombudsmannen",
            )
        ],
        data_dir,
    )
    item["attachments"] = [item["attachments"][1]]
    sync_remisser([item], CODES, data_dir)

    assert len(load(Document, data_dir)) == 1
    assert load(Document, data_dir)[0].kind == "answer"
    assert load(Consultee, data_dir) == []


def test_refresh_reclassifies_response_as_invitation_list(data_dir, item):
    item["attachments"] = [item["attachments"][0]]
    item["attachments"][0]["name"] = "Unrecognised title"
    sync_remisser([item], CODES, data_dir)
    assert load(Document, data_dir)[0].kind == "answer"
    item["attachments"][0]["name"] = "Remissinstanser (pdf 10 kB)"
    sync_remisser([item], CODES, data_dir)

    documents = load(Document, data_dir)
    assert len(documents) == 1
    assert documents[0].kind == "consultee_list"
    assert documents[0].extraction_status == "pending"


def test_missing_optional_metadata_and_duplicate_links(data_dir, item):
    item["senders"] = []
    item["id"] = None
    item["attachments"] = [item["attachments"][1]] * 2
    sync_remisser([item], CODES, data_dir)

    remiss = load(Remiss, data_dir)[0]
    assert remiss.issuer is None
    assert remiss.diary_number is None
    assert len(load(Document, data_dir)) == 1


def test_changed_response_label_clears_stale_organisation(data_dir, item):
    sync_remisser([item], CODES, data_dir)
    documents = load(Document, data_dir)
    documents[1].organisation = "Old organisation"
    save(Document, documents, data_dir)
    item["attachments"][1]["name"] = "Corrected organisation (pdf 1 MB)"
    sync_remisser([item], CODES, data_dir)

    answer = load(Document, data_dir)[1]
    assert answer.name == "Corrected organisation"
    assert answer.organisation is None


def test_shared_attachment_keeps_separate_consultation_contexts(data_dir, item):
    second = {**item, "url": "/remisser/another/", "title": "Another consultation"}
    sync_remisser([item, second], CODES, data_dir)
    documents = load(Document, data_dir)
    assert len(documents) == 6
    assert len({(doc.remiss_url, doc.url) for doc in documents}) == 6

    sync_remisser([item], CODES, data_dir)
    assert len(load(Remiss, data_dir)) == 2
    assert len(load(Document, data_dir)) == 6


def test_download_command_imports_from_g0v(data_dir, item, monkeypatch):
    from download_data import main
    from service.downloader import Downloader

    monkeypatch.setattr(Downloader, "get_remisser", lambda: [item])
    monkeypatch.setattr(Downloader, "get_codes", lambda: CODES)
    main(data_dir)

    assert len(load(Remiss, data_dir)) == 1
    assert len(load(Document, data_dir)) == 3
