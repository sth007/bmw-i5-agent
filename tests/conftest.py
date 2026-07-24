from __future__ import annotations

import os
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database.test_database import ensure_database_exists, require_test_database_url

APPLICATION_DATABASE_URL = os.getenv("DATABASE_URL")
TEST_DATABASE_URL = require_test_database_url()
ensure_database_exists(TEST_DATABASE_URL, admin_database_url=APPLICATION_DATABASE_URL)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from fastapi.testclient import TestClient

from app.database.base import Base
from app.database.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(TEST_DATABASE_URL, future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    with db_engine.begin() as setup_connection:
        Base.metadata.drop_all(setup_connection)
        Base.metadata.create_all(setup_connection)

    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, future=True, expire_on_commit=False)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session_, transaction_):
        if transaction_.nested and not transaction_._parent.nested:
            session_.begin_nested()

    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
