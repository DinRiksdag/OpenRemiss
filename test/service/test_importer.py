from datetime import date

import pytest

from models import Consultee, Document, Remiss
from service.importer import document_type, sync_remisser
from service.document_reviews import DOCUMENT_REVIEWS, SOURCE_EXCEPTIONS
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


@pytest.mark.parametrize(
    "label,expected",
    [
        ("Boverket.PDF", "Boverket"),
        ("Boverket.pdf", "Boverket"),
        ("Boverket.PdF (pDf 950 kB)", "Boverket"),
        ("Sveriges PDF-förening (PDF 10 kB)", "Sveriges PDF-förening"),
    ],
)
def test_pdf_name_cleanup_is_case_insensitive(data_dir, item, label, expected):
    item["attachments"] = [{"name": label, "url": "/response.pdf"}]
    sync_remisser([item], CODES, data_dir)
    assert load(Document, data_dir)[0].name == expected


@pytest.mark.parametrize(
    "name,kind",
    [
        ("PROMEMORIA.PDF (PDF 20 kB)", "other"),
        ("remissinstanser.PDF (PDF 20 kB)", "consultee_list"),
    ],
)
def test_document_classification_is_case_insensitive(data_dir, item, name, kind):
    item["attachments"] = [{"name": name, "url": "/attachment.pdf"}]
    sync_remisser([item], CODES, data_dir)
    assert load(Document, data_dir)[0].kind == kind


def test_refresh_preserves_skipped_status(data_dir, item):
    sync_remisser([item], CODES, data_dir)
    documents = load(Document, data_dir)
    documents[0].extraction_status = "skipped"
    documents[0].extraction_error = "Unsupported non-PDF document"
    save(Document, documents, data_dir)
    sync_remisser([item], CODES, data_dir)
    assert load(Document, data_dir)[0].extraction_status == "skipped"
    assert (
        load(Document, data_dir)[0].extraction_error == "Unsupported non-PDF document"
    )


@pytest.mark.parametrize(
    "name,expected",
    [
        (
            "Myndigheten för säkerhet och integritetsskydd "
            "(Säkerhets- och integritetsskyddsnämnden i remisslistan)",
            "answer",
        ),
        ("Förbundet FÖR delaktighet och jämlikhet (utanför remisslistan)", "answer"),
        ("Utom remisslistan_Skytten Fastighets AB", "answer"),
        ("Bilaga till remissmissiv - förordningsförslag", "other"),
        ("Ytterligare remissinstanser som avstått från att lämna synpunkter", "other"),
        ("Ytterligare remissinstanser som avstår från att lämna synpunkter", "other"),
        (
            "Remissinstanser för betänkandet Tillträdesförbud (SOU 2026:48)",
            "consultee_list",
        ),
        (
            "Komplettering av remissinstans - Länsstyrelsen i Norrbottens län",
            "consultee_list",
        ),
        ("Remissmissiv", "consultee_list"),
        ("Remisslista (komplettering)", "consultee_list"),
        ("Remissmissinstanser för promemorian Kraftfullare åtgärder", "consultee_list"),
        ("Remissinstaner för promemorian Utfasning av ersättning", "consultee_list"),
        ("Remissbrev Ds 2025:13 Rätt att installera laddpunkt hemma", "consultee_list"),
        ("Remissinbjudan", "consultee_list"),
        (
            "Remittering av promemorian Kompletterande författningsförslag",
            "consultee_list",
        ),
        ("Remiss Promemoria om ersättning för digitala vårdmöten", "consultee_list"),
        ("Inbjudan till remissmöte om digitalt grönt intyg", "consultee_list"),
        ("Inbjudan till lärosätena att inkomma med underlag", "consultee_list"),
        ("Inbjudan om yttrande om Europeiska kommissionens förslag", "consultee_list"),
        ("Inbjudan hearing SOU 2017:28", "other"),
        ("00 Remiss Promemoria Swedpartnership", "other"),
        ("SOU 2016_27 Som ett brev på posten", "other"),
        ("Remissvar - Promemoria gällande uppgiftsskyldighet", "answer"),
        ("A2017-01158-ARM_svar_nr_015_Kronofogdemyndigheten - Promemoria", "answer"),
        (
            "Betänkande av Klimatanpassningsutredningen SOU 2017:42 Vem har ansvaret?",
            "other",
        ),
        ("Betänkandet Ett stärkt skydd", "other"),
        ("Stockholms kommun - remissvar över betänkandet", "answer"),
        (
            "Remiss av SOU 2018:82 Kompletteringar till den nya säkerhetsskyddslagen",
            "consultee_list",
        ),
    ],
)
def test_document_classification_for_reviewed_attachment_labels(name, expected):
    assert document_type(name) == expected


def test_refresh_reclassifies_report_and_clears_organisation(data_dir, item):
    label = "Betänkande av Klimatanpassningsutredningen SOU 2017:42 Vem har ansvaret?"
    item["attachments"] = [{"name": label, "url": "/betankande.pdf"}]
    save(
        Document,
        [
            Document(
                remiss_url="https://www.regeringen.se" + item["url"],
                url="https://www.regeringen.se/betankande.pdf",
                name=label,
                kind="answer",
                organisation=label,
            )
        ],
        data_dir,
    )
    sync_remisser([item], CODES, data_dir)
    stored = load(Document, data_dir)[0]
    assert stored.kind == "other"
    assert stored.organisation is None


@pytest.mark.parametrize(
    "review",
    [r for r in DOCUMENT_REVIEWS.values() if not r.get("exclude_by_default", False)],
)
def test_reviewed_valid_documents_use_their_type_without_being_excluded(
    data_dir, item, review
):
    item["attachments"] = [{"url": review["url"], "name": review["label"]}]
    sync_remisser([item], CODES, data_dir)
    stored = load(Document, data_dir)[0]
    assert stored.kind == review["kind"]
    assert stored.organisation == review.get("organisation")


def test_refresh_corrects_false_invitation_and_removes_derived_names(data_dir, item):
    item["attachments"] = [
        {"name": "Utom remisslistan_Skytten Fastighets AB", "url": "/response.pdf"}
    ]
    document = Document(
        remiss_url="https://www.regeringen.se" + item["url"],
        url="https://www.regeringen.se/response.pdf",
        name=item["attachments"][0]["name"],
        kind="consultee_list",
        extraction_status="failed",
        extraction_error="No invitation list could be extracted",
    )
    save(Document, [document], data_dir)
    save(
        Consultee,
        [
            Consultee(
                remiss_url=document.remiss_url,
                document_url=document.url,
                name="Incorrect",
            )
        ],
        data_dir,
    )

    sync_remisser([item], CODES, data_dir)

    stored = load(Document, data_dir)[0]
    assert stored.kind == "answer"
    assert stored.extraction_status is None
    assert stored.extraction_error is None
    assert load(Consultee, data_dir) == []


def test_source_exception_is_excluded_or_included_with_reviewed_type(
    data_dir, item, caplog
):
    exception = next(iter(SOURCE_EXCEPTIONS.values()))
    item["attachments"] = [{"name": exception["label"], "url": exception["url"]}]

    sync_remisser([item], CODES, data_dir)
    assert load(Document, data_dir) == []
    assert exception["url"] in caplog.text
    assert exception["reason"] in caplog.text

    sync_remisser([item], CODES, data_dir, include_source_exceptions=True)
    document = load(Document, data_dir)[0]
    assert document.url == exception["url"]
    assert document.name == exception["label"]
    assert document.kind == exception["kind"] == "other"
    assert document.extraction_status is None

    sync_remisser([item], CODES, data_dir)
    assert load(Document, data_dir) == []


def test_download_command_can_include_source_exceptions(data_dir, item, monkeypatch):
    from download_data import main
    from service.downloader import Downloader

    exception = next(iter(SOURCE_EXCEPTIONS.values()))
    item["attachments"] = [{"name": exception["label"], "url": exception["url"]}]
    monkeypatch.setattr(Downloader, "get_remisser", lambda: [item])
    monkeypatch.setattr(Downloader, "get_codes", lambda: CODES)

    main(data_dir, include_source_exceptions=True)

    assert load(Document, data_dir)[0].kind == "other"


@pytest.mark.parametrize(
    "name",
    [
        "Remiss Socialstyrelsens rapport Rättsliga anpassningar till EUs humanmaterialförordning",
        "Remiss Ds 2026:19 Utökad tillsyn över barn",
        "Remiss: Ökade möjligheter till modersmålsundervisning",
        "Remiss, Förstärkt rehabilitering för återgång i arbete",
        "Remiss-Förslag till lag om ersättning",
        "Remisslinstanser för Ny lag om koordineringsinsatser",
        "Remissminstanser för Boverkets förslag",
        "Remissinsatnaser för Transportstyrelsens redovisning",
        "Remissintstanser för förslag till direktiv",
        "Remissinsatser: Nya skatteregler för företagssektorn",
        "Remissmisiv Ytterligare anpassningar",
        "Remissmisslista Vägen mot fossiloberoende jordbruk",
    ],
)
def test_missed_invitation_title_patterns_found_by_remiss_query(name):
    assert document_type(name) == "consultee_list"


@pytest.mark.parametrize(
    "name",
    [
        "Utkast till lagrådsremiss Statlig ersättning för personskada",
        "Remissdokument: Underlag till beredningen av nytt mediestöd",
        "Remiss Förlängd remisstid Frågor kring 2009 års renskötselkonvention",
    ],
)
def test_supporting_documents_found_by_remiss_query(name):
    assert document_type(name) == "other"
