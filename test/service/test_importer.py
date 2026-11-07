from datetime import date

import pytest

from database import Answer, Consultee, ConsulteeList, Document, File, Remiss
from service.importer import sync_remisser

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


def test_import_maps_g0v_metadata_and_attachment_types(session, item):
    assert sync_remisser([item], CODES, session) == 1
    session.commit()

    remiss = session.query(Remiss).one()
    assert remiss.title == item["title"]
    assert remiss.published_on == date(2026, 11, 6)
    assert remiss.issuer == "Justitiedepartementet"
    assert remiss.diary_number == "Ju2026/02439"
    assert remiss.url == "https://www.regeringen.se" + item["url"]
    assert session.query(Document).count() == 3
    assert session.query(ConsulteeList).count() == 1
    assert session.query(Answer).count() == 1
    assert session.query(Answer).one().files[0].name == "Barnombudsmannen"
    assert session.query(Answer).one().files[0].url.endswith("/barnombudsmannen/")
    assert {file.name for file in session.query(File)} == {
        "Remissinstanser Lyssna på barnet!",
        "Barnombudsmannen",
        "Promemoria",
    }


def test_refresh_adds_responses_without_an_updated_date_and_preserves_derived_data(
    session, item
):
    sync_remisser([item], CODES, session)
    session.commit()
    remiss_id = session.query(Remiss).one().id
    answer = session.query(Answer).one()
    answer.organisation = "Cleaned organisation"
    answer_id = answer.id
    invitation = session.query(ConsulteeList).one()
    invitation.consultee_list = [
        Consultee(name="Original name", cleaned_name="Cleaned name")
    ]
    session.commit()

    item["title"] = "Updated title"
    item["attachments"].append(
        {"name": "Socialstyrelsen (pdf 10 kB)", "url": "/new.pdf"}
    )
    sync_remisser([item], CODES, session)
    session.commit()
    sync_remisser([item], CODES, session)
    session.commit()
    session.expire_all()

    assert session.query(Remiss).one().id == remiss_id
    assert session.query(Remiss).one().title == "Updated title"
    assert session.query(Document).count() == 4
    assert (
        session.query(Answer).filter_by(id=answer_id).one().organisation
        == "Cleaned organisation"
    )
    assert session.query(Consultee).one().cleaned_name == "Cleaned name"


def test_source_removals_delete_attachments_and_their_derived_data(session, item):
    sync_remisser([item], CODES, session)
    session.commit()
    invitation = session.query(ConsulteeList).one()
    invitation.consultee_list = [Consultee(name="Barnombudsmannen")]
    session.commit()

    item["attachments"] = [item["attachments"][1]]
    sync_remisser([item], CODES, session)
    session.commit()

    assert session.query(Document).count() == 1
    assert session.query(Answer).count() == 1
    assert session.query(File).count() == 1
    assert session.query(ConsulteeList).count() == 0
    assert session.query(Consultee).count() == 0


def test_refresh_reclassifies_legacy_response_as_invitation_list(session, item):
    item["attachments"] = [item["attachments"][0]]
    item["attachments"][0]["name"] = "Unrecognised title"
    sync_remisser([item], CODES, session)
    session.commit()
    assert session.query(Answer).count() == 1

    item["attachments"][0]["name"] = "Remissinstanser (pdf 10 kB)"
    sync_remisser([item], CODES, session)
    session.commit()

    assert session.query(Answer).count() == 0
    assert session.query(ConsulteeList).count() == 1
    assert session.query(Document).count() == 1
    assert session.query(File).count() == 1


def test_missing_optional_metadata_and_duplicate_links(session, item):
    item["senders"] = []
    item["id"] = None
    item["attachments"] = [item["attachments"][1]] * 2
    sync_remisser([item], CODES, session)
    session.commit()

    remiss = session.query(Remiss).one()
    assert remiss.issuer is None
    assert remiss.diary_number is None
    assert session.query(Document).count() == 1


def test_changed_response_label_clears_stale_organisation(session, item):
    sync_remisser([item], CODES, session)
    session.commit()
    answer = session.query(Answer).one()
    answer.organisation = "Old organisation"
    answer_id = answer.id
    session.commit()

    item["attachments"][1]["name"] = "Corrected organisation (pdf 1 MB)"
    sync_remisser([item], CODES, session)
    session.commit()

    answer = session.query(Answer).one()
    assert answer.id == answer_id
    assert answer.files[0].name == "Corrected organisation"
    assert answer.organisation is None


def test_download_command_imports_from_g0v(session, item, monkeypatch):
    from download_data import main
    from service.downloader import Downloader

    monkeypatch.setattr(Downloader, "get_remisser", lambda: [item])
    monkeypatch.setattr(Downloader, "get_codes", lambda: CODES)
    main()

    assert session.query(Remiss).count() == 1
    assert session.query(Document).count() == 3
