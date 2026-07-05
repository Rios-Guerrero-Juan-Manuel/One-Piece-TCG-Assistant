import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.persistence import session as sess_module
from app.infrastructure.persistence.models import Base
from app.presentation.main import app


@pytest.fixture
def test_db():
    """Create a temp file SQLite DB for tests that need real DB access."""
    db_path = os.path.join(tempfile.gettempdir(), f"test_{os.urandom(8).hex()}.db")

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    original_engine = sess_module.engine
    original_session_local = sess_module.SessionLocal

    sess_module.engine = engine
    sess_module.SessionLocal = session_factory

    session = session_factory()
    try:
        yield session, session_factory
    finally:
        session.close()
        sess_module.engine = original_engine
        sess_module.SessionLocal = original_session_local
        # Dispose engine before deleting file
        engine.dispose()
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
        except PermissionError:
            pass  # Ignore cleanup errors on Windows


@pytest.fixture
def db_session(test_db):
    """Return the session."""
    return test_db[0]


@pytest.fixture
def session_factory(test_db):
    """Return the session factory."""
    return test_db[1]


@pytest.fixture
def client(test_db):
    """TestClient with temp file DB."""
    session, session_factory = test_db

    from app.infrastructure.persistence.session import get_db

    def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
