from database.answer import Answer
from database.consultee import Consultee
from database.consultee_list import ConsulteeList
from database.file import File
from database.remiss import Remiss
from service.database import Database


def test_query_returns_usable_query(session):
    session.add(Remiss(title="Example consultation"))
    session.commit()

    assert Database.query(Remiss).one().title == "Example consultation"


def test_consultation_documents_are_queryable(session):
    remiss = Remiss(title="Example consultation")
    session.add_all(
        [
            remiss,
            Answer(
                remiss=remiss,
                organisation="Barnombudsmannen",
                files=[File(name="Response", url="https://example.org/response.pdf")],
            ),
            ConsulteeList(
                remiss=remiss,
                consultee_list=[Consultee(name="Barnombudsmannen")],
            ),
        ]
    )
    session.commit()

    saved = Database.query(Remiss).one()
    assert saved.answers[0].organisation == "Barnombudsmannen"
    assert saved.answers[0].files[0].url == "https://example.org/response.pdf"
    assert saved.consultees.consultee_list[0].name == "Barnombudsmannen"


def test_empty_column_updates_records(session):
    session.add(Consultee(name="Original name", cleaned_name="Cleaned name"))
    session.commit()

    Database.empty_column(Consultee, Consultee.cleaned_name)
    session.commit()

    assert session.query(Consultee).one().cleaned_name is None


def test_popular_names_groups_organisations(session):
    session.add_all(
        [
            Consultee(cleaned_name="Barnombudsmannen"),
            Consultee(cleaned_name="Barnombudsmannen"),
            Consultee(cleaned_name="Stockholms universitet"),
        ]
    )
    session.commit()

    assert Database.get_popular_names(100) == [
        ("Stockholms universitet", 1),
        ("Barnombudsmannen", 2),
    ]
