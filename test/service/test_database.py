import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from api.schema import schema
from database import base
from database.answer import Answer
from database.consultee import Consultee
from database.remiss import Remiss
from service.database import Database


@pytest.fixture
def session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    base.Base.metadata.create_all(engine)
    sessions = scoped_session(sessionmaker(bind=engine))
    monkeypatch.setattr(base, "db_session", sessions)
    try:
        yield sessions()
    finally:
        sessions.remove()
        engine.dispose()


def test_query_returns_usable_query(session):
    session.add(Remiss(title="Example consultation"))
    session.commit()

    assert Database.query(Remiss).one().title == "Example consultation"


def test_graphql_answers_use_database_query(session):
    session.add(Answer(organisation="Barnombudsmannen"))
    session.commit()

    result = schema.execute("{ answers { organisation } }")

    assert result.errors is None
    assert result.data == {"answers": [{"organisation": "Barnombudsmannen"}]}


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
