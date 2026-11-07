import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from database import base


@pytest.fixture
def session(monkeypatch):
    engine = create_engine("sqlite:///:memory:")
    base.Base.metadata.create_all(engine)
    sessions = scoped_session(sessionmaker(bind=engine))
    monkeypatch.setattr(base, "engine", engine)
    monkeypatch.setattr(base, "db_session", sessions)
    try:
        yield sessions()
    finally:
        sessions.remove()
        engine.dispose()
